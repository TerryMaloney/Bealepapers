"""
PHASE 7 G2: OUT-OF-RANGE NUMBER ANALYSIS
Test 4 hypotheses for the 10 numbers that exceed DOI word count (>1322).
"""

import re
from datetime import datetime
import extractors
import transposition
import signal_score


def load_doi_from_beale():
    """Load DOI exactly as used in previous phases"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    doi_line = lines[54]
    pattern = r'(\w+)\((\d+)\)'
    matches = re.findall(pattern, doi_line)
    max_num = max(int(num) for word, num in matches)
    words = [''] * (max_num + 1)
    for word, num in matches:
        words[int(num)] = word.lower()
    
    return words[1:]


def load_cipher1():
    """Load Cipher 1 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]


def analyze_oor_context():
    """Analyze the context around out-of-range numbers"""
    cipher1 = load_cipher1()
    doi_words = load_doi_from_beale()
    
    oor_numbers = [1431, 1496, 1629, 1701, 1706, 1780, 1817, 2018, 2160, 2906]
    oor_positions = [i for i, n in enumerate(cipher1) if n in oor_numbers]
    
    print("=" * 80)
    print("OUT-OF-RANGE NUMBER CONTEXT ANALYSIS")
    print("=" * 80)
    
    print(f"\nTotal OOR numbers: {len(oor_numbers)}")
    print(f"DOI word count: {len(doi_words)}")
    print(f"Cipher 1 length: {len(cipher1)}")
    print(f"\nOOR positions: {oor_positions}")
    print(f"Position distribution: min={min(oor_positions)}, max={max(oor_positions)}, spread={max(oor_positions)-min(oor_positions)}")
    
    print("\n" + "-" * 80)
    print("LOCAL CONTEXT (±5 cipher numbers)")
    print("-" * 80)
    
    for pos in oor_positions:
        start = max(0, pos - 5)
        end = min(len(cipher1), pos + 6)
        context = cipher1[start:end]
        oor_val = cipher1[pos]
        
        print(f"\nPosition {pos:3d}: cipher_number = {oor_val}")
        print(f"  Context: {context}")
        print(f"  OOR offset: {oor_val - len(doi_words)} beyond DOI")
    
    return oor_positions


def test_hypothesis_1_nulls(cipher1, doi_words, extractor, trans):
    """H1: Treat OOR as nulls/separators (drop them)"""
    oor_set = {1431, 1496, 1629, 1701, 1706, 1780, 1817, 2018, 2160, 2906}
    
    # Extract, skipping OOR positions
    stream = []
    for position, cipher_num in enumerate(cipher1):
        if cipher_num in oor_set:
            continue  # Skip OOR numbers
        
        word_idx = cipher_num - 1
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            char = extractor.extract(word, word_idx, position, 'DOI')
            stream.append(char)
    
    raw = ''.join(stream)
    final = trans.apply(raw)
    scores = signal_score.score_stream(final, use_phase3_metrics=True)
    
    return {
        'hypothesis': 'nulls_dropped',
        'stream_length': len(raw),
        'score': scores['total_score'],
        'stream': final
    }


def test_hypothesis_2_modulo(cipher1, doi_words, extractor, trans):
    """H2: Map OOR by modulo (n % 1322)"""
    stream = []
    
    for position, cipher_num in enumerate(cipher1):
        # Apply modulo to ALL numbers (or just OOR)
        mapped_num = ((cipher_num - 1) % len(doi_words)) + 1
        word_idx = mapped_num - 1
        
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            char = extractor.extract(word, word_idx, position, 'DOI')
            stream.append(char)
        else:
            stream.append('?')
    
    raw = ''.join(stream)
    final = trans.apply(raw)
    scores = signal_score.score_stream(final, use_phase3_metrics=True)
    
    return {
        'hypothesis': 'modulo_mapping',
        'stream_length': len(raw),
        'score': scores['total_score'],
        'stream': final
    }


