"""
PHASE 6 TASK B: Optimal Segment Configuration Test
Test the best extractor per segment (from Phase 5 analysis) with top 10 transpositions.
"""

from phase6_stitched_decoder import StitchedStrategy, evaluate_stitched_strategy, load_doi_from_beale, load_cipher1, save_results_csv, save_top20_readable
import extractors
import transposition
from datetime import datetime


def run_optimal_configuration_test():
    """Test Phase 5 best-per-segment extractors with top transpositions"""
    print("=" * 80)
    print("PHASE 6 TASK B: OPTIMAL SEGMENT CONFIGURATION")
    print("Testing segment-specific extraction hypothesis")
    print("=" * 80)
    
    # Load data
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    
    print(f"\nDOI corpus: {len(doi_words)} words")
    print(f"Cipher 1: {len(cipher1)} numbers")
    
    # Phase 5 best extractors per segment
    print("\n" + "-" * 80)
    print("SEGMENT-SPECIFIC EXTRACTORS (from Phase 5 analysis)")
    print("-" * 80)
    
    segment_config = {
        1: extractors.get_extractor('reverse_position'),      # Segment 1: 37.74/100
        2: extractors.get_extractor('gen_pos_a7_b2'),          # Segment 2: 34.70/100
        3: extractors.get_extractor('xor_position'),           # Segment 3: 38.76/100
        4: extractors.get_extractor('gen_pos_a3_b1'),          # Segment 4: 44.31/100 (BEST)
        5: extractors.get_extractor('gen_pos_a7_b5')           # Segment 5: 36.35/100
    }
    
    print("Segment 1 (0-99):    reverse_position     (37.74/100 when tested alone)")
    print("Segment 2 (100-199): gen_pos_a7_b2        (34.70/100 when tested alone)")
    print("Segment 3 (200-299): xor_position         (38.76/100 when tested alone)")
    print("Segment 4 (300-399): gen_pos_a3_b1        (44.31/100 when tested alone) <-- BEST")
    print("Segment 5 (400-519): gen_pos_a7_b5        (36.35/100 when tested alone)")
    
    # Top 10 transpositions from Phase 5
    top_trans_names = [
        'rect_w13_spiral_ccw',
        'rect_w40_diagonal',
        'chunk_reverse_3',
        'rect_w40_spiral_cw',
        'every_3th',
        'rect_w40_spiral_ccw',
        'rect_w26_spiral_ccw',
        'double_columnar_w7_columnar_w11',
        'rect_w20_spiral_ccw',
        'rect_w10_diagonal'
    ]
    
    top_trans = [transposition.get_transposition(name) for name in top_trans_names]
    
    print(f"\nTop {len(top_trans)} transpositions to test:")
    for i, t in enumerate(top_trans, 1):
        print(f"  {i}. {t.name}")
    
    print(f"\nTotal tests: {len(top_trans)}")
    print("-" * 80)
    
    # Baseline for comparison
    baseline_score = 37.28
    print(f"\nBaseline (Phase 5 best, uniform extraction): {baseline_score:.2f}/100")
    print("  Extractor: cycle_every_5")
    print("  Transposition: rect_w13_spiral_ccw")
    print("")
    
    # Run tests
    results = []
    
    print("Running stitched decoder tests...")
    for i, trans in enumerate(top_trans, 1):
        strategy = StitchedStrategy(segment_config, trans)
        result = evaluate_stitched_strategy(strategy, cipher1, doi_words)
        results.append(result)
        
        score = result['total_score']
        improvement = score - baseline_score
        status = "BREAKTHROUGH!" if score > 40 else "progress" if improvement > 0 else "no change"
        
        print(f"  {i}/{len(top_trans)}: {trans.name:<30} = {score:5.2f}/100 ({improvement:+.2f}) [{status}]")
    
    print(f"\nAll {len(results)} tests completed!")
    
    # Sort by score
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"output/phase6/phase6_optimal_results_{timestamp}.csv"
    top20_file = f"output/phase6/phase6_optimal_top10_{timestamp}.txt"
    
    save_results_csv(results, csv_file)
    save_top20_readable(results, top20_file, baseline_score=baseline_score)
    
    print(f"\nResults saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Top 10: {top20_file}")
    
    return results, baseline_score


if __name__ == "__main__":
    results, baseline = run_optimal_configuration_test()
    
    print("\n" + "=" * 80)
    print("TASK B COMPLETE: OPTIMAL CONFIGURATION TEST")
    print("=" * 80)
    
    best = results[0]
    improvement = best['total_score'] - baseline
    
    print(f"\nBest stitched score: {best['total_score']:.2f}/100")
    print(f"Phase 5 baseline:    {baseline:.2f}/100")
    print(f"Improvement:         {improvement:+.2f} points")
    
    print(f"\nBest configuration:")
    print(f"  {best['extractor_config']}")
    print(f"  Transposition: {best['transposition']}")
    print(f"  Coverage: {best['coverage']:.1f}%")
    
    # Verdict
    print("\n" + "-" * 80)
    print("VERDICT:")
    print("-" * 80)
    
    if best['total_score'] > 40:
        print("BREAKTHROUGH! Score exceeded 40/100.")
        print("Segment-specific extraction hypothesis CONFIRMED.")
        print("The cipher uses different encoding rules for different segments.")
    elif improvement > 1.0:
        print("PROGRESS: Stitched decoder shows improvement over uniform extraction.")
        print("Hypothesis partially confirmed - continue beam search (Task C).")
    elif improvement > 0:
        print("MARGINAL: Slight improvement, but not significant.")
        print("Segment hypothesis weakly supported - continue testing.")
    else:
        print("NO IMPROVEMENT: Stitched decoder performs same or worse than baseline.")
        print("Segment-specific extraction hypothesis DISPROVEN for these extractors.")
        print("May need to test alternative boundaries or extractors.")
    
    print("\nNext: Run phase6_beam_search.py (Task C) for deeper exploration")
