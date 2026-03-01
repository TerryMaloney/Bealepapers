"""
Phase 12C/12D: Offset Sweep - Constant and Progressive Offset Testing

Phase 12C: Test small constant offsets (-5 to +5) on early segment (first 100)
Phase 12D: Test progressive offsets (conditional, only if 12C yields >=85%)

Critical: Apply bounded search, not exhaustive sweeps.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import csv
import math

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import Cipher2Oracle, load_cipher2, load_cipher2_known_plaintext
from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry


def load_doi_tokens(edition_id: str = "beale_embedded", tokenizer_name: str = "hyphen_keep") -> List[str]:
    """Load DOI tokens."""
    loader = DOICorpusLoader()
    edition = loader.load_edition(edition_id)
    tokenizer = TokenizerRegistry.get_tokenizer(tokenizer_name)
    tokens = tokenizer.tokenize(edition.source_text)
    return tokens


def evaluate_constant_offset_early(offset: int, doi_tokens: List[str], 
                                   cipher2_numbers: List[int], known_plaintext: str,
                                   segment_size: int = 100) -> Dict:
    """
    Evaluate a constant offset applied ONLY to the early segment.
    
    Args:
        offset: Offset to add to cipher numbers (-5 to +5)
        doi_tokens: DOI word list
        cipher2_numbers: Cipher 2 number sequence
        known_plaintext: Known Cipher 2 plaintext
        segment_size: Size of early segment to test (default: 100)
    
    Returns:
        Dictionary with match statistics for the early segment
    """
    known_clean = ''.join(c.upper() for c in known_plaintext if c.isalpha())
    
    # Decode early segment with offset
    decoded = []
    for i, cipher_num in enumerate(cipher2_numbers[:segment_size]):
        effective_num = cipher_num + offset
        word_idx = effective_num - 1  # 1-indexed to 0-indexed
        
        if 0 <= word_idx < len(doi_tokens) and doi_tokens[word_idx]:
            decoded.append(doi_tokens[word_idx][0].upper())
        else:
            decoded.append('?')
    
    # Compute match rate
    matches = sum(1 for i, (d, k) in enumerate(zip(decoded, known_clean[:segment_size])) if d == k)
    total = min(len(decoded), len(known_clean[:segment_size]))
    match_pct = (matches / total * 100) if total > 0 else 0.0
    
    # Find first mismatch
    first_mismatch = -1
    for i, (d, k) in enumerate(zip(decoded, known_clean[:segment_size])):
        if d != k:
            first_mismatch = i
            break
    
    return {
        'offset': offset,
        'match_pct': match_pct,
        'matches': matches,
        'total': total,
        'first_mismatch': first_mismatch,
        'decoded_sample': ''.join(decoded[:50])
    }


def evaluate_progressive_offset(k: float, doi_tokens: List[str], 
                                cipher2_numbers: List[int], known_plaintext: str) -> Dict:
    """
    Evaluate a progressive offset model: effective_num = cipher_num + floor(k * position)
    
    Args:
        k: Drift coefficient (typically -0.1 to 0.1)
        doi_tokens: DOI word list
        cipher2_numbers: Cipher 2 number sequence
        known_plaintext: Known Cipher 2 plaintext
    
    Returns:
        Dictionary with full-document match statistics
    """
    known_clean = ''.join(c.upper() for c in known_plaintext if c.isalpha())
    
    # Decode with progressive offset
    decoded = []
    for i, cipher_num in enumerate(cipher2_numbers):
        progressive_offset = math.floor(k * i)
        effective_num = cipher_num + progressive_offset
        word_idx = effective_num - 1
        
        if 0 <= word_idx < len(doi_tokens) and doi_tokens[word_idx]:
            decoded.append(doi_tokens[word_idx][0].upper())
        else:
            decoded.append('?')
    
    # Compute match rate
    decoded_str = ''.join(decoded)
    matches = sum(1 for i, (d, k_char) in enumerate(zip(decoded_str, known_clean)) if d == k_char)
    total = min(len(decoded_str), len(known_clean))
    match_pct = (matches / total * 100) if total > 0 else 0.0
    
    # Regional matches
    third = len(decoded_str) // 3
    early_matches = sum(1 for i in range(third) if i < len(decoded_str) and i < len(known_clean) 
                       and decoded_str[i] == known_clean[i])
    early_pct = (early_matches / third * 100) if third > 0 else 0.0
    
    # Find first mismatch
    first_mismatch = -1
    for i, (d, k_char) in enumerate(zip(decoded_str, known_clean)):
        if d != k_char:
            first_mismatch = i
            break
    
    return {
        'k': k,
        'match_pct': match_pct,
        'matches': matches,
        'total': total,
        'early_pct': early_pct,
        'first_mismatch': first_mismatch,
        'decoded_sample': decoded_str[:50]
    }


def run_constant_offset_sweep(offset_range: Tuple[int, int] = (-5, 5), 
                               segment_size: int = 100) -> List[Dict]:
    """
    Phase 12C: Run constant offset sweep on early segment.
    
    Args:
        offset_range: (min_offset, max_offset) inclusive
        segment_size: Size of early segment to test
    
    Returns:
        List of results for each offset
    """
    print("\nPhase 12C: Early-Segment Constant Offset Sweep")
    print("=" * 80)
    print(f"Testing offsets {offset_range[0]} to {offset_range[1]} on first {segment_size} positions...")
    print()
    
    # Load data
    doi_tokens = load_doi_tokens()
    cipher2_numbers = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    results = []
    
    for offset in range(offset_range[0], offset_range[1] + 1):
        result = evaluate_constant_offset_early(offset, doi_tokens, cipher2_numbers, 
                                               known_plaintext, segment_size)
        results.append(result)
        
        print(f"Offset {offset:+3d}: {result['match_pct']:6.2f}% ({result['matches']}/{result['total']} matches)")
    
    print()
    
    return results


def run_progressive_offset_sweep(k_range: Tuple[float, float, float] = (-0.1, 0.1, 0.01)) -> List[Dict]:
    """
    Phase 12D: Run progressive offset sweep (conditional).
    
    Args:
        k_range: (k_min, k_max, k_step)
    
    Returns:
        List of results for each k value
    """
    print("\nPhase 12D: Progressive Offset Sweep")
    print("=" * 80)
    print(f"Testing k from {k_range[0]} to {k_range[1]} in steps of {k_range[2]}...")
    print("Model: effective_num = cipher_num + floor(k * position)")
    print()
    
    # Load data
    doi_tokens = load_doi_tokens()
    cipher2_numbers = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    results = []
    
    k = k_range[0]
    while k <= k_range[1]:
        result = evaluate_progressive_offset(k, doi_tokens, cipher2_numbers, known_plaintext)
        results.append(result)
        
        print(f"k = {k:+.3f}: {result['match_pct']:6.2f}% overall, {result['early_pct']:6.2f}% early")
        
        k += k_range[2]
    
    print()
    
    return results


def save_constant_offset_results(results: List[Dict], output_dir: Path):
    """Save Phase 12C results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV
    csv_path = output_dir / f"constant_offset_sweep_{timestamp}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['offset', 'match_pct', 'matches', 'total', 'first_mismatch']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in fieldnames})
    
    print(f"CSV saved: {csv_path}")
    
    # Text report
    txt_path = output_dir / f"constant_offset_sweep_{timestamp}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 12C: EARLY-SEGMENT CONSTANT OFFSET SWEEP\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Segment size: first {results[0]['total']} positions\n")
        f.write("\n")
        
        f.write("RESULTS\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Offset':<10} {'Match %':<10} {'Matches':<15} {'1st Mismatch':<15}\n")
        f.write("-" * 80 + "\n")
        
        for r in results:
            f.write(f"{r['offset']:+3d}        {r['match_pct']:6.2f}     "
                   f"{r['matches']}/{r['total']:<10} {r['first_mismatch']:<15}\n")
        
        f.write("\n")
        
        # Analysis
        best = max(results, key=lambda x: x['match_pct'])
        baseline = next((r for r in results if r['offset'] == 0), results[0])
        
        f.write("ANALYSIS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Baseline (offset 0): {baseline['match_pct']:.2f}%\n")
        f.write(f"Best offset: {best['offset']:+d} with {best['match_pct']:.2f}%\n")
        f.write(f"Improvement: {best['match_pct'] - baseline['match_pct']:+.2f} percentage points\n")
        f.write("\n")
        
        if best['match_pct'] >= 85.0:
            f.write("VERDICT: [SUCCESS] Constant offset achieves >=85% early-segment match\n")
            f.write(f"RECOMMENDATION: Apply offset {best['offset']:+d} and proceed to Phase 12D\n")
        elif best['match_pct'] > baseline['match_pct'] + 10.0:
            f.write("VERDICT: [WARNING] Material improvement with constant offset\n")
            f.write("RECOMMENDATION: Consider wider offset range or progressive models\n")
        else:
            f.write("VERDICT: [INFO] No constant offset materially improves alignment\n")
            f.write("RECOMMENDATION: Revisit edition acquisition (Stone 1823) or conventions\n")
        
        f.write("\n")
    
    print(f"Report saved: {txt_path}")


