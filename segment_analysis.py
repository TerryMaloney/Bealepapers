"""
SEGMENT ANALYSIS (Phase 3)
Split Cipher 1 into segments and analyze each independently.
Detect structural breaks, method changes, or signal spikes.
"""

from strategy_runner import load_corpus, load_cipher1, extract_stream
import extractors
import transposition
import signal_score
from datetime import datetime


def analyze_segment(cipher_numbers, corpus, extractor, trans, offset, start, end, label):
    """
    Analyze a specific segment of the cipher.
    
    Args:
        cipher_numbers: Full list of cipher numbers
        corpus: Corpus dictionary with 'master' key
        extractor: Extractor object
        trans: Transposition object
        offset: VDR offset value
        start: Start index (inclusive)
        end: End index (exclusive)
        label: Segment label
    
    Returns:
        Dictionary with segment results
    """
    # Extract segment
    segment = cipher_numbers[start:end]
    
    # Get master word list and corpus info
    master = corpus['master']
    vdr_len = len(corpus['vdr'])
    doi_len = len(corpus['doi'])
    signers_len = len(corpus['signers'])
    
    # Extract raw stream using same logic as extract_stream from strategy_runner
    raw_stream = ""
    for i, cipher_num in enumerate(segment):
        # Apply offset logic (same as strategy_runner)
        if cipher_num <= offset:
            idx = cipher_num - 1
        else:
            idx = (cipher_num - offset) + vdr_len - 1
        
        # Handle out of range
        if idx < 0 or idx >= len(master):
            raw_stream += "?"
            continue
        
        word = master[idx]
        # Determine document source
        if idx < vdr_len:
            doc_source = 'VDR'
        elif idx < vdr_len + doi_len:
            doc_source = 'DOI'
        elif idx < vdr_len + doi_len + signers_len:
            doc_source = 'SIGNERS'
        else:
            doc_source = 'ARTICLES'
        
        # Use global position (start + i) for position-dependent extraction
        char = extractor.extract(word, idx, start + i, doc_source)
        raw_stream += char
    
    # Apply transposition
    transformed_stream = trans.apply(raw_stream)
    
    # Score with Phase 3 metrics
    scores = signal_score.score_stream(transformed_stream, use_phase3_metrics=True)
    
    # Additional analysis
    vowel_count = sum(1 for c in transformed_stream if c in 'AEIOU')
    consonant_count = sum(1 for c in transformed_stream if c.isalpha() and c not in 'AEIOU')
    vowel_ratio = vowel_count / (vowel_count + consonant_count) if (vowel_count + consonant_count) > 0 else 0
    
    fragments = signal_score.detect_word_fragments(transformed_stream)
    
    return {
        'segment': label,
        'start': start,
        'end': end,
        'length': end - start,
        'raw_stream': raw_stream,
        'transformed_stream': transformed_stream,
        'scores': scores,
        'vowel_ratio': round(vowel_ratio, 3),
        'fragments': fragments
    }


def run_segment_analysis():
    """
    Split Cipher 1 into 5 segments and analyze each.
    Identify where signal strengthens or degrades.
    """
    print("=" * 80)
    print("SEGMENT ANALYSIS - Phase 3")
    print("Detecting structural breaks and signal variations")
    print("=" * 80)
    
    # Load data
    corpus = load_corpus()
    cipher1 = load_cipher1()
    
    print(f"\nCorpus loaded: {len(corpus['master'])} words")
    print(f"Cipher 1 loaded: {len(cipher1)} numbers")
    
    # Define segments
    segments = [
        (0, 100, "Early cipher (1-100)"),
        (100, 200, "Mid-early (101-200)"),
        (200, 300, "Middle (201-300)"),
        (300, 400, "Mid-late (301-400)"),
        (400, 520, "Late cipher (401-520)")
    ]
    
    # Best strategy from Phase 2
    best_config = {
        'offset': 338,
        'extractor': 'nth_letter_by_position',
        'trans': 'every_2th'
    }
    
    ext = extractors.get_extractor(best_config['extractor'])
    trans_obj = transposition.get_transposition(best_config['trans'])
    
    print(f"\nTesting strategy: offset={best_config['offset']}, {best_config['extractor']}, {best_config['trans']}")
    print("-" * 80)
    
    results = []
    
    for start, end, label in segments:
        print(f"\nAnalyzing: {label}")
        
        result = analyze_segment(
            cipher1, corpus, ext, trans_obj, best_config['offset'],
            start, end, label
        )
        
        score = result['scores']['total_score']
        vowel_ratio = result['vowel_ratio']
        fragment_count = len(result['fragments'])
        
        print(f"  Score:          {score:.2f}/100")
        print(f"  Vowel ratio:    {vowel_ratio:.3f}")
        print(f"  Fragments:      {fragment_count} unique")
        
        results.append(result)
    
    return results


