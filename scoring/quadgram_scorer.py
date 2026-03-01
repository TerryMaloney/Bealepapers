"""
Quadgram fitness scorer for English text detection.

Uses log-probability of 4-letter sequences to score how English-like
a decoded stream is. Based on quadgram frequencies from
practicalcryptography.com.

Scoring: higher = more English-like.
  - English text: typically -2.2 to -2.5 per quadgram (normalized)
  - Random letters: typically -3.5 to -4.0 per quadgram
  - The gap is large and reliable for streams >= 50 characters.
"""

import math
from pathlib import Path
from typing import Optional

_QUADGRAMS = None
_TOTAL = 0
_FLOOR = 0.0

QUADGRAM_FILE = Path(__file__).resolve().parent / "english_quadgrams.txt"


def _load_quadgrams():
    global _QUADGRAMS, _TOTAL, _FLOOR
    if _QUADGRAMS is not None:
        return

    _QUADGRAMS = {}
    with open(QUADGRAM_FILE, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                _QUADGRAMS[parts[0]] = int(parts[1])
                _TOTAL += int(parts[1])

    _FLOOR = math.log10(0.01 / _TOTAL)


def quadgram_score(text: str) -> float:
    """
    Compute average log10-probability per quadgram for text.
    Only considers alphabetic characters (uppercase).
    Returns 0.0 for text shorter than 4 characters.
    """
    _load_quadgrams()

    letters = "".join(c for c in text.upper() if c.isalpha())
    n = len(letters)
    if n < 4:
        return 0.0

    total = 0.0
    count = 0
    for i in range(n - 3):
        qg = letters[i:i + 4]
        c = _QUADGRAMS.get(qg, 0)
        if c > 0:
            total += math.log10(c / _TOTAL)
        else:
            total += _FLOOR
        count += 1

    return total / count if count > 0 else 0.0


def quadgram_score_raw(text: str) -> float:
    """Return the raw (non-normalized) sum of log10 probabilities."""
    _load_quadgrams()

    letters = "".join(c for c in text.upper() if c.isalpha())
    n = len(letters)
    if n < 4:
        return 0.0

    total = 0.0
    for i in range(n - 3):
        qg = letters[i:i + 4]
        c = _QUADGRAMS.get(qg, 0)
        if c > 0:
            total += math.log10(c / _TOTAL)
        else:
            total += _FLOOR
        count = n - 3

    return total


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from corpus.canonical import CanonicalCorpus
    from constraints.overlap_engine import load_cipher
    from extractors import get_extractor

    corpus = CanonicalCorpus.load("corpus/CANON_DOI.json")

    print("=== Quadgram Scorer Calibration ===\n")

    # Cipher 2 known correct
    c2 = load_cipher(2)
    ext = get_extractor("first_letter")
    c2_stream = corpus.decode_with_extractor(c2, ext)
    c2_score = quadgram_score(c2_stream)
    print(f"Cipher 2 (known correct, DOI): {c2_score:.4f} per quadgram")

    # Cipher 1 first_letter (should be noise)
    c1 = load_cipher(1)
    c1_stream = corpus.decode_with_extractor(c1, ext)
    c1_score = quadgram_score(c1_stream)
    print(f"Cipher 1 (first_letter, DOI): {c1_score:.4f} per quadgram")

    # Known English text
    english = "IHAVEDEPOSITEDINTHECOOUNTYOFBEDFORDABOUTFOURMILESFROMBUFORDS"
    eng_score = quadgram_score(english)
    print(f"Known English sentence:       {eng_score:.4f} per quadgram")

    # Random letters
    import random
    random.seed(42)
    rand_text = "".join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(520))
    rand_score = quadgram_score(rand_text)
    print(f"Random 26-letter alphabet:    {rand_score:.4f} per quadgram")

    print(f"\nGap (English - Random): {eng_score - rand_score:.4f}")
    print(f"Gap (C2 correct - C1 noise): {c2_score - c1_score:.4f}")
