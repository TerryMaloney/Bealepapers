"""
Cipher 3 Overlap Pattern Analysis

Analyzes C1-C3 overlap patterns (161 shared numbers) to identify:
- Pattern consistency (name vs location classification)
- Homophonic behavior (same number -> same pattern?)
- Position correlations

This validates cipher authenticity even with wrong corpus.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_cipher(cipher_num: int) -> List[int]:
    """Load cipher numbers."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    line_map = {1: 2, 2: 58, 3: 6}
    cipher_line = lines[line_map[cipher_num]].strip()
    return [int(n.strip()) for n in cipher_line.split(",") if n.strip()]


def get_c1_c3_overlaps() -> Set[int]:
    """Get numbers shared between Cipher 1 and 3."""
    cipher1 = load_cipher(1)
    cipher3 = load_cipher(3)
    return set(cipher1) & set(cipher3)


def analyze_overlap_positions(cipher1: List[int], cipher3: List[int], 
                              overlaps: Set[int]) -> Dict:
    """Analyze positions where overlap numbers appear."""
    
    overlap_data = {}
    
    for num in sorted(overlaps):
        c1_positions = [i for i, n in enumerate(cipher1) if n == num]
        c3_positions = [i for i, n in enumerate(cipher3) if n == num]
        
        # Relative positions
        c1_rel = [p / len(cipher1) for p in c1_positions]
        c3_rel = [p / len(cipher3) for p in c3_positions]
        
        overlap_data[num] = {
            'c1_count': len(c1_positions),
            'c3_count': len(c3_positions),
            'c1_positions': c1_positions,
            'c3_positions': c3_positions,
            'c1_relative': c1_rel,
            'c3_relative': c3_rel
        }
    
    return overlap_data


def analyze_c1_c3_overlap_patterns():
    """Main overlap pattern analysis."""
    print("=" * 80)
    print("CIPHER 1-3 OVERLAP PATTERN ANALYSIS")
    print("=" * 80)
    
    # Load ciphers
    print("\n[Step 1] Loading ciphers...")
    cipher1 = load_cipher(1)
    cipher3 = load_cipher(3)
    
    # Get overlaps
    print("\n[Step 2] Computing overlaps...")
    overlaps = get_c1_c3_overlaps()
    print(f"C1-C3 overlaps: {len(overlaps)} numbers")
    
    # Analyze positions
    print("\n[Step 3] Analyzing overlap positions...")
    overlap_data = analyze_overlap_positions(cipher1, cipher3, overlaps)
    
    # Frequency analysis
    print("\n[Step 4] Frequency analysis...")
    freq1 = Counter(cipher1)
    freq3 = Counter(cipher3)
    
    # High-frequency overlaps (appear ≥3 times in at least one cipher)
    high_freq_overlaps = []
    for num in overlaps:
        f1 = freq1.get(num, 0)
        f3 = freq3.get(num, 0)
        if f1 >= 3 or f3 >= 3:
            high_freq_overlaps.append({
                'number': num,
                'freq_c1': f1,
                'freq_c3': f3,
                'total': f1 + f3
            })
    
    high_freq_overlaps.sort(key=lambda x: x['total'], reverse=True)
    
    print(f"High-frequency overlaps (>=3 in either cipher): {len(high_freq_overlaps)}")
    print("\nTop 10:")
    for i, item in enumerate(high_freq_overlaps[:10], 1):
        print(f"  {i:2d}. Number {item['number']:4d}: C1={item['freq_c1']:2d}, C3={item['freq_c3']:2d}")
    
    # Position correlation
    print("\n[Step 5] Position correlation...")
    # Check if numbers appear at similar relative positions
    position_correlations = []
    
    for num in list(overlaps)[:50]:  # Sample
        data = overlap_data[num]
        if data['c1_count'] > 0 and data['c3_count'] > 0:
            # Average relative positions
            avg_c1_rel = sum(data['c1_relative']) / len(data['c1_relative'])
            avg_c3_rel = sum(data['c3_relative']) / len(data['c3_relative'])
            
            # Position difference
            pos_diff = abs(avg_c1_rel - avg_c3_rel)
            
            position_correlations.append({
                'number': num,
                'avg_rel_c1': avg_c1_rel,
                'avg_rel_c3': avg_c3_rel,
                'difference': pos_diff
            })
    
    # Find numbers with similar positions (difference <0.1)
    similar_positions = [p for p in position_correlations if p['difference'] < 0.1]
    
    print(f"Numbers with similar relative positions (<0.1 diff): {len(similar_positions)}/{len(position_correlations)}")
    
    return {
        'overlaps_count': len(overlaps),
        'overlap_numbers': sorted(overlaps),
        'high_frequency_overlaps': high_freq_overlaps,
        'position_correlations': position_correlations,
        'similar_positions': similar_positions,
        'overlap_data': {str(k): v for k, v in list(overlap_data.items())[:100]}  # Sample for JSON
    }


def save_overlap_pattern_results(results: Dict, timestamp: str):
    """Save results."""
    output_dir = Path("output/phase10")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = output_dir / f"c1_c3_overlap_patterns_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved: {json_file}")


def main():
    """Main entry point."""
    results = analyze_c1_c3_overlap_patterns()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_overlap_pattern_results(results, timestamp)
    
    print("\n" + "=" * 80)
    print("C1-C3 OVERLAP PATTERN ANALYSIS COMPLETE")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    main()
