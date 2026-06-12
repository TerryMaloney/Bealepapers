"""Workstream K: the soft skeleton — "Guess Who in reverse".

A cipher number's OCCURRENCE COUNT constrains its letter without any
plaintext guessing: high-frequency numbers must serve high-frequency
letters. The count -> letter-distribution mapping is calibrated empirically
from Cipher 2's verified table, then applied to the unknown ciphers to
produce per-key-index letter posteriors — a probabilistic fingerprint of
the unknown key document that the soft slide matcher can hunt with.

Ground-truth gate (must pass before any real-cipher use): using ONLY C2's
number statistics (no plaintext), the soft matcher must rank the DOI #1
across the corpus.
"""

from __future__ import annotations

import math
from collections import Counter

from .data import BealeData
from .keytable import reconstruct
from .keytext import KeyText
from .scoring import ENGLISH_FREQ

A2Z = "abcdefghijklmnopqrstuvwxyz"


def _bucket(k: int) -> str:
    if k == 1:
        return "1"
    if k == 2:
        return "2"
    if k <= 4:
        return "3-4"
    return "5+"


def calibrate_count_posteriors(data: BealeData,
                               alpha: float = 0.6) -> dict[str, dict[str, float]]:
    """P(letter | occurrence-count bucket), from C2's verified table,
    smoothed toward English first-letter-ish frequencies."""
    kt = reconstruct(data)
    buckets: dict[str, Counter] = {}
    for e in kt.entries.values():
        buckets.setdefault(_bucket(e.occurrences), Counter())[e.letter] += 1
    out = {}
    for b, c in buckets.items():
        total = sum(c.values())
        out[b] = {ch: (c.get(ch, 0) + alpha * 26 * ENGLISH_FREQ[ch])
                  / (total + alpha * 26) for ch in A2Z}
    return out


def soft_skeleton(numbers, posteriors,
                  min_count: int = 2) -> dict[int, dict[str, float]]:
    """key-document word index -> letter distribution, for numbers whose
    count makes the posterior informative."""
    counts = Counter(numbers)
    return {n: posteriors[_bucket(k)] for n, k in counts.items()
            if k >= min_count}


def refine_with_bigrams(numbers, skel: dict[int, dict[str, float]],
                        rounds: int = 2, damp: float = 0.5,
                        ) -> dict[int, dict[str, float]]:
    """Sharpen count-based posteriors using positional context: every
    occurrence of a number sits between neighbors whose letter
    distributions constrain it through the English bigram LM. Damped
    mean-field updates over the tied-symbol chain."""
    from .ngrams import Quadgrams
    from .scanhmm import bigram_logprobs

    big = bigram_logprobs(Quadgrams.load())
    B = [[10 ** big[a][b] for b in range(26)] for a in range(26)]
    # current belief per number (uniform-ish English for non-skeleton numbers)
    base = {ch: ENGLISH_FREQ[ch] for ch in A2Z}
    belief: dict[int, list[float]] = {}
    for n in set(numbers):
        dist = skel.get(n, base)
        belief[n] = [dist[ch] for ch in A2Z]
    occ: dict[int, list[int]] = {}
    for i, n in enumerate(numbers):
        occ.setdefault(n, []).append(i)
    for _ in range(rounds):
        new: dict[int, list[float]] = {}
        for n, positions in occ.items():
            if n not in skel:
                continue  # only refine informative symbols
            logp = [math.log(max(skel[n][A2Z[c]], 1e-9)) for c in range(26)]
            for i in positions:
                if i > 0:
                    prev = belief[numbers[i - 1]]
                    for c in range(26):
                        m = sum(prev[a] * B[a][c] for a in range(26))
                        logp[c] += math.log(max(m, 1e-12))
                if i + 1 < len(numbers):
                    nxt = belief[numbers[i + 1]]
                    for c in range(26):
                        m = sum(B[c][b] * nxt[b] for b in range(26))
                        logp[c] += math.log(max(m, 1e-12))
            mx = max(logp)
            p = [math.exp(v - mx) for v in logp]
            z = sum(p)
            p = [v / z for v in p]
            old = belief[n]
            mixed = [(o ** damp) * (v ** (1 - damp)) for o, v in zip(old, p)]
            z = sum(mixed)
            new[n] = [v / z for v in mixed]
        belief.update(new)
    return {n: {A2Z[c]: belief[n][c] for c in range(26)}
            for n in skel}


def soft_slide_match(skel: dict[int, dict[str, float]], kt: KeyText,
                     offsets: range | None = None):
    """Best offset by total log-likelihood-ratio of doc first letters under
    the soft skeleton vs the doc's own letter background."""
    F = [w[0] if w else "?" for w in kt.tokens]
    n = len(F)
    bg = Counter(F)
    total = sum(bg.values())
    bgp = {ch: bg.get(ch, 0.5) / total for ch in A2Z}
    items = sorted(skel.items())
    if not items:
        return None
    max_idx = items[-1][0]
    offs = offsets if offsets is not None else range(-50, max(1, n - max_idx + 50))
    best = (-1e18, 0, 0)
    for o in offs:
        s = 0.0
        used = 0
        for idx, dist in items:
            q = (idx - 1) + o
            if 0 <= q < n and F[q] in dist:
                s += math.log10(dist[F[q]] / max(bgp.get(F[q], 1e-4), 1e-4))
                used += 1
        if used >= 20 and s > best[0]:
            best = (s, o, used)
    score, off, used = best
    # null: same skeleton against random circular shifts of the doc letters
    import random

    rng = random.Random(13)
    null = []
    for _ in range(60):
        shift = rng.randrange(1, n)
        s = 0.0
        for idx, dist in items:
            q = ((idx - 1 + off + shift) % n)
            if F[q] in dist:
                s += math.log10(dist[F[q]] / max(bgp.get(F[q], 1e-4), 1e-4))
        null.append(s)
    import statistics

    mu, sd = statistics.mean(null), statistics.stdev(null)
    z = (score - mu) / sd if sd else 0.0
    return {"doc_id": kt.id, "offset": off, "score": score, "used": used,
            "z": z}


def soft_rank_documents(skel, keytexts, top: int = 10):
    hits = []
    for kt in keytexts:
        h = soft_slide_match(skel, kt)
        if h:
            hits.append(h)
    hits.sort(key=lambda h: h["z"], reverse=True)
    return hits[:top]
