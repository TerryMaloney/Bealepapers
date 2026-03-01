"""
H1: WORD NUMBERING OFFSET TEST

HYPOTHESIS: The DOI word indices have a systematic offset error of +/-1 to +/-10 positions.

PREDICTION: Shifting all cipher numbers by a constant offset will improve scores.

TEST: For each offset in [-10..+10]:
  - Map cipher_num to (cipher_num + offset)
  - Decode Cipher 2 with first-letter (oracle test)
  - Decode Cipher 1 with best Phase 6/7 methods
  - Look for offset where BOTH improve

EXPECTED: One offset shows >40/100 for Cipher 1 AND >50% for Cipher 2.
"""

import re
from datetime import datetime
import extractors
import transposition
import signal_score


def load_doi_from_beale():
    """Load DOI"""
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


def load_cipher2():
    """Load Cipher 2 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[58].strip().split(",") if n.strip()]


def get_cipher2_known_plaintext():
    """Get Cipher 2 known plaintext"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    plaintext_parts = []
    for line_idx in [62, 64, 66]:
        if line_idx < len(lines):
            plaintext_parts.append(lines[line_idx].strip())
    
    return ' '.join(plaintext_parts)


def test_cipher2_with_offset(cipher2, doi_words, offset, known_plaintext):
    """Test Cipher 2 decoding with word number offset"""
    # Remove spaces/punctuation from known plaintext
    known_clean = ''.join(c.upper() for c in known_plaintext if c.isalpha())
    
    decoded = []
    out_of_range = 0
    
    for cipher_num in cipher2:
        # Apply offset
        shifted_num = cipher_num + offset
        word_idx = shifted_num - 1
        
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            if word:
                decoded.append(word[0].upper())
            else:
                decoded.append('?')
        else:
            decoded.append('?')
            out_of_range += 1
    
    decoded_str = ''.join(decoded)
    
    # Compare to known plaintext
    matches = sum(1 for d, k in zip(decoded_str, known_clean) if d == k)
    total = min(len(decoded_str), len(known_clean))
    match_pct = (matches / total * 100) if total > 0 else 0
    
    return {
        'offset': offset,
        'match_pct': match_pct,
        'matches': matches,
        'total': total,
        'out_of_range': out_of_range
    }


def test_cipher1_with_offset(cipher1, doi_words, offset, extractor, trans):
    """Test Cipher 1 decoding with word number offset"""
    stream = []
    out_of_range = 0
    
    for position, cipher_num in enumerate(cipher1):
        # Apply offset
        shifted_num = cipher_num + offset
        word_idx = shifted_num - 1
        
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            char = extractor.extract(word, word_idx, position, 'DOI')
            stream.append(char)
        else:
            stream.append('?')
            out_of_range += 1
    
    raw = ''.join(stream)
    final = trans.apply(raw)
    scores = signal_score.score_stream(final, use_phase3_metrics=True)
    
    return {
        'offset': offset,
        'total_score': scores['total_score'],
        'out_of_range': out_of_range,
        'stream': final[:200]  # First 200 chars
    }


