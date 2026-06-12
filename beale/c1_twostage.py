"""Two-stage attack on Cipher 1.

Hypothesis (user's "stacked methods" idea): C1's plaintext was transformed
(monoalphabetic substitution and/or transposition/decimation) BEFORE being
book-encoded against Beale's key. Then the decode of C1 under Beale's
reconstructed key table is an intermediate ciphertext, and a second-stage
solver over it should reveal English.

The decode has ~53% coverage (positions whose numbers appear in the C2
table); the rest are wildcards. Scoring uses exact wildcard-marginalized
quadgram likelihood. Guardrail G1: every search family is also run on
shuffled nulls; a real hit must beat the null-maximum distribution.
"""

from __future__ import annotations

import math
import random
from array import array
from dataclasses import dataclass

from .ngrams import Quadgrams

WILD = 26


def build_marginals(qtab: array) -> tuple[list[array], list[array]]:
    """Exact logsumexp marginals of the quadgram table.

    marg1[pos] : 26^3 table = log10 sum_x P(quad with slot pos = x)
    marg2[(p,q) index] : 26^2 tables for two missing slots.
    """
    probs = [10 ** v for v in qtab]
    marg1 = []
    for pos in range(4):
        t = [0.0] * (26 ** 3)
        for i, p in enumerate(probs):
            l = [(i // 26 ** 3) % 26, (i // 26 ** 2) % 26, (i // 26) % 26, i % 26]
            del l[pos]
            t[(l[0] * 26 + l[1]) * 26 + l[2]] += p
        marg1.append(array("f", [math.log10(max(v, 1e-12)) for v in t]))
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    marg2 = []
    for a, b in pairs:
        t = [0.0] * (26 ** 2)
        for i, p in enumerate(probs):
            l = [(i // 26 ** 3) % 26, (i // 26 ** 2) % 26, (i // 26) % 26, i % 26]
            keep = [l[j] for j in range(4) if j not in (a, b)]
            t[keep[0] * 26 + keep[1]] += p
        marg2.append(array("f", [math.log10(max(v, 1e-12)) for v in t]))
    return marg1, marg2


_PAIR_IDX = {(0, 1): 0, (0, 2): 1, (0, 3): 2, (1, 2): 3, (1, 3): 4, (2, 3): 5}


def wildcard_quad_score(codes: list[int], qtab: array,
                        marg1: list[array], marg2: list[array]) -> float:
    """Mean log10 quadgram likelihood with exact 1- and 2-missing
    marginalization; windows with 3+ wildcards skipped."""
    total = 0.0
    n_used = 0
    for w in range(len(codes) - 3):
        quad = codes[w : w + 4]
        wilds = [j for j in range(4) if quad[j] == WILD]
        if len(wilds) == 0:
            total += qtab[((quad[0] * 26 + quad[1]) * 26 + quad[2]) * 26 + quad[3]]
        elif len(wilds) == 1:
            known = [quad[j] for j in range(4) if j not in wilds]
            total += marg1[wilds[0]][(known[0] * 26 + known[1]) * 26 + known[2]]
        elif len(wilds) == 2:
            known = [quad[j] for j in range(4) if j not in wilds]
            total += marg2[_PAIR_IDX[tuple(wilds)]][known[0] * 26 + known[1]]
        else:
            continue
        n_used += 1
    return total / n_used if n_used else -12.0


def intermediate_text(data, keytable) -> list[int]:
    """C1 decoded with Beale's reconstructed table; wildcards elsewhere."""
    out = []
    for n in data.cipher1:
        letter = keytable.letter(n)
        out.append(ord(letter) - 97 if letter else WILD)
    return out


@dataclass
class StageResult:
    family: str
    transform: str
    score: float
    text: str


def codes_to_text(codes: list[int]) -> str:
    return "".join(chr(97 + c) if c < 26 else "?" for c in codes)


# ---------------------------------------------------------- stage A: mono --

def mono_hillclimb(codes: list[int], qtab, marg1, marg2,
                   restarts: int = 30, sweeps: int = 60,
                   seed: int = 0) -> StageResult:
    """Search a 26-letter permutation applied to the intermediate text."""
    rng = random.Random(seed)
    best_sc, best_perm = -1e18, list(range(26))
    for r in range(restarts):
        perm = list(range(26))
        rng.shuffle(perm)
        mapped = [perm[c] if c < 26 else WILD for c in codes]
        sc = wildcard_quad_score(mapped, qtab, marg1, marg2)
        for _ in range(sweeps):
            improved = False
            for _ in range(120):
                a, b = rng.sample(range(26), 2)
                perm[a], perm[b] = perm[b], perm[a]
                mapped = [perm[c] if c < 26 else WILD for c in codes]
                nsc = wildcard_quad_score(mapped, qtab, marg1, marg2)
                if nsc > sc:
                    sc = nsc
                    improved = True
                else:
                    perm[a], perm[b] = perm[b], perm[a]
            if not improved:
                break
        if sc > best_sc:
            best_sc, best_perm = sc, list(perm)
    mapped = [best_perm[c] if c < 26 else WILD for c in codes]
    return StageResult("mono", f"perm={''.join(chr(97+p) for p in best_perm)}",
                       best_sc, codes_to_text(mapped))


# ----------------------------------------------------- stage B: columnar --

def columnar_search(codes: list[int], qtab, marg1, marg2,
                    widths=range(2, 8)) -> StageResult:
    """Exhaustive column-order search for small widths, applied as
    un-transposition of the letter sequence."""
    from itertools import permutations

    n = len(codes)
    best = StageResult("columnar", "none", -1e18, "")
    for w in widths:
        rows = -(-n // w)
        for perm in permutations(range(w)):
            cols = []
            i = 0
            base, extra = divmod(n, w)
            for c in range(w):
                ln = base + (1 if c < extra else 0)
                cols.append(codes[i : i + ln])
                i += ln
            seq = []
            for r in range(rows):
                for c in perm:
                    if r < len(cols[c]):
                        seq.append(cols[c][r])
            sc = wildcard_quad_score(seq, qtab, marg1, marg2)
            if sc > best.score:
                best = StageResult("columnar", f"w={w} perm={perm}", sc,
                                   codes_to_text(seq))
    return best


# --------------------------------------------------- stage C: decimation --

def decimation_search(codes: list[int], qtab, marg1, marg2) -> StageResult:
    n = len(codes)
    best = StageResult("decimation", "none", -1e18, "")
    ks = [k for k in range(2, n) if math.gcd(k, n) == 1]
    for k in ks:
        seq = [codes[(i * k) % n] for i in range(n)]
        sc = wildcard_quad_score(seq, qtab, marg1, marg2)
        if sc > best.score:
            best = StageResult("decimation", f"k={k}", sc, codes_to_text(seq))
    return best


# --------------------------------------------------------------- nulls ----

def null_maxima(codes: list[int], qtab, marg1, marg2, family: str,
                n_nulls: int = 40, seed: int = 0) -> list[float]:
    """Run the identical search on shuffled copies; collect each null's
    MAXIMUM score (extreme-value calibration)."""
    rng = random.Random(seed)
    out = []
    for i in range(n_nulls):
        shuf = codes[:]
        rng.shuffle(shuf)
        if family == "mono":
            r = mono_hillclimb(shuf, qtab, marg1, marg2, restarts=6,
                               sweeps=30, seed=seed + i)
        elif family == "columnar":
            r = columnar_search(shuf, qtab, marg1, marg2, widths=range(2, 7))
        else:
            r = decimation_search(shuf, qtab, marg1, marg2)
        out.append(r.score)
    return out


def z_vs_nulls(score: float, nulls: list[float]) -> float:
    import statistics

    mu = statistics.mean(nulls)
    sd = statistics.stdev(nulls) if len(nulls) > 1 else 1.0
    return (score - mu) / sd if sd else 0.0
