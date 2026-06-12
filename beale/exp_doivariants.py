"""Workstream H: exhaustive cheap sweep of DOI-only decode variants for C1
(and C3 for free), plus Gillogly-runs-as-structure statistics.

Grid (preregistered as one unit): extraction rule x index transform x
text base. Scored with wildcard-marginalized quadgrams; extreme-value null
= the identical grid run on shuffled ciphers, hit declared only at z >= 4
versus the null-maximum distribution (c1_twostage pattern).

Run:  python -m beale.exp_doivariants
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

from .c1_twostage import build_marginals, wildcard_quad_score, WILD
from .data import load_beale
from .edits import apply_edits
from .homophonic import flat_quadgram_table
from .keytable import reconstruct
from .ngrams import Quadgrams
from .oracle import load_doi_edits


@dataclass(frozen=True)
class Variant:
    base: str          # "pamphlet" | "adjusted" | "+rev" suffix for reversed
    extraction: str    # "first" | "second" | "third" | "last"
    transform: str     # "shift k" | "affine a,b,M" | "revnum M"
    score: float


def _extract(word: str, rule: str) -> int:
    if not word:
        return WILD
    if rule == "first":
        ch = word[0]
    elif rule == "second":
        if len(word) < 2:
            return WILD
        ch = word[1]
    elif rule == "third":
        if len(word) < 3:
            return WILD
        ch = word[2]
    else:  # last
        ch = word[-1]
    return ord(ch) - 97 if "a" <= ch <= "z" else WILD


def _grid(bases: dict[str, tuple[str, ...]]):
    """Yield (base_name, tokens, transform_name, fn n->idx0 or None)."""
    for bname, toks in bases.items():
        M = len(toks)
        for k in range(0, 41):
            yield bname, toks, f"shift {k}", (lambda n, k=k: n - 1 - k)
        for a in (3, 5, 7, M - 1):
            for b in range(0, 10):
                yield (bname, toks, f"affine {a},{b}",
                       (lambda n, a=a, b=b, M=M: (a * n + b) % M))
        yield bname, toks, "revnum", (lambda n, M=M: M - n)


def sweep(numbers, bases, qtab, marg1, marg2, top: int = 5):
    out = []
    for bname, toks, tname, fn in _grid(bases):
        M = len(toks)
        for rule in ("first", "second", "third", "last"):
            codes = []
            for n in numbers:
                idx = fn(n)
                codes.append(_extract(toks[idx], rule)
                             if 0 <= idx < M else WILD)
            wild_frac = sum(1 for c in codes if c == WILD) / len(codes)
            if wild_frac > 0.5:
                continue
            sc = wildcard_quad_score(codes, qtab, marg1, marg2)
            out.append(Variant(bname, rule, tname, sc))
    out.sort(key=lambda v: v.score, reverse=True)
    return out[:top], (out[0].score if out else -99.0)


def run_h(n_nulls: int = 50) -> None:
    data = load_beale()
    quad = Quadgrams.load()
    qtab = flat_quadgram_table(quad)
    marg1, marg2 = build_marginals(qtab)
    adjusted = apply_edits(data.doi_words, load_doi_edits())
    bases = {
        "pamphlet": data.doi_words,
        "adjusted": adjusted,
        "pamphlet-rev": tuple(reversed(data.doi_words)),
        "adjusted-rev": tuple(reversed(adjusted)),
    }
    from .runlog import Criteria, start_run

    crit = Criteria("doi-variants", "c1",
                    ("hit only if grid max exceeds shuffled-null grid maxima "
                     "by z>=4; grid preregistered as one unit",))
    for cipher in ("C1", "C3"):
        numbers = data.cipher_for(cipher)
        rec = start_run("doi-variants", cipher.lower(),
                        {"grid": "ext4 x (41 shifts + 40 affine + revnum) x 4 bases",
                         "n_nulls": n_nulls}, criteria=crit)
        best, real_max = sweep(numbers, bases, qtab, marg1, marg2)
        rng = random.Random(99)
        null_maxima = []
        nums = list(numbers)
        for _ in range(n_nulls):
            rng.shuffle(nums)
            _, mx = sweep(nums, bases, qtab, marg1, marg2, top=1)
            null_maxima.append(mx)
        mu = statistics.mean(null_maxima)
        sd = statistics.stdev(null_maxima)
        z = (real_max - mu) / sd if sd else 0.0
        print(f"\n=== {cipher}: grid max {real_max:.3f}  "
              f"null max {mu:.3f}±{sd:.3f}  z={z:+.2f}  "
              f"{'HIT - VERIFY' if z >= 4 else 'no hit'} ===")
        for v in best:
            print(f"  {v.score:7.3f}  {v.base:13s} {v.extraction:6s} {v.transform}")
        rec.finish(real_max=real_max, null_mu=mu, null_sd=sd, z=z,
                   top=[v.__dict__ for v in best])


# ------------------------------------------------- Gillogly segmentation --

def keytable_runs(data, min_len=5, min_known=4):
    """Alphabetically non-decreasing windows in the keytable decode of C1."""
    kt = reconstruct(data)
    letters = [kt.letter(n) for n in data.cipher1]
    runs = []
    i = 0
    n = len(letters)
    while i < n:
        j = i
        last = None
        known = 0
        while j < n:
            ch = letters[j]
            if ch is not None:
                if last is not None and ch < last:
                    break
                last = ch
                known += 1
            j += 1
        if j - i >= min_len and known >= min_known:
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def segmentation_stats(data, n_null: int = 1000, seed: int = 5) -> dict:
    """S2 key-locality and S4 rare-number sharing across segments; segment
    boundaries from detected alphabetical runs. S1/S3 reported descriptively
    (segment count too small for distributional tests)."""
    runs = keytable_runs(data)
    bounds = [0] + [e for _, e in runs] + [len(data.cipher1)]
    segments = [list(data.cipher1[a:b]) for a, b in zip(bounds, bounds[1:])
                if b - a >= 3]
    rng = random.Random(seed)

    def within_var(segs):
        tot, cnt = 0.0, 0
        for s in segs:
            if len(s) > 1:
                tot += statistics.pvariance(s)
                cnt += 1
        return tot / max(1, cnt)

    real_wv = within_var(segments)
    lens = [len(s) for s in segments]
    pool = [n for s in segments for n in s]
    null_wv = []
    for _ in range(n_null):
        rng.shuffle(pool)
        i = 0
        segs = []
        for ln in lens:
            segs.append(pool[i:i + ln])
            i += ln
        null_wv.append(within_var(segs))
    mu, sd = statistics.mean(null_wv), statistics.stdev(null_wv)
    z_local = (real_wv - mu) / sd if sd else 0.0
    return {"n_runs": len(runs), "runs": runs, "n_segments": len(segments),
            "seg_lengths": lens, "locality_z": z_local,
            "interpretation": ("segments use LOCAL key regions (z<-4: "
                               "within-segment variance far below shuffle)"
                               if z_local <= -4 else "no segment locality")}


def main() -> None:
    run_h()
    data = load_beale()
    print("\n=== Gillogly segmentation (exploratory) ===")
    st = segmentation_stats(data)
    print(f"  alphabetical runs at: {st['runs']}")
    print(f"  segments: {st['n_segments']} lengths {st['seg_lengths']}")
    print(f"  key-locality z = {st['locality_z']:+.2f} -> {st['interpretation']}")


if __name__ == "__main__":
    main()
