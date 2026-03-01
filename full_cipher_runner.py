"""
FULL CIPHER RUNNER (Phase 3)
Run top Phase 2 strategies on ALL 520 cipher numbers.
Compare scores to Phase 2 baseline (200 numbers).
"""

from strategy_runner import load_corpus, load_cipher1, extract_stream
import extractors
import transposition
import signal_score
from datetime import datetime


def run_full_strategy(cipher_numbers, corpus, extractor, trans, offset, count=520):
    """
    Run a complete strategy on specified number of cipher numbers.
    
    Args:
        cipher_numbers: List of cipher numbers
        corpus: Master word list
        extractor: Extractor object
        trans: Transposition object
        offset: VDR offset value
        count: Number of cipher numbers to process
    
    Returns:
        Dictionary with results
    """
    # Extract raw stream
    raw_stream = extract_stream(cipher_numbers, corpus, extractor, offset, count)
    
    # Apply transposition
    transformed_stream = trans.apply(raw_stream)
    
    # Score the result (use Phase 3 metrics)
    scores = signal_score.score_stream(transformed_stream, use_phase3_metrics=True)
    
    return {
        'offset': offset,
        'extractor': extractor.name,
        'transposition': trans.name,
        'raw_stream': raw_stream[:200],  # First 200 chars for inspection
        'transformed_stream': transformed_stream,
        'stream_length': len(transformed_stream),
        'scores': scores
    }


def run_comprehensive_full_test():
    """
    Run top Phase 2 strategies on full 520-number cipher.
    Compare to Phase 2 baseline (200 numbers).
    """
    print("=" * 80)
    print("FULL CIPHER RUNNER - Phase 3")
    print("Testing top strategies on ALL 520 cipher numbers")
    print("=" * 80)
    
    # Load data
    corpus = load_corpus()
    cipher1 = load_cipher1()
    
    print(f"\nCorpus loaded: {len(corpus)} words")
    print(f"Cipher 1 loaded: {len(cipher1)} numbers")
    
    # Top 5 strategies from Phase 2
    top_strategies = [
        {'offset': 338, 'extractor': 'nth_letter_by_position', 'trans': 'every_2th'},
        {'offset': 333, 'extractor': 'nth_letter_by_position', 'trans': 'every_2th'},
        {'offset': 337, 'extractor': 'nth_letter_by_position', 'trans': 'every_2th'},
        {'offset': 330, 'extractor': 'nth_letter_by_position', 'trans': 'every_2th'},
        {'offset': 332, 'extractor': 'nth_letter_by_position', 'trans': 'reverse_all'},
    ]
    
    # Phase 2 baseline scores (from strategy_results.txt)
    phase2_baseline = {
        '338_nth_letter_by_position_every_2th': 42.96,
        '333_nth_letter_by_position_every_2th': 42.89,
        '337_nth_letter_by_position_every_2th': 42.78,
        '330_nth_letter_by_position_every_2th': 42.54,
        '332_nth_letter_by_position_reverse_all': 42.41,
    }
    
    print("\nRunning strategies on full 520 numbers...")
    print("-" * 80)
    
    results = []
    
    for config in top_strategies:
        # Get extractor and transposition objects
        ext = extractors.get_extractor(config['extractor'])
        trans_obj = transposition.get_transposition(config['trans'])
        
        print(f"\nTesting: offset={config['offset']}, {config['extractor']}, {config['trans']}")
        
        # Run on full cipher (520 numbers)
        full_result = run_full_strategy(
            cipher1, corpus, ext, trans_obj, config['offset'], count=520
        )
        
        # Run on first 200 for comparison
        baseline_result = run_full_strategy(
            cipher1, corpus, ext, trans_obj, config['offset'], count=200
        )
        
        # Get Phase 2 baseline score
        strategy_key = f"{config['offset']}_{config['extractor']}_{config['trans']}"
        phase2_score = phase2_baseline.get(strategy_key, 0.0)
        
        # Calculate score changes
        full_score = full_result['scores']['total_score']
        baseline_score = baseline_result['scores']['total_score']
        
        score_change_from_phase2 = full_score - phase2_score
        score_change_baseline = full_score - baseline_score
        
        print(f"  Phase 2 (200 numbers):  {phase2_score:.2f}/100")
        print(f"  Current (200 numbers):  {baseline_score:.2f}/100")
        print(f"  Full cipher (520):      {full_score:.2f}/100")
        print(f"  Change from Phase 2:    {score_change_from_phase2:+.2f} points")
        
        results.append({
            'config': config,
            'full_result': full_result,
            'baseline_result': baseline_result,
            'phase2_score': phase2_score,
            'score_changes': {
                'from_phase2': score_change_from_phase2,
                'from_baseline': score_change_baseline
            }
        })
    
    return results


