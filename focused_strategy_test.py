"""
FOCUSED STRATEGY TEST (Phase 3)
Test new Phase 3 extractor variants with top offsets and transpositions.

Matrix: 5 offsets × 8 new extractors × 5 transpositions = 200 combinations
"""

from strategy_runner import load_corpus, load_cipher1, extract_stream
import extractors
import transposition
import signal_score
from datetime import datetime


def run_focused_test(sample_size=200):
    """
    Test new Phase 3 extractor variants with best offsets and transpositions.
    
    Args:
        sample_size: Number of cipher numbers to test (default 200)
    
    Returns:
        List of results sorted by score
    """
    print("=" * 80)
    print("FOCUSED STRATEGY TEST - Phase 3")
    print("Testing new extractor variants with top configurations")
    print("=" * 80)
    
    # Load data
    corpus = load_corpus()
    cipher1 = load_cipher1()
    
    print(f"\nCorpus loaded: {len(corpus['master'])} words")
    print(f"Cipher 1 loaded: {len(cipher1)} numbers")
    print(f"Testing on first {sample_size} numbers")
    
    # Top 5 offsets from Phase 2
    top_offsets = [338, 333, 337, 330, 332]
    
    # New Phase 3 extractors (the 8 advanced position-based ones)
    new_extractor_names = [
        'position_plus_offset_335',
        'position_times_2',
        'position_times_3',
        'alternating_first_last',
        'cycle_every_5',
        'cycle_every_7',
        'reverse_position',
        'position_mod_offset_335'
    ]
    
    # Top 5 transpositions from Phase 2
    top_trans_names = [
        'every_2th',
        'reverse_all',
        'zigzag_w13',
        'every_7th',
        'columnar_w7'
    ]
    
    # Get extractor and transposition objects
    new_extractors = [extractors.get_extractor(name) for name in new_extractor_names]
    top_trans = [transposition.get_transposition(name) for name in top_trans_names]
    
    print(f"\nTesting matrix:")
    print(f"  Offsets: {len(top_offsets)}")
    print(f"  New extractors: {len(new_extractors)}")
    print(f"  Transpositions: {len(top_trans)}")
    print(f"  Total combinations: {len(top_offsets) * len(new_extractors) * len(top_trans)}")
    print("-" * 80)
    
    results = []
    total_tests = len(top_offsets) * len(new_extractors) * len(top_trans)
    test_count = 0
    
    for offset in top_offsets:
        for ext in new_extractors:
            for trans_obj in top_trans:
                test_count += 1
                
                # Extract stream
                raw_stream = extract_stream(cipher1, corpus, ext, offset, sample_size)
                
                # Apply transposition
                transformed_stream = trans_obj.apply(raw_stream)
                
                # Score with Phase 3 metrics
                scores = signal_score.score_stream(transformed_stream, use_phase3_metrics=True)
                
                result = {
                    'offset': offset,
                    'extractor': ext.name,
                    'transposition': trans_obj.name,
                    'total_score': scores['total_score'],
                    'scores': scores,
                    'stream': transformed_stream
                }
                
                results.append(result)
                
                # Progress indicator
                if test_count % 20 == 0:
                    print(f"Progress: {test_count}/{total_tests} tests completed...")
    
    # Sort by total score
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    print(f"\nAll {total_tests} tests completed!")
    print("-" * 80)
    
    return results


