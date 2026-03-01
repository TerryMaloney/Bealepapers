"""
FRAGMENT DETECTOR (Phase 3)
Search decoded streams for partial English words and meaningful fragments.
Focuses on 3-8 letter words and Beale cipher context.
"""

from strategy_runner import load_corpus, load_cipher1, extract_stream
import extractors
import transposition
import signal_score
from datetime import datetime


def search_for_fragments(stream, min_length=3, max_length=8):
    """
    Search for English word fragments in a character stream.
    
    Args:
        stream: Character stream to search
        min_length: Minimum fragment length (default 3)
        max_length: Maximum fragment length (default 8)
    
    Returns:
        Dictionary of found fragments with positions
    """
    fragments = signal_score.detect_word_fragments(stream)
    
    # Add position information
    fragment_positions = {}
    
    for word, count in fragments.items():
        positions = []
        start = 0
        while True:
            pos = stream.find(word, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        
        fragment_positions[word] = {
            'count': count,
            'positions': positions,
            'length': len(word)
        }
    
    return fragment_positions


def analyze_best_streams():
    """
    Analyze top-scoring streams from Phase 2/3 for fragments.
    """
    print("=" * 80)
    print("FRAGMENT DETECTOR - Phase 3")
    print("Searching for partial English words in decoded streams")
    print("=" * 80)
    
    # Load data
    corpus = load_corpus()
    cipher1 = load_cipher1()
    
    print(f"\nCorpus loaded: {len(corpus['master'])} words")
    print(f"Cipher 1 loaded: {len(cipher1)} numbers")
    
    # Best strategies to test
    strategies = [
        {'offset': 338, 'extractor': 'nth_letter_by_position', 'trans': 'every_2th', 'label': 'Phase 2 Best'},
        {'offset': 333, 'extractor': 'nth_letter_by_position', 'trans': 'every_2th', 'label': 'Phase 2 #2'},
        {'offset': 337, 'extractor': 'position_mod_offset_335', 'trans': 'reverse_all', 'label': 'Phase 3 Best'},
        {'offset': 338, 'extractor': 'nth_letter_by_position', 'trans': 'no', 'label': 'No transposition'},
        {'offset': 335, 'extractor': 'first_letter', 'trans': 'no', 'label': 'Simple first-letter'},
    ]
    
    print("\nAnalyzing streams for fragments...")
    print("-" * 80)
    
    results = []
    
    for config in strategies:
        ext = extractors.get_extractor(config['extractor'])
        trans_obj = transposition.get_transposition(config['trans'])
        
        # Generate stream (full 520 numbers)
        raw_stream = extract_stream(cipher1, corpus, ext, config['offset'], count=520)
        transformed_stream = trans_obj.apply(raw_stream)
        
        # Search for fragments
        fragments = search_for_fragments(transformed_stream)
        
        # Score the stream
        scores = signal_score.score_stream(transformed_stream, use_phase3_metrics=True)
        
        print(f"\n{config['label']}:")
        print(f"  Configuration: offset {config['offset']}, {config['extractor']}, {config['trans']}")
        print(f"  Score: {scores['total_score']:.2f}/100")
        print(f"  Fragments found: {len(fragments)}")
        
        if fragments:
            # Show top fragments by count
            sorted_frags = sorted(fragments.items(), key=lambda x: x[1]['count'], reverse=True)
            top_frags = sorted_frags[:5]
            frag_str = ', '.join([f"{w}({info['count']}x)" for w, info in top_frags])
            print(f"  Top fragments: {frag_str}")
        
        results.append({
            'config': config,
            'stream': transformed_stream,
            'fragments': fragments,
            'scores': scores
        })
    
    return results


def generate_fragment_report(results):
    """Generate detailed fragment analysis report"""
    filename = "output/fragment_analysis.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 3 FRAGMENT DETECTION ANALYSIS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE\n")
        f.write("-" * 80 + "\n")
        f.write("Search decoded streams for partial English words and meaningful fragments.\n")
        f.write("Detection of 3+ recognizable words suggests method is approaching plaintext.\n\n")
        f.write("Target fragments:\n")
        f.write("  - 3-letter common words: THE, AND, FOR, etc.\n")
        f.write("  - 4-letter words: THAT, WITH, FROM, etc.\n")
        f.write("  - Beale context: BEDFORD, COUNTY, VIRGINIA, TREASURE, etc.\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("FRAGMENT DETECTION RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results, 1):
            config = result['config']
            fragments = result['fragments']
            scores = result['scores']
            
            f.write(f"STRATEGY {i}: {config['label']}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Configuration:\n")
            f.write(f"  Offset:        {config['offset']}\n")
            f.write(f"  Extractor:     {config['extractor']}\n")
            f.write(f"  Transposition: {config['trans']}\n\n")
            
            f.write(f"Overall score: {scores['total_score']:.2f}/100\n")
            f.write(f"Fragment score: {scores['fragment_score']:.2f}/100\n")
            f.write(f"Fragments detected: {len(fragments)}\n\n")
            
            if fragments:
                # Group by length
                by_length = {}
                for word, info in fragments.items():
                    length = info['length']
                    if length not in by_length:
                        by_length[length] = []
                    by_length[length].append((word, info))
                
                # Report by length
                for length in sorted(by_length.keys()):
                    frags = by_length[length]
                    f.write(f"{length}-letter fragments ({len(frags)} found):\n")
                    
                    # Sort by count
                    sorted_frags = sorted(frags, key=lambda x: x[1]['count'], reverse=True)
                    
                    for word, info in sorted_frags[:10]:  # Top 10 per length
                        positions_str = ', '.join(map(str, info['positions'][:5]))
                        if len(info['positions']) > 5:
                            positions_str += f", ... (+{len(info['positions'])-5} more)"
                        f.write(f"  {word}: {info['count']}x at positions [{positions_str}]\n")
                    
                    f.write("\n")
                
                # Check for Beale context words
                beale_words = ['BEDFORD', 'COUNTY', 'VIRGINIA', 'TREASURE', 'BURIED', 'VAULT', 
                              'GOLD', 'SILVER', 'NORTH', 'SOUTH', 'MILES', 'FEET']
                found_context = [w for w in beale_words if w in fragments]
                
                if found_context:
                    f.write("BEALE CONTEXT WORDS DETECTED:\n")
                    for word in found_context:
                        info = fragments[word]
                        f.write(f"  {word}: {info['count']}x\n")
                    f.write("\n")
                    f.write("[!] SIGNIFICANT: Beale cipher context words detected.\n")
                    f.write("    This suggests partial decode success.\n\n")
            else:
                f.write("No fragments detected.\n\n")
            
            # Output sample
            stream = result['stream']
            f.write("Output stream (first 200 chars):\n")
            f.write(f"  {stream[:200]}\n\n")
            
            f.write("=" * 80 + "\n\n")
        
        # Summary
        f.write("SUMMARY\n")
        f.write("-" * 80 + "\n\n")
        
        total_fragments = sum(len(r['fragments']) for r in results)
        best_result = max(results, key=lambda x: len(x['fragments']))
        best_config = best_result['config']['label']
        best_count = len(best_result['fragments'])
        
        f.write(f"Total unique fragments across all strategies: {total_fragments}\n")
        f.write(f"Best strategy: {best_config} with {best_count} fragments\n\n")
        
        # Check for any Beale context words
        all_beale_words = set()
        beale_context = ['BEDFORD', 'COUNTY', 'VIRGINIA', 'TREASURE', 'BURIED', 'VAULT', 
                        'GOLD', 'SILVER', 'NORTH', 'SOUTH', 'MILES', 'FEET']
        
        for result in results:
            for word in beale_context:
                if word in result['fragments']:
                    all_beale_words.add(word)
        
        if all_beale_words:
            f.write(f"CRITICAL FINDING: {len(all_beale_words)} Beale context words detected\n")
            f.write(f"  Words: {', '.join(sorted(all_beale_words))}\n\n")
            f.write("VERDICT: Partial plaintext emergence detected.\n")
            f.write("Recommendation: Focus refinement on strategies showing context words.\n")
        elif total_fragments > 10:
            f.write("VERDICT: Common English fragments detected.\n")
            f.write("Signal is present but not yet yielding full plaintext.\n")
            f.write("Recommendation: Continue method refinement.\n")
        else:
            f.write("VERDICT: Minimal fragment detection.\n")
            f.write("Current methods not producing recognizable English.\n")
            f.write("Recommendation: Consider alternative corpus or method hypothesis.\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"\nFragment analysis report saved to: {filename}")
    return filename


if __name__ == "__main__":
    results = analyze_best_streams()
    report_file = generate_fragment_report(results)
    
    print("\n" + "=" * 80)
    print("FRAGMENT DETECTION COMPLETE")
    print("=" * 80)
    
    # Summary
    total_frags = sum(len(r['fragments']) for r in results)
    print(f"\nTotal unique fragments detected: {total_frags}")
    
    for result in results:
        config = result['config']
        frag_count = len(result['fragments'])
        score = result['scores']['total_score']
        print(f"  {config['label']}: {frag_count} fragments, score {score:.2f}/100")
    
    print(f"\nFull report: {report_file}")
    print("\nNext step: Run vdr_only_full_test.py to validate VDR primary key hypothesis")
