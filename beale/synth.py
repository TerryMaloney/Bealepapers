"""Synthetic cipher generators for solver validation.

Every solver must recover known period English encoded under its own
assumed model — at the real target's length, symbol count, and singleton
fraction — before its output on real ciphers is taken seriously.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .data import BealeData
from .keytext import KeyText


@dataclass(frozen=True)
class CipherProfile:
    name: str
    length: int
    distinct: int
    singleton_frac: float  # fraction of TEXT positions carrying a singleton


def profile_of(data: BealeData, cipher: str) -> CipherProfile:
    from collections import Counter

    nums = data.cipher_for(cipher)
    c = Counter(nums)
    singles = sum(1 for n in nums if c[n] == 1)
    return CipherProfile(cipher, len(nums), len(c), singles / len(nums))


def encode_book_cipher(
    plaintext: str, key: KeyText, rng: random.Random
) -> list[int] | None:
    """Encode by choosing uniformly among key words with the right initial.

    Natural homophone structure (Zipf reuse, realistic singleton rates)
    emerges from the key text itself. Returns None if a letter has no
    matching word in the key.
    """
    by_letter: dict[str, list[int]] = {}
    for i, w in enumerate(key.tokens):
        if w:
            by_letter.setdefault(w[0], []).append(i + 1)
    out = []
    for ch in plaintext:
        pool = by_letter.get(ch)
        if not pool:
            return None
        out.append(rng.choice(pool))
    return out


def encode_scan_forward(
    plaintext: str, key: KeyText, rng: random.Random, skip_prob: float = 0.0
) -> list[int] | None:
    """Finger-on-the-page encoding: for each letter take the NEXT word
    starting with it, wrapping at the end of the document. ``skip_prob``
    models encoder sloppiness (occasionally skipping a matching word).
    """
    n = len(key.tokens)
    firsts = [w[0] if w else "" for w in key.tokens]
    pos = 0  # 0-based index of last used word
    out = []
    for ch in plaintext:
        found = None
        for step in range(1, n + 1):
            j = (pos + step) % n
            if firsts[j] == ch:
                if skip_prob and rng.random() < skip_prob:
                    continue
                found = j
                break
        if found is None:
            return None
        out.append(found + 1)
        pos = found
    return out


def columnar_transpose(seq: list, width: int, perm: list[int]) -> list:
    """Write row-wise into `width` columns, read columns in `perm` order."""
    cols = [seq[i::width] for i in range(width)]
    out = []
    for p in perm:
        out.extend(cols[p])
    return out


def sample_plaintext(
    tokens_pool: list[str], length: int, rng: random.Random
) -> str:
    """Contiguous letter-stream excerpt of the given length from a token list."""
    stream = "".join(tokens_pool)
    start = rng.randrange(0, max(1, len(stream) - length))
    return stream[start : start + length]


def names_list_plaintext(rng: random.Random, length: int) -> str:
    """Synthetic 'names and residences' plaintext matching C3's claimed content."""
    first = ["thomas", "james", "william", "john", "robert", "george", "samuel",
             "joseph", "richard", "charles", "daniel", "peter", "henry", "edward"]
    last = ["beale", "morriss", "buford", "harper", "clayton", "witcher", "otey",
            "saunders", "moseley", "luck", "board", "wright", "johnson", "scott"]
    places = ["oflynchburgvirginia", "ofbedfordcounty", "ofbotetourtcounty",
              "ofrichmondvirginia", "offincastle", "ofroanokecounty",
              "ofcampbellcounty", "ofnewlondonvirginia"]
    parts = []
    while sum(map(len, parts)) < length:
        parts.append(rng.choice(first) + rng.choice(last) + rng.choice(places))
    return "".join(parts)[:length]
