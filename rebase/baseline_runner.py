"""
Phase B: Baseline Rebase Runner

Re-run all Phase 5-6-7 best extractors with CANON_DOI after oracle validation.
Expected: Significant score improvement with correct corpus.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.canonical import CanonicalCorpus
from extractors import ALL_EXTRACTORS
from transposition import ALL_TRANSPOSITIONS
from signal_score import score_candidate


def load_cipher(cipher_num: int) -> List[int]:
    """Load cipher numbers from beale_papers.txt."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    line_map = {1: 2, 2: 58, 3: 6}  # Cipher -> line index
    cipher_line = lines[line_map[cipher_num]].strip()
    return [int(n.strip()) for n in cipher_line.split(",") if n.strip()]


def run_baseline_with_canon_corpus(cipher_num: int, topk: int = 50) -> List[Dict]:
    """
    Re-run Phase 5-6-7 best extractors with CANON_DOI.
    
    Args:
        cipher_num: Cipher number (1, 2, or 3)
        topk: Number of top strategies to return
    
    Returns:
        List of results sorted by score
    """
    print("=" * 80)
    print(f"PHASE B: BASELINE REBASE - CIPHER {cipher_num}")
    print("=" * 80)
    
    # Load canonical corpus
    print("\n[Step 1] Loading CANON_DOI...")
    try:
        corpus = CanonicalCorpus.load('corpus/CANON_DOI.json')
        print(f"Loaded: {corpus}")
    except FileNotFoundError:
        print("[ERROR] CANON_DOI.json not found")
        print("ACTION: Run 'python run_pipeline.py lock_corpus' first")
        return []
    
    # Load cipher
    print(f"\n[Step 2] Loading Cipher {cipher_num}...")
    cipher_numbers = load_cipher(cipher_num)
    print(f"Cipher {cipher_num}: {len(cipher_numbers)} numbers")
    
    # Best extractors from Phases 5-7
    print("\n[Step 3] Testing best extractors from Phases 5-7...")
    best_extractor_names = [
        'position_times_2',
        'cycle_every_5',
        'nth_letter_by_position',
        'reverse_position'
    ]
    
    extractors_to_test = [ext for ext in ALL_EXTRACTORS if ext.name in best_extractor_names]
    print(f"Extractors: {[e.name for e in extractors_to_test]}")
    
    # Best transpositions from Phases 5-7
    print("\n[Step 4] Testing best transpositions from Phases 5-7...")
    best_transposition_names = [
        'rect_w26_spiral_ccw',
        'every_3th',
        'rect_w13_spiral_ccw',
        'rect_w40_diagonal',
        'chunk_reverse_3'
    ]
    
    transpositions_to_test = [t for t in ALL_TRANSPOSITIONS if t.name in best_transposition_names]
    print(f"Transpositions: {[t.name for t in transpositions_to_test]}")
    
    # Run evaluation
    print(f"\n[Step 5] Evaluating {len(extractors_to_test)} × {len(transpositions_to_test)} = {len(extractors_to_test) * len(transpositions_to_test)} strategies...")
    print("-" * 80)
    
    results = []
    for extractor in extractors_to_test:
        for transposition in transpositions_to_test:
            # Decode with corpus
            decoded = corpus.decode_with_extractor(cipher_numbers, extractor)
            
            # Apply transposition
            transposed = transposition.apply(decoded)
            
            # Score
            score_result = score_candidate(transposed)
            
            results.append({
                'extractor': extractor.name,
                'transposition': transposition.name,
                'total_score': score_result['total_score'],
                'decoded': transposed[:200],  # Sample
                **score_result
            })
            
            print(f"  {extractor.name:25s} + {transposition.name:25s}: {score_result['total_score']:6.2f}/100")
    
    # Sort by score
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Save results
    print(f"\n[Step 6] Saving top {topk} results...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_baseline_results(results[:topk], cipher_num, timestamp)
    
    # Summary
    print("\n" + "=" * 80)
    print(f"CIPHER {cipher_num} REBASE RESULTS")
    print("=" * 80)
    
    print(f"\nTop 10 strategies:")
    for i, result in enumerate(results[:10], 1):
        print(f"{i:2d}. {result['extractor']:25s} + {result['transposition']:25s} | {result['total_score']:6.2f}/100")
    
    best = results[0]
    print(f"\nBest strategy:")
    print(f"  Extractor: {best['extractor']}")
    print(f"  Transposition: {best['transposition']}")
    print(f"  Score: {best['total_score']:.2f}/100")
    print(f"\nDecoded sample (first 200 chars):")
    print(f"  {best['decoded']}")
    
    return results[:topk]


def save_baseline_results(results: List[Dict], cipher_num: int, timestamp: str):
    """Save baseline rebase results."""
    output_dir = Path(f"output/rebase")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # CSV
    csv_file = output_dir / f"cipher{cipher_num}_baseline_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if results:
            fieldnames = ['rank', 'extractor', 'transposition', 'total_score',
                         'bigram', 'trigram', 'quadgram', 'vowel_ratio',
                         'entropy', 'dict_coverage', 'fragment_score']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, result in enumerate(results, 1):
                row = {k: result.get(k, '') for k in fieldnames if k != 'rank'}
                row['rank'] = i
                writer.writerow(row)
    
    # Text report
    txt_file = output_dir / f"cipher{cipher_num}_baseline_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"PHASE B: CIPHER {cipher_num} BASELINE REBASE\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE:\n")
        f.write("Re-run best methods from Phases 5-7 with validated CANON_DOI.\n")
        f.write("Expected: Score improvement with correct corpus.\n\n")
        
        f.write(f"Strategies tested: {len(results)}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write(f"TOP {min(len(results), 20)} STRATEGIES\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results[:20], 1):
            f.write(f"RANK {i}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Extractor: {result['extractor']}\n")
            f.write(f"Transposition: {result['transposition']}\n")
            f.write(f"Total score: {result['total_score']:.2f}/100\n")
            f.write(f"  Bigram: {result.get('bigram', 0):.2f}\n")
            f.write(f"  Trigram: {result.get('trigram', 0):.2f}\n")
            f.write(f"  Quadgram: {result.get('quadgram', 0):.2f}\n")
            f.write(f"  Vowel ratio: {result.get('vowel_ratio', 0):.2f}\n")
            f.write(f"  Entropy: {result.get('entropy', 0):.2f}\n")
            f.write(f"  Dict coverage: {result.get('dict_coverage', 0):.2f}\n")
            f.write(f"  Fragment score: {result.get('fragment_score', 0):.2f}\n")
            f.write(f"\nDecoded sample:\n{result['decoded']}\n\n")
            f.write("=" * 80 + "\n\n")
    
    print(f"Results saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Report: {txt_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Re-run baseline with CANON_DOI")
    parser.add_argument('--cipher', type=int, choices=[1,2,3], required=True,
                       help='Cipher number to decode')
    parser.add_argument('--topk', type=int, default=50,
                       help='Number of top strategies to save')
    
    args = parser.parse_args()
    
    results = run_baseline_with_canon_corpus(args.cipher, args.topk)
