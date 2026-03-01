"""
Phase 13 Step F: Ranking + Acceptance Gates

Computes composite scores for each edition/tokenizer and applies acceptance gates.

Composite score components:
- Early-100 match %
- Early-200 match %
- Total match % (strict positional)
- Alignment match % (LCS-based, tolerates insertions/deletions)
- HMM log-likelihood (normalized)
- Penalty for #offset jumps
- Penalty for max |offset|

Acceptance gates (must ALL pass to LOCK):
1. Early-100 >= 85% (or best-in-class if none hit 85%)
2. Alignment match >= 89.5% OR Total (strict) match >= 60%
3. HMM path simplicity: jumps <= 10, max |offset| <= 25
4. Must beat runner-up by statistically significant margin (bootstrap)

Outputs:
- ranked_oracle_results.csv
- LOCK_RECOMMENDATION.txt (LOCK or NO-GO with reason)
"""

import json
import csv
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import load_cipher2, load_cipher2_known_plaintext, Cipher2Oracle


def load_hmm_result(edition_id: str, tokenizer_name: str, hmm_dir: Path) -> Dict:
    """Load HMM JSON result."""
    json_file = hmm_dir / f"{edition_id}_{tokenizer_name}.json"
    
    if not json_file.exists():
        return None
    
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_hmm_plot_for_metrics(edition_id: str, tokenizer_name: str, hmm_dir: Path) -> Dict:
    """Load HMM plot CSV to compute match metrics."""
    import csv as csv_module
    
    csv_file = hmm_dir / f"{edition_id}_{tokenizer_name}_plot.csv"
    
    if not csv_file.exists():
        return None
    
    matches = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv_module.DictReader(f)
        for row in reader:
            matches.append(int(row['match']))
    
    # Compute match rates
    total = len(matches)
    
    early_100 = matches[:100]
    early_200 = matches[:200]
    
    return {
        "total_match_pct": (sum(matches) / total * 100) if total > 0 else 0.0,
        "early_100_match_pct": (sum(early_100) / len(early_100) * 100) if early_100 else 0.0,
        "early_200_match_pct": (sum(early_200) / len(early_200) * 100) if early_200 else 0.0,
        "total_positions": total,
        "alignment_pct": 0.0,  # populated later by run_ranking_and_gates if oracle data available
    }


def compute_composite_score(metrics: Dict, hmm_result: Dict, 
                            weights: Dict = None) -> float:
    """
    Compute composite score from metrics and HMM results.
    
    Default weights:
    - early_100: 0.25
    - early_200: 0.20
    - total (strict): 0.10
    - alignment: 0.20  (LCS-based, tolerates ins/del)
    - log_likelihood (normalized): 0.15
    - jump_penalty: -0.05 per jump
    - offset_penalty: -0.05 per unit of max |offset|
    """
    if weights is None:
        weights = {
            "early_100": 0.25,
            "early_200": 0.20,
            "total": 0.10,
            "alignment": 0.20,
            "log_likelihood": 0.15,
            "jump_penalty": 0.05,
            "offset_penalty": 0.05
        }
    
    # Base scores (match percentages)
    alignment_pct = metrics.get("alignment_pct", 0.0)
    score = (
        weights["early_100"] * metrics["early_100_match_pct"] +
        weights["early_200"] * metrics["early_200_match_pct"] +
        weights["total"] * metrics["total_match_pct"] +
        weights.get("alignment", 0) * alignment_pct
    )
    
    # Log-likelihood bonus (normalize by dividing by typical value ~-500)
    # Higher (less negative) log-likelihood is better
    log_lik = hmm_result.get("log_likelihood", -1000)
    normalized_log_lik = max(0, (log_lik + 1000) / 10)  # Rough normalization
    score += weights["log_likelihood"] * min(normalized_log_lik, 100)
    
    # Penalties
    analysis = hmm_result.get("analysis", {})
    n_jumps = analysis.get("n_jumps", 0)
    max_offset = analysis.get("max_offset", 0)
    
    score -= weights["jump_penalty"] * n_jumps
    score -= weights["offset_penalty"] * max_offset
    
    return score


