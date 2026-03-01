import re
from pathlib import Path

print("Creating detailed context report...")

# Load data
with open("beale_papers.txt", "r") as f:
    lines = f.readlines()

cipher1 = [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]

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

offset = 335
window = 10

# Create detailed report
with open("output/cipher1_detailed_context.txt", "w", encoding="utf-8") as f:
    f.write("BEALE CIPHER 1 - DETAILED CONTEXT REPORT\n")
    f.write(f"Offset: {offset}, Window: ±{window} words\n")
    f.write("=" * 80 + "\n\n")
    
    for i, cipher_num in enumerate(cipher1[:30], 1):  # First 30 for detail
        if cipher_num <= offset:
            idx = cipher_num - 1
        else:
            idx = (cipher_num - offset) + len(vdr_words) - 1
        
        if 0 <= idx < len(master_words):
            word = master_words[idx]
            letter = word[0].upper() if word else "?"
            
            # Get context
            start = max(0, idx - window)
            end = min(len(master_words), idx + window + 1)
            context_words = master_words[start:end]
            
            # Mark the target word
            target_pos = idx - start
            if target_pos < len(context_words):
                context_words[target_pos] = f"**{context_words[target_pos]}**"
            
            context = " ".join(context_words)
            
            f.write(f"#{i:2d}. Cipher number: {cipher_num}\n")
            f.write(f"     Base word: '{word}' [First letter: {letter}]\n")
            f.write(f"     Context: {context}\n\n")
        else:
            f.write(f"#{i:2d}. Cipher number: {cipher_num} - OUT OF RANGE\n\n")

print("Detailed report saved to output/cipher1_detailed_context.txt")

# Create summary
print("\nSUMMARY OF RESULTS:")
print("=" * 70)
print(f"- Created texts/ with VDR ({len(vdr_words)} words), DOI ({len(doi_words)} words), Signers ({len(signers_words)} words)")
print(f"- Total word index: {len(master_words)} words")
print(f"- Cipher 1: {len(cipher1)} numbers, max value {max(cipher1)}")
print(f"- Batch offset trial completed (offsets 330-340)")
print(f"- Detailed context report created (first 30 numbers)")
print("\nOutput files:")
print("  - output/cipher1_decode.txt")
print("  - output/batch_offset_trial.txt")
print("  - output/cipher1_detailed_context.txt")
print("\nNext steps:")
print("  - Review first-letter sequences for patterns")
print("  - Check if context windows show geographic/directional terms")
print("  - Consider if Articles text is needed (Cipher 1 max=2906, current corpus=2322)")