def save_progressive_offset_results(results: List[Dict], output_dir: Path):
    """Save Phase 12D results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV
    csv_path = output_dir / f"progressive_offset_sweep_{timestamp}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['k', 'match_pct', 'early_pct', 'matches', 'total', 'first_mismatch']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in fieldnames})
    
    print(f"CSV saved: {csv_path}")
    
    # Text report
    txt_path = output_dir / f"progressive_offset_sweep_{timestamp}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 12D: PROGRESSIVE OFFSET SWEEP\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("Model: effective_num = cipher_num + floor(k * position)\n")
        f.write("\n")
        
        f.write("RESULTS\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'k':<10} {'Overall %':<12} {'Early %':<12} {'Matches':<15} {'1st Mismatch':<15}\n")
        f.write("-" * 80 + "\n")
        
        for r in results:
            f.write(f"{r['k']:+.3f}     {r['match_pct']:6.2f}       "
                   f"{r['early_pct']:6.2f}       {r['matches']}/{r['total']:<10} {r['first_mismatch']:<15}\n")
        
        f.write("\n")
        
        # Analysis
        best = max(results, key=lambda x: x['match_pct'])
        baseline = next((r for r in results if abs(r['k']) < 0.001), results[0])
        
        f.write("ANALYSIS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Baseline (k ~ 0): {baseline['match_pct']:.2f}%\n")
        f.write(f"Best k: {best['k']:+.3f} with {best['match_pct']:.2f}%\n")
        f.write(f"Improvement: {best['match_pct'] - baseline['match_pct']:+.2f} percentage points\n")
        f.write("\n")
        
        if best['match_pct'] >= 95.0:
            f.write("VERDICT: [SUCCESS] ANCHOR LOCKED - Progressive offset achieves >=95%!\n")
            f.write(f"RECOMMENDATION: Lock k={best['k']:+.3f} and proceed to Cipher 1 decoding\n")
        elif best['match_pct'] >= 90.0:
            f.write("VERDICT: [SUCCESS] Very strong alignment with progressive offset\n")
            f.write("RECOMMENDATION: Refine k search around optimal value\n")
        elif best['match_pct'] > baseline['match_pct'] + 10.0:
            f.write("VERDICT: [WARNING] Material improvement with progressive offset\n")
            f.write("RECOMMENDATION: Consider piecewise models or alternative editions\n")
        else:
            f.write("VERDICT: [INFO] Linear progressive offset insufficient\n")
            f.write("RECOMMENDATION: Acquire Stone 1823 or test piecewise/quadratic models\n")
        
        f.write("\n")
    
    print(f"Report saved: {txt_path}")


def run_offset_sweep_pipeline(mode: str = "constant", output_dir: str = "output/oracle_diagnostic",
                               offset_range: Optional[Tuple[int, int]] = None,
                               segment_size: int = 100,
                               k_range: Optional[Tuple[float, float, float]] = None):
    """
    Main entry point for Phase 12C/12D offset sweep.
    
    Args:
        mode: "constant" (12C) or "progressive" (12D)
        output_dir: Directory to save results
        offset_range: (min, max) for constant offsets
        segment_size: Early segment size for constant offset
        k_range: (min, max, step) for progressive k
    """
    output_path = Path(output_dir)
    
    if mode == "constant":
        if offset_range is None:
            offset_range = (-5, 5)
        
        results = run_constant_offset_sweep(offset_range, segment_size)
        save_constant_offset_results(results, output_path)
        
        # Print summary
        best = max(results, key=lambda x: x['match_pct'])
        baseline = next((r for r in results if r['offset'] == 0), results[0])
        
        print("\n" + "=" * 80)
        print("CONSTANT OFFSET SUMMARY")
        print("=" * 80)
        print(f"Baseline (offset 0): {baseline['match_pct']:.2f}%")
        print(f"Best: offset {best['offset']:+d} - {best['match_pct']:.2f}%")
        print(f"Improvement: {best['match_pct'] - baseline['match_pct']:+.2f} pp")
        print()
        
        if best['match_pct'] >= 85.0:
            print("[SUCCESS] BREAKTHROUGH: Offset achieves >=85% early-segment!")
            print(f"   Proceed to Phase 12D with offset {best['offset']:+d} as baseline")
        elif best['match_pct'] > baseline['match_pct'] + 10.0:
            print("[WARNING] Material improvement detected")
            print("   Consider wider offset range or progressive models")
        else:
            print("[INFO] No constant offset materially improves alignment")
            print("   Consider: (1) Stone 1823 acquisition, (2) refined conventions")
        
    elif mode == "progressive":
        if k_range is None:
            k_range = (-0.1, 0.1, 0.01)
        
        results = run_progressive_offset_sweep(k_range)
        save_progressive_offset_results(results, output_path)
        
        # Print summary
        best = max(results, key=lambda x: x['match_pct'])
        baseline = next((r for r in results if abs(r['k']) < 0.001), results[0])
        
        print("\n" + "=" * 80)
        print("PROGRESSIVE OFFSET SUMMARY")
        print("=" * 80)
        print(f"Baseline (k ~ 0): {baseline['match_pct']:.2f}%")
        print(f"Best: k = {best['k']:+.3f} - {best['match_pct']:.2f}%")
        print(f"Improvement: {best['match_pct'] - baseline['match_pct']:+.2f} pp")
        print()
        
        if best['match_pct'] >= 95.0:
            print("[SUCCESS] ANCHOR LOCKED: Progressive offset achieves >=95%!")
            print(f"   Lock k={best['k']:+.3f} and proceed to Cipher 1")
        elif best['match_pct'] >= 90.0:
            print("[SUCCESS] Strong alignment achieved")
            print("   Refine k search around optimal value")
        else:
            print("[INFO] Linear progressive offset insufficient")
            print("   Consider: (1) Stone 1823, (2) piecewise models")
    
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'constant' or 'progressive'")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 12C/12D: Offset Sweep")
    parser.add_argument('--mode', choices=['constant', 'progressive'], default='constant',
                       help='Offset mode: constant (12C) or progressive (12D)')
    parser.add_argument('--output-dir', default='output/oracle_diagnostic',
                       help='Output directory for results')
    parser.add_argument('--offset-min', type=int, default=-5,
                       help='Minimum offset for constant mode')
    parser.add_argument('--offset-max', type=int, default=5,
                       help='Maximum offset for constant mode')
    parser.add_argument('--segment-size', type=int, default=100,
                       help='Early segment size for constant mode')
    parser.add_argument('--k-min', type=float, default=-0.1,
                       help='Minimum k for progressive mode')
    parser.add_argument('--k-max', type=float, default=0.1,
                       help='Maximum k for progressive mode')
    parser.add_argument('--k-step', type=float, default=0.01,
                       help='Step size for k in progressive mode')
    
    args = parser.parse_args()
    
    run_offset_sweep_pipeline(
        mode=args.mode,
        output_dir=args.output_dir,
        offset_range=(args.offset_min, args.offset_max),
        segment_size=args.segment_size,
        k_range=(args.k_min, args.k_max, args.k_step)
    )
