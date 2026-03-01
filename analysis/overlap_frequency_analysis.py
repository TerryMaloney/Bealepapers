"""
Cross-Cipher Overlap and Frequency Analysis

Pure statistical analysis of overlapping cipher numbers across Cipher 1, 2, 3.
Does NOT require correct DOI or decoding - this can run NOW.

Identifies:
- Overlapping numbers between ciphers
- Frequency patterns (homophonic candidates)
- Position correlations
- High-frequency numbers that appear in multiple ciphers
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_cipher(cipher_num: int) -> List[int]:
    """Load cipher numbers from beale_papers.txt."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    line_map = {1: 2, 2: 58, 3: 6}
    cipher_line = lines[line_map[cipher_num]].strip()
    return [int(n.strip()) for n in cipher_line.split(",") if n.strip()]


def analyze_cipher_overlaps() -> Dict:
    """
    Analyze overlapping cipher numbers across Cipher 1, 2, 3.
    
    Returns comprehensive overlap analysis dict.
    """
    print("=" * 80)
    print("CROSS-CIPHER OVERLAP & FREQUENCY ANALYSIS")
    print("=" * 80)
    
    # Load all ciphers
    print("\n[Step 1] Loading ciphers...")
    cipher1 = load_cipher(1)
    cipher2 = load_cipher(2)
    cipher3 = load_cipher(3)
    
    print(f"Cipher 1: {len(cipher1)} numbers")
    print(f"Cipher 2: {len(cipher2)} numbers")
    print(f"Cipher 3: {len(cipher3)} numbers")
    
    # Compute frequency distributions
    print("\n[Step 2] Computing frequency distributions...")
    freq1 = Counter(cipher1)
    freq2 = Counter(cipher2)
    freq3 = Counter(cipher3)
    
    print(f"Cipher 1: {len(freq1)} unique numbers")
    print(f"Cipher 2: {len(freq2)} unique numbers")
    print(f"Cipher 3: {len(freq3)} unique numbers")
    
    # Compute overlaps
    print("\n[Step 3] Computing overlaps...")
    overlaps_12 = set(cipher1) & set(cipher2)
    overlaps_13 = set(cipher1) & set(cipher3)
    overlaps_23 = set(cipher2) & set(cipher3)
    overlaps_all = overlaps_12 & set(cipher3)
    
    print(f"Cipher 1 AND 2: {len(overlaps_12)} numbers")
    print(f"Cipher 1 AND 3: {len(overlaps_13)} numbers")
    print(f"Cipher 2 AND 3: {len(overlaps_23)} numbers")
    print(f"All three:    {len(overlaps_all)} numbers")
    
    # High-frequency numbers in overlaps
    print("\n[Step 4] Identifying high-frequency overlap numbers...")
    high_freq_overlaps = []
    
    for num in sorted(overlaps_all):
        f1 = freq1.get(num, 0)
        f2 = freq2.get(num, 0)
        f3 = freq3.get(num, 0)
        total_freq = f1 + f2 + f3
        
        if total_freq >= 10:  # High frequency threshold
            high_freq_overlaps.append({
                'number': num,
                'freq_c1': f1,
                'freq_c2': f2,
                'freq_c3': f3,
                'total_freq': total_freq
            })
    
    high_freq_overlaps.sort(key=lambda x: x['total_freq'], reverse=True)
    
    print(f"High-frequency overlaps (>=10 total occurrences): {len(high_freq_overlaps)}")
    print("\nTop 10 high-frequency overlap numbers:")
    for i, item in enumerate(high_freq_overlaps[:10], 1):
        print(f"  {i:2d}. Number {item['number']:4d}: C1={item['freq_c1']:2d}, "
              f"C2={item['freq_c2']:2d}, C3={item['freq_c3']:2d}, Total={item['total_freq']:3d}")
    
    # Position correlations
    print("\n[Step 5] Analyzing position correlations...")
    position_correlations = analyze_position_correlations(cipher1, cipher2, cipher3, overlaps_all)
    
    # Most frequent numbers per cipher
    print("\n[Step 6] Top 10 most frequent numbers per cipher...")
    
    print("\nCipher 1:")
    for num, count in freq1.most_common(10):
        print(f"  {num:4d}: {count:3d} occurrences")
    
    print("\nCipher 2:")
    for num, count in freq2.most_common(10):
        print(f"  {num:4d}: {count:3d} occurrences")
    
    print("\nCipher 3:")
    for num, count in freq3.most_common(10):
        print(f"  {num:4d}: {count:3d} occurrences")
    
    # Build output dict
    analysis_result = {
        'metadata': {
            'generated': datetime.now().isoformat(),
            'cipher_lengths': {
                'cipher1': len(cipher1),
                'cipher2': len(cipher2),
                'cipher3': len(cipher3)
            },
            'unique_numbers': {
                'cipher1': len(freq1),
                'cipher2': len(freq2),
                'cipher3': len(freq3)
            }
        },
        'overlaps': {
            'cipher_1_2': list(overlaps_12),
            'cipher_1_3': list(overlaps_13),
            'cipher_2_3': list(overlaps_23),
            'all_three': list(overlaps_all),
            'counts': {
                'overlap_12': len(overlaps_12),
                'overlap_13': len(overlaps_13),
                'overlap_23': len(overlaps_23),
                'overlap_all': len(overlaps_all)
            }
        },
        'high_frequency_overlaps': high_freq_overlaps,
        'position_correlations': position_correlations,
        'top_frequencies': {
            'cipher1': [{'number': num, 'count': count} for num, count in freq1.most_common(20)],
            'cipher2': [{'number': num, 'count': count} for num, count in freq2.most_common(20)],
            'cipher3': [{'number': num, 'count': count} for num, count in freq3.most_common(20)]
        }
    }
    
    return analysis_result


