"""
Phase 13 Step D: HMM/Viterbi Offset Path Solver

Core diagnostic: replaces "overall oracle %" with alignment-grade analysis.

Model:
- Observations: match (1) or mismatch (0) at each Cipher 2 position
- Hidden state: integer offset s_t in range [-K, +K]
- Emission: P(match|s) = p_match, P(mismatch|s) = 1 - p_match
- Transition: P(s_t=s_{t-1}) high, small jumps moderate, large jumps rare

Algorithm: Viterbi to find best offset path and log-likelihood

Outputs:
- offset path over all positions
- number of jumps, jump locations
- max |offset|
- log-likelihood (quality metric)
- plot CSV for visualization
"""

import json
import csv
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import math
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import load_cipher2, load_cipher2_known_plaintext


class HMMOffsetSolver:
    """
    HMM-based offset path solver for Cipher 2 oracle.
    
    Finds the most likely sequence of offsets that explains the
    observed match/mismatch pattern.
    """
    
    def __init__(self, K: int = 50, p_match: float = 0.9, 
                 p_stay: float = 0.995, p_small_jump: float = 0.004):
        """
        Initialize HMM parameters.
        
        Args:
            K: Maximum absolute offset (state space: -K to +K)
            p_match: Probability of match given correct offset
            p_stay: Probability of staying at same offset
            p_small_jump: Total probability mass for ±1 jumps
        """
        self.K = K
        self.p_match = p_match
        self.p_mismatch = 1.0 - p_match
        
        # Transition probabilities
        self.p_stay = p_stay
        self.p_small_jump = p_small_jump / 2  # Split between +1 and -1
        self.p_large_jump = (1.0 - p_stay - 2 * self.p_small_jump)  # Remaining mass
        
        # State space: offsets from -K to +K
        self.states = list(range(-K, K + 1))
        self.num_states = len(self.states)
    
    def emission_prob(self, observation: int, state: int) -> float:
        """
        Emission probability: P(observation | state)
        
        Args:
            observation: 1 (match) or 0 (mismatch)
            state: offset value
        
        Returns:
            Probability
        """
        if observation == 1:
            return self.p_match
        else:
            return self.p_mismatch
    
    def transition_prob(self, from_state: int, to_state: int) -> float:
        """
        Transition probability: P(to_state | from_state)
        
        High probability to stay, moderate for ±1, low for larger jumps.
        """
        jump = abs(to_state - from_state)
        
        if jump == 0:
            return self.p_stay
        elif jump == 1:
            return self.p_small_jump
        else:
            # Spread remaining mass over large jumps
            # Could use geometric decay, but uniform for simplicity
            num_large_jumps = 2 * self.K - 2  # Total large jumps possible
            if num_large_jumps > 0:
                return self.p_large_jump / num_large_jumps
            else:
                return 0.0
    
    def viterbi(self, observations: List[int]) -> Tuple[List[int], float]:
        """
        Viterbi algorithm: find most likely state sequence.
        
        Args:
            observations: List of 0/1 (mismatch/match)
        
        Returns:
            (best_path, log_likelihood)
            best_path: List of offset values (same length as observations)
            log_likelihood: Log probability of best path
        """
        T = len(observations)
        
        # Initialize DP tables
        # viterbi[t][s] = max log-prob of path ending at state s at time t
        # backpointer[t][s] = state at t-1 that maximizes viterbi[t][s]
        viterbi = np.full((T, self.num_states), -np.inf)
        backpointer = np.zeros((T, self.num_states), dtype=int)
        
        # Initial distribution: uniform over all offsets
        # (could refine: prefer offset 0 or fit from data)
        init_prob = 1.0 / self.num_states
        
        for s in range(self.num_states):
            emission = self.emission_prob(observations[0], self.states[s])
            viterbi[0, s] = math.log(init_prob + 1e-10) + math.log(emission + 1e-10)
        
        # Forward pass
        for t in range(1, T):
            for s in range(self.num_states):
                emission = self.emission_prob(observations[t], self.states[s])
                log_emission = math.log(emission + 1e-10)
                
                # Find best previous state
                max_prob = -np.inf
                best_prev = 0
                
                for s_prev in range(self.num_states):
                    trans = self.transition_prob(self.states[s_prev], self.states[s])
                    log_trans = math.log(trans + 1e-10)
                    
                    prob = viterbi[t-1, s_prev] + log_trans + log_emission
                    
                    if prob > max_prob:
                        max_prob = prob
                        best_prev = s_prev
                
                viterbi[t, s] = max_prob
                backpointer[t, s] = best_prev
        
        # Backward pass: reconstruct best path
        best_path = []
        
        # Find best final state
        best_final_s = np.argmax(viterbi[T-1, :])
        best_path.append(self.states[best_final_s])
        log_likelihood = viterbi[T-1, best_final_s]
        
        # Trace back
        current_s = best_final_s
        for t in range(T-1, 0, -1):
            current_s = backpointer[t, current_s]
            best_path.append(self.states[current_s])
        
        best_path.reverse()
        
        return best_path, log_likelihood
    
    def analyze_path(self, path: List[int]) -> Dict:
        """
        Analyze offset path for structural features.
        
        Returns:
            Dict with: n_jumps, jump_positions, max_offset, mean_offset, etc.
        """
        jumps = []
        jump_positions = []
        
        for i in range(1, len(path)):
            if path[i] != path[i-1]:
                jump_size = path[i] - path[i-1]
                jumps.append(jump_size)
                jump_positions.append(i)
        
        return {
            "n_jumps": len(jumps),
            "jump_positions": jump_positions,
            "jump_sizes": jumps,
            "max_offset": max(abs(s) for s in path),
            "mean_offset": sum(path) / len(path) if path else 0.0,
            "median_offset": sorted(path)[len(path) // 2] if path else 0.0
        }


def build_observations(doi_tokens: List[str], cipher2_numbers: List[int], 
                      known_plaintext: str, offset: int = 0) -> List[int]:
    """
    Build observation sequence: 1 if match, 0 if mismatch.
    
    Args:
        doi_tokens: DOI word list
        cipher2_numbers: Cipher 2 number sequence
        known_plaintext: Known Cipher 2 plaintext
        offset: Constant offset to apply (default: 0, used for oracle baseline)
    
    Returns:
        List of 0/1 observations
    """
    known_clean = ''.join(c.upper() for c in known_plaintext if c.isalpha())
    
    observations = []
    
    for i, cipher_num in enumerate(cipher2_numbers):
        if i >= len(known_clean):
            break
        
        # Apply offset
        effective_num = cipher_num + offset
        word_idx = effective_num - 1
        
        # Extract letter
        if 0 <= word_idx < len(doi_tokens) and doi_tokens[word_idx]:
            extracted = doi_tokens[word_idx][0].upper()
        else:
            extracted = '?'
        
        # Compare
        expected = known_clean[i]
        observations.append(1 if extracted == expected else 0)
    
    return observations


def solve_hmm_offset_path(doi_tokens: List[str], edition_id: str, tokenizer_name: str,
                          K: int = 50) -> Dict:
    """
    Solve HMM offset path for a given edition/tokenizer.
    
    Returns:
        Dict with path, log_likelihood, jumps, etc.
    """
    # Load Cipher 2 and known plaintext
    cipher2 = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    print(f"  Edition: {edition_id}")
    print(f"  Tokenizer: {tokenizer_name}")
    print(f"  Cipher 2 length: {len(cipher2)}")
    print(f"  Known plaintext length: {len(known_plaintext)} chars")
    
    # Build observations (offset=0 baseline)
    observations = build_observations(doi_tokens, cipher2, known_plaintext, offset=0)
    
    print(f"  Observations: {len(observations)}")
    print(f"  Matches: {sum(observations)}/{len(observations)} ({sum(observations)/len(observations)*100:.2f}%)")
    
    # Solve HMM
    print(f"  Running Viterbi (K={K})...")
    solver = HMMOffsetSolver(K=K)
    path, log_likelihood = solver.viterbi(observations)
    
    # Analyze path
    analysis = solver.analyze_path(path)
    
    print(f"  Log-likelihood: {log_likelihood:.2f}")
    print(f"  Jumps: {analysis['n_jumps']}")
    print(f"  Max |offset|: {analysis['max_offset']}")
    print(f"  Mean offset: {analysis['mean_offset']:.2f}")
    
    return {
        "edition_id": edition_id,
        "tokenizer_name": tokenizer_name,
        "path": path,
        "observations": observations,
        "log_likelihood": log_likelihood,
        "analysis": analysis,
        "K": K,
        "solved_at": datetime.now().isoformat()
    }


def save_hmm_results(result: Dict, output_dir: Path):
    """
    Save HMM results to:
    - output/phase13/oracle_hmm/<edition>_<tokenizer>.json
    - output/phase13/oracle_hmm/<edition>_<tokenizer>_plot.csv
    """
    hmm_dir = output_dir / "oracle_hmm"
    hmm_dir.mkdir(parents=True, exist_ok=True)
    
    edition_id = result["edition_id"]
    tokenizer_name = result["tokenizer_name"]
    
    # Save JSON (without full path to save space)
    json_file = hmm_dir / f"{edition_id}_{tokenizer_name}.json"
    json_data = {
        "edition_id": edition_id,
        "tokenizer_name": tokenizer_name,
        "log_likelihood": result["log_likelihood"],
        "K": result["K"],
        "analysis": result["analysis"],
        "solved_at": result["solved_at"],
        "path_summary": {
            "length": len(result["path"]),
            "mean": result["analysis"]["mean_offset"],
            "median": result["analysis"]["median_offset"],
            "max_abs": result["analysis"]["max_offset"]
        }
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"  Saved JSON: {json_file}")
    
    # Save plot CSV
    csv_file = hmm_dir / f"{edition_id}_{tokenizer_name}_plot.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["position", "match", "offset"])
        
        for i, (obs, offset) in enumerate(zip(result["observations"], result["path"])):
            writer.writerow([i, obs, offset])
    
    print(f"  Saved plot CSV: {csv_file}")
    
    return json_file


def run_hmm_oracle_sweep(edition_ids: List[str], tokenizer_names: List[str],
                        corpus_dir: Path = None, output_dir: Path = None,
                        K: int = 50):
    """
    Run HMM offset solver for multiple edition/tokenizer pairs.
    
    Typically run on cluster representatives × top tokenizers.
    """
    if corpus_dir is None:
        corpus_dir = Path("corpus")
    if output_dir is None:
        output_dir = Path("output/phase13")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("PHASE 13 STEP D: HMM/VITERBI OFFSET PATH SOLVER")
    print("=" * 80)
    print(f"\nEditions: {len(edition_ids)}")
    print(f"Tokenizers: {len(tokenizer_names)}")
    print(f"Total combinations: {len(edition_ids) * len(tokenizer_names)}")
    print(f"Offset range: [-{K}, +{K}]")
    print()
    
    results = []
    
    for edition_id in edition_ids:
        print(f"\n[Edition: {edition_id}]")
        
        for tokenizer_name in tokenizer_names:
            print(f"\n  [Tokenizer: {tokenizer_name}]")
            
            # Load tokens
            tokens_file = corpus_dir / "locked_candidates" / edition_id / tokenizer_name / "tokens.json"
            
            if not tokens_file.exists():
                print(f"  [SKIP] Tokens not found: {tokens_file}")
                continue
            
            with open(tokens_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            doi_tokens = data.get("tokens", [])
            
            if not doi_tokens:
                print(f"  [SKIP] Empty tokens")
                continue
            
            # Solve HMM
            result = solve_hmm_offset_path(doi_tokens, edition_id, tokenizer_name, K)
            
            # Save results
            save_hmm_results(result, output_dir)
            
            results.append(result)
            print()
    
    print("=" * 80)
    print("HMM ORACLE SUMMARY")
    print("=" * 80)
    print(f"Solved: {len(results)} combinations")
    
    if results:
        log_likelihoods = [r["log_likelihood"] for r in results]
        print(f"\nLog-likelihood statistics:")
        print(f"  Best: {max(log_likelihoods):.2f}")
        print(f"  Worst: {min(log_likelihoods):.2f}")
        print(f"  Mean: {sum(log_likelihoods) / len(log_likelihoods):.2f}")
    
    print("\nNext step: Run phase13_changepoints for breakpoint detection")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 13 Step D: HMM Offset Solver")
    parser.add_argument('--corpus-dir', default='corpus', help='Corpus directory')
    parser.add_argument('--output-dir', default='output/phase13', help='Output directory')
    parser.add_argument('--editions', nargs='+', required=True, help='Edition IDs to solve')
    parser.add_argument('--tokenizers', nargs='+', default=['hyphen_keep'], 
                       help='Tokenizer names')
    parser.add_argument('--K', type=int, default=50, help='Max offset magnitude')
    
    args = parser.parse_args()
    
    run_hmm_oracle_sweep(args.editions, args.tokenizers, 
                        Path(args.corpus_dir), Path(args.output_dir), args.K)