def generate_report(results):
    """Generate detailed report of full cipher results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output/full_cipher_results.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 3 FULL CIPHER RESULTS (520 numbers)\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("METHODOLOGY\n")
        f.write("-" * 80 + "\n")
        f.write("Phase 2 established that nth_letter_by_position + every_2th scored 42.96/100\n")
        f.write("on the first 200 cipher numbers (offset 338).\n\n")
        f.write("Phase 3 tests whether this signal holds across the FULL 520-number cipher.\n")
        f.write("A score increase suggests the method is correct.\n")
        f.write("A score decrease suggests the method works only on a subset.\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("RESULTS SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        
        # Sort by full cipher score
        sorted_results = sorted(results, key=lambda x: x['full_result']['scores']['total_score'], reverse=True)
        
        for i, result in enumerate(sorted_results, 1):
            config = result['config']
            full_res = result['full_result']
            phase2_score = result['phase2_score']
            score_change = result['score_changes']['from_phase2']
            
            f.write(f"RANK #{i}: offset {config['offset']}, {config['extractor']}, {config['trans']}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Phase 2 baseline (200 numbers):  {phase2_score:.2f}/100\n")
            f.write(f"Full cipher score (520 numbers):  {full_res['scores']['total_score']:.2f}/100\n")
            f.write(f"Score change:                     {score_change:+.2f} points\n\n")
            
            # Detailed scores
            scores = full_res['scores']
            f.write("Detailed metrics:\n")
            f.write(f"  Bigram score:       {scores['bigram_score']:6.2f}/100\n")
            f.write(f"  Trigram score:      {scores['trigram_score']:6.2f}/100\n")
            f.write(f"  Quadgram score:     {scores['quadgram_score']:6.2f}/100\n")
            f.write(f"  Vowel ratio:        {scores['vowel_ratio_score']:6.2f}/100\n")
            f.write(f"  Dictionary hits:    {scores['dictionary_score']:6.2f}/100\n")
            f.write(f"  Letter frequency:   {scores['letter_freq_score']:6.2f}/100\n")
            f.write(f"  Entropy:            {scores['entropy_score']:6.2f}/100\n")
            f.write(f"  Fragment score:     {scores['fragment_score']:6.2f}/100\n")
            f.write(f"  Word count:         {scores['word_count']}\n\n")
            
            # Output samples
            stream = full_res['transformed_stream']
            f.write("Output stream segments:\n")
            f.write(f"  Chars 1-100:    {stream[:100]}\n")
            f.write(f"  Chars 101-200:  {stream[100:200]}\n")
            f.write(f"  Chars 201-300:  {stream[200:300]}\n")
            f.write(f"  Chars 301-400:  {stream[300:400]}\n")
            f.write(f"  Chars 401-520:  {stream[400:]}\n\n")
            
            # Fragment detection
            fragments = signal_score.detect_word_fragments(stream)
            if fragments:
                f.write(f"Fragments detected ({len(fragments)} unique):\n")
                sorted_fragments = sorted(fragments.items(), key=lambda x: x[1], reverse=True)
                for word, count in sorted_fragments[:20]:
                    f.write(f"  {word}: {count}x\n")
            else:
                f.write("Fragments detected: None\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
        
        f.write("ANALYSIS\n")
        f.write("-" * 80 + "\n\n")
        
        # Calculate average score change
        avg_change = sum(r['score_changes']['from_phase2'] for r in results) / len(results)
        best_result = sorted_results[0]
        best_score = best_result['full_result']['scores']['total_score']
        
        f.write(f"Average score change from Phase 2: {avg_change:+.2f} points\n")
        f.write(f"Best full-cipher score: {best_score:.2f}/100\n\n")
        
        if avg_change > 2:
            f.write("VERDICT: Signal STRENGTHENS on full cipher\n")
            f.write("The position-dependent extraction method appears valid across all 520 numbers.\n")
            f.write("Recommendation: Continue with method refinement in Phase 3.\n")
        elif avg_change > -2:
            f.write("VERDICT: Signal MAINTAINS on full cipher\n")
            f.write("The method performs consistently across the full cipher.\n")
            f.write("Recommendation: Focus on transposition refinement and segment analysis.\n")
        else:
            f.write("VERDICT: Signal DEGRADES on full cipher\n")
            f.write("The method may only work on the first 200 numbers.\n")
            f.write("Recommendation: Investigate structural breaks via segment_analysis.py.\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"\nReport saved to: {filename}")
    return filename


if __name__ == "__main__":
    results = run_comprehensive_full_test()
    report_file = generate_report(results)
    
    print("\n" + "=" * 80)
    print("FULL CIPHER TEST COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {report_file}")
    print("\nNext steps:")
    print("1. Review full_cipher_results.txt for score changes")
    print("2. Run segment_analysis.py to detect structural breaks")
    print("3. If signal maintained, proceed to focused_strategy_test.py")
