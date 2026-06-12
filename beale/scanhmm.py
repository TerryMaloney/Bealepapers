"""Gap-HMM scan-forward attack (keyless) — aimed at Cipher 3's anomaly.

Hypothesis: the encoder kept a finger on the key document and, for each
plaintext letter, took the NEXT word starting with that letter (wrapping at
the end). That discipline produces ascending number runs with resets —
exactly C3's signature (lag-1 autocorrelation z=+16.2; runs of 10).

Under this model the scan position is OBSERVED (the cipher number itself),
so the hidden state is just the plaintext letter. The gap between
consecutive numbers is geometric with parameter p_letter = fraction of key
words starting with that letter. Letters are decodable WITHOUT the key
text, using only a first-letter frequency profile of period English plus a
letter bigram language model.

Emissions for step i with gap g (forward) or wrap:
    P(d_i | letter) = (1-eps) * Geom(g; p_letter) * (wrap term) + eps * U
The eps-uniform mixture absorbs encoder sloppiness (skips, misreads).
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .ngrams import Quadgrams

A2Z = "abcdefghijklmnopqrstuvwxyz"


def first_letter_profile(corpus_dir: str = "corpus/keytexts/normalized",
                         sources: list[str] | None = None) -> list[float]:
    """P(word starts with letter) averaged over corpus texts."""
    counts = Counter()
    total = 0
    paths = (
        [Path(corpus_dir) / s for s in sources] if sources
        else sorted(Path(corpus_dir).glob("*.json"))
    )
    for p in paths:
        try:
            toks = json.loads(p.read_text(encoding="utf-8"))["tokens"]
        except (KeyError, ValueError, OSError):
            continue
        for t in toks:
            if t and "a" <= t[0] <= "z":
                counts[t[0]] += 1
                total += 1
    return [counts.get(ch, 1) / total for ch in A2Z]


def profile_from_tokens(tokens: Sequence[str]) -> list[float]:
    counts = Counter(t[0] for t in tokens if t and "a" <= t[0] <= "z")
    total = sum(counts.values())
    return [counts.get(ch, 1 / 26) / max(1, total) for ch in A2Z]


def bigram_logprobs(quad: Quadgrams) -> list[list[float]]:
    """log10 P(b|a) marginalized from the quadgram resource."""
    counts = [[1.0] * 26 for _ in range(26)]  # add-one smoothing
    for q, lp in quad._logp.items():
        a, b = ord(q[0]) - 65, ord(q[1]) - 65
        counts[a][b] += 10 ** lp  # back to (relative) probability mass
    out = []
    for a in range(26):
        tot = sum(counts[a])
        out.append([math.log10(c / tot) for c in counts[a]])
    return out


@dataclass(frozen=True)
class HMMParams:
    profile: tuple[float, ...]     # 26 first-letter probabilities
    doc_len: int                   # assumed key document length L
    wrap_rate: float = 0.05        # P(wrap) per step
    eps: float = 0.05              # uniform robustness mixture


def _emission_logp(prev: int, cur: int, params: HMMParams) -> list[float]:
    """log10 P(observed step prev->cur | letter) for all 26 letters."""
    L = params.doc_len
    d = cur - prev
    if d > 0:
        g = d
        wrap = False
    else:
        g = L - prev + cur
        wrap = True
    if g <= 0:
        g = 1
    out = []
    u = params.eps / L
    for letter in range(26):
        p = min(0.5, max(1e-4, params.profile[letter]))
        geo = (1 - p) ** (g - 1) * p
        w = params.wrap_rate if wrap else (1 - params.wrap_rate)
        val = (1 - params.eps) * w * geo + u
        out.append(math.log10(val))
    return out


def viterbi(numbers: Sequence[int], params: HMMParams,
            bigram: list[list[float]]) -> str:
    n = len(numbers)
    prior = [math.log10(max(p, 1e-6)) for p in params.profile]
    # step 0: treat gap from position 0
    em0 = _emission_logp(0, numbers[0], params)
    dp = [prior[l] + em0[l] for l in range(26)]
    back: list[list[int]] = []
    for i in range(1, n):
        em = _emission_logp(numbers[i - 1], numbers[i], params)
        ndp = [-1e18] * 26
        nb = [0] * 26
        for b in range(26):
            best_v, best_a = -1e18, 0
            for a in range(26):
                v = dp[a] + bigram[a][b]
                if v > best_v:
                    best_v, best_a = v, a
            ndp[b] = best_v + em[b]
            nb[b] = best_a
        dp = ndp
        back.append(nb)
    # backtrack
    cur = max(range(26), key=lambda l: dp[l])
    path = [cur]
    for nb in reversed(back):
        cur = nb[cur]
        path.append(cur)
    path.reverse()
    return "".join(A2Z[l] for l in path)


def posteriors(numbers: Sequence[int], params: HMMParams,
               bigram: list[list[float]]) -> list[list[float]]:
    """Forward-backward letter posteriors per position (probabilities)."""
    n = len(numbers)
    LOG0 = -1e18

    def logsumexp(vals):
        m = max(vals)
        if m <= LOG0 / 2:
            return LOG0
        return m + math.log10(sum(10 ** (v - m) for v in vals))

    prior = [math.log10(max(p, 1e-6)) for p in params.profile]
    em0 = _emission_logp(0, numbers[0], params)
    fwd = [[prior[l] + em0[l] for l in range(26)]]
    for i in range(1, n):
        em = _emission_logp(numbers[i - 1], numbers[i], params)
        prev = fwd[-1]
        fwd.append([
            logsumexp([prev[a] + bigram[a][b] for a in range(26)]) + em[b]
            for b in range(26)
        ])
    bwd = [[0.0] * 26 for _ in range(n)]
    for i in range(n - 2, -1, -1):
        em = _emission_logp(numbers[i], numbers[i + 1], params)
        nxt = bwd[i + 1]
        bwd[i] = [
            logsumexp([bigram[a][b] + em[b] + nxt[b] for b in range(26)])
            for a in range(26)
        ]
    out = []
    for i in range(n):
        joint = [fwd[i][l] + bwd[i][l] for l in range(26)]
        z = logsumexp(joint)
        out.append([10 ** (j - z) for j in joint])
    return out


def estimate_wrap_rate(numbers: Sequence[int]) -> float:
    downs = sum(1 for a, b in zip(numbers, numbers[1:]) if b <= a)
    return max(0.01, min(0.6, downs / max(1, len(numbers) - 1)))


def tie_agreement(numbers: Sequence[int], decoded: str) -> float:
    """Fraction of repeated-number position pairs decoding to the same
    letter. The HMM never enforces this, so high agreement is evidence the
    model fits. Null for English first-letter profiles ~ 0.09-0.11."""
    groups: dict[int, list[str]] = {}
    for n, ch in zip(numbers, decoded):
        groups.setdefault(n, []).append(ch)
    pairs = agree = 0
    for letters in groups.values():
        k = len(letters)
        if k < 2:
            continue
        for i in range(k):
            for j in range(i + 1, k):
                pairs += 1
                if letters[i] == letters[j]:
                    agree += 1
    return agree / pairs if pairs else 0.0


@dataclass(frozen=True)
class ScanResult:
    decoded: str
    params: HMMParams
    tie_agreement: float
    quadgram: float
    posteriors_conf: tuple[float, ...]  # max posterior per position


def attack(numbers: Sequence[int], quad: Quadgrams,
           profile: list[float] | None = None,
           doc_lens: Sequence[int] = (975, 1000, 1050, 1100, 1200),
           eps_grid: Sequence[float] = (0.02, 0.05, 0.10),
           ) -> ScanResult:
    """Sweep (L, eps), pick by total likelihood proxy (quadgram of Viterbi
    text is reported but selection uses the HMM's own best path score)."""
    profile = profile or first_letter_profile()
    bigram = bigram_logprobs(quad)
    wrap = estimate_wrap_rate(numbers)
    best = None
    for L in doc_lens:
        if L < max(numbers):
            continue
        for eps in eps_grid:
            params = HMMParams(tuple(profile), L, wrap, eps)
            text = viterbi(numbers, params, bigram)
            q = quad.score(text.upper())
            if best is None or q > best[0]:
                best = (q, params, text)
    q, params, text = best
    post = posteriors(numbers, params, bigram)
    conf = tuple(max(p) for p in post)
    return ScanResult(decoded=text, params=params,
                      tie_agreement=tie_agreement(numbers, text),
                      quadgram=q, posteriors_conf=conf)
