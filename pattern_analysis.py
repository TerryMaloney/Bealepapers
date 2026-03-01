import re
from pathlib import Path

def normalize(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]

print("=" * 70)
print("PATTERN ANALYSIS - Offset-Stable Clusters")
print("=" * 70)

# Load corpus
vdr = normalize(Path("texts/vdr.txt").read_text(encoding="utf-8"))
doi = normalize(Path("texts/doi_from_beale.txt").read_text(encoding="utf-8"))
signers = normalize(Path("texts/signers.txt").read_text(encoding="utf-8"))
articles = normalize(Path("texts/articles.txt").read_text(encoding="utf-8"))

master = vdr + doi + signers + articles

# Extract ciphers
with open("beale_papers.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
cipher1 = [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]

print(f"\nCorpus: {len(master)} words")
print(f"Cipher 1: {len(cipher1)} numbers (max {max(cipher1)})")
print(f"Coverage: {len(master)/max(cipher1)*100:.1f}% - FULL COVERAGE")

# Collect letter sequences for each offset
print("\nGenerating sequences for offsets 330-340...")
sequences = {}
for offset in range(330, 341):
    letters = []
    for cipher_num in cipher1[:100]:
        if cipher_num <= offset:
            idx = cipher_num - 1
        else:
            idx = (cipher_num - offset) + len(vdr) - 1
        
        if 0 <= idx < len(master):
            letters.append(master[idx][0].upper())
        else:
            letters.append("?")
    
    sequences[offset] = "".join(letters)

# Find offset-stable clusters
print("\nSearching for 5-letter clusters appearing in 8+ offsets...")
from collections import Counter

cluster_counts = Counter()
for offset, seq in sequences.items():
    for i in range(len(seq) - 4):
        cluster = seq[i:i+5]
        cluster_counts[cluster] += 1

stable_clusters = [(c, count) for c, count in cluster_counts.items() if count >= 8]
stable_clusters.sort(key=lambda x: x[1], reverse=True)

print("\nOffset-stable clusters:")
for cluster, count in stable_clusters[:20]:
    print(f"  {cluster} - appears in {count}/11 offsets")

print("\n" + "=" * 70)
print("OFFSET 335 - Full 100-letter sequence:")
print("=" * 70)
print(sequences[335])
print()
grouped = " ".join([sequences[335][i:i+20] for i in range(0, len(sequences[335]), 20)])
print("Grouped by 20:")
for line in [grouped[i:i+70] for i in range(0, len(grouped), 70)]:
    print(f"  {line}")

# Save
with open("output/pattern_analysis.txt", "w", encoding="utf-8") as f:
    f.write("PATTERN ANALYSIS - Offset-Stable Clusters\n\n")
    f.write("Clusters appearing in 8+ offsets:\n")
    for cluster, count in stable_clusters[:30]:
        f.write(f"  {cluster}: {count}/11 offsets\n")
    f.write(f"\n\nOffset 335 full sequence (100 numbers):\n{sequences[335]}\n")

print("\nAnalysis saved to output/pattern_analysis.txt")
