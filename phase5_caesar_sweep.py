"""
PHASE 5 CAESAR SWEEP (Stage 3)
Test top 50 strategies from grid search with all 26 Caesar shifts.
"""

import csv
from phase5_runner import Strategy, evaluate_strategy, load_doi_from_beale, load_cipher1, save_results_csv, save_top20_readable
import extractors
import transposition
import substitution
from datetime import datetime


def load_top_strategies_from_grid(grid_csv_file, count=50):
    """Load top N strategies from grid search results"""
    strategies = []
    
    with open(grid_csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= count:
                break
            
            ext = extractors.get_extractor(row['extractor'])
            trans = transposition.get_transposition(row['transposition'])
            
            if ext and trans:
                strategies.append({
                    'extractor': ext,
                    'transposition': trans,
                    'base_score': float(row['total_score'])
                })
    
    return strategies


def run_caesar_sweep(grid_csv_file):
    """Run Caesar sweep on top 50 strategies from grid search"""
    print("=" * 80)
    print("PHASE 5 CAESAR SWEEP - Stage 3")
    print("Testing top 50 strategies with all 26 Caesar shifts")
    print("=" * 80)
    
    # Load data
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    
    # Load top 50 from grid search
    print(f"\nLoading top 50 strategies from: {grid_csv_file}")
    top_strategies = load_top_strategies_from_grid(grid_csv_file, count=50)
    print(f"Loaded {len(top_strategies)} strategies")
    
    # Generate all Caesar shifts
    all_caesar = substitution.generate_all_caesar()
    print(f"Caesar shifts: {len(all_caesar)}")
    
    total_tests = len(top_strategies) * len(all_caesar)
    print(f"\nTotal tests: {len(top_strategies)} strategies × {len(all_caesar)} shifts = {total_tests}")
    print("-" * 80)
    
    results = []
    test_count = 0
    
    for i, strat_info in enumerate(top_strategies, 1):
        ext = strat_info['extractor']
        trans = strat_info['transposition']
        base_score = strat_info['base_score']
        
        print(f"\nStrategy {i}/50: {ext.name} + {trans.name} (base: {base_score:.2f})")
        
        for caesar in all_caesar:
            test_count += 1
            
            strategy = Strategy(ext, trans, sub=caesar)
            result = evaluate_strategy(strategy, cipher1, doi_words)
            results.append(result)
            
            if test_count % 100 == 0:
                print(f"  Progress: {test_count}/{total_tests} tests...")
    
    print(f"\nAll {test_count} tests completed!")
    
    # Sort by score
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"output/phase5/phase5_caesar_results_{timestamp}.csv"
    top20_file = f"output/phase5/phase5_caesar_top20_{timestamp}.txt"
    
    save_results_csv(results, csv_file)
    save_top20_readable(results, top20_file)
    
    print(f"\nResults saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Top 20: {top20_file}")
    
    return results


if __name__ == "__main__":
    # Find most recent grid search results
    import glob
    grid_files = glob.glob("output/phase5/phase5_grid_results_*.csv")
    
    if not grid_files:
        print("ERROR: No grid search results found!")
        print("Please run phase5_grid_search.py first.")
        exit(1)
    
    grid_file = max(grid_files)  # Most recent
    print(f"Using grid search results: {grid_file}\n")
    
    results = run_caesar_sweep(grid_file)
    
    print("\n" + "=" * 80)
    print("CAESAR SWEEP COMPLETE")
    print("=" * 80)
    
    print(f"\nTop 10 strategies with Caesar:")
    for i, result in enumerate(results[:10], 1):
        print(f"{i:2d}. {result['extractor']:<30} + {result['transposition']:<20} + {result['substitution']:<10} = {result['total_score']:.2f}/100")
    
    best = results[0]
    print(f"\nBest score: {best['total_score']:.2f}/100")
    print(f"Configuration: {best['extractor']} + {best['transposition']} + {best['substitution']}")
    print(f"Coverage: {best['coverage']:.1f}%")
    
    # Find best without Caesar (shift 0) for comparison
    no_caesar_best = max([r for r in results if r['substitution'] == 'caesar_0'], 
                         key=lambda x: x['total_score'])
    
    print(f"\nBest without Caesar (shift 0): {no_caesar_best['total_score']:.2f}/100")
    print(f"Best with Caesar: {best['total_score']:.2f}/100")
    print(f"Caesar improvement: {best['total_score'] - no_caesar_best['total_score']:+.2f} points")
    
    print("\nNext: Run phase5_vigenere_search.py on top 20 strategies")
