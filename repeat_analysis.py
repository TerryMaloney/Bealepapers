"""
REPEATED NUMBER ANALYSIS ENGINE
Investigate if repeated cipher numbers reveal positional encoding patterns.

Tests whether repeated cipher numbers produce consistent or position-dependent results.
"""

import re
from pathlib import Path
from collections import defaultdict


def normalize(text):
    """Normalize text to lowercase words only"""
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]


def load_corpus():
    """Load all text files and return word lists"""
    vdr = normalize(Path("texts/vdr.txt").read_text(encoding="utf-8"))
    doi = normalize(Path("texts/doi_from_beale.txt").read_text(encoding="utf-8"))
    signers = normalize(Path("texts/signers.txt").read_text(encoding="utf-8"))
    articles = normalize(Path("texts/articles.txt").read_text(encoding="utf-8"))
    
    return vdr + doi + signers + articles


def load_cipher1():
    """Load Cipher 1 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]


def analyze_repeated_numbers(cipher_numbers, corpus, offset=335, sample_size=200):
    """
    Analyze repeated cipher numbers to detect positional patterns.
    
    Args:
        cipher_numbers: List of cipher numbers
        corpus: List of words
        offset: Offset value
        sample_size: How many cipher numbers to analyze
    
    Returns:
        Dictionary with analysis results
    """
    # Find repeated numbers in the sample
    number_positions = defaultdict(list)
    
    for i, num in enumerate(cipher_numbers[:sample_size]):
        number_positions[num].append(i)
    
    # Filter to only numbers that repeat
    repeated = {num: positions for num, positions in number_positions.items() 
                if len(positions) > 1}
    
    # Analyze each repeated number
    results = []
    vdr_len = 860  # From Phase 1
    
    for num in sorted(repeated.keys(), key=lambda n: len(repeated[n]), reverse=True):
        positions = repeated[num]
        
        # Map number to word
        if num <= offset:
            idx = num - 1
        else:
            idx = (num - offset) + vdr_len - 1
        
        if 0 <= idx < len(corpus):
            word = corpus[idx]
            
            # Extract first letter at each position
            first_letters = [word[0].upper()] * len(positions)
            
            # Extract position-dependent letters (nth letter by position)
            pos_dependent_letters = []
            for pos in positions:
                letter_idx = pos % len(word)
                pos_dependent_letters.append(word[letter_idx].upper())
            
            # Check consistency
            is_consistent = len(set(first_letters)) == 1
            is_positional = len(set(pos_dependent_letters)) > 1
            
            results.append({
                'number': num,
                'word': word,
                'frequency': len(positions),
                'positions': positions,
                'first_letters': first_letters,
                'position_dependent': pos_dependent_letters,
                'is_consistent': is_consistent,
                'is_positional': is_positional
            })
        else:
            results.append({
                'number': num,
                'word': '[OUT OF RANGE]',
                'frequency': len(positions),
                'positions': positions,
                'first_letters': ['?'] * len(positions),
                'position_dependent': ['?'] * len(positions),
                'is_consistent': False,
                'is_positional': False
            })
    
    return results


def print_repeat_analysis():
    """Run and print repeat analysis"""
    print("=" * 70)
    print("REPEATED NUMBER ANALYSIS")
    print("=" * 70)
    
    # Load data
    print("\n[1/3] Loading data...")
    corpus = load_corpus()
    cipher1 = load_cipher1()
    
    print(f"  Corpus: {len(corpus)} words")
    print(f"  Cipher 1: {len(cipher1)} numbers")
    
    # Analyze for different offsets
    offsets_to_test = [330, 333, 335, 338]
    
    print("\n[2/3] Analyzing repeated numbers...")
    print(f"  Testing offsets: {offsets_to_test}")
    print(f"  Sample size: first 200 numbers")
    
    # Run analysis for offset 335 (hypothesis default)
    offset = 335
    results = analyze_repeated_numbers(cipher1, corpus, offset, sample_size=200)
    
    print(f"\n[3/3] Results for offset {offset}:")
    print("=" * 70)
    
    # Summary statistics
    total_repeated = len(results)
    consistent_count = sum(1 for r in results if r['is_consistent'])
    positional_count = sum(1 for r in results if r['is_positional'])
    
    print(f"\nSummary:")
    print(f"  Total repeated numbers: {total_repeated}")
    print(f"  Consistent (same first letter): {consistent_count}")
    print(f"  Positional (varies by position): {positional_count}")
    
    # Detailed results
    print("\n" + "=" * 70)
    print("DETAILED REPEAT PATTERNS (Top 20 by frequency)")
    print("=" * 70)
    print(f"\n{'Num':>5} | {'Freq':>4} | {'Word':15s} | {'Positions'} | {'Position-Dependent Letters'}")
    print("-" * 70)
    
    for result in results[:20]:
        num = result['number']
        freq = result['frequency']
        word = result['word'][:15]
        positions_str = str(result['positions'][:5])
        if len(result['positions']) > 5:
            positions_str += "..."
        
        # Show position-dependent extraction
        pd_letters = ''.join(result['position_dependent'])
        
        # Mark if positional
        marker = " [POSITIONAL]" if result['is_positional'] else ""
        
        print(f"{num:5d} | {freq:4d} | {word:15s} | {positions_str:25s} | {pd_letters}{marker}")
    
    # Save detailed report
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "repeat_analysis.txt", "w", encoding="utf-8") as f:
        f.write("REPEATED NUMBER ANALYSIS\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Offset: {offset}\n")
        f.write(f"Sample Size: 200 cipher numbers\n\n")
        
        f.write("Summary:\n")
        f.write(f"  Total repeated numbers: {total_repeated}\n")
        f.write(f"  Consistent: {consistent_count}\n")
        f.write(f"  Positional: {positional_count}\n\n")
        
        f.write("=" * 70 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("=" * 70 + "\n\n")
        
        for result in results:
            f.write(f"Cipher Number: {result['number']}\n")
            f.write(f"Word: {result['word']}\n")
            f.write(f"Frequency: {result['frequency']}\n")
            f.write(f"Positions: {result['positions']}\n")
            f.write(f"First Letters: {result['first_letters']}\n")
            f.write(f"Position-Dependent: {result['position_dependent']}\n")
            f.write(f"Is Consistent: {result['is_consistent']}\n")
            f.write(f"Is Positional: {result['is_positional']}\n")
            f.write("-" * 70 + "\n\n")
    
    print(f"\nDetailed report saved to: output/repeat_analysis.txt")
    
    # Key finding
    print("\n" + "=" * 70)
    print("KEY FINDING:")
    print("=" * 70)
    
    if positional_count > 0:
        print(f"\n{positional_count} repeated numbers show POSITIONAL VARIATION")
        print("This suggests the extraction method may be position-dependent,")
        print("which aligns with the top-scoring 'nth_letter_by_position' method!")
    else:
        print("\nAll repeated numbers are CONSISTENT across positions.")
        print("This suggests the extraction method is NOT position-dependent.")
    
    return results


if __name__ == "__main__":
    print_repeat_analysis()
