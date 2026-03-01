"""
PHASE 7 G5: CROSS-CIPHER CONSTRAINTS
Use Cipher 2 oracle (known plaintext) to constrain Cipher 1 search.
Find overlapping cipher numbers and use them as validation constraints.
"""

import re
from datetime import datetime


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


def load_cipher3():
    """Load Cipher 3 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[6].strip().split(",") if n.strip()]


def get_cipher2_known_plaintext():
    """Get Cipher 2 known plaintext (all 3 paragraphs)"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Lines 63, 65, 67 contain the known plaintext
    plaintext_parts = []
    for line_idx in [62, 64, 66]:  # 0-indexed
        if line_idx < len(lines):
            plaintext_parts.append(lines[line_idx].strip())
    
    return ' '.join(plaintext_parts)


def find_overlapping_numbers():
    """Find cipher numbers that appear in multiple ciphers"""
    cipher1 = load_cipher1()
    cipher2 = load_cipher2()
    cipher3 = load_cipher3()
    
    cipher1_set = set(cipher1)
    cipher2_set = set(cipher2)
    cipher3_set = set(cipher3)
    
    overlaps = {
        '1_2': cipher1_set & cipher2_set,
        '1_3': cipher1_set & cipher3_set,
        '2_3': cipher2_set & cipher3_set,
        'all': cipher1_set & cipher2_set & cipher3_set
    }
    
    return overlaps, (cipher1, cipher2, cipher3)


def extract_oracle_constraints():
    """
    For numbers appearing in both Cipher 1 and Cipher 2,
    use Cipher 2's known plaintext letter as constraint.
    """
    overlaps, (cipher1, cipher2, cipher3) = find_overlapping_numbers()
    doi_words = load_doi_from_beale()
    known_plaintext = get_cipher2_known_plaintext()
    
    # Remove spaces/punctuation from known plaintext for alignment
    known_clean = ''.join(c.upper() for c in known_plaintext if c.isalpha())
    
    constraints = {}
    
    for cipher_num in overlaps['1_2']:
        # Find ALL positions of this number in Cipher 2
        c2_positions = [i for i, n in enumerate(cipher2) if n == cipher_num]
        
        # Get the DOI word for this cipher number
        word_idx = cipher_num - 1
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            
            # For each position in Cipher 2, get oracle letter
            oracle_letters = []
            for pos in c2_positions:
                if pos < len(known_clean):
                    oracle_letters.append(known_clean[pos])
            
            if oracle_letters:
                constraints[cipher_num] = {
                    'word': word,
                    'oracle_letters': oracle_letters,  # All observed letters for this cipher_num
                    'c2_positions': c2_positions,
                    'c1_positions': [i for i, n in enumerate(cipher1) if n == cipher_num]
                }
    
    return constraints, overlaps


def run_cross_cipher_analysis():
    """Main cross-cipher analysis"""
    print("=" * 80)
    print("PHASE 7 G5: CROSS-CIPHER CONSTRAINTS")
    print("=" * 80)
    
    # Find overlaps
    print("\n[Step 1] Finding overlapping cipher numbers...")
    overlaps, ciphers = find_overlapping_numbers()
    
    print(f"\nOverlap statistics:")
    print(f"  Cipher 1 & 2: {len(overlaps['1_2'])} shared numbers")
    print(f"  Cipher 1 & 3: {len(overlaps['1_3'])} shared numbers")
    print(f"  Cipher 2 & 3: {len(overlaps['2_3'])} shared numbers")
    print(f"  All 3 ciphers: {len(overlaps['all'])} shared numbers")
    
    # Extract constraints
    print("\n[Step 2] Extracting Cipher 2 oracle constraints...")
    constraints, _ = extract_oracle_constraints()
    
    print(f"\nOracle constraints extracted: {len(constraints)} cipher numbers")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/phase7/cross_cipher_constraints_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 7 G5: CROSS-CIPHER CONSTRAINTS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OVERLAP STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Cipher 1 & 2: {len(overlaps['1_2'])} shared numbers\n")
        f.write(f"Cipher 1 & 3: {len(overlaps['1_3'])} shared numbers\n")
        f.write(f"Cipher 2 & 3: {len(overlaps['2_3'])} shared numbers\n")
        f.write(f"All 3 ciphers: {len(overlaps['all'])} shared numbers\n\n")
        
        f.write("ORACLE CONSTRAINTS (Cipher 1 & 2 overlaps)\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total constraints: {len(constraints)}\n\n")
        
        # Show sample constraints
        f.write("Sample constraints (first 20):\n\n")
        for i, (cipher_num, info) in enumerate(list(constraints.items())[:20], 1):
            f.write(f"{i}. Cipher #{cipher_num}: word='{info['word']}'\n")
            f.write(f"   Cipher 2 oracle letters: {info['oracle_letters']}\n")
            f.write(f"   Cipher 2 positions: {info['c2_positions']}\n")
            f.write(f"   Cipher 1 positions: {info['c1_positions']}\n\n")
        
        if len(constraints) > 20:
            f.write(f"... and {len(constraints) - 20} more constraints\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("USAGE\n")
        f.write("=" * 80 + "\n\n")
        f.write("These constraints can be used to:\n")
        f.write("1. Filter extractors that violate oracle constraints\n")
        f.write("2. Validate Cipher 1 extraction rules against known Cipher 2 results\n")
        f.write("3. Prune search space by eliminating inconsistent methods\n\n")
        
        f.write("NOTE: Cipher 2 oracle only matches ~26.5% with current DOI.\n")
        f.write("      Constraints are weak due to DOI edition mismatch.\n")
        f.write("      For strong constraints, correct DOI edition needed first.\n")
    
    print(f"\nResults saved: {output_file}")
    
    return constraints, overlaps


if __name__ == "__main__":
    constraints, overlaps = run_cross_cipher_analysis()
    
    print("\n" + "=" * 80)
    print("CROSS-CIPHER ANALYSIS COMPLETE")
    print("=" * 80)
    
    print(f"\nExtracted {len(constraints)} oracle constraints from Cipher 1&2 overlaps")
    print(f"\nNOTE: Oracle strength limited by DOI edition mismatch (26.5% Cipher 2 match)")
    print(f"      For strong constraints, correct historical DOI edition needed.")
