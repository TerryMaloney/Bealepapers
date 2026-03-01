"""
Names/kin-aware scorer for nomenclator-style decoded streams.

No external lists. Nameslike: vowel ratio, name bigrams/trigrams, separator reward.
Kin/legal beacons: soft bonus. Used to score C3 as names list.
"""

import re
from typing import Dict, Tuple

# Name-like bigrams (common in English names)
NAME_BIGRAMS = frozenset([
    "AL", "AN", "AR", "ER", "EL", "EN", "ON", "OR", "TH", "ST", "CH", "SH",
    "IN", "ED", "IA", "LE", "RE", "ES", "TE", "NE", "TI", "AT", "IT", "IS",
    "AS", "OU", "CO", "RO", "LI", "LL", "EE", "OO", "SS", "TT", "NN", "RR",
])
# Name-like trigrams
NAME_TRIGRAMS = frozenset([
    "SON", "TON", "ING", "AND", "ENT", "ION", "TIO", "ERE", "TER", "EST",
    "ATE", "ITH", "HIS", "HER", "FOR", "THA", "THE", "CON", "COM", "ALL",
    "ILL", "ELL", "ORE", "ARD", "ART", "ERT", "ORT", "IAN", "ELL", "BER",
])
# Kin/legal vocabulary (soft bonus)
KIN_BEACONS = frozenset([
    "SON", "DAUGHTER", "HEIR", "HEIRS", "WIDOW", "ESTATE", "COUNTY",
    "VIRGINIA", "NAME", "NAMES", "RESIDES",
])
VOWELS = set("AEIOUaeiou")


def names_kin_score(stream: str) -> Tuple[float, Dict[str, float]]:
    """
    Single score 0-100 plus breakdown. Higher = more name/kin-like.
    """
    if not stream or len(stream) < 4:
        return 0.0, {}
    up = stream.upper()
    letters = "".join(c for c in up if c.isalpha())
    if len(letters) < 4:
        return 0.0, {}
    n = len(letters)

    # --- Vowel ratio in windows 4-12 ---
    vowel_ok = 0
    windows_checked = 0
    for wlen in [4, 6, 8, 10, 12]:
        if wlen > n:
            continue
        for i in range(0, n - wlen + 1):
            w = letters[i : i + wlen]
            v = sum(1 for c in w if c in VOWELS)
            r = v / len(w)
            if 0.25 <= r <= 0.55:  # plausible for names
                vowel_ok += 1
            windows_checked += 1
    vowel_component = (vowel_ok / windows_checked * 100.0) if windows_checked else 0.0

    # --- Penalize long consonant runs ---
    max_consonant = 0
    run = 0
    for c in letters:
        if c in VOWELS:
            run = 0
        else:
            run += 1
            max_consonant = max(max_consonant, run)
    consonant_penalty = 0.0
    if max_consonant > 5:
        consonant_penalty = min(30.0, (max_consonant - 5) * 5.0)
    vowel_component = max(0.0, vowel_component - consonant_penalty)

    # --- Name bigrams/trigrams ---
    bigrams = [letters[i : i + 2] for i in range(len(letters) - 1)]
    trigrams = [letters[i : i + 3] for i in range(len(letters) - 2)]
    hit_b = sum(1 for b in bigrams if b in NAME_BIGRAMS)
    hit_t = sum(1 for t in trigrams if t in NAME_TRIGRAMS)
    denom_b = len(bigrams) or 1
    denom_t = len(trigrams) or 1
    ngram_component = min(100.0, (hit_b / denom_b * 50.0) + (hit_t / denom_t * 50.0))

    # --- Separator reward (space or rare char as proxy) ---
    spaces = sum(1 for c in stream if c.isspace() or c in ",.;")
    sep_component = min(20.0, (spaces / max(1, len(stream)) * 100.0))

    # --- Kin beacons (soft) ---
    kin_hits = 0
    for token in KIN_BEACONS:
        if token in up:
            kin_hits += 1
    kin_component = min(25.0, kin_hits * 4.0)

    # Combined: vowel 30%, ngram 40%, sep 10%, kin 20% (soft)
    total = (
        0.30 * vowel_component
        + 0.40 * ngram_component
        + 0.10 * sep_component
        + 0.20 * kin_component
    )
    total = max(0.0, min(100.0, total))
    breakdown = {
        "vowel": round(vowel_component, 2),
        "ngram": round(ngram_component, 2),
        "separator": round(sep_component, 2),
        "kin": round(kin_component, 2),
    }
    return round(total, 4), breakdown


def test_names_kin_scorer():
    """Unit test: random => low, hardcoded surnames => higher."""
    import random
    random.seed(103)
    # Random letters
    rand_stream = "".join(chr(random.randint(65, 90)) for _ in range(200))
    score_rand, _ = names_kin_score(rand_stream)
    # Hardcoded tiny set of real surnames (no external list)
    surnames = "SMITH JOHNSON WILLIAMS BROWN JONES GARCIA MILLER DAVIS"
    score_names, br = names_kin_score(surnames)
    assert score_rand < 50, f"Random should score low, got {score_rand}"
    assert score_names > score_rand, f"Names should score higher than random: {score_names} vs {score_rand}"
    return score_rand, score_names, br


if __name__ == "__main__":
    sr, sn, br = test_names_kin_scorer()
    print(f"Random letters score: {sr}")
    print(f"Surnames score: {sn} {br}")
