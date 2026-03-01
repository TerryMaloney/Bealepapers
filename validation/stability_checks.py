"""
Stability Checks Framework

Tests to avoid false positives and ensure strategies are not fitting noise:

1. Tokenization Stability: Re-run with nearby tokenization presets
2. Shuffle Control: Shuffle cipher order, score should collapse
3. Random Wordlist Control: Replace DOI with random words, score should collapse
4. Fragment Consensus: Check if multiple independent strategies find same fragments

A strategy PASSES only if:
- Tokenization stability >0.8 (score remains high under minor tokenization changes)
- Shuffle collapse <0.5 (score collapses with shuffled cipher)
- Random collapse <0.5 (score collapses with random wordlist)
"""

import random
import json
from pathlib import Path
from typing import Dict, List, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.canonical import CanonicalCorpus
from corpus.tokenizers import TokenizerRegistry
from extractors import ALL_EXTRACTORS
from transposition import ALL_TRANSPOSITIONS
from signal_score import score_candidate


def get_nearby_tokenization_presets(base_preset: str) -> List[str]:
    """
    Get tokenization presets that are 'nearby' to the base preset.
    
    Nearby = differ by only one rule (hyphen, apostrophe, punctuation, case, headers).
    """
    all_presets = TokenizerRegistry.list_presets()
    
    # Heuristic: return presets that share substring with base
    nearby = []
    
    for preset in all_presets:
        if preset == base_preset:
            continue
        
        # Check for similarity
        base_parts = set(base_preset.split('_'))
        preset_parts = set(preset.split('_'))
        
        # If they share most components, consider nearby
        shared = len(base_parts & preset_parts)
        if shared >= len(base_parts) - 1:
            nearby.append(preset)
    
    # Fallback: return a few generic presets
    if not nearby:
        nearby = ['hyphen_keep', 'hyphen_split', 'strict_word']
        if base_preset in nearby:
            nearby.remove(base_preset)
    
    return nearby[:3]  # Return at most 3


def create_perturbed_corpus(base_corpus: CanonicalCorpus, tokenizer_name: str) -> CanonicalCorpus:
    """Create corpus with different tokenization from same edition."""
    return CanonicalCorpus(
        edition_id=base_corpus.metadata.edition_id,
        tokenizer_name=tokenizer_name,
        drift_model=None,
        oracle_score=0.0  # Not re-validated
    )


def create_random_wordlist_corpus(word_count: int, avg_word_length: int = 6) -> List[str]:
    """Create random wordlist for control testing."""
    import string
    
    random.seed(42)  # Deterministic
    
    words = []
    for _ in range(word_count):
        length = random.randint(3, avg_word_length + 3)
        word = ''.join(random.choice(string.ascii_lowercase) for _ in range(length))
        words.append(word)
    
    return words


def evaluate_strategy_on_corpus(corpus_or_wordlist, cipher_numbers: List[int],
                                extractor, transposition) -> float:
    """
    Evaluate a strategy on given corpus/wordlist.
    
    Args:
        corpus_or_wordlist: CanonicalCorpus or List[str]
        cipher_numbers: Cipher number sequence
        extractor: Extractor instance
        transposition: Transposition instance
    
    Returns:
        Total score (0-100)
    """
    # Decode
    if isinstance(corpus_or_wordlist, CanonicalCorpus):
        decoded = corpus_or_wordlist.decode_with_extractor(cipher_numbers, extractor)
    else:
        # wordlist
        decoded = []
        for cipher_pos, cipher_num in enumerate(cipher_numbers):
            word_idx = cipher_num - 1
            if 0 <= word_idx < len(corpus_or_wordlist):
                word = corpus_or_wordlist[word_idx]
                try:
                    letter = extractor.extract(word, word_idx, cipher_pos, 'DOI')
                    decoded.append(letter if letter else '?')
                except:
                    decoded.append('?')
            else:
                decoded.append('?')
        decoded = ''.join(decoded)
    
    # Apply transposition
    transposed = transposition.apply(decoded)
    
    # Score
    result = score_candidate(transposed)
    return result['total_score']


