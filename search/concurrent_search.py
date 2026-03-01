"""
Phase E: Concurrent Cipher 1+3 Search

Evaluates strategies on both Cipher 1 and Cipher 3 simultaneously, using:
- Cipher 1: English likelihood scoring (MultiObjectiveScorer)
- Cipher 3: Domain-specific scoring (Cipher3DomainScorer)
- Cross-cipher: Overlap consistency scoring

Composite score = 0.50*C1_english + 0.35*C3_domain + 0.15*overlap_consistency

This forces strategies to work well on BOTH ciphers, reducing false positives.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.canonical import CanonicalCorpus
from constraints.overlap_engine import CrossCipherConstraints, load_cipher
from extractors import ALL_EXTRACTORS
from transposition import ALL_TRANSPOSITIONS
from signal_score import score_stream
from scoring.multi_objective import MultiObjectiveScorer
from scoring.cipher3_domain_scorer import Cipher3DomainScorer


def run_concurrent_search(corpus: CanonicalCorpus,
                         extractors: List,
                         transpositions: List,
                         constraints: CrossCipherConstraints,
                         budget: int = 2000) -> List[Dict]:
    """
    Search strategies on Cipher 1 and Cipher 3 concurrently.
    
    Args:
        corpus: CanonicalCorpus (locked after oracle passes)
        extractors: List of extractor instances
        transpositions: List of transposition instances
        constraints: CrossCipherConstraints instance
        budget: Maximum strategies to evaluate
    
    Returns:
        List of results sorted by composite score
    """
    print("=" * 80)
    print("PHASE 8+9: CONCURRENT CIPHER 1+3 SEARCH")
    print("=" * 80)
    
    # Load ciphers
    cipher1 = load_cipher(1)
    cipher3 = load_cipher(3)
    
    print(f"\nCipher 1: {len(cipher1)} numbers")
    print(f"Cipher 3: {len(cipher3)} numbers")
    
    # Initialize scorers
    print("\n[Step 1] Initializing scorers...")
    c1_scorer = MultiObjectiveScorer()
    c3_scorer = Cipher3DomainScorer()
    
    print("  Cipher 1: MultiObjectiveScorer (English likelihood)")
    print("  Cipher 3: Cipher3DomainScorer (Names & Residences domain)")
    
    # Derive constraints (only use Cipher 2 when corpus is oracle-validated)
    print("\n[Step 2] Loading constraints...")
    alignment_pct = getattr(corpus.metadata, 'oracle_alignment_pct', 0.0)
    strict_pct = corpus.metadata.oracle_score
    c2_validated = getattr(corpus.metadata, 'cipher2_validated', False)
    print(f"  [INFO] Oracle strict={strict_pct:.2f}%, alignment={alignment_pct:.2f}%, validated={c2_validated}")
    if c2_validated or alignment_pct >= 89.5 or strict_pct >= 90.0:
        oracle_constraints = constraints.derive_cipher2_oracle_constraints()
        print(f"  Cipher 2 oracle constraints ENABLED: {len(oracle_constraints)} constraints derived")
    else:
        oracle_constraints = {}
        print("  [INFO] Skipping Cipher 2 constraint filter (not validated)")
    
    # Run search
    print(f"\n[Step 3] Evaluating strategies...")
    print(f"  Extractors: {len(extractors)}")
    print(f"  Transpositions: {len(transpositions)}")
    print(f"  Total combinations: {len(extractors) * len(transpositions)}")
    print(f"  Budget: {budget}")
    print("-" * 80)
    
    results = []
    tested_count = 0
    filtered_count = 0
    
    for extractor in extractors:
        for transposition in transpositions:
            # Pre-filter with oracle constraints (if available)
            if oracle_constraints:
                passes, violation_rate = constraints.validate_strategy(
                    extractor, transposition, oracle_constraints
                )
                if not passes:
                    filtered_count += 1
                    continue
            else:
                violation_rate = 0.0
            
            # Decode Cipher 1
            c1_decoded = corpus.decode_with_extractor(cipher1, extractor)
            c1_transposed = transposition.apply(c1_decoded)
            
            # Score Cipher 1 (use existing score_candidate as fallback)
            try:
                c1_score, c1_components = c1_scorer.score(c1_transposed)
            except Exception:
                # Fallback to signal_score.score_stream
                c1_result = score_stream(c1_transposed, use_phase3_metrics=True)
                c1_score = c1_result['total_score']
                c1_components = c1_result
            
            # Decode Cipher 3
            c3_decoded = corpus.decode_with_extractor(cipher3, extractor)
            c3_transposed = transposition.apply(c3_decoded)
            
            # Score Cipher 3
            c3_score, c3_components = c3_scorer.score(c3_transposed)
            
            # Overlap consistency score (use violation_rate)
            overlap_score = (1.0 - violation_rate) * 100 if oracle_constraints else 50.0
            
            # Composite score
            composite = (
                0.50 * c1_score +
                0.35 * c3_score +
                0.15 * overlap_score
            )
            
            results.append({
                'extractor': extractor.name,
                'transposition': transposition.name,
                'composite_score': composite,
                'c1_score': c1_score,
                'c3_score': c3_score,
                'overlap_score': overlap_score,
                'violation_rate': violation_rate,
                'c1_stream': c1_transposed[:200],
                'c3_stream': c3_transposed[:200],
                'c1_components': c1_components,
                'c3_components': c3_components
            })
            
            tested_count += 1
            
            if tested_count % 100 == 0:
                print(f"  Tested: {tested_count}, Filtered: {filtered_count}")
            
            if tested_count >= budget:
                print(f"\n[Budget limit reached: {budget}]")
                break
        
        if tested_count >= budget:
            break
    
    print(f"\nSearch complete:")
    print(f"  Tested: {tested_count}")
    print(f"  Filtered: {filtered_count}")
    print(f"  Valid strategies: {len(results)}")
    
    # Sort by composite score
    results.sort(key=lambda x: x['composite_score'], reverse=True)
    
    return results


def save_concurrent_search_results(results: List[Dict], timestamp: str):
    """Save concurrent search results."""
    output_dir = Path("output/phase89")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full CSV
    csv_file = output_dir / f"search_ranked_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if results:
            fieldnames = ['rank', 'extractor', 'transposition', 'composite_score',
                         'c1_score', 'c3_score', 'overlap_score', 'violation_rate']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, result in enumerate(results, 1):
                row = {k: result.get(k, '') for k in fieldnames if k != 'rank'}
                row['rank'] = i
                writer.writerow(row)
    
    # Save top 50 detailed report
    txt_file = output_dir / f"top50_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 8+9: CONCURRENT SEARCH TOP 50 STRATEGIES\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        if results:
            for i, result in enumerate(results[:50], 1):
                f.write(f"RANK {i}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Extractor: {result['extractor']}\n")
                f.write(f"Transposition: {result['transposition']}\n")
                f.write(f"\nScores:\n")
                f.write(f"  Composite: {result['composite_score']:.2f}/100\n")
                f.write(f"  Cipher 1 (English): {result['c1_score']:.2f}/100\n")
                f.write(f"  Cipher 3 (Domain): {result['c3_score']:.2f}/100\n")
                f.write(f"  Overlap consistency: {result['overlap_score']:.2f}/100\n")
                f.write(f"  Violation rate: {result['violation_rate']:.2%}\n")
                
                f.write(f"\nCipher 1 stream (first 200 chars):\n")
                f.write(f"{result['c1_stream']}\n\n")
                
                f.write(f"Cipher 3 stream (first 200 chars):\n")
                f.write(f"{result['c3_stream']}\n\n")
                
                f.write("=" * 80 + "\n\n")
    
    # Save best streams
    if results:
        c1_best_file = output_dir / f"cipher1_best_stream_{timestamp}.txt"
        with open(c1_best_file, 'w', encoding='utf-8') as f:
            # Get full decoded stream for best strategy
            # (We saved only sample, but note this for full runs)
            f.write(results[0]['c1_stream'])  # Would be full stream in real run
        
        c3_best_file = output_dir / f"cipher3_best_stream_{timestamp}.txt"
        with open(c3_best_file, 'w', encoding='utf-8') as f:
            f.write(results[0]['c3_stream'])
    
    print(f"\nResults saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Top 50: {txt_file}")
    if results:
        print(f"  Best C1 stream: {output_dir / f'cipher1_best_stream_{timestamp}.txt'}")
        print(f"  Best C3 stream: {output_dir / f'cipher3_best_stream_{timestamp}.txt'}")


def run_concurrent_search_pipeline(topk: int = 2000, time_budget_minutes: int = 30):
    """Main concurrent search execution."""
    print("=" * 80)
    print("PHASE 8+9: CONCURRENT CIPHER 1+3 SEARCH PIPELINE")
    print("=" * 80)
    
    # Load corpus
    print("\n[Step 1] Loading CANON_DOI...")
    try:
        corpus = CanonicalCorpus.load('corpus/CANON_DOI.json')
        print(f"Loaded: {corpus}")
        
        alignment_pct = getattr(corpus.metadata, 'oracle_alignment_pct', 0.0)
        c2_validated = getattr(corpus.metadata, 'cipher2_validated', False)
        if not c2_validated and alignment_pct < 89.5 and corpus.metadata.oracle_score < 90.0:
            print(f"\n[WARNING] Corpus not validated (strict={corpus.metadata.oracle_score:.2f}%, "
                  f"alignment={alignment_pct:.2f}%)")
            print("Concurrent search may not produce meaningful results.")
            print("Continuing anyway (non-interactive mode)...")
    except FileNotFoundError:
        print("[ERROR] CANON_DOI.json not found")
        print("ACTION: Run 'python run_pipeline.py oracle_sweep_enhanced' first")
        print("        Then 'python run_pipeline.py lock_corpus' after oracle passes")
        return []
    
    # Create constraints
    print("\n[Step 2] Initializing cross-cipher constraints...")
    constraints = CrossCipherConstraints(corpus)
    
    # Select extractors
    print("\n[Step 3] Selecting extractors...")
    # Include first_letter (validated for Cipher 2) plus Phase 5-7 best
    best_extractor_names = [
        'first_letter',
        'position_times_2',
        'cycle_every_5',
        'nth_letter_by_position',
        'reverse_position'
    ]
    
    extractors = [e for e in ALL_EXTRACTORS if e.name in best_extractor_names]
    print(f"  Selected: {[e.name for e in extractors]}")
    
    # Select transpositions (include 'none' for identity/no transposition)
    print("\n[Step 4] Selecting transpositions...")
    best_transposition_names = [
        'none',
        'rect_w26_spiral_ccw',
        'every_3th',
        'rect_w13_spiral_ccw',
        'rect_w40_diagonal',
        'chunk_reverse_3'
    ]
    
    transpositions = [t for t in ALL_TRANSPOSITIONS if t.name in best_transposition_names]
    print(f"  Selected: {[t.name for t in transpositions]}")
    
    total_combinations = len(extractors) * len(transpositions)
    print(f"\n[Step 5] Total combinations: {total_combinations}")
    print(f"  Budget: {topk}")
    print(f"  Time budget: {time_budget_minutes} minutes")
    
    # Run search
    print("\n[Step 6] Running concurrent search...")
    results = run_concurrent_search(corpus, extractors, transpositions, 
                                    constraints, budget=topk)
    
    # Save results
    print(f"\n[Step 7] Saving results...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_concurrent_search_results(results, timestamp)
    
    # Summary
    print("\n" + "=" * 80)
    print("CONCURRENT SEARCH COMPLETE")
    print("=" * 80)
    
    if results:
        print(f"\nTop 10 strategies:")
        for i, result in enumerate(results[:10], 1):
            print(f"{i:2d}. {result['extractor']:25s} + {result['transposition']:25s}")
            print(f"    Composite: {result['composite_score']:6.2f} | "
                  f"C1: {result['c1_score']:5.2f} | "
                  f"C3: {result['c3_score']:5.2f} | "
                  f"Overlap: {result['overlap_score']:5.2f}")
        
        best = results[0]
        print(f"\nBest strategy:")
        print(f"  {best['extractor']} + {best['transposition']}")
        print(f"  Composite score: {best['composite_score']:.2f}/100")
        print(f"    Cipher 1 (English): {best['c1_score']:.2f}/100")
        print(f"    Cipher 3 (Domain): {best['c3_score']:.2f}/100")
        print(f"    Overlap consistency: {best['overlap_score']:.2f}/100")
        
        print(f"\n  Cipher 1 sample: {best['c1_stream'][:80]}...")
        print(f"  Cipher 3 sample: {best['c3_stream'][:80]}...")
    else:
        print("\n[WARNING] No valid strategies found")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run concurrent Cipher 1+3 search")
    parser.add_argument('--topk', type=int, default=2000,
                       help='Maximum strategies to evaluate')
    parser.add_argument('--time-budget', type=str, default='30m',
                       help='Time budget (e.g., 30m, 1h)')
    
    args = parser.parse_args()
    
    # Parse time budget
    time_budget_minutes = 30
    if args.time_budget.endswith('m'):
        time_budget_minutes = int(args.time_budget[:-1])
    elif args.time_budget.endswith('h'):
        time_budget_minutes = int(args.time_budget[:-1]) * 60
    
    results = run_concurrent_search_pipeline(args.topk, time_budget_minutes)