def analyze_position_correlations(cipher1: List[int], cipher2: List[int],
                                  cipher3: List[int], overlap_numbers: Set[int]) -> Dict:
    """
    Analyze if overlapping numbers appear at similar relative positions.
    
    This could indicate:
    - Homophonic behavior (same number = same plaintext element)
    - Position-dependent behavior (same number at different positions)
    """
    correlations = {}
    
    for num in list(overlap_numbers)[:50]:  # Sample top 50 to keep manageable
        positions = {
            'cipher1': [i for i, n in enumerate(cipher1) if n == num],
            'cipher2': [i for i, n in enumerate(cipher2) if n == num],
            'cipher3': [i for i, n in enumerate(cipher3) if n == num]
        }
        
        # Relative positions (as fraction of cipher length)
        rel_positions = {
            'cipher1': [p / len(cipher1) for p in positions['cipher1']],
            'cipher2': [p / len(cipher2) for p in positions['cipher2']],
            'cipher3': [p / len(cipher3) for p in positions['cipher3']]
        }
        
        correlations[num] = {
            'absolute_positions': positions,
            'relative_positions': rel_positions
        }
    
    return correlations


def save_overlap_analysis(analysis: Dict, output_path: str = "output/analysis/overlaps.json"):
    """Save overlap analysis to JSON file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\nAnalysis saved: {output_file}")


def generate_overlap_report(analysis: Dict, output_path: str = "output/analysis/overlaps_report.txt"):
    """Generate human-readable overlap report."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        from datetime import datetime
        
        f.write("=" * 80 + "\n")
        f.write("CROSS-CIPHER OVERLAP & FREQUENCY ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE:\n")
        f.write("Identify overlapping numbers and frequency patterns across Cipher 1, 2, 3.\n")
        f.write("This analysis does NOT require correct DOI edition.\n\n")
        
        # Summary statistics
        f.write("=" * 80 + "\n")
        f.write("SUMMARY STATISTICS\n")
        f.write("=" * 80 + "\n\n")
        
        meta = analysis['metadata']
        f.write(f"Cipher lengths:\n")
        f.write(f"  Cipher 1: {meta['cipher_lengths']['cipher1']} numbers\n")
        f.write(f"  Cipher 2: {meta['cipher_lengths']['cipher2']} numbers\n")
        f.write(f"  Cipher 3: {meta['cipher_lengths']['cipher3']} numbers\n\n")
        
        f.write(f"Unique numbers:\n")
        f.write(f"  Cipher 1: {meta['unique_numbers']['cipher1']} unique\n")
        f.write(f"  Cipher 2: {meta['unique_numbers']['cipher2']} unique\n")
        f.write(f"  Cipher 3: {meta['unique_numbers']['cipher3']} unique\n\n")
        
        # Overlaps
        f.write("=" * 80 + "\n")
        f.write("OVERLAP SETS\n")
        f.write("=" * 80 + "\n\n")
        
        counts = analysis['overlaps']['counts']
        f.write(f"Cipher 1 AND 2: {counts['overlap_12']} numbers\n")
        f.write(f"Cipher 1 AND 3: {counts['overlap_13']} numbers\n")
        f.write(f"Cipher 2 AND 3: {counts['overlap_23']} numbers\n")
        f.write(f"All three:    {counts['overlap_all']} numbers\n\n")
        
        # High-frequency overlaps
        f.write("=" * 80 + "\n")
        f.write("HIGH-FREQUENCY OVERLAP NUMBERS (>=10 total occurrences)\n")
        f.write("=" * 80 + "\n\n")
        
        high_freq = analysis['high_frequency_overlaps']
        f.write(f"Count: {len(high_freq)}\n\n")
        
        f.write(f"{'Rank':<6s} {'Number':<8s} {'C1':<6s} {'C2':<6s} {'C3':<6s} {'Total':<6s}\n")
        f.write("-" * 50 + "\n")
        for i, item in enumerate(high_freq[:20], 1):
            f.write(f"{i:<6d} {item['number']:<8d} {item['freq_c1']:<6d} "
                   f"{item['freq_c2']:<6d} {item['freq_c3']:<6d} {item['total_freq']:<6d}\n")
        
        # Top frequencies per cipher
        f.write("\n" + "=" * 80 + "\n")
        f.write("TOP 20 MOST FREQUENT NUMBERS PER CIPHER\n")
        f.write("=" * 80 + "\n\n")
        
        for cipher_id in ['cipher1', 'cipher2', 'cipher3']:
            f.write(f"{cipher_id.upper()}:\n")
            for item in analysis['top_frequencies'][cipher_id][:20]:
                f.write(f"  {item['number']:4d}: {item['count']:3d} occurrences\n")
            f.write("\n")
        
        # Implications
        f.write("=" * 80 + "\n")
        f.write("IMPLICATIONS FOR CONSTRAINTS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"1. {counts['overlap_12']} Cipher 1-2 overlaps can be used as hard constraints\n")
        f.write(f"   once Cipher 2 oracle is validated (>=90% match).\n\n")
        
        f.write(f"2. {len(high_freq)} high-frequency numbers appear across ciphers.\n")
        f.write(f"   These may be:\n")
        f.write(f"   - Common words (the, of, and, etc.)\n")
        f.write(f"   - Homophonic substitutes (multiple numbers -> same plaintext)\n")
        f.write(f"   - Null/padding characters\n\n")
        
        f.write(f"3. Position correlation analysis available in JSON output.\n")
        f.write(f"   Check if same number at different positions suggests position-dependent extraction.\n\n")
    
    print(f"Report saved: {output_file}")


def main():
    """Main entry point."""
    print("=" * 80)
    print("OVERLAP ANALYSIS - CAN RUN NOW (NO ORACLE REQUIRED)")
    print("=" * 80)
    print("\nThis analysis does NOT require correct DOI edition.")
    print("It provides statistical insights that inform constraint design.")
    print("=" * 80)
    
    # Run analysis
    analysis = analyze_cipher_overlaps()
    
    # Save results
    print("\n[Saving results...]")
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    save_overlap_analysis(analysis, f"output/analysis/overlaps_{timestamp}.json")
    generate_overlap_report(analysis, f"output/analysis/overlaps_report_{timestamp}.txt")
    
    print("\n" + "=" * 80)
    print("OVERLAP ANALYSIS COMPLETE")
    print("=" * 80)
    
    # Summary
    counts = analysis['overlaps']['counts']
    print(f"\nKey findings:")
    print(f"  - {counts['overlap_12']} numbers shared between Cipher 1 and 2")
    print(f"  - {counts['overlap_13']} numbers shared between Cipher 1 and 3")
    print(f"  - {counts['overlap_all']} numbers appear in ALL THREE ciphers")
    print(f"  - {len(analysis['high_frequency_overlaps'])} high-frequency overlaps (>=10 occurrences)")
    
    print(f"\nThese overlaps provide constraints once oracle passes (>=90%).")
    
    return analysis


if __name__ == "__main__":
    main()
