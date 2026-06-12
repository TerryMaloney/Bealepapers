"""Document fingerprint matcher: find the key document from a skeleton.

Stage 1: slide the pinned first letters over every candidate document's
first-letter string; binomial significance versus the letter-frequency
null. Stage 2: banded insert/delete drift alignment on top candidates —
real keys drift (the known C2 key has an extra word near 155 and several
missing words near 467), so exact sliding alone is not enough.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from .keytext import KeyText


@dataclass(frozen=True)
class SlideHit:
    doc_id: str
    offset: int               # doc word index of skeleton index 1 (0-based)
    hits: int
    pins: int
    expected: float
    z: float


def first_letter_string(kt: KeyText) -> str:
    return "".join(w[0] if w else "?" for w in kt.tokens)


def slide_match(pins: dict[int, str], kt: KeyText,
                min_overlap: int = 10) -> SlideHit | None:
    """Best offset of the skeleton against one document (exact, no drift)."""
    F = first_letter_string(kt)
    n = len(F)
    if not pins or n < min_overlap:
        return None
    items = sorted(pins.items())
    # per-letter doc positions
    by_letter: dict[str, list[int]] = {}
    for q, ch in enumerate(F):
        by_letter.setdefault(ch, []).append(q)
    offsets: Counter = Counter()
    for idx, letter in items:
        for q in by_letter.get(letter, ()):
            offsets[q - (idx - 1)] += 1
    if not offsets:
        return None
    # null match rate weighted by the doc's own letter frequencies
    freq = {ch: len(ps) / n for ch, ps in by_letter.items()}
    m0 = sum(freq.get(letter, 0.0) for _, letter in items) / len(items)
    best_o, best_hits, best_z = 0, -1, -99.0
    for o, hits in offsets.most_common(50):
        p = sum(1 for idx, _ in items if 0 <= (idx - 1) + o < n)
        if p < min_overlap:
            continue
        mu = p * m0
        sd = math.sqrt(max(1e-9, p * m0 * (1 - m0)))
        z = (hits - mu) / sd
        if z > best_z:
            best_o, best_hits, best_z = o, hits, z
    if best_hits < 0:
        return None
    p = sum(1 for idx, _ in items if 0 <= (idx - 1) + best_o < len(F))
    return SlideHit(kt.id, best_o, best_hits, p, p * m0, best_z)


@dataclass(frozen=True)
class DriftAlignment:
    doc_id: str
    offset: int
    matches: int
    pins: int
    cost: float
    drift_profile: tuple[tuple[int, int], ...]   # (skeleton index, drift)


def drift_align(pins: dict[int, str], kt: KeyText, offset: int,
                band: int = 12, mismatch: float = 1.0,
                drift_cost: float = 0.5) -> DriftAlignment:
    """Banded DP allowing cumulative insert/delete drift across the doc."""
    F = first_letter_string(kt)
    n = len(F)
    items = sorted(pins.items())
    width = 2 * band + 1
    INF = float("inf")
    dp = [0.0] * width
    back: list[list[int]] = []
    for idx, letter in items:
        ndp = [INF] * width
        nb = [0] * width
        for d in range(width):
            delta = d - band
            q = (idx - 1) + offset + delta
            step = mismatch if (q < 0 or q >= n or F[q] != letter) else 0.0
            best_v, best_pd = INF, d
            for pd in range(width):
                v = dp[pd] + drift_cost * abs(d - pd)
                if v < best_v:
                    best_v, best_pd = v, pd
            ndp[d] = best_v + step
            nb[d] = best_pd
        dp = ndp
        back.append(nb)
    end_d = min(range(width), key=lambda d: dp[d])
    cost = dp[end_d]
    # backtrack drift profile
    path = [end_d]
    for nb in reversed(back[1:]):
        path.append(nb[path[-1]])
    path.reverse()
    profile = []
    last = None
    matches = 0
    for (idx, letter), d in zip(items, path):
        delta = d - band
        q = (idx - 1) + offset + delta
        if 0 <= q < n and F[q] == letter:
            matches += 1
        if delta != last:
            profile.append((idx, delta))
            last = delta
    return DriftAlignment(kt.id, offset, matches, len(items), cost,
                          tuple(profile))


def rank_documents(pins: dict[int, str], keytexts, top: int = 20,
                   ) -> list[SlideHit]:
    hits = []
    for kt in keytexts:
        h = slide_match(pins, kt)
        if h:
            hits.append(h)
    hits.sort(key=lambda h: h.z, reverse=True)
    return hits[:top]