def run_stability_checks(corpus: CanonicalCorpus, strategy_config: Dict,
                        cipher_num: int) -> Dict:
    """
    Run stability checks on a strategy.
    
    Args:
        corpus: CanonicalCorpus (locked)
        strategy_config: Dict with 'extractor' and 'transposition' names
        cipher_num: Cipher number (1, 2, or 3)
    
    Returns:
        Dict with stability metrics and verdict
    """
    print("=" * 80)
    print(f"STABILITY CHECKS: CIPHER {cipher_num}")
    print("=" * 80)
    
    print(f"\nStrategy: {strategy_config['extractor']} + {strategy_config['transposition']}")
    
    # Load cipher
    from constraints.overlap_engine import load_cipher
    cipher_numbers = load_cipher(cipher_num)
    
    # Get extractor and transposition
    extractor = next((e for e in ALL_EXTRACTORS if e.name == strategy_config['extractor']), None)
    transposition = next((t for t in ALL_TRANSPOSITIONS if t.name == strategy_config['transposition']), None)
    
    if not extractor or not transposition:
        print("[ERROR] Extractor or transposition not found")
        return {'verdict': 'ERROR'}
    
    # Baseline score
    print("\n[Test 0] Baseline score...")
    baseline_score = evaluate_strategy_on_corpus(corpus, cipher_numbers, extractor, transposition)
    print(f"  Baseline: {baseline_score:.2f}/100")
    
    # Test 1: Tokenization perturbation
    print("\n[Test 1] Tokenization stability...")
    nearby_presets = get_nearby_tokenization_presets(corpus.metadata.tokenizer_name)
    print(f"  Testing with nearby presets: {nearby_presets}")
    
    tokenization_scores = []
    for preset in nearby_presets:
        try:
            perturbed_corpus = create_perturbed_corpus(corpus, preset)
            score = evaluate_strategy_on_corpus(perturbed_corpus, cipher_numbers, 
                                               extractor, transposition)
            tokenization_scores.append(score)
            print(f"    {preset:25s}: {score:6.2f}/100 (ratio: {score/baseline_score:.3f})")
        except Exception as e:
            print(f"    {preset:25s}: ERROR ({e})")
    
    tokenization_stability = (min(tokenization_scores) / baseline_score 
                             if tokenization_scores and baseline_score > 0 else 0.0)
    
    # Test 2: Shuffle control
    print("\n[Test 2] Shuffle control...")
    random.seed(42)
    shuffled_cipher = cipher_numbers.copy()
    random.shuffle(shuffled_cipher)
    
    shuffle_score = evaluate_strategy_on_corpus(corpus, shuffled_cipher, extractor, transposition)
    shuffle_collapse = shuffle_score / baseline_score if baseline_score > 0 else 1.0
    
    print(f"  Shuffled cipher score: {shuffle_score:.2f}/100 (ratio: {shuffle_collapse:.3f})")
    print(f"  Expected: <0.5 (should collapse)")
    
    # Test 3: Random wordlist control
    print("\n[Test 3] Random wordlist control...")
    random_wordlist = create_random_wordlist_corpus(len(corpus.tokens))
    random_score = evaluate_strategy_on_corpus(random_wordlist, cipher_numbers, 
                                              extractor, transposition)
    random_collapse = random_score / baseline_score if baseline_score > 0 else 1.0
    
    print(f"  Random wordlist score: {random_score:.2f}/100 (ratio: {random_collapse:.3f})")
    print(f"  Expected: <0.5 (should collapse)")
    
    # Verdict
    print("\n" + "=" * 80)
    print("STABILITY VERDICT")
    print("=" * 80)
    
    checks = {
        'tokenization_stability': (tokenization_stability, tokenization_stability > 0.8),
        'shuffle_collapse': (shuffle_collapse, shuffle_collapse < 0.5),
        'random_collapse': (random_collapse, random_collapse < 0.5)
    }
    
    all_pass = all(passed for _, passed in checks.values())
    
    for check_name, (value, passed) in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check_name:30s}: {value:.3f} [{status}]")
    
    verdict = "PASS" if all_pass else "FAIL"
    print(f"\nOverall: {verdict}")
    
    if verdict == "PASS":
        print("Strategy appears stable and not fitting noise.")
    else:
        print("Strategy may be fitting noise or tokenization artifacts.")
    
    return {
        'baseline_score': baseline_score,
        'tokenization_stability': tokenization_stability,
        'shuffle_collapse': shuffle_collapse,
        'random_collapse': random_collapse,
        'tokenization_scores': tokenization_scores,
        'verdict': verdict
    }


def run_stability_batch(strategy_file: str, cipher_num: int = 1):
    """Run stability checks from strategy config file."""
    print("=" * 80)
    print("BATCH STABILITY CHECKS")
    print("=" * 80)
    
    # Load strategy config
    with open(strategy_file, 'r', encoding='utf-8') as f:
        strategy_config = json.load(f)
    
    # Load corpus
    corpus = CanonicalCorpus.load('corpus/CANON_DOI.json')
    
    # Run checks
    results = run_stability_checks(corpus, strategy_config, cipher_num)
    
    # Save results
    output_file = strategy_file.replace('.json', '_stability.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nStability results saved: {output_file}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run stability checks on strategy")
    parser.add_argument('--strategy-file', required=True,
                       help='Path to strategy config JSON')
    parser.add_argument('--cipher', type=int, default=1, choices=[1,2,3],
                       help='Cipher number to test')
    
    args = parser.parse_args()
    
    run_stability_batch(args.strategy_file, args.cipher)
