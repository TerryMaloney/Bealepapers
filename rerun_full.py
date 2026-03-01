import re
from pathlib import Path

print("=" * 70)
print("BEALE DECODER - FULL CORPUS RERUN")
print("=" * 70)

# Extract ciphers
with open("beale_papers.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

cipher1 = [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]

# Load texts
vdr_text = Path("texts/vdr.txt").read_text(encoding="utf-8")
doi_text = Path("texts/doi_from_beale.txt").read_text(encoding="utf-8")
signers_text = Path("texts/signers.txt").read_text(encoding="utf-8")
articles_text = Path("texts/articles.txt").read_text(encoding="utf-8")

def normalize(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]

vdr_words = normalize(vdr_text)
doi_words = normalize(doi_text)
signers_words = normalize(signers_text)
articles_words = normalize(articles_text)

master_words = vdr_words + doi_words + signers_words + articles_words

print(f"\nCorpus loaded:")
print(f"  VDR: {len(vdr_words)}")
print(f"  DOI: {len(doi_words)}")
print(f"  Signers: {len(signers_words)}")
print(f"  Articles: {len(articles_words)}")
print(f"  TOTAL: {len(master_words)} words")
print(f"\nCipher 1 max: {max(cipher1)}")
print(f"Coverage: {len(master_words)/max(cipher1)*100:.1f}%")

# Run batch offset trial with first 100 numbers
print("\n" + "=" * 70)
print("BATCH OFFSET TRIAL - Offsets 330-340 (First 100 Numbers)")
print("=" * 70)

for offset in range(330, 341):
    results = []
    out_of_range = 0
    
    for cipher_num in cipher1[:100]:
        if cipher_num <= offset:
            idx = cipher_num - 1
        else:
            idx = (cipher_num - offset) + len(vdr_words) - 1
        
        if 0 <= idx < len(master_words):
            word = master_words[idx]
            letter = word[0].upper() if word else "?"
        else:
            letter = "?"
            out_of_range += 1
        
        results.append(letter)
    
    letters = "".join(results)
    grouped = " ".join([letters[i:i+10] for i in range(0, len(letters), 10)])
    print(f"Offset {offset}: {grouped} [{out_of_range} OOR]")

print("\n" + "=" * 70)
print("Looking for offset-stable clusters and repeated patterns...")