def test_hypothesis_3_separators(cipher1, doi_words, extractor, trans):
    """H3: OOR numbers are block separators (reset transposition)"""
    oor_set = {1431, 1496, 1629, 1701, 1706, 1780, 1817, 2018, 2160, 2906}
    oor_positions = [i for i, n in enumerate(cipher1) if n in oor_set]
    
    # Split cipher into blocks between OOR markers
    blocks = []
    prev = 0
    for pos in oor_positions + [len(cipher1)]:
        if pos > prev:
            blocks.append((prev, pos))
        prev = pos + 1  # Skip the OOR marker itself
    
    # Extract and transpose each block independently
    final_stream = []
    for start, end in blocks:
        block_stream = []
        for position in range(start, end):
            cipher_num = cipher1[position]
            word_idx = cipher_num - 1
            
            if 0 <= word_idx < len(doi_words):
                word = doi_words[word_idx]
                char = extractor.extract(word, word_idx, position, 'DOI')
                block_stream.append(char)
            else:
                block_stream.append('?')
        
        # Apply transposition to this block only
        raw_block = ''.join(block_stream)
        transposed_block = trans.apply(raw_block)
        final_stream.append(transposed_block)
    
    final = ''.join(final_stream)
    scores = signal_score.score_stream(final, use_phase3_metrics=True)
    
    return {
        'hypothesis': 'block_separators',
        'stream_length': len(final),
        'block_count': len(blocks),
        'score': scores['total_score'],
        'stream': final
    }


def test_hypothesis_4_replacement(cipher1, doi_words, extractor, trans):
    """H4: Replace OOR with common letters (E, T, A)"""
    oor_set = {1431, 1496, 1629, 1701, 1706, 1780, 1817, 2018, 2160, 2906}
    common_letters = ['E', 'T', 'A', 'O', 'I', 'N', 'S', 'H', 'R', 'D']
    
    stream = []
    oor_count = 0
    
    for position, cipher_num in enumerate(cipher1):
        if cipher_num in oor_set:
            # Replace with common letter (cycle through)
            stream.append(common_letters[oor_count % len(common_letters)])
            oor_count += 1
        else:
            word_idx = cipher_num - 1
            if 0 <= word_idx < len(doi_words):
                word = doi_words[word_idx]
                char = extractor.extract(word, word_idx, position, 'DOI')
                stream.append(char)
            else:
                stream.append('?')
    
    raw = ''.join(stream)
    final = trans.apply(raw)
    scores = signal_score.score_stream(final, use_phase3_metrics=True)
    
    return {
        'hypothesis': 'common_letter_replacement',
        'stream_length': len(raw),
        'score': scores['total_score'],
        'stream': final
    }