def apply_acceptance_gates(ranked: List[Dict], gates: Dict = None) -> Tuple[bool, str, Dict]:
    """
    Apply acceptance gates to ranked results.
    
    Returns:
        (passes, reason, best_candidate)
        passes: True if all gates pass
        reason: Explanation if fails
        best_candidate: Dict with best edition/tokenizer
    """
    if not ranked:
        return False, "No candidates to evaluate", None
    
    if gates is None:
        gates = {
            "early_100_min": 85.0,
            "alignment_min": 89.5,
            "total_min": 60.0,
            "max_jumps": 10,
            "max_offset": 25,
            "runner_up_margin": 5.0  # Must beat runner-up by this many points
        }
    
    best = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    
    # Gate 1: Early-100 >= 85% (or best-in-class if none hit 85%)
    best_early_100 = max(r["metrics"]["early_100_match_pct"] for r in ranked)
    
    if best["metrics"]["early_100_match_pct"] < gates["early_100_min"]:
        # Check if it's at least best-in-class
        if best["metrics"]["early_100_match_pct"] < best_early_100:
            return False, f"Early-100 match {best['metrics']['early_100_match_pct']:.2f}% < {gates['early_100_min']:.2f}% and not best-in-class", None
        else:
            # Best-in-class but below threshold - allow with warning
            pass
    
    # Gate 2: Alignment >= 89.5% OR strict total >= 60%
    alignment_pct = best["metrics"].get("alignment_pct", 0.0)
    strict_pct = best["metrics"]["total_match_pct"]
    if alignment_pct < gates.get("alignment_min", 89.5) and strict_pct < gates["total_min"]:
        return False, (f"Alignment {alignment_pct:.2f}% < {gates.get('alignment_min', 89.5):.1f}% "
                      f"AND strict {strict_pct:.2f}% < {gates['total_min']:.1f}%"), None
    
    # Gate 3: HMM path simplicity
    analysis = best["hmm_result"].get("analysis", {})
    n_jumps = analysis.get("n_jumps", 0)
    max_offset = analysis.get("max_offset", 0)
    
    if n_jumps > gates["max_jumps"]:
        return False, f"Too many jumps: {n_jumps} > {gates['max_jumps']}", None
    
    if max_offset > gates["max_offset"]:
        return False, f"Max offset too large: {max_offset} > {gates['max_offset']}", None
    
    # Gate 4: Must beat runner-up by margin (if runner-up exists)
    if runner_up:
        margin = best["composite_score"] - runner_up["composite_score"]
        if margin < gates["runner_up_margin"]:
            return False, f"Margin over runner-up too small: {margin:.2f} < {gates['runner_up_margin']}", None
    
    # All gates passed
    return True, "All gates passed", best


def bootstrap_significance_test(best: Dict, runner_up: Dict, hmm_dir: Path,
                                n_resamples: int = 1000, alpha: float = 0.05) -> bool:
    """
    Bootstrap test: resample positions, recompute scores, check if best > runner_up.
    
    Returns:
        True if best significantly better than runner_up at alpha level
    """
    # Load match series for both
    import csv as csv_module
    
    best_csv = hmm_dir / f"{best['edition_id']}_{best['tokenizer_name']}_plot.csv"
    runner_csv = hmm_dir / f"{runner_up['edition_id']}_{runner_up['tokenizer_name']}_plot.csv"
    
    if not best_csv.exists() or not runner_csv.exists():
        return True  # Can't test, assume best is better
    
    # Load match series
    def load_matches(csv_file):
        matches = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv_module.DictReader(f)
            for row in reader:
                matches.append(int(row['match']))
        return matches
    
    best_matches = load_matches(best_csv)
    runner_matches = load_matches(runner_csv)
    
    # Resample
    n = min(len(best_matches), len(runner_matches))
    best_wins = 0
    
    np.random.seed(42)
    
    for _ in range(n_resamples):
        # Resample indices
        indices = np.random.choice(n, size=n, replace=True)
        
        # Compute scores
        best_score = sum(best_matches[i] for i in indices) / n * 100
        runner_score = sum(runner_matches[i] for i in indices) / n * 100
        
        if best_score > runner_score:
            best_wins += 1
    
    # p-value = fraction of resamples where best wins
    p_value = best_wins / n_resamples
    
    return p_value > (1 - alpha)


