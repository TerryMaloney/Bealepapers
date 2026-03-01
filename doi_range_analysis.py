"""
DOI RANGE ANALYSIS (Phase 4)
Analyze cipher number distribution relative to DOI corpus size.
Identify in-range vs out-of-range numbers.
"""

import re
from pathlib import Path


def normalize(text):
    """Normalize text to lowercase words only"""
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]


def load_doi_from_beale():
    """Load DOI exactly as used in Cipher 2 decoding"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Line 55 (index 54) contains numbered Declaration
    doi_line = lines[54]
    
    # Extract numbered words
    pattern = r'(\w+)\((\d+)\)'
    matches = re.findall(pattern, doi_line)
    max_num = max(int(num) for word, num in matches)
    words = [''] * (max_num + 1)
    for word, num in matches:
        words[int(num)] = word.lower()
    
    return words[1:]  # Skip index 0, return 1-indexed words


def load_cipher1():
    """Load Cipher 1 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]


def analyze_cipher_range():
    """Analyze cipher number distribution relative to DOI corpus"""
    print("=" * 80)
    print("DOI RANGE ANALYSIS - Phase 4")
    print("=" * 80)
    
    # Load data
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    
    print(f"\nDOI corpus: {len(doi_words)} words")
    print(f"Cipher 1: {len(cipher1)} numbers")
    
    # Separate in-range and out-of-range
    in_range = [n for n in cipher1 if n <= len(doi_words)]
    out_range = [n for n in cipher1 if n > len(doi_words)]
    
    print("\n" + "-" * 80)
    print("RANGE DISTRIBUTION")
    print("-" * 80)
    print(f"In DOI range (<={len(doi_words)}): {len(in_range)} ({len(in_range)/len(cipher1)*100:.1f}%)")
    print(f"Out of range (>{len(doi_words)}): {len(out_range)} ({len(out_range)/len(cipher1)*100:.1f}%)")
    
    # Analyze out-of-range numbers
    if out_range:
        print("\n" + "-" * 80)
        print("OUT-OF-RANGE ANALYSIS")
        print("-" * 80)
        print(f"Count: {len(out_range)}")
        print(f"Min: {min(out_range)}")
        print(f"Max: {max(out_range)}")
        print(f"Range: {max(out_range) - min(out_range)}")
        
        # Check distribution patterns
        doi_repeat_range = [n for n in out_range if 1324 <= n <= 2646]  # DOI repeated
        higher_range = [n for n in out_range if n > 2646]
        
        print(f"\nDistribution:")
        print(f"  1324-2646 (DOI second pass): {len(doi_repeat_range)} ({len(doi_repeat_range)/len(out_range)*100:.1f}%)")
        print(f"  2647+ (beyond DOI repeat): {len(higher_range)} ({len(higher_range)/len(out_range)*100:.1f}%)")
        
        # Show specific out-of-range numbers
        print(f"\nOut-of-range numbers (first 20):")
        for n in sorted(out_range)[:20]:
            print(f"  {n}", end="")
        if len(out_range) > 20:
            print(f"  ... (+{len(out_range)-20} more)")
        else:
            print()
    
    # Segment analysis
    print("\n" + "-" * 80)
    print("SEGMENT COVERAGE")
    print("-" * 80)
    
    segments = [
        (0, 100, "Segment 1-100"),
        (100, 200, "Segment 101-200"),
        (200, 300, "Segment 201-300"),
        (300, 400, "Segment 301-400"),
        (400, 520, "Segment 401-520")
    ]
    
    for start, end, label in segments:
        segment_numbers = cipher1[start:end]
        seg_in_range = [n for n in segment_numbers if n <= len(doi_words)]
        coverage = len(seg_in_range) / len(segment_numbers) * 100
        
        print(f"{label}: {coverage:5.1f}% DOI coverage ({len(seg_in_range)}/{len(segment_numbers)} numbers)")
    
    # Generate report
    output_file = "output/doi_range_analysis.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("DOI RANGE ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"DOI corpus: {len(doi_words)} words\n")
        f.write(f"Cipher 1: {len(cipher1)} numbers\n\n")
        
        f.write("RANGE DISTRIBUTION\n")
        f.write("-" * 80 + "\n")
        f.write(f"In range (<={len(doi_words)}): {len(in_range)} ({len(in_range)/len(cipher1)*100:.1f}%)\n")
        f.write(f"Out of range (>{len(doi_words)}): {len(out_range)} ({len(out_range)/len(cipher1)*100:.1f}%)\n\n")
        
        if out_range:
            f.write("OUT-OF-RANGE NUMBERS\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total: {len(out_range)}\n")
            f.write(f"Range: {min(out_range)} to {max(out_range)}\n\n")
            
            f.write("All out-of-range numbers:\n")
            for n in sorted(out_range):
                f.write(f"{n} ")
            f.write("\n\n")
        
        f.write("SEGMENT COVERAGE\n")
        f.write("-" * 80 + "\n")
        for start, end, label in segments:
            segment_numbers = cipher1[start:end]
            seg_in_range = [n for n in segment_numbers if n <= len(doi_words)]
            coverage = len(seg_in_range) / len(segment_numbers) * 100
            f.write(f"{label}: {coverage:.1f}% ({len(seg_in_range)}/{len(segment_numbers)})\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"\nReport saved to: {output_file}")
    
    return {
        'doi_word_count': len(doi_words),
        'cipher_count': len(cipher1),
        'in_range': len(in_range),
        'out_range': len(out_range),
        'coverage': len(in_range) / len(cipher1) * 100
    }


if __name__ == "__main__":
    result = analyze_cipher_range()
    
    print("\n" + "=" * 80)
    print("RANGE ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"DOI coverage: {result['coverage']:.1f}%")
    print(f"In-range: {result['in_range']}/520")
    print(f"Out-of-range: {result['out_range']}/520")
    
    if result['coverage'] < 70:
        print("\n[!] LOW COVERAGE: Many cipher numbers exceed DOI range.")
        print("    This suggests Cipher 1 may use multiple source texts.")
    elif result['coverage'] > 90:
        print("\n[OK] HIGH COVERAGE: Most cipher numbers within DOI range.")
        print("    DOI-only hypothesis is viable.")
    else:
        print("\n[~] MODERATE COVERAGE: Some numbers exceed DOI range.")
        print("    May indicate corpus extension or secondary text.")
