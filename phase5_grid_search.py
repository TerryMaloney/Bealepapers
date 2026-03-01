"""
PHASE 5 GRID SEARCH (Stage 2)
Test ~1,000 strategies: new extractors with best transpositions + best extractors with new transpositions.
"""

from phase5_runner import Strategy, evaluate_strategy, load_doi_from_beale, load_cipher1, save_results_csv, save_top20_readable
import extractors
import transposition
from datetime import datetime


def run_grid_search():
    """Run comprehensive grid search without substitution layer"""
    print("=" * 80)
    print("PHASE 5 GRID SEARCH - Stage 2")
    print("Testing ~1,000 extraction + transposition strategies")
    print("=" * 80)
    
    # Load data
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    
    print(f"\nDOI corpus: {len(doi_words)} words")
    print(f"Cipher 1: {len(cipher1)} numbers")
    
    # Define test matrix
    # Phase 5 extractors: indices 23-54 (32 extractors)
    phase5_extractors = extractors.ALL_EXTRACTORS[23:55]
    
    # Best 10 existing transpositions from Phase 2-4
    best_trans_names = [
        'every_2th', 'every_3th', 'railfence_2', 'railfence_3', 'reverse_all',
        'columnar_w7', 'zigzag_w13', 'every_7th', 'columnar_w5', 'chunk_reverse_3'
    ]
    best_trans = [transposition.get_transposition(name) for name in best_trans_names]
    
    # Best 23 existing extractors from Phase 1-3 (indices 0-22)
    best_extractors = extractors.ALL_EXTRACTORS[:23]
    
    # Phase 5 transpositions: indices 34-63 (29 transpositions)
    phase5_trans = transposition.ALL_TRANSPOSITIONS[34:63]
    
    print(f"\nTest matrix:")
    print(f"  Set 1: {len(phase5_extractors)} Phase 5 extractors x {len(best_trans)} best trans = {len(phase5_extractors) * len(best_trans)}")
    print(f"  Set 2: {len(best_extractors)} best extractors x {len(phase5_trans)} Phase 5 trans = {len(best_extractors) * len(phase5_trans)}")
    print(f"  Total: {len(phase5_extractors) * len(best_trans) + len(best_extractors) * len(phase5_trans)} strategies")
    print("-" * 80)
    
    results = []
    test_count = 0
    total_tests = len(phase5_extractors) * len(best_trans) + len(best_extractors) * len(phase5_trans)
    
    # Set 1: Phase 5 extractors with best transpositions
    print("\nSet 1: Testing Phase 5 extractors...")
    for ext in phase5_extractors:
        for trans in best_trans:
            test_count += 1
            
            strategy = Strategy(ext, trans, sub=None)
            result = evaluate_strategy(strategy, cipher1, doi_words)
            results.append(result)
            
            if test_count % 50 == 0:
                print(f"  Progress: {test_count}/{total_tests} tests...")
    
    # Set 2: Best extractors with Phase 5 transpositions
    print("\nSet 2: Testing Phase 5 transpositions...")
    for ext in best_extractors:
        for trans in phase5_trans:
            test_count += 1
            
            strategy = Strategy(ext, trans, sub=None)
            result = evaluate_strategy(strategy, cipher1, doi_words)
            results.append(result)
            
            if test_count % 50 == 0:
                print(f"  Progress: {test_count}/{total_tests} tests...")
    
    print(f"\nAll {test_count} tests completed!")
    
    # Sort by score
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"output/phase5/phase5_grid_results_{timestamp}.csv"
    top20_file = f"output/phase5/phase5_grid_top20_{timestamp}.txt"
    
    save_results_csv(results, csv_file)
    save_top20_readable(results, top20_file)
    
    print(f"\nResults saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Top 20: {top20_file}")
    
    return results


if __name__ == "__main__":
    results = run_grid_search()
    
    print("\n" + "=" * 80)
    print("GRID SEARCH COMPLETE")
    print("=" * 80)
    
    print(f"\nTop 10 strategies (no substitution):")
    for i, result in enumerate(results[:10], 1):
        print(f"{i:2d}. {result['extractor']:<30} + {result['transposition']:<20} = {result['total_score']:.2f}/100")
    
    best = results[0]
    print(f"\nBest score: {best['total_score']:.2f}/100")
    print(f"Configuration: {best['extractor']} + {best['transposition']}")
    print(f"Coverage: {best['coverage']:.1f}%")
    print(f"Fragments: {len(best['fragments'])}")
    
    print("\nPhase 4 baseline: 34.38/100")
    print(f"Phase 5 grid best: {best['total_score']:.2f}/100")
    print(f"Improvement: {best['total_score'] - 34.38:+.2f} points")
    
    print("\nNext: Run phase5_caesar_sweep.py on top 50 strategies")
