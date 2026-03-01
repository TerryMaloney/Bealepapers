import re
from pathlib import Path

print("=" * 60)
print("BEALE CIPHER DECODER - Sliding Window Analysis")
print("=" * 60)

# Extract ciphers
print("\n[1/5] Extracting cipher numbers...")
with open("beale_papers.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

cipher1 = [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]
cipher2 = [int(n.strip()) for n in lines[57].strip().split(",") if n.strip()]  # Fixed: line 58 = index 57

print(f"Cipher 1: {len(cipher1)} numbers (max: {max(cipher1)})")
print(f"Cipher 2: {len(cipher2)} numbers")

# Load texts
print("\n[2/5] Loading text files...")
vdr_text = Path("texts/vdr.txt").read_text(encoding="utf-8")
doi_text = Path("texts/doi_from_beale.txt").read_text(encoding="utf-8")
signers_text = Path("texts/signers.txt").read_text(encoding="utf-8")

def normalize(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]

vdr_words = normalize(vdr_text)
doi_words = normalize(doi_text)
signers_words = normalize(signers_text)

print(f"VDR: {len(vdr_words)} words")
print(f"DOI: {len(doi_words)} words")
print(f"Signers: {len(signers_words)} words")

# Build master index
print("\n[3/5] Building master word index...")
master_words = vdr_words + doi_words + signers_words

print(f"Total words: {len(master_words)}")

# Decode Cipher 1
print("\n[4/5] Decoding Cipher 1 (first 50, offset=335)...")

offset = 335
results = []

for cipher_num in cipher1[:50]:
    if cipher_num <= offset:
        idx = cipher_num - 1
    else:
        idx = (cipher_num - offset) + len(vdr_words) - 1
    
    if 0 <= idx < len(master_words):
        word = master_words[idx]
        letter = word[0].upper() if word else "?"
        results.append({"num": cipher_num, "word": word, "letter": letter})
    else:
        results.append({"num": cipher_num, "word": "OUT_OF_RANGE", "letter": "?"})

# Display
print("\nFirst 20 mappings:")
for i, r in enumerate(results[:20], 1):
    print(f"{i:2d}. Cipher {r['num']:4d} -> {r['word']:15s} [{r['letter']}]")

# First-letter sequence
print("\n[5/5] First-letter sequence (first 50):")
letters = "".join([r["letter"] for r in results])
print(letters)
print(f"\nGrouped by 10: {' '.join([letters[i:i+10] for i in range(0, len(letters), 10)])}")

# Save
Path("output").mkdir(exist_ok=True)
with open("output/cipher1_decode.txt", "w", encoding="utf-8") as f:
    f.write("CIPHER 1 - First 50 Numbers (Offset 335)\n\n")
    for i, r in enumerate(results, 1):
        f.write(f"{i:2d}. {r['num']:4d} -> {r['word']:15s} [{r['letter']}]\n")
    f.write(f"\nFirst letters: {letters}\n")

print("\nResults saved to output/cipher1_decode.txt")
print("\nDone!")