def generate_focused_report(results):
    """Generate detailed report of focused strategy test results"""
    filename = "output/refined_extractors.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 3 REFINED EXTRACTOR RESULTS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE\n")
        f.write("-" * 80 + "\n")
        f.write("Phase 2 identified nth_letter_by_position as the best extractor (42.96/100).\n")
        f.write("Phase 3 tests 8 new position-based variants to find better extraction rules.\n\n")
        f.write("Test matrix: 5 offsets × 8 extractors × 5 transpositions = 200 combinations\n")
        f.write("Tested on first 200 cipher numbers.\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("TOP 20 RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        # Top 20 results
        for i, result in enumerate(results[:20], 1):
            f.write(f"RANK #{i}  Score: {result['total_score']:.2f}/100\n")
            f.write("-" * 80 + "\n")
            f.write(f"Configuration:\n")
            f.write(f"  Offset:        {result['offset']}\n")
            f.write(f"  Extractor:     {result['extractor']}\n")
            f.write(f"  Transposition: {result['transposition']}\n\n")
            
            scores = result['scores']
            f.write("Detailed scores:\n")
            f.write(f"  Bigram:        {scores['bigram_score']:6.2f}/100\n")
            f.write(f"  Trigram:       {scores['trigram_score']:6.2f}/100\n")
            f.write(f"  Quadgram:      {scores['quadgram_score']:6.2f}/100\n")
            f.write(f"  Vowel ratio:   {scores['vowel_ratio_score']:6.2f}/100\n")
            f.write(f"  Dictionary:    {scores['dictionary_score']:6.2f}/100\n")
            f.write(f"  Letter freq:   {scores['letter_freq_score']:6.2f}/100\n")
            f.write(f"  Entropy:       {scores['entropy_score']:6.2f}/100\n")
            f.write(f"  Fragments:     {scores['fragment_score']:6.2f}/100\n\n")
            
            # Output sample
            stream = result['stream']
            f.write(f"Output (first 100 chars): {stream[:100]}\n")
            
            # Fragments
            fragments = signal_score.detect_word_fragments(stream)
            if fragments:
                sorted_frags = sorted(fragments.items(), key=lambda x: x[1], reverse=True)
                frag_str = ', '.join([f"{w}({c}x)" for w, c in sorted_frags[:10]])
                f.write(f"Fragments: {frag_str}\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
        
        # Analysis by extractor
        f.write("ANALYSIS BY EXTRACTOR\n")
        f.write("-" * 80 + "\n\n")
        
        extractor_scores = {}
        for result in results:
            ext_name = result['extractor']
            if ext_name not in extractor_scores:
                extractor_scores[ext_name] = []
            extractor_scores[ext_name].append(result['total_score'])
        
        # Calculate averages
        extractor_avgs = []
        for ext_name, scores_list in extractor_scores.items():
            avg = sum(scores_list) / len(scores_list)
            max_score = max(scores_list)
            extractor_avgs.append((ext_name, avg, max_score))
        
        # Sort by average
        extractor_avgs.sort(key=lambda x: x[1], reverse=True)
        
        f.write(f"{'Extractor':<35} {'Avg Score':>12} {'Max Score':>12}\n")
        f.write("-" * 80 + "\n")
        for ext_name, avg, max_score in extractor_avgs:
            f.write(f"{ext_name:<35} {avg:>12.2f} {max_score:>12.2f}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("COMPARISON TO PHASE 2 BASELINE\n")
        f.write("=" * 80 + "\n\n")
        
        phase2_baseline = 42.96
        best_phase3 = results[0]['total_score']
        improvement = best_phase3 - phase2_baseline
        
        f.write(f"Phase 2 best (nth_letter_by_position + every_2th): {phase2_baseline:.2f}/100\n")
        f.write(f"Phase 3 best ({results[0]['extractor']} + {results[0]['transposition']}): {best_phase3:.2f}/100\n")
        f.write(f"Improvement: {improvement:+.2f} points\n\n")
        
        if improvement > 5:
            f.write("VERDICT: Significant improvement found\n")
            f.write(f"New extractor '{results[0]['extractor']}' outperforms Phase 2 baseline.\n")
            f.write("Recommendation: Use this extraction rule for full-cipher test.\n")
        elif improvement > 0:
            f.write("VERDICT: Marginal improvement\n")
            f.write("New extractors perform slightly better than Phase 2 baseline.\n")
            f.write("Recommendation: Continue with Phase 2 method, test transposition refinement.\n")
        else:
            f.write("VERDICT: No improvement\n")
            f.write("Phase 2 extraction rule (nth_letter_by_position) remains best.\n")
            f.write("Recommendation: Focus on transposition layer or corpus refinement.\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"\nReport saved to: {filename}")
    return filename


if __name__ == "__main__":
    results = run_focused_test(sample_size=200)
    report_file = generate_focused_report(results)
    
    print("\n" + "=" * 80)
    print("FOCUSED STRATEGY TEST COMPLETE")
    print("=" * 80)
    
    # Show top 5 results
    print("\nTop 5 new extractor strategies:")
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result['extractor']:<35} + {result['transposition']:<20} "
              f"(offset {result['offset']}) = {result['total_score']:.2f}/100")
    
    phase2_best = 42.96
    phase3_best = results[0]['total_score']
    
    print(f"\nPhase 2 baseline: {phase2_best:.2f}/100")
    print(f"Phase 3 best:     {phase3_best:.2f}/100")
    print(f"Change:           {phase3_best - phase2_best:+.2f} points")
    
    print(f"\nFull report: {report_file}")