def run_oor_analysis():
    """Run all OOR hypothesis tests"""
    print("=" * 80)
    print("PHASE 7 G2: OUT-OF-RANGE NUMBER ANALYSIS")
    print("=" * 80)
    
    # Analyze context
    oor_positions = analyze_oor_context()
    
    # Load data
    cipher1 = load_cipher1()
    doi_words = load_doi_from_beale()
    
    # Use Phase 6 best extractor and transposition as baseline
    ext = extractors.get_extractor('cycle_every_5')
    trans = transposition.get_transposition('rect_w26_spiral_ccw')
    
    print("\n" + "=" * 80)
    print("HYPOTHESIS TESTING")
    print("=" * 80)
    print(f"\nBaseline extractor: {ext.name}")
    print(f"Baseline transposition: {trans.name}")
    print(f"Phase 6 baseline score: 37.88/100")
    
    # Test each hypothesis
    print("\n" + "-" * 80)
    print("Testing 4 OOR hypotheses...")
    print("-" * 80)
    
    results = []
    
    print("\n[H1] Nulls/Separators (drop OOR positions)...")
    h1 = test_hypothesis_1_nulls(cipher1, doi_words, ext, trans)
    results.append(h1)
    print(f"  Stream length: {h1['stream_length']} (dropped 10 chars)")
    print(f"  Score: {h1['score']:.2f}/100")
    
    print("\n[H2] Modulo mapping (n % 1322)...")
    h2 = test_hypothesis_2_modulo(cipher1, doi_words, ext, trans)
    results.append(h2)
    print(f"  Stream length: {h2['stream_length']}")
    print(f"  Score: {h2['score']:.2f}/100")
    
    print("\n[H3] Block separators (independent transposition)...")
    h3 = test_hypothesis_3_separators(cipher1, doi_words, ext, trans)
    results.append(h3)
    print(f"  Blocks: {h3['block_count']}")
    print(f"  Stream length: {h3['stream_length']}")
    print(f"  Score: {h3['score']:.2f}/100")
    
    print("\n[H4] Common letter replacement...")
    h4 = test_hypothesis_4_replacement(cipher1, doi_words, ext, trans)
    results.append(h4)
    print(f"  Stream length: {h4['stream_length']}")
    print(f"  Score: {h4['score']:.2f}/100")
    
    # Baseline (treat OOR as '?')
    print("\n[BASELINE] Treat OOR as '?' (current method)...")
    baseline_stream = []
    for position, cipher_num in enumerate(cipher1):
        word_idx = cipher_num - 1
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            char = ext.extract(word, word_idx, position, 'DOI')
            baseline_stream.append(char)
        else:
            baseline_stream.append('?')
    
    baseline_raw = ''.join(baseline_stream)
    baseline_final = trans.apply(baseline_raw)
    baseline_scores = signal_score.score_stream(baseline_final, use_phase3_metrics=True)
    baseline_score = baseline_scores['total_score']
    
    print(f"  Stream length: {len(baseline_raw)}")
    print(f"  Score: {baseline_score:.2f}/100")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/phase7/oor_analysis_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 7 G2: OUT-OF-RANGE NUMBER ANALYSIS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"OOR numbers (>1322): 10 total\n")
        f.write(f"Values: {oor_numbers}\n")
        f.write(f"Positions: {oor_positions}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("HYPOTHESIS TEST RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Baseline (OOR='?'): {baseline_score:.2f}/100\n\n")
        
        for result in results:
            f.write(f"Hypothesis: {result['hypothesis']}\n")
            f.write(f"  Score: {result['score']:.2f}/100\n")
            f.write(f"  Improvement: {result['score'] - baseline_score:+.2f} points\n")
            if 'block_count' in result:
                f.write(f"  Blocks: {result['block_count']}\n")
            f.write(f"  Stream length: {result['stream_length']}\n\n")
        
        # Determine best
        best = max(results, key=lambda x: x['score'])
        
        f.write("=" * 80 + "\n")
        f.write("VERDICT\n")
        f.write("=" * 80 + "\n\n")
        
        if best['score'] > baseline_score + 1.0:
            f.write(f"IMPROVEMENT FOUND: {best['hypothesis']}\n")
            f.write(f"Score: {best['score']:.2f}/100 ({best['score'] - baseline_score:+.2f})\n")
            f.write(f"Recommended OOR handling: {best['hypothesis']}\n")
        else:
            f.write("NO SIGNIFICANT IMPROVEMENT\n")
            f.write(f"Best: {best['hypothesis']} = {best['score']:.2f}/100\n")
            f.write(f"OOR handling does not break plateau.\n")
            f.write(f"\nConclusion: OOR numbers are likely genuinely out-of-range or\n")
            f.write(f"            their correct handling requires knowledge not captured\n")
            f.write(f"            by these four hypotheses.\n")
    
    print(f"\nResults saved: {output_file}")
    
    return results, baseline_score


if __name__ == "__main__":
    oor_numbers = [1431, 1496, 1629, 1701, 1706, 1780, 1817, 2018, 2160, 2906]
    
    results, baseline = run_oor_analysis()
    
    print("\n" + "=" * 80)
    print("OOR ANALYSIS COMPLETE")
    print("=" * 80)
    
    print(f"\nBaseline (OOR='?'): {baseline:.2f}/100")
    print("\nHypothesis results:")
    for result in results:
        improvement = result['score'] - baseline
        status = "IMPROVED" if improvement > 1.0 else "no change"
        print(f"  {result['hypothesis']:30s}: {result['score']:5.2f}/100 ({improvement:+.2f}) [{status}]")
    
    best = max(results, key=lambda x: x['score'])
    if best['score'] > baseline + 1.0:
        print(f"\nBest OOR handling: {best['hypothesis']}")
    else:
        print(f"\nNo OOR hypothesis improves score significantly.")
