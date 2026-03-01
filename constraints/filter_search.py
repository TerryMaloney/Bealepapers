"""
Phase D: Constraint-Filtered Beam Search

Beam search filtered by cross-cipher constraints to eliminate invalid strategies.
"""

from typing import List, Dict
from pathlib import Path
import sys
import csv
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.canonical import CanonicalCorpus
from constraints.overlap_engine import CrossCipherConstraints, load_cipher
from extractors import ALL_EXTRACTORS
from transposition import ALL_TRANSPOSITIONS
from signal_score import score_candidate


def search_with_constraints(extractors: List, transpositions: List,
                            constraints_engine: CrossCipherConstraints,
                            cipher_num: int = 1,
                            budget: int = 1000) -> List[Dict]:
    """
    Beam search filtered by cross-cipher constraints.
    
    Args:
        extractors: List of extractor instances to test
        transpositions: List of transposition instances to test
        constraints_engine: CrossCipherConstraints instance
        cipher_num: Cipher number to decode (1 or 3)
        budget: Maximum strategies to evaluate
    
    Returns:
        List of valid strategies sorted by score
    """
    print("=" * 80)
    print(f"PHASE D: CONSTRAINED SEARCH - CIPHER {cipher_num}")
    print("=" * 80)
    
    # Get constraints
    print("\n[Step 1] Loading constraints...")
    constraints = constraints_engine.derive_cipher2_oracle_constraints()
    print(f"Constraints: {len(constraints)} from Cipher 1-2 overlaps")
    
    # Load cipher
    cipher = load_cipher(cipher_num)
    corpus = constraints_engine.corpus
    
    print(f"\n[Step 2] Testing {len(extractors)} extractors × {len(transpositions)} transpositions")
    print(f"Budget: {budget} strategies")
    print(f"Pre-filter: Check oracle constraints before full evaluation")
    print("-" * 80)
    
    valid_strategies = []
    tested_count = 0
    filtered_count = 0
    
    for extractor in extractors:
        for transposition in transpositions:
            # Pre-filter: check constraints before full evaluation
            passes, violation_rate = constraints_engine.validate_strategy(
                extractor, transposition, constraints
            )
            
            if not passes:
                filtered_count += 1
                continue
            
            # Full evaluation
            decoded = corpus.decode_with_extractor(cipher, extractor)
            transposed = transposition.apply(decoded)
            score_result = score_candidate(transposed)
            
            valid_strategies.append({
                'extractor': extractor.name,
                'transposition': transposition.name,
                'total_score': score_result['total_score'],
                'violation_rate': violation_rate,
                'decoded': transposed[:200],
                **score_result
            })
            
            tested_count += 1
            
            if tested_count >= budget:
                print(f"\n[Budget limit reached: {budget}]")
                break
        
        if tested_count >= budget:
            break
    
    print(f"\nFiltering complete:")
    print(f"  Tested: {tested_count}")
    print(f"  Filtered out: {filtered_count}")
    print(f"  Passed: {len(valid_strategies)}")
    
    # Sort by score
    valid_strategies.sort(key=lambda x: x['total_score'], reverse=True)
    
    return valid_strategies


def run_constrained_search(budget: int = 1000, cipher_num: int = 1):
    """Main constrained search execution."""
    print("=" * 80)
    print("PHASE D: CONSTRAINT-FILTERED SEARCH")
    print("=" * 80)
    
    # Load corpus
    print("\n[Step 1] Loading CANON_DOI...")
    try:
        corpus = CanonicalCorpus.load('corpus/CANON_DOI.json')
        print(f"Loaded: {corpus}")
    except FileNotFoundError:
        print("[ERROR] CANON_DOI.json not found")
        print("ACTION: Run 'python run_pipeline.py lock_corpus' first")
        return []
    
    # Create constraints engine
    print("\n[Step 2] Initializing constraints...")
    constraints_engine = CrossCipherConstraints(corpus)
    
    # Select extractors and transpositions
    print("\n[Step 3] Building search space...")
    
    # Use best extractors from Phases 5-7
    best_extractor_names = [
        'position_times_2',
        'cycle_every_5',
        'nth_letter_by_position',
        'reverse_position'
    ]
    extractors = [e for e in ALL_EXTRACTORS if e.name in best_extractor_names]
    
    # Use all transpositions (constraints will filter)
    transpositions = ALL_TRANSPOSITIONS[:20]  # Top 20 to keep budget sane
    
    print(f"Extractors: {len(extractors)}")
    print(f"Transpositions: {len(transpositions)}")
    print(f"Total combinations: {len(extractors) * len(transpositions)}")
    
    # Run search
    print("\n[Step 4] Running constrained search...")
    results = search_with_constraints(
        extractors, transpositions, constraints_engine, cipher_num, budget
    )
    
    # Save results
    print(f"\n[Step 5] Saving results...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_search_results(results, cipher_num, timestamp)
    
    # Summary
    print("\n" + "=" * 80)
    print("CONSTRAINED SEARCH COMPLETE")
    print("=" * 80)
    
    if results:
        print(f"\nTop 10 valid strategies:")
        for i, result in enumerate(results[:10], 1):
            print(f"{i:2d}. {result['extractor']:25s} + {result['transposition']:25s} | "
                  f"{result['total_score']:6.2f}/100 (violations: {result['violation_rate']:.2%})")
        
        best = results[0]
        print(f"\nBest strategy:")
        print(f"  {best['extractor']} + {best['transposition']}")
        print(f"  Score: {best['total_score']:.2f}/100")
        print(f"  Violation rate: {best['violation_rate']:.2%}")
    else:
        print("\n[WARNING] No strategies passed constraints!")
        print("ACTION: Relax constraint threshold or expand search space")
    
    return results


def save_search_results(results: List[Dict], cipher_num: int, timestamp: str):
    """Save constrained search results."""
    output_dir = Path("output/phaseD_best")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # CSV
    csv_file = output_dir / f"cipher{cipher_num}_constrained_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if results:
            fieldnames = ['rank', 'extractor', 'transposition', 'total_score',
                         'violation_rate', 'bigram', 'trigram', 'quadgram']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, result in enumerate(results, 1):
                row = {k: result.get(k, '') for k in fieldnames if k != 'rank'}
                row['rank'] = i
                writer.writerow(row)
    
    # Best stream
    if results:
        stream_file = output_dir / f"cipher{cipher_num}_best_stream_{timestamp}.txt"
        with open(stream_file, 'w', encoding='utf-8') as f:
            f.write(results[0]['decoded'])
    
    print(f"Results saved:")
    print(f"  CSV: {csv_file}")
    if results:
        print(f"  Best stream: {stream_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run constrained search")
    parser.add_argument('--budget', type=int, default=1000,
                       help='Maximum strategies to evaluate')
    parser.add_argument('--cipher', type=int, choices=[1,3], default=1,
                       help='Cipher number to decode')
    
    args = parser.parse_args()
    
    results = run_constrained_search(args.budget, args.cipher)
