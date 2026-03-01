"""
SEGMENT RUNNER (Phase 5 Stage 6)
Test segment-specific strategies with beam search.
"""

from phase5_runner import Strategy, load_doi_from_beale, load_cipher1, save_results_csv
import extractors
import transposition
import signal_score
from datetime import datetime


def extract_segment(cipher_numbers, doi_words, extractor, start, end):
    """Extract a specific segment"""
    stream = []
    
    for position in range(start, end):
        if position >= len(cipher_numbers):
            break
        
        cipher_num = cipher_numbers[position]
        word_idx = cipher_num - 1
        
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            char = extractor.extract(word, word_idx, position, 'DOI')
            stream.append(char)
        else:
            stream.append('?')
    
    return ''.join(stream)


def score_segment(stream, use_phase3=True):
    """Score a segment stream"""
    scores = signal_score.score_stream(stream, use_phase3_metrics=use_phase3)
    return scores['total_score']


def run_segment_beam_search(beam_width=5):
    """Run segment-specific beam search"""
    print("=" * 80)
    print("PHASE 5 SEGMENT BEAM SEARCH - Stage 6")
    print(f"Beam width: {beam_width}")
    print("=" * 80)
    
    # Load data
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    
    # Define segments
    segments = [
        (0, 100, "seg1"),
        (100, 200, "seg2"),
        (200, 300, "seg3"),
        (300, 400, "seg4"),
        (400, 520, "seg5")
    ]
    
    print(f"\nSegments: {len(segments)}")
    for start, end, label in segments:
        print(f"  {label}: positions {start}-{end-1} ({end-start} numbers)")
    
    # Get all extractors
    all_extractors = extractors.ALL_EXTRACTORS
    print(f"\nTotal extractors to test per segment: {len(all_extractors)}")
    
    # Find best extractors for each segment
    print("\n" + "-" * 80)
    print("Finding best extractors per segment...")
    print("-" * 80)
    
    segment_best = {}
    
    for start, end, label in segments:
        print(f"\n{label} (positions {start}-{end-1}):")
        seg_numbers = cipher1[start:end]
        
        scores = []
        for ext in all_extractors:
            stream = extract_segment(cipher1, doi_words, ext, start, end)
            score = score_segment(stream)
            scores.append((ext, score))
        
        # Sort and keep top beam_width
        scores.sort(key=lambda x: x[1], reverse=True)
        segment_best[label] = scores[:beam_width]
        
        print(f"  Top {beam_width}:")
        for i, (ext, score) in enumerate(segment_best[label], 1):
            print(f"    {i}. {ext.name:<35} = {score:.2f}/100")
    
    # Test segment-specific combinations with global transposition
    print("\n" + "=" * 80)
    print("Testing segment combinations with transpositions...")
    print("=" * 80)
    
    # Get top 5 transpositions from grid search
    top_trans_names = ['rect_w13_spiral_ccw', 'rect_w40_diagonal', 'chunk_reverse_3', 
                       'rect_w40_spiral_cw', 'every_3th']
    top_trans = [transposition.get_transposition(name) for name in top_trans_names]
    
    results = []
    test_count = 0
    
    # For simplicity, test uniform extractors across all segments
    # (full combinatorial would be beam_width^5 = 3125 per transposition)
    for seg_label, seg_extractors in segment_best.items():
        for ext, seg_score in seg_extractors[:3]:  # Top 3 per segment
            for trans in top_trans:
                test_count += 1
                
                # Apply to full cipher
                strategy = Strategy(ext, trans, sub=None)
                
                # Extract full stream
                raw_stream = []
                for position, cipher_num in enumerate(cipher1):
                    word_idx = cipher_num - 1
                    if 0 <= word_idx < len(doi_words):
                        word = doi_words[word_idx]
                        char = ext.extract(word, word_idx, position, 'DOI')
                        raw_stream.append(char)
                    else:
                        raw_stream.append('?')
                
                raw_str = ''.join(raw_stream)
                final_stream = trans.apply(raw_str)
                
                # Score
                scores = signal_score.score_stream(final_stream, use_phase3_metrics=True)
                valid = sum(1 for c in raw_str if c != '?')
                coverage = (valid / len(raw_str)) * 100
                fragments = signal_score.detect_word_fragments(final_stream)
                
                results.append({
                    'strategy_name': f"{ext.name}+{trans.name}+segment_{seg_label}",
                    'extractor': ext.name,
                    'transposition': trans.name,
                    'substitution': 'none',
                    'segment_source': seg_label,
                    'total_score': scores['total_score'],
                    'bigram_score': scores['bigram_score'],
                    'trigram_score': scores['trigram_score'],
                    'quadgram_score': scores['quadgram_score'],
                    'vowel_score': scores['vowel_ratio_score'],
                    'dict_score': scores['dictionary_score'],
                    'letter_freq_score': scores['letter_freq_score'],
                    'entropy_score': scores['entropy_score'],
                    'fragment_score': scores['fragment_score'],
                    'coverage': coverage,
                    'valid_mappings': valid,
                    'fragments': fragments,
                    'final_stream': final_stream
                })
                
                if test_count % 20 == 0:
                    print(f"  Progress: {test_count} tests...")
    
    print(f"\nTotal segment tests: {test_count}")
    
    # Sort by score
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/phase5/phase5_segment_results_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 5 SEGMENT BEAM SEARCH RESULTS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total strategies tested: {len(results)}\n")
        f.write(f"Beam width: {beam_width}\n\n")
        
        f.write("SEGMENT ANALYSIS:\n")
        f.write("-" * 80 + "\n")
        for label, best_list in segment_best.items():
            f.write(f"\n{label}:\n")
            for i, (ext, score) in enumerate(best_list, 1):
                f.write(f"  {i}. {ext.name:<35} = {score:.2f}/100\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("TOP 20 SEGMENT-BASED STRATEGIES\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results[:20], 1):
            f.write(f"RANK #{i}  Score: {result['total_score']:.2f}/100\n")
            f.write("-" * 80 + "\n")
            f.write(f"Extractor:     {result['extractor']}\n")
            f.write(f"Transposition: {result['transposition']}\n")
            f.write(f"Segment:       {result['segment_source']}\n")
            f.write(f"Coverage:      {result['coverage']:.1f}%\n\n")
            
            stream = result['final_stream']
            f.write(f"Output (first 150 chars): {stream[:150]}\n")
            f.write("\n")
    
    print(f"\nResults saved to: {output_file}")
    
    return results, segment_best


if __name__ == "__main__":
    results, segment_best = run_segment_beam_search(beam_width=5)
    
    print("\n" + "=" * 80)
    print("SEGMENT BEAM SEARCH COMPLETE")
    print("=" * 80)
    
    print(f"\nTop 5 segment-based strategies:")
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result['extractor']:<35} + {result['transposition']:<20} = {result['total_score']:.2f}/100")
    
    best = results[0]
    print(f"\nBest segment strategy score: {best['total_score']:.2f}/100")
    print(f"Best overall Phase 5 score:  37.28/100")