def generate_segment_report(results):
    """Generate detailed segment analysis report"""
    filename = "output/segment_analysis.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 3 SEGMENT ANALYSIS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE\n")
        f.write("-" * 80 + "\n")
        f.write("Full cipher test showed score degradation from 42.96 to ~35/100.\n")
        f.write("Segment analysis identifies WHERE the signal breaks down or changes.\n\n")
        f.write("A signal spike in one segment suggests the method works there.\n")
        f.write("Consistent scores suggest the method is uniform.\n")
        f.write("Progressive decay suggests wrong method or corpus misalignment.\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("SEGMENT SCORES\n")
        f.write("=" * 80 + "\n\n")
        
        # Summary table
        f.write(f"{'Segment':<25} {'Score':>10} {'Vowel Ratio':>15} {'Fragments':>12}\n")
        f.write("-" * 80 + "\n")
        
        for result in results:
            seg = result['segment']
            score = result['scores']['total_score']
            vowel = result['vowel_ratio']
            frag_count = len(result['fragments'])
            
            f.write(f"{seg:<25} {score:>10.2f} {vowel:>15.3f} {frag_count:>12}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED SEGMENT ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        baseline_score = results[0]['scores']['total_score']  # First segment as baseline
        
        for i, result in enumerate(results, 1):
            f.write(f"SEGMENT {i}: {result['segment']}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Cipher numbers: {result['start']+1} to {result['end']}\n")
            f.write(f"Length: {result['length']} numbers\n\n")
            
            scores = result['scores']
            f.write("Detailed scores:\n")
            f.write(f"  Bigram score:       {scores['bigram_score']:6.2f}/100\n")
            f.write(f"  Trigram score:      {scores['trigram_score']:6.2f}/100\n")
            f.write(f"  Quadgram score:     {scores['quadgram_score']:6.2f}/100\n")
            f.write(f"  Vowel ratio:        {scores['vowel_ratio_score']:6.2f}/100\n")
            f.write(f"  Dictionary hits:    {scores['dictionary_score']:6.2f}/100\n")
            f.write(f"  Letter frequency:   {scores['letter_freq_score']:6.2f}/100\n")
            f.write(f"  Entropy:            {scores['entropy_score']:6.2f}/100\n")
            f.write(f"  Fragment score:     {scores['fragment_score']:6.2f}/100\n")
            f.write(f"  TOTAL:              {scores['total_score']:6.2f}/100\n\n")
            
            # Change from baseline
            score_diff = scores['total_score'] - baseline_score
            f.write(f"Change from segment 1: {score_diff:+.2f} points\n\n")
            
            # Output sample
            stream = result['transformed_stream']
            f.write(f"Output stream ({len(stream)} chars):\n")
            f.write(f"  {stream[:80]}\n")
            if len(stream) > 80:
                f.write(f"  {stream[80:160]}\n")
            f.write("\n")
            
            # Fragments
            if result['fragments']:
                f.write(f"Fragments detected ({len(result['fragments'])} unique):\n")
                sorted_frags = sorted(result['fragments'].items(), key=lambda x: x[1], reverse=True)
                for word, count in sorted_frags[:15]:
                    f.write(f"  {word}: {count}x\n")
            else:
                f.write("Fragments detected: None\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
        
        # Trend analysis
        f.write("TREND ANALYSIS\n")
        f.write("-" * 80 + "\n\n")
        
        scores_list = [r['scores']['total_score'] for r in results]
        max_score = max(scores_list)
        min_score = min(scores_list)
        avg_score = sum(scores_list) / len(scores_list)
        max_segment = results[scores_list.index(max_score)]['segment']
        min_segment = results[scores_list.index(min_score)]['segment']
        
        f.write(f"Average segment score: {avg_score:.2f}/100\n")
        f.write(f"Highest score: {max_score:.2f}/100 ({max_segment})\n")
        f.write(f"Lowest score: {min_score:.2f}/100 ({min_segment})\n")
        f.write(f"Score range: {max_score - min_score:.2f} points\n\n")
        
        # Detect pattern
        if max_score - min_score < 5:
            f.write("PATTERN: Uniform signal across all segments\n")
            f.write("The method performs consistently throughout the cipher.\n")
            f.write("Recommendation: Method is valid but needs refinement (transposition/extraction).\n")
        elif scores_list.index(max_score) < 2:
            f.write("PATTERN: Signal strongest in early segments\n")
            f.write("The method works best on cipher numbers 1-200.\n")
            f.write("Recommendation: Investigate corpus alignment or method transition point.\n")
        elif scores_list.index(max_score) >= 2:
            f.write("PATTERN: Signal spike in middle/late segments\n")
            f.write("The method works better on later cipher numbers.\n")
            f.write("Recommendation: Different offset or extraction rule may apply to early cipher.\n")
        else:
            # Check for progressive decay
            first_half_avg = sum(scores_list[:2]) / 2
            second_half_avg = sum(scores_list[2:]) / (len(scores_list) - 2)
            
            if first_half_avg - second_half_avg > 5:
                f.write("PATTERN: Progressive signal decay\n")
                f.write("The method degrades as the cipher progresses.\n")
                f.write("Recommendation: Late cipher may use different corpus or method.\n")
            else:
                f.write("PATTERN: Variable signal (no clear trend)\n")
                f.write("The method's effectiveness varies unpredictably.\n")
                f.write("Recommendation: Test alternative extraction rules and transpositions.\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"\nSegment analysis report saved to: {filename}")
    return filename


if __name__ == "__main__":
    results = run_segment_analysis()
    report_file = generate_segment_report(results)
    
    print("\n" + "=" * 80)
    print("SEGMENT ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Results saved to: {report_file}")
    print("\nKey findings:")
    
    scores = [r['scores']['total_score'] for r in results]
    print(f"  Segment 1 (1-100):    {scores[0]:.2f}/100")
    print(f"  Segment 2 (101-200):  {scores[1]:.2f}/100")
    print(f"  Segment 3 (201-300):  {scores[2]:.2f}/100")
    print(f"  Segment 4 (301-400):  {scores[3]:.2f}/100")
    print(f"  Segment 5 (401-520):  {scores[4]:.2f}/100")
    
    print("\nNext steps:")
    print("1. Review segment_analysis.txt for detailed breakdown")
    print("2. If spike detected, focus refinement on that segment")
    print("3. Proceed to focused_strategy_test.py for new extractor variants")