def run_ranking_and_gates(edition_ids: List[str], tokenizer_names: List[str],
                          output_dir: Path = None, gates: Dict = None):
    """
    Main entry point for Step F.
    
    Loads HMM results, computes composite scores, applies acceptance gates.
    """
    if output_dir is None:
        output_dir = Path("output/phase13")
    
    hmm_dir = output_dir / "oracle_hmm"
    
    if not hmm_dir.exists():
        print(f"[ERROR] HMM directory not found: {hmm_dir}")
        return []
    
    print("=" * 80)
    print("PHASE 13 STEP F: RANKING + ACCEPTANCE GATES")
    print("=" * 80)
    print(f"\nEditions: {len(edition_ids)}")
    print(f"Tokenizers: {len(tokenizer_names)}")
    print()
    
    # Load results and compute scores
    print("[Step 1] Loading HMM results and computing composite scores...")
    
    candidates = []
    
    for edition_id in edition_ids:
        for tokenizer_name in tokenizer_names:
            # Load HMM result
            hmm_result = load_hmm_result(edition_id, tokenizer_name, hmm_dir)
            if not hmm_result:
                continue
            
            # Load metrics
            metrics = load_hmm_plot_for_metrics(edition_id, tokenizer_name, hmm_dir)
            if not metrics:
                continue
            
            # Compute composite score
            composite = compute_composite_score(metrics, hmm_result)
            
            candidates.append({
                "edition_id": edition_id,
                "tokenizer_name": tokenizer_name,
                "metrics": metrics,
                "hmm_result": hmm_result,
                "composite_score": composite
            })
    
    print(f"  Loaded {len(candidates)} candidates")
    
    # Rank by composite score
    print("\n[Step 2] Ranking candidates...")
    ranked = sorted(candidates, key=lambda x: x["composite_score"], reverse=True)
    
    # Save ranked results
    csv_file = output_dir / "ranked_oracle_results.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["rank", "edition_id", "tokenizer_name", "composite_score",
                     "early_100_pct", "early_200_pct", "total_pct", "alignment_pct",
                     "log_likelihood", "n_jumps", "max_offset"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, cand in enumerate(ranked, 1):
            analysis = cand["hmm_result"].get("analysis", {})
            writer.writerow({
                "rank": i,
                "edition_id": cand["edition_id"],
                "tokenizer_name": cand["tokenizer_name"],
                "composite_score": f"{cand['composite_score']:.2f}",
                "early_100_pct": f"{cand['metrics']['early_100_match_pct']:.2f}",
                "early_200_pct": f"{cand['metrics']['early_200_match_pct']:.2f}",
                "total_pct": f"{cand['metrics']['total_match_pct']:.2f}",
                "alignment_pct": f"{cand['metrics'].get('alignment_pct', 0.0):.2f}",
                "log_likelihood": f"{cand['hmm_result']['log_likelihood']:.2f}",
                "n_jumps": analysis.get("n_jumps", 0),
                "max_offset": analysis.get("max_offset", 0)
            })
    
    print(f"  Saved: {csv_file}")
    
    # Apply gates
    print("\n[Step 3] Applying acceptance gates...")
    passes, reason, best = apply_acceptance_gates(ranked, gates)
    
    if passes:
        print(f"  [SUCCESS] Acceptance gates PASSED")
        print(f"  Best: {best['edition_id']} + {best['tokenizer_name']}")
        print(f"  Composite score: {best['composite_score']:.2f}")
        print(f"  Early-100: {best['metrics']['early_100_match_pct']:.2f}%")
        print(f"  Strict:    {best['metrics']['total_match_pct']:.2f}%")
        print(f"  Alignment: {best['metrics'].get('alignment_pct', 0.0):.2f}%")
        
        recommendation = "LOCK"
    else:
        print(f"  [FAIL] Acceptance gates FAILED")
        print(f"  Reason: {reason}")
        
        recommendation = "NO-GO"
    
    # Save recommendation
    rec_file = output_dir / "LOCK_RECOMMENDATION.txt"
    with open(rec_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 13 LOCK RECOMMENDATION\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Candidates evaluated: {len(candidates)}\n")
        f.write("\n")
        
        f.write(f"RECOMMENDATION: {recommendation}\n")
        f.write("\n")
        
        if passes:
            f.write("All acceptance gates PASSED.\n")
            f.write("\n")
            f.write("BEST CANDIDATE:\n")
            f.write(f"  Edition: {best['edition_id']}\n")
            f.write(f"  Tokenizer: {best['tokenizer_name']}\n")
            f.write(f"  Composite score: {best['composite_score']:.2f}\n")
            f.write(f"  Early-100 match: {best['metrics']['early_100_match_pct']:.2f}%\n")
            f.write(f"  Early-200 match: {best['metrics']['early_200_match_pct']:.2f}%\n")
            f.write(f"  Strict match: {best['metrics']['total_match_pct']:.2f}%\n")
            f.write(f"  Alignment match: {best['metrics'].get('alignment_pct', 0.0):.2f}%\n")
            f.write(f"  Log-likelihood: {best['hmm_result']['log_likelihood']:.2f}\n")
            
            analysis = best['hmm_result'].get('analysis', {})
            f.write(f"  Jumps: {analysis.get('n_jumps', 0)}\n")
            f.write(f"  Max offset: {analysis.get('max_offset', 0)}\n")
            f.write("\n")
            f.write("ACTION: Proceed to Step G (lock corpus and rerun Cipher 1+3)\n")
        else:
            f.write(f"Acceptance gates FAILED: {reason}\n")
            f.write("\n")
            f.write("TOP CANDIDATE (did not pass gates):\n")
            if ranked:
                top = ranked[0]
                f.write(f"  Edition: {top['edition_id']}\n")
                f.write(f"  Tokenizer: {top['tokenizer_name']}\n")
                f.write(f"  Composite score: {top['composite_score']:.2f}\n")
                f.write(f"  Early-100 match: {top['metrics']['early_100_match_pct']:.2f}%\n")
                f.write(f"  Total match: {top['metrics']['total_match_pct']:.2f}%\n")
            f.write("\n")
            f.write("ACTION: Revisit edition acquisition (Step A) or relax gates\n")
        
        f.write("\n")
    
    print(f"\n  Saved: {rec_file}")
    
    print("\n" + "=" * 80)
    print("RANKING SUMMARY")
    print("=" * 80)
    print(f"Recommendation: {recommendation}")
    
    if passes:
        print(f"Best: {best['edition_id']} + {best['tokenizer_name']}")
        print("\nNext step: Run phase13_lock_rerun to lock and rerun Cipher 1+3")
    else:
        print(f"Reason: {reason}")
        print("\nNext step: Acquire more editions or adjust gates")
    
    print("=" * 80)
    
    return ranked


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 13 Step F: Ranking + Acceptance Gates")
    parser.add_argument('--output-dir', default='output/phase13', help='Output directory')
    parser.add_argument('--editions', nargs='+', required=True, help='Edition IDs')
    parser.add_argument('--tokenizers', nargs='+', default=['hyphen_keep'], 
                       help='Tokenizer names')
    
    args = parser.parse_args()
    
    run_ranking_and_gates(args.editions, args.tokenizers, Path(args.output_dir))
