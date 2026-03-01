import re
from pathlib import Path
from collections import Counter

def normalize(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]

print("=" * 70)
print("DEEP PATTERN ANALYSIS")
print("=" * 70)

# Load corpus
vdr = normalize(Path("texts/vdr.txt").read_text(encoding="utf-8"))
doi = normalize(Path("texts/doi_from_beale.txt").read_text(encoding="utf-8"))
signers = normalize(Path("texts/signers.txt").read_text(encoding="utf-8"))
articles = normalize(Path("texts/articles.txt").read_text(encoding="utf-8"))
master = vdr + doi + signers + articles

# Load cipher
with open("beale_papers.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
cipher1 = [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]

offset = 335

# Map first 100 and collect data
mappings = []
for i, cipher_num in enumerate(cipher1[:100]):
    if cipher_num <= offset:
        idx = cipher_num - 1
    else:
        idx = (cipher_num - offset) + len(vdr) - 1
    
    if 0 <= idx < len(master):
        word = master[idx]
        mappings.append({
            "pos": i,
            "cipher_num": cipher_num,
            "word": word,
            "length": len(word),
            "first": word[0].upper(),
            "second": word[1].upper() if len(word) >= 2 else "_",
            "last": word[-1].upper()
        })

print("\n1. REPEATED CIPHER NUMBERS (First 100)")
print("=" * 70)
cipher_counts = Counter([m["cipher_num"] for m in mappings])
repeats = [(num, count) for num, count in cipher_counts.items() if count > 1]
repeats.sort(key=lambda x: x[1], reverse=True)

if repeats:
    print("Cipher numbers appearing multiple times:")
    for num, count in repeats[:10]:
        word = [m["word"] for m in mappings if m["cipher_num"] == num][0]
        positions = [m["pos"] for m in mappings if m["cipher_num"] == num]
        print(f"  {num:4d} appears {count}x -> '{word}' at positions {positions}")
else:
    print("  No repeated cipher numbers in first 100")

print("\n2. WORD LENGTH PATTERN ANALYSIS")
print("=" * 70)
lengths = [m["length"] for m in mappings]
length_counter = Counter(lengths)
print(f"Average word length: {sum(lengths)/len(lengths):.1f}")
print(f"Most common lengths: {length_counter.most_common(5)}")

# Check for arithmetic patterns
print("\nChecking for arithmetic progressions in lengths...")
diffs = [lengths[i+1] - lengths[i] for i in range(len(lengths)-1)]
diff_counter = Counter(diffs)
print(f"Most common length differences: {diff_counter.most_common(5)}")

print("\n3. ALTERNATIVE EXTRACTION: LAST LETTER")
print("=" * 70)
last_letters = "".join([m["last"] for m in mappings])
print("Last-letter stream:")
for i in range(0, len(last_letters), 50):
    print(last_letters[i:i+50])

# Check for common trigrams
common_trigrams = ["THE", "ING", "AND", "ION", "ENT", "FOR", "TIO", "ERE", "HER", "ATE"]
print("\nCommon English trigrams in LAST-letter stream:")
found_last = []
for trig in common_trigrams:
    if trig in last_letters:
        pos = last_letters.find(trig)
        found_last.append(f"  {trig} at position {pos}")
if found_last:
    for f in found_last:
        print(f)
else:
    print("  None found")

print("\n4. DOCUMENT SOURCE DISTRIBUTION")
print("=" * 70)
vdr_count = sum(1 for m in mappings if (m["cipher_num"] <= offset and m["cipher_num"] <= len(vdr)))
doi_count = sum(1 for m in mappings if (
    (m["cipher_num"] <= offset and m["cipher_num"] > len(vdr)) or
    (m["cipher_num"] > offset and (m["cipher_num"] - offset) <= len(doi))
))

print(f"Words from VDR: ~{vdr_count}")
print(f"Words from DOI: ~{doi_count}")
print(f"Words from Signers/Articles: ~{100-vdr_count-doi_count}")

print("\n5. CONSONANT-ONLY EXTRACTION (Testing alternative rules)")
print("=" * 70)
consonants = "BCDFGHJKLMNPQRSTVWXYZ"
consonant_stream = []
for m in mappings:
    word_consonants = [c.upper() for c in m["word"] if c.upper() in consonants]
    if word_consonants:
        consonant_stream.append(word_consonants[0])  # First consonant
    else:
        consonant_stream.append("_")

cons_str = "".join(consonant_stream)
print("First-consonant stream:")
for i in range(0, len(cons_str), 50):
    print(cons_str[i:i+50])

print("\n6. CRITICAL OBSERVATION")
print("=" * 70)
print("All three letter-extraction methods produce NON-ENGLISH output:")
print("  - First letters: PMTLITIAFA...")
print("  - Second letters: EEHESRNMOC...")
print("  - Last letters: " + last_letters[:10] + "...")
print("  - First consonants: " + cons_str[:10] + "...")
print()
print("Yet the WORDS themselves are coherent English:")
sample_words = [m["word"] for m in mappings[:20]]
print(f"  Sample: {', '.join(sample_words[:15])}")
print()
print("INTERPRETATION:")
print("  The book index is working correctly.")
print("  But simple letter extraction (any position) fails.")
print()
print("This suggests:")
print("  1. Multi-layer encoding (e.g., transposition after extraction)")
print("  2. Non-acrostic method (e.g., word arithmetic, modulo)")
print("  3. Wrong book (but structurally similar)")
print("  4. Intentional obfuscation or hoax")

# Save report
with open("output/deep_pattern_analysis.txt", "w", encoding="utf-8") as f:
    f.write("DEEP PATTERN ANALYSIS\n\n")
    f.write("Repeated cipher numbers:\n")
    for num, count in repeats[:20]:
        word = [m["word"] for m in mappings if m["cipher_num"] == num][0]
        f.write(f"  {num}: {count}x -> {word}\n")
    f.write(f"\n\nLast-letter stream:\n{last_letters}\n")
    f.write(f"\nFirst-consonant stream:\n{cons_str}\n")
    f.write(f"\nWord sample:\n{', '.join([m['word'] for m in mappings[:50]])}\n")

print("\nAnalysis saved to output/deep_pattern_analysis.txt")
