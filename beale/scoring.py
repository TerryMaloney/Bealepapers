"""Answer-free English-likeness metrics for candidate decodes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .ngrams import Quadgrams

# Standard English letter frequencies (fractions).
ENGLISH_FREQ = {
    "a": 0.0817, "b": 0.0150, "c": 0.0278, "d": 0.0425, "e": 0.1270,
    "f": 0.0223, "g": 0.0202, "h": 0.0609, "i": 0.0697, "j": 0.0015,
    "k": 0.0077, "l": 0.0403, "m": 0.0241, "n": 0.0675, "o": 0.0751,
    "p": 0.0193, "q": 0.0010, "r": 0.0599, "s": 0.0633, "t": 0.0906,
    "u": 0.0276, "v": 0.0098, "w": 0.0236, "x": 0.0015, "y": 0.0197,
    "z": 0.0007,
}

ENGLISH_IOC = 0.0667
RANDOM_IOC = 1 / 26  # ~0.0385


@dataclass(frozen=True)
class ScoreReport:
    quadgram: float       # mean log10 P per quadgram; English ~ -3.5, random < -5
    ioc: float            # index of coincidence; English ~ 0.067, random ~ 0.038
    chi2: float           # letter chi-squared vs English; lower is better
    dict_coverage: float  # fraction of letters covered by dictionary words >= 3


def letters_only(text: str) -> str:
    return "".join(c for c in text.lower() if "a" <= c <= "z")


def index_of_coincidence(text: str) -> float:
    t = letters_only(text)
    n = len(t)
    if n < 2:
        return 0.0
    counts = Counter(t)
    return sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))


def chi_squared(text: str) -> float:
    t = letters_only(text)
    n = len(t)
    if not n:
        return float("inf")
    counts = Counter(t)
    return sum(
        (counts.get(ch, 0) - f * n) ** 2 / (f * n) for ch, f in ENGLISH_FREQ.items()
    )


def dictionary_coverage(text: str, words: frozenset[str]) -> float:
    """Fraction of letters covered by greedy longest-match dictionary words."""
    t = letters_only(text)
    if not t:
        return 0.0
    max_len = 12
    covered = 0
    i = 0
    while i < len(t):
        match = 0
        for ln in range(min(max_len, len(t) - i), 2, -1):
            if t[i : i + ln] in words:
                match = ln
                break
        if match:
            covered += match
            i += match
        else:
            i += 1
    return covered / len(t)


@lru_cache(maxsize=1)
def default_wordlist() -> frozenset[str]:
    """Word set built from the repo's normalized keytext corpus."""
    import json

    corpus = Path("corpus/keytexts/normalized")
    words: set[str] = set()
    for name in ("bible_asv.json", "pride_prejudice.json", "common_sense.json",
                 "autobiography_franklin.json", "ivanhoe.json"):
        p = corpus / name
        if p.exists():
            for tok in json.loads(p.read_text(encoding="utf-8"))["tokens"]:
                if len(tok) >= 3 and tok.isalpha():
                    words.add(tok.lower())
    return frozenset(words)


def score_text(
    text: str, quad: Quadgrams, words: frozenset[str] | None = None
) -> ScoreReport:
    words = words if words is not None else default_wordlist()
    return ScoreReport(
        quadgram=quad.score(letters_only(text)),
        ioc=index_of_coincidence(text),
        chi2=chi_squared(text),
        dict_coverage=dictionary_coverage(text, words),
    )
