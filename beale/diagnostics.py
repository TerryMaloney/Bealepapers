"""Hoax / randomness diagnostics — first-class honest output.

When the DOI (Cipher 2's key) is applied to Cipher 1, the decode contains
Jim Gillogly's famous near-alphabetical run ("abfdefghiijklmmnohpp"), which
is astronomically unlikely in a genuine message and is the canonical
evidence that C1-with-DOI is an artifact, not a plaintext. These tests
quantify that, and compare candidate decodes against a random baseline so
the tool can say honestly whether a decode is distinguishable from noise.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from typing import Sequence

from .engine import DecodeConfig, decode
from .ngrams import Quadgrams
from .scoring import index_of_coincidence, letters_only


@dataclass(frozen=True)
class Run:
    start: int
    text: str


def detect_alphabetical_runs(text: str, min_len: int = 5) -> list[Run]:
    """Find runs where letters ascend by 0 or 1 (e.g. 'abcdefghiij')."""
    t = letters_only(text)
    runs: list[Run] = []
    i = 0
    while i < len(t):
        j = i
        while j + 1 < len(t) and 0 <= ord(t[j + 1]) - ord(t[j]) <= 1:
            j += 1
        if j - i + 1 >= min_len:
            runs.append(Run(start=i, text=t[i : j + 1]))
        i = max(j, i + 1)
    return runs


def incremental_fraction(text: str) -> float:
    """Fraction of adjacent letter pairs that ascend by exactly one."""
    t = letters_only(text)
    if len(t) < 2:
        return 0.0
    ups = sum(1 for a, b in zip(t, t[1:]) if ord(b) - ord(a) == 1)
    return ups / (len(t) - 1)


@dataclass(frozen=True)
class DiagReport:
    decoded: str
    quadgram: float
    ioc: float
    alphabetical_runs: tuple[Run, ...]
    incremental_fraction: float
    quadgram_z: float  # z-score vs shuffled-cipher baseline; >3 = real signal
    verdict: str


def randomness_report(
    numbers: Sequence[int],
    tokens: Sequence[str],
    quad: Quadgrams,
    cfg: DecodeConfig | None = None,
    n_baseline: int = 30,
    seed: int = 1885,
) -> DiagReport:
    cfg = cfg or DecodeConfig()
    res = decode(numbers, tokens, cfg)
    q_score = quad.score(letters_only(res.text))
    ioc = index_of_coincidence(res.text)
    runs = detect_alphabetical_runs(res.text)
    inc = incremental_fraction(res.text)

    # Baseline: shuffle the same number multiset, decode, score. A genuine
    # book-cipher decode should beat this distribution decisively.
    rng = random.Random(seed)
    base_scores = []
    nums = list(numbers)
    for _ in range(n_baseline):
        rng.shuffle(nums)
        base_scores.append(quad.score(letters_only(decode(nums, tokens, cfg).text)))
    mu = statistics.mean(base_scores)
    sd = statistics.stdev(base_scores) if len(base_scores) > 1 else 1.0
    z = (q_score - mu) / sd if sd else 0.0

    if any(len(r.text) >= 8 for r in runs):
        verdict = "alphabetical artifact (Gillogly-type): key-dependent structure, not a message"
    elif z >= 3.0 and q_score > -6.0:
        verdict = "looks like language: decode beats shuffled baseline decisively"
    else:
        verdict = "indistinguishable from random: no message signal with this key"

    return DiagReport(
        decoded=res.text,
        quadgram=q_score,
        ioc=ioc,
        alphabetical_runs=tuple(runs),
        incremental_fraction=inc,
        quadgram_z=z,
        verdict=verdict,
    )
