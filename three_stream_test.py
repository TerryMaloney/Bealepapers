import re
from pathlib import Path

def normalize(text):
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]

print("=" * 70)
print("THREE-STREAM EXTRACTION TEST")
print("Testing H2: Right book, wrong extraction rule")
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

print(f"\nCorpus: {len(master)} words")
print(f"Testing first 100 cipher numbers with offset 335")
print()

# Extract three streams
offset = 335
stream1_first = []    # First letter (existing method)
stream2_second = []   # Second letter (new)
stream3_length = []   # Word length (new)
words_mapped = []     # Store actual words for reference

for cipher_num in cipher1[:100]:
    if cipher_num <= offset:
        idx = cipher_num - 1
    else:
        idx = (cipher_num - offset) + len(vdr) - 1
    
    if 0 <= idx < len(master):
        word = master[idx]
        words_mapped.append(word)
        
        # Stream 1: First letter
        stream1_first.append(word[0].upper() if word else "?")
        
        # Stream 2: Second letter
        if len(word) >= 2:
            stream2_second.append(word[1].upper())
        else:
            stream2_second.append("_")  # Underscore for 1-letter words
        
        # Stream 3: Word length
        stream3_length.append(len(word))
    else:
        words_mapped.append("[OOR]")
        stream1_first.append("?")
        stream2_second.append("?")
        stream3_length.append(0)

# Format output
s1 = "".join(stream1_first)
s2 = "".join(stream2_second)

print("STREAM 1 - FIRST LETTERS (current method):")
print("=" * 70)
for i in range(0, len(s1), 50):
    print(s1[i:i+50])

print("\n" + "=" * 70)
print("STREAM 2 - SECOND LETTERS (alternative extraction):")
print("=" * 70)
for i in range(0, len(s2), 50):
    print(s2[i:i+50])

print("\n" + "=" * 70)
print("STREAM 3 - WORD LENGTHS (numeric pattern):")
print("=" * 70)
length_str = " ".join([str(l) if l < 10 else "X" for l in stream3_length])
print(length_str)

print("\n" + "=" * 70)
print("SIDE-BY-SIDE COMPARISON (grouped by 10):")
print("=" * 70)
print("Position | First | Second | Lengths | Sample Words")
print("-" * 70)
for i in range(0, 100, 10):
    chunk_1 = s1[i:i+10]
    chunk_2 = s2[i:i+10]
    chunk_len = " ".join([str(stream3_length[j]) for j in range(i, min(i+10, 100))])
    sample_words = ", ".join(words_mapped[i:min(i+3, 100)])
    print(f"{i:3d}-{i+9:3d}  | {chunk_1:10s} | {chunk_2:10s} | {chunk_len:20s} | {sample_words[:30]}")

print("\n" + "=" * 70)
print("ANALYSIS - Looking for English patterns:")
print("=" * 70)

# Check for common trigrams in second-letter stream
common_trigrams = ["THE", "ING", "AND", "ION", "ENT", "FOR", "TIO", "ERE", "HER", "ATE"]
print("\nCommon English trigrams in FIRST-letter stream:")
found_first = []
for trig in common_trigrams:
    if trig in s1:
        pos = s1.find(trig)
        found_first.append(f"  {trig} at position {pos}")
if found_first:
    for f in found_first:
        print(f)
else:
    print("  None found")

print("\nCommon English trigrams in SECOND-letter stream:")
found_second = []
for trig in common_trigrams:
    if trig in s2:
        pos = s2.find(trig)
        found_second.append(f"  {trig} at position {pos}")
if found_second:
    for f in found_second:
        print(f)
else:
    print("  None found")

# Save detailed report
with open("output/three_stream_analysis.txt", "w", encoding="utf-8") as f:
    f.write("THREE-STREAM EXTRACTION TEST\n")
    f.write("Testing H2: Right book, wrong extraction rule\n\n")
    f.write(f"Offset: {offset}\n")
    f.write(f"Cipher numbers: 1-100\n\n")
    f.write("STREAM 1 (First letters):\n")
    f.write(s1 + "\n\n")
    f.write("STREAM 2 (Second letters):\n")
    f.write(s2 + "\n\n")
    f.write("STREAM 3 (Word lengths):\n")
    f.write(length_str + "\n\n")
    f.write("\nDETAILED MAPPING:\n")
    f.write("Pos | Cipher# | Word           | 1st | 2nd | Len\n")
    f.write("-" * 60 + "\n")
    for i in range(100):
        cipher_num = cipher1[i]
        word = words_mapped[i][:15].ljust(15)
        l1 = stream1_first[i]
        l2 = stream2_second[i]
        length = stream3_length[i]
        f.write(f"{i+1:3d} | {cipher_num:4d}    | {word} | {l1}   | {l2}   | {length}\n")

print("\nDetailed analysis saved to output/three_stream_analysis.txt")