def run_h1_offset_test():
    """Main H1 offset test"""
    print("=" * 80)
    print("H1: WORD NUMBERING OFFSET TEST")
    print("=" * 80)
    
    # Load data
    print("\n[Step 1] Loading data...")
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    cipher2 = load_cipher2()
    known_plaintext = get_cipher2_known_plaintext()
    
    print(f"DOI words: {len(doi_words)}")
    print(f"Cipher 1: {len(cipher1)} numbers")
    print(f"Cipher 2: {len(cipher2)} numbers")
    print(f"Known plaintext: {len(known_plaintext)} chars")
    
    # Baseline (offset = 0)
    print("\n[Step 2] Testing baseline (offset = 0)...")
    
    c2_baseline = test_cipher2_with_offset(cipher2, doi_words, 0, known_plaintext)
    print(f"Cipher 2 baseline: {c2_baseline['match_pct']:.2f}% match")
    
    # Test best Cipher 1 extractors from Phase 6-7
    ext = extractors.get_extractor('position_times_2')
    trans = transposition.get_transposition('rect_w26_spiral_ccw')
    
    c1_baseline = test_cipher1_with_offset(cipher1, doi_words, 0, ext, trans)
    print(f"Cipher 1 baseline: {c1_baseline['total_score']:.2f}/100")
    
    # Test offsets
    print("\n[Step 3] Testing offsets from -10 to +10...")
    print("-" * 80)
    
    offset_range = range(-10, 11)
    c2_results = []
    c1_results = []
    
    for offset in offset_range:
        if offset == 0:
            c2_results.append(c2_baseline)
            c1_results.append(c1_baseline)
            continue
        
        c2_result = test_cipher2_with_offset(cipher2, doi_words, offset, known_plaintext)
        c2_results.append(c2_result)
        
        c1_result = test_cipher1_with_offset(cipher1, doi_words, offset, ext, trans)
        c1_results.append(c1_result)
        
        if (offset + 10) % 5 == 0:
            print(f"  Tested offsets up to {offset}...")
    
    print(f"  Tested all 21 offsets.")
    
    # Find best offsets
    best_c2 = max(c2_results, key=lambda x: x['match_pct'])
    best_c1 = max(c1_results, key=lambda x: x['total_score'])
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    print("\nCipher 2 (Oracle Test):")
    print(f"  Baseline (offset=0): {c2_baseline['match_pct']:.2f}% match")
    print(f"  Best offset={best_c2['offset']:+3d}: {best_c2['match_pct']:.2f}% match")
    print(f"  Improvement: {best_c2['match_pct'] - c2_baseline['match_pct']:+.2f} points")
    
    print("\nCipher 1 (Signal Score):")
    print(f"  Baseline (offset=0): {c1_baseline['total_score']:.2f}/100")
    print(f"  Best offset={best_c1['offset']:+3d}: {best_c1['total_score']:.2f}/100")
    print(f"  Improvement: {best_c1['total_score'] - c1_baseline['total_score']:+.2f} points")
    
    # Check if same offset helps both
    print("\n" + "-" * 80)
    print("Top 5 offsets for each cipher:")
    print("-" * 80)
    
    c2_sorted = sorted(c2_results, key=lambda x: x['match_pct'], reverse=True)
    c1_sorted = sorted(c1_results, key=lambda x: x['total_score'], reverse=True)
    
    print("\nCipher 2 top 5:")
    for i, result in enumerate(c2_sorted[:5], 1):
        print(f"  {i}. Offset {result['offset']:+3d}: {result['match_pct']:6.2f}% ({result['matches']}/{result['total']}) OOR: {result['out_of_range']}")
    
    print("\nCipher 1 top 5:")
    for i, result in enumerate(c1_sorted[:5], 1):
        print(f"  {i}. Offset {result['offset']:+3d}: {result['total_score']:6.2f}/100  OOR: {result['out_of_range']}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/phase7/h1_offset_test_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("H1: WORD NUMBERING OFFSET TEST RESULTS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("HYPOTHESIS:\n")
        f.write("DOI word indices have a systematic offset error of +/-1 to +/-10 positions.\n\n")
        
        f.write("TEST:\n")
        f.write("Applied offsets from -10 to +10 to all cipher numbers.\n")
        f.write("Measured impact on both Cipher 2 oracle match and Cipher 1 signal score.\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("CIPHER 2 RESULTS (Oracle Match %)\n")
        f.write("=" * 80 + "\n\n")
        
        for result in c2_sorted:
            f.write(f"Offset {result['offset']:+3d}: {result['match_pct']:6.2f}% ")
            f.write(f"({result['matches']:3d}/{result['total']:3d}) OOR: {result['out_of_range']:3d}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("CIPHER 1 RESULTS (Signal Score)\n")
        f.write("=" * 80 + "\n\n")
        
        for result in c1_sorted:
            f.write(f"Offset {result['offset']:+3d}: {result['total_score']:6.2f}/100  OOR: {result['out_of_range']:3d}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("VERDICT\n")
        f.write("=" * 80 + "\n\n")
        
        c2_improvement = best_c2['match_pct'] - c2_baseline['match_pct']
        c1_improvement = best_c1['total_score'] - c1_baseline['total_score']
        
        if c2_improvement > 10.0 and c1_improvement > 5.0:
            f.write("BREAKTHROUGH: Significant improvement found!\n")
            f.write(f"Cipher 2: {c2_improvement:+.2f} points (offset {best_c2['offset']:+d})\n")
            f.write(f"Cipher 1: {c1_improvement:+.2f} points (offset {best_c1['offset']:+d})\n")
            
            if best_c2['offset'] == best_c1['offset']:
                f.write(f"\nSAME OFFSET WORKS FOR BOTH: {best_c2['offset']:+d}\n")
                f.write("This strongly validates the offset hypothesis.\n")
            else:
                f.write("\nDifferent offsets work best for each cipher.\n")
                f.write("Suggests more complex numbering issue.\n")
        
        elif c2_improvement > 5.0 or c1_improvement > 3.0:
            f.write("MODERATE IMPROVEMENT: Offset helps but not dramatically.\n")
            f.write(f"Cipher 2: {c2_improvement:+.2f} points\n")
            f.write(f"Cipher 1: {c1_improvement:+.2f} points\n")
            f.write("\nSimple offset is not the full answer.\n")
            f.write("Consider testing H2 (progressive drift).\n")
        
        else:
            f.write("NO SIGNIFICANT IMPROVEMENT\n")
            f.write(f"Cipher 2: {c2_improvement:+.2f} points (threshold: >5.0)\n")
            f.write(f"Cipher 1: {c1_improvement:+.2f} points (threshold: >3.0)\n")
            f.write("\nH1 (simple offset) is REJECTED.\n")
            f.write("\nThe DOI numbering issue is likely more complex than a uniform offset.\n")
            f.write("Next steps:\n")
            f.write("- Test H2 (progressive drift)\n")
            f.write("- Acquire historical DOI editions\n")
            f.write("- Consider H3 (homophonic substitution)\n")
    
    print(f"\nResults saved: {output_file}")
    
    # Print verdict
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)
    
    c2_improvement = best_c2['match_pct'] - c2_baseline['match_pct']
    c1_improvement = best_c1['total_score'] - c1_baseline['total_score']
    
    if c2_improvement > 10.0 and c1_improvement > 5.0:
        print("\n*** BREAKTHROUGH FOUND ***")
        print(f"Cipher 2 improved by {c2_improvement:+.2f} points with offset {best_c2['offset']:+d}")
        print(f"Cipher 1 improved by {c1_improvement:+.2f} points with offset {best_c1['offset']:+d}")
        
        if best_c2['offset'] == best_c1['offset']:
            print(f"\nSAME OFFSET {best_c2['offset']:+d} WORKS FOR BOTH CIPHERS!")
            print("H1 hypothesis VALIDATED.")
        else:
            print("\nDifferent best offsets - more complex issue.")
    
    elif c2_improvement > 5.0 or c1_improvement > 3.0:
        print("\nModerate improvement found.")
        print("Simple offset is not the full answer.")
        print("Next: Test H2 (progressive drift).")
    
    else:
        print("\nH1 (simple uniform offset) REJECTED.")
        print("No significant improvement with any tested offset.")
        print("\nThe plateau is NOT caused by a simple numbering offset.")
        print("Most likely cause remains: Wrong DOI edition entirely.")
    
    return c2_results, c1_results


if __name__ == "__main__":
    c2_results, c1_results = run_h1_offset_test()
    
    print("\n" + "=" * 80)
    print("H1 TEST COMPLETE")
    print("=" * 80)
