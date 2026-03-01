"""
Re-run word-cipher test on corrected niche texts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from corpus.keytexts.loader import load_normalized

LOCATION_WORDS = {"county", "creek", "ridge", "mountain", "river", "road", "mile",
                  "miles", "north", "south", "east", "west", "degrees", "vault",
                  "cave", "rock", "tree", "feet", "inches", "buried", "deposited",
                  "treasure", "gold", "silver", "iron", "stone", "bedford", "buford",
                  "virginia", "pot", "pots", "covered", "lined"}
FUNCTION_WORDS = {"the", "of", "and", "to", "in", "a", "is", "that", "for", "it",
                  "with", "as", "was", "on", "are", "be", "by", "at", "from", "or",
                  "an", "not", "but", "have", "this", "had", "has", "which", "their",
                  "been", "its", "all", "were", "they", "will", "would", "shall",
                  "may", "can", "no", "if", "so", "we", "our", "he", "his", "her"}


def test_wc(cnums, tokens, label):
    tc = len(tokens)
    word_seq = []
    valid = 0
    for cn in cnums:
        idx = cn - 1
        if 0 <= idx < tc:
            word_seq.append(tokens[idx].lower())
            valid += 1
        else:
            word_seq.append("???")

    n = len(word_seq)
    func_count = sum(1 for w in word_seq if w in FUNCTION_WORDS)
    loc_count = sum(1 for w in word_seq if w in LOCATION_WORDS)
    func_rate = func_count / n if n else 0

    preview = " ".join(word_seq[:50])
    print(f"\n{label}:")
    print(f"  valid={valid}/{n}, func_rate={func_rate:.3f}, loc_words={loc_count}")
    print(f"  preview: {preview[:200]}")


c1 = load_cipher(1)
c3 = load_cipher(3)

for kid in ["webb_freemason_monitor", "anderson_constitutions", "hening_statutes_v1",
            "hening_statutes_v7", "preston_illustrations_masonry"]:
    norm = load_normalized(kid)
    if norm:
        tokens = norm["tokens"]
        if len(tokens) >= max(c1):
            test_wc(c1, tokens, f"C1 | {kid}")
        if len(tokens) >= max(c3):
            test_wc(c3, tokens, f"C3 | {kid}")
