"""
PHASE 6 TASK D: Boundary Variation Testing
Test alternative segment boundaries to verify if 5-segment division is correct.
"""

from phase6_stitched_decoder import StitchedStrategy, evaluate_stitched_strategy, load_doi_from_beale, load_cipher1, save_results_csv
import extractors
import transposition
from datetime import datetime


def find_best_extractor_for_segment(cipher_numbers, doi_words, start, end, top_n=3):
    """Find best N extractors for a given segment"""
    all_extractors = extractors.ALL_EXTRACTORS
    scores = []
    
    for ext in all_extractors:
        stream = []
        for position in range(start, min(end, len(cipher_numbers))):
            cipher_num = cipher_numbers[position]
            word_idx = cipher_num - 1
            
            if 0 <= word_idx < len(doi_words):
                word = doi_words[word_idx]
                char = ext.extract(word, word_idx, position, 'DOI')
                stream.append(char)
            else:
                stream.append('?')
        
        if stream:
            import signal_score
            stream_str = ''.join(stream)
            score = signal_score.score_stream(stream_str, use_phase3_metrics=False)['total_score']
            scores.append((ext, score))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_n]


def test_segmentation(cipher_numbers, doi_words, segments, top_trans, segmentation_name):
    """Test a specific segmentation with best extractors per segment"""
    print(f"\n{'=' * 80}")
    print(f"TESTING SEGMENTATION: {segmentation_name}")
    print(f"{'=' * 80}")
    
    print(f"\nSegments ({len(segments)} total):")
    for start, end, seg_id in segments:
        print(f"  Segment {seg_id}: positions {start}-{end-1} ({end-start} numbers)")
    
    # Find best extractor for each segment
    print("\nFinding best extractors per segment...")
    segment_config = {}
    
    for start, end, seg_id in segments:
        best = find_best_extractor_for_segment(cipher_numbers, doi_words, start, end, top_n=1)
        if best:
            segment_config[seg_id] = best[0][0]
            print(f"  Segment {seg_id}: {best[0][0].name} (score: {best[0][1]:.2f}/100)")
    
    # Test with top transpositions
    print(f"\nTesting with top {len(top_trans)} transpositions...")
    results = []
    
    for i, trans in enumerate(top_trans, 1):
        strategy = StitchedStrategy(segment_config, trans, segments=segments)
        result = evaluate_stitched_strategy(strategy, cipher_numbers, doi_words)
        results.append(result)
        
        score = result['total_score']
        print(f"  {i}/{len(top_trans)}: {trans.name:<30} = {score:5.2f}/100")
    
    results.sort(key=lambda x: x['total_score'], reverse=True)
    return results


def run_boundary_test():
    """Test alternative boundary segmentations"""
    print("=" * 80)
    print("PHASE 6 TASK D: BOUNDARY VARIATION TEST")
    print("Testing alternative segment boundaries")
    print("=" * 80)
    
    # Load data
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    
    baseline_score = 37.28
    best_so_far = 37.88  # From Task C
    
    print(f"\nBaseline (Phase 5 uniform): {baseline_score:.2f}/100")
    print(f"Best so far (Task C):       {best_so_far:.2f}/100")
    
    # Top transpositions to test with each segmentation
    top_trans_names = [
        'rect_w26_spiral_ccw',
        'rect_w13_spiral_ccw',
        'rect_w40_diagonal',
        'chunk_reverse_3',
        'every_3th'
    ]
    
    top_trans = [transposition.get_transposition(name) for name in top_trans_names]
    
    # Define alternative segmentations
    segmentations = {
        '4_segments': [
            (0, 130, 1),
            (130, 260, 2),
            (260, 390, 3),
            (390, 520, 4)
        ],
        '3_segments': [
            (0, 173, 1),
            (173, 346, 2),
            (346, 520, 3)
        ],
        '6_segments': [
            (0, 87, 1),
            (87, 174, 2),
            (174, 261, 3),
            (261, 348, 4),
            (348, 435, 5),
            (435, 520, 6)
        ]
    }
    
    all_results = []
    
    # Test each segmentation
    for seg_name, segments in segmentations.items():
        results = test_segmentation(cipher1, doi_words, segments, top_trans, seg_name)
        
        best = results[0]
        improvement = best['total_score'] - baseline_score
        
        print(f"\nBest for {seg_name}: {best['total_score']:.2f}/100 ({improvement:+.2f} vs baseline)")
        
        all_results.extend(results)
    
    # Sort all results
    all_results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"output/phase6/phase6_boundary_results_{timestamp}.csv"
    
    save_results_csv(all_results, csv_file)
    
    print(f"\n{'=' * 80}")
    print(f"All boundary tests saved: {csv_file}")
    print(f"{'=' * 80}")
    
    return all_results, baseline_score


if __name__ == "__main__":
    results, baseline = run_boundary_test()
    
    print("\n" + "=" * 80)
    print("TASK D COMPLETE: BOUNDARY VARIATION TEST")
    print("=" * 80)
    
    best = results[0]
    improvement = best['total_score'] - baseline
    
    print(f"\nBest across all segmentations: {best['total_score']:.2f}/100")
    print(f"Phase 5 baseline:              {baseline:.2f}/100")
    print(f"Improvement:                   {improvement:+.2f} points")
    
    print(f"\nBest configuration:")
    print(f"  {best['extractor_config']}")
    print(f"  Transposition: {best['transposition']}")
    
    # Final analysis
    print("\n" + "-" * 80)
    print("BOUNDARY TEST VERDICT:")
    print("-" * 80)
    
    if best['total_score'] > 40:
        print("BREAKTHROUGH! Alternative segmentation breaks plateau.")
    elif improvement > 1.0:
        print("Significant improvement with alternative boundaries.")
        print("Suggests segment boundaries matter.")
    else:
        print("No significant improvement with alternative boundaries.")
        print("The 5-segment division was not the limiting factor.")
        print("\nConclusion: Segment-specific extraction does not break plateau.")
        print("The hypothesis that different segments use different rules is WEAK.")
    
    print("\nReady for final verdict report (Task E)")
