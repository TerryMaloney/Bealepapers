"""
Quick test: Verify current DOI (from beale_papers.txt) actually decodes Cipher 2 correctly.
"""

import re


def load_doi_from_beale():
    """Load DOI exactly as used throughout Phases 1-6"""
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


def load_cipher2():
    """Load Cipher 2 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[58].strip().split(",") if n.strip()]


def get_cipher2_known_plaintext():
    """Get Cipher 2 known plaintext"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return lines[62].strip()


# Load everything
doi = load_doi_from_beale()
cipher2 = load_cipher2()
known = get_cipher2_known_plaintext()

print(f"DOI words: {len(doi)}")
print(f"Cipher 2 numbers: {len(cipher2)}")
print(f"Known plaintext: {len(known)} chars")
print(f"\nKnown plaintext:\n{known}\n")

# Decode Cipher 2 using first-letter rule
decoded = []
for cipher_num in cipher2:
    word_idx = cipher_num - 1
    if 0 <= word_idx < len(doi):
        word = doi[word_idx]
        if word:
            decoded.append(word[0].upper())
        else:
            decoded.append('?')
    else:
        decoded.append('?')

decoded_str = ''.join(decoded)

print(f"Decoded (first {len(known)} chars):")
print(decoded_str[:len(known)])
print()

# Compare
matches = sum(1 for d, k in zip(decoded_str, known) if d.upper() == k.upper())
match_pct = (matches / len(known)) * 100

print(f"Match: {matches}/{len(known)} = {match_pct:.2f}%")

# Show first mismatch
for i, (d, k) in enumerate(zip(decoded_str, known)):
    if d.upper() != k.upper():
        print(f"\nFirst mismatch at position {i}:")
        print(f"  Expected: {k}")
        print(f"  Got:      {d}")
        print(f"  Context:  ...{decoded_str[max(0,i-10):i+11]}...")
        break
