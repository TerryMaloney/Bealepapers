"""
PHASE 6 TASK C: Beam Search Across Segment Configurations
Since optimal config didn't break through, test variations focusing on segment 4.
"""

from phase6_stitched_decoder import StitchedStrategy, evaluate_stitched_strategy, load_doi_from_beale, load_cipher1, save_results_csv, save_top20_readable
import extractors
import transposition
from datetime import datetime


def run_beam_search():
    """Test variations of segment extractors with focus on segment 4"""
    print("=" * 80)
    print("PHASE 6 TASK C: BEAM SEARCH")
    print("Testing segment extractor variations (focus on segment 4)")
    print("=" * 80)
    
    # Load data
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    
    baseline_score = 37.28
    optimal_test_best = 37.12
    
    print(f"\nBaseline (Phase 5 uniform): {baseline_score:.2f}/100")
    print(f"Task B (optimal stitched):  {optimal_test_best:.2f}/100")
    print("")
    
    # Top 3 extractors per segment from Phase 5
    segment_options = {
        1: [
            extractors.get_extractor('reverse_position'),
            extractors.get_extractor('gen_pos_a7_b1'),
            extractors.get_extractor('gen_pos_a7_b2')
        ],
        2: [
            extractors.get_extractor('gen_pos_a7_b2'),
            extractors.get_extractor('gen_pos_a2_b1'),
            extractors.get_extractor('gen_pos_a7_b3')
        ],
        3: [
            extractors.get_extractor('xor_position'),
            extractors.get_extractor('gen_pos_a5_b2'),
            extractors.get_extractor('cycle_every_5')
        ],
        4: [
            extractors.get_extractor('gen_pos_a3_b1'),
            extractors.get_extractor('letter_at_cipher_mod'),
            extractors.get_extractor('letter_at_index_mod')
        ],
        5: [
            extractors.get_extractor('gen_pos_a7_b5'),
            extractors.get_extractor('cycle_every_7'),
            extractors.get_extractor('cmod_a1_b0_c2_m5')
        ]
    }
    
    print("Segment extractor options:")
    for seg_id, extractors_list in segment_options.items():
        print(f"  Segment {seg_id}: {', '.join([e.name for e in extractors_list])}")
    
    # Top 5 transpositions
    top_trans_names = [
        'rect_w13_spiral_ccw',
        'rect_w40_diagonal',
        'chunk_reverse_3',
        'rect_w26_spiral_ccw',
        'every_3th'
    ]
    
    top_trans = [transposition.get_transposition(name) for name in top_trans_names]
    
    print(f"\nTop {len(top_trans)} transpositions:")
    for t in top_trans:
        print(f"  - {t.name}")
    
    # Strategy: Fix segments 1,2,3,5 to their best, vary segment 4
    print("\n" + "-" * 80)
    print("STRATEGY: Fix segs 1,2,3,5 to best extractors, vary segment 4")
    print("-" * 80)
    
    fixed_config = {
        1: segment_options[1][0],  # reverse_position
        2: segment_options[2][0],  # gen_pos_a7_b2
        3: segment_options[3][0],  # xor_position
        5: segment_options[5][0]   # gen_pos_a7_b5
    }
    
    print("Fixed extractors:")
    for seg_id, ext in fixed_config.items():
        print(f"  Segment {seg_id}: {ext.name}")
    
    print("\nVarying segment 4:")
    for ext in segment_options[4]:
        print(f"  - {ext.name}")
    
    results = []
    test_count = 0
    total_tests = len(segment_options[4]) * len(top_trans)
    
    print(f"\nTotal tests: {total_tests}")
    print("-" * 80)
    
    for seg4_ext in segment_options[4]:
        print(f"\nTesting segment 4 with: {seg4_ext.name}")
        
        for trans in top_trans:
            test_count += 1
            
            # Build config with varied segment 4
            config = fixed_config.copy()
            config[4] = seg4_ext
            
            strategy = StitchedStrategy(config, trans)
            result = evaluate_stitched_strategy(strategy, cipher1, doi_words)
            results.append(result)
            
            score = result['total_score']
            improvement = score - baseline_score
            status = "BREAKTHROUGH!" if score > 40 else "progress" if improvement > 0 else "no change"
            
            print(f"  {test_count}/{total_tests}: {trans.name:<30} = {score:5.2f}/100 ({improvement:+.2f}) [{status}]")
    
    print(f"\n" + "=" * 80)
    print("ADDITIONAL TEST: All segments with same top extractor")
    print("=" * 80)
    
    # Also test: what if all segments use the same "best overall" extractor?
    # This is a sanity check
    print("\nTesting uniform extraction with best individual segment extractors...")
    
    for seg_id, extractors_list in segment_options.items():
        best_ext = extractors_list[0]
        
        uniform_config = {1: best_ext, 2: best_ext, 3: best_ext, 4: best_ext, 5: best_ext}
        
        for trans in top_trans[:3]:  # Just top 3 trans for this sanity check
            strategy = StitchedStrategy(uniform_config, trans)
            result = evaluate_stitched_strategy(strategy, cipher1, doi_words)
            results.append(result)
            
            score = result['total_score']
            print(f"  All segs with {best_ext.name:<25} + {trans.name:<25} = {score:5.2f}/100")
    
    print(f"\nAll tests completed! Total: {len(results)}")
    
    # Sort by score
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"output/phase6/phase6_beam_results_{timestamp}.csv"
    top20_file = f"output/phase6/phase6_beam_top20_{timestamp}.txt"
    
    save_results_csv(results, csv_file)
    save_top20_readable(results, top20_file, baseline_score=baseline_score)
    
    print(f"\nResults saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Top 20: {top20_file}")
    
    return results, baseline_score


if __name__ == "__main__":
    results, baseline = run_beam_search()
    
    print("\n" + "=" * 80)
    print("TASK C COMPLETE: BEAM SEARCH")
    print("=" * 80)
    
    best = results[0]
    improvement = best['total_score'] - baseline
    
    print(f"\nBest beam search score: {best['total_score']:.2f}/100")
    print(f"Phase 5 baseline:       {baseline:.2f}/100")
    print(f"Improvement:            {improvement:+.2f} points")
    
    print(f"\nBest configuration:")
    print(f"  {best['extractor_config']}")
    print(f"  Transposition: {best['transposition']}")
    
    # Analysis
    print("\n" + "-" * 80)
    print("ANALYSIS:")
    print("-" * 80)
    
    if best['total_score'] > 40:
        print("BREAKTHROUGH achieved through beam search!")
    elif improvement > 1.0:
        print("Significant improvement found. Continue optimization.")
    elif improvement > 0:
        print("Marginal improvement. Hypothesis weakly supported.")
    else:
        print("No improvement. Segment-specific hypothesis appears incorrect.")
        print("Consider:")
        print("  1. Testing alternative boundary segmentations (Task D)")
        print("  2. Re-examining the fundamental encoding assumptions")
        print("  3. Testing Theory C (wrong DOI version) or Theory D (word-level encoding)")
    
    print("\nNext: Run phase6_boundary_test.py (Task D) to test alternative segmentations")
