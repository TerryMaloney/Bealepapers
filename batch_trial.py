import re
from pathlib import Path

print("=" * 70)
print("BEALE CIPHER DECODER - BATCH OFFSET TRIAL (330-340)")
print("=" * 70)

# Extract ciphers
with open("beale_papers.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

cipher1 = [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]
print(f"Cipher 1: {len(cipher1)} numbers")

# Load texts
vdr_text = Path("texts/vdr.txt").read_text(encoding="utf-8")
doi_text = Path("texts/doi_from_beale.txt").read_text(encoding="utf-8")
signers_text = Path("texts/signers.txt").read_text(encoding="utf-8")

def normalize(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]

vdr_words = normalize(vdr_text)
doi_words = normalize(doi_text)
signers_words = normalize(signers_text)

master_words = vdr_words + doi_words + signers_words

print(f"Text corpus: {len(master_words)} words total")
print(f"  VDR: {len(vdr_words)}, DOI: {len(doi_words)}, Signers: {len(signers_words)}")
print()

# Run batch trial
results_by_offset = {}

for offset in range(330, 341):
    results = []
    for cipher_num in cipher1[:50]:
        if cipher_num <= offset:
            idx = cipher_num - 1
        else:
            idx = (cipher_num - offset) + len(vdr_words) - 1
        
        if 0 <= idx < len(master_words):
            word = master_words[idx]
            letter = word[0].upper() if word else "?"
        else:
            letter = "?"
        
        results.append(letter)
    
    results_by_offset[offset] = "".join(results)

# Display results
print("FIRST-LETTER SEQUENCES BY OFFSET (Cipher 1, first 50 numbers):")
print("=" * 70)

for offset in range(330, 341):
    letters = results_by_offset[offset]
    grouped = " ".join([letters[i:i+10] for i in range(0, len(letters), 10)])
    print(f"Offset {offset}: {grouped}")

# Save
with open("output/batch_offset_trial.txt", "w", encoding="utf-8") as f:
    f.write("BATCH OFFSET TRIAL - Offsets 330-340\n")
    f.write("Cipher 1, First 50 Numbers\n\n")
    for offset in range(330, 341):
        f.write(f"Offset {offset}:\n")
        f.write(f"  {results_by_offset[offset]}\n\n")

print("\n" + "=" * 70)
print("Results saved to output/batch_offset_trial.txt")
print("\nNOTE: Look for sequences that form words, place names, or")
print("coherent patterns. The 'correct' offset should show structure.")
