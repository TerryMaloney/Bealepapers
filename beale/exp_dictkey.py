"""Workstream L: the alphabetized-key (dictionary) attack.

If a cipher's key is an ALPHABETIZED word list (pocket dictionary, index,
gazetteer), first letters are a monotone step function of the number: 25
thresholds fully determine the decode, fittable directly with no key text.
This would also offer a mundane explanation of C3's ascending runs (an
encoder scanning down an alphabetized column).

Controls (preregistered): synthetic dictionary-encoded messages must
recover >=80% of letters; C2 (known non-dictionary) must NOT beat its own
shuffle null; real hits require z>=4 vs identical fits on 30 shuffles.

Run:  python -m beale.exp_dictkey
"""

from __future__ import annotations

import random
import statistics

from .data import load_beale
from .homophonic import flat_quadgram_table, quintgram_table
from .ngrams import Quadgrams
from .runlog import Criteria, start_run

A2Z = "abcdefghijklmnopqrstuvwxyz"
# English letter frequencies in a..z order (for threshold init)
_FREQ = [0.0817, 0.0150, 0.0278, 0.0425, 0.1270, 0.0223, 0.0202, 0.0609,
         0.0697, 0.0015, 0.0077, 0.0403, 0.0241, 0.0675, 0.0751, 0.0193,
         0.0010, 0.0599, 0.0633, 0.0906, 0.0276, 0.0098, 0.0236, 0.0015,
         0.0197, 0.0007]


class DictFit:
    """Monotone number->letter step function, scored with quad+quint."""

    def __init__(self, numbers, qtab4, qtab5):
        self.numbers = list(numbers)
        self.values = sorted(set(numbers))
        self.qtab4, self.qtab5 = qtab4, qtab5
        self.n = len(self.numbers)

    def letters_for(self, bounds: list[int]) -> list[int]:
        """bounds: 25 ascending indices into self.values (bucket ends)."""
        letter_of_value = {}
        lo = 0
        for li, b in enumerate(bounds + [len(self.values)]):
            for v in self.values[lo:b]:
                letter_of_value[v] = li
            lo = b
        return [letter_of_value[n] for n in self.numbers]

    def score(self, bounds) -> float:
        cur = self.letters_for(bounds)
        s = 0.0
        for w in range(self.n - 3):
            s += self.qtab4[((cur[w] * 26 + cur[w + 1]) * 26
                             + cur[w + 2]) * 26 + cur[w + 3]]
        for w in range(self.n - 4):
            s += self.qtab5[(((cur[w] * 26 + cur[w + 1]) * 26 + cur[w + 2])
                             * 26 + cur[w + 3]) * 26 + cur[w + 4]]
        return s

    def init_bounds(self, rng=None, jitter=0.0) -> list[int]:
        from collections import Counter

        counts = Counter(self.numbers)
        total = self.n
        cum, bounds, acc = 0.0, [], 0
        target = []
        for f in _FREQ[:-1]:
            cum += f
            target.append(cum)
        ti = 0
        for vi, v in enumerate(self.values):
            acc += counts[v]
            while ti < 25 and acc / total >= target[ti]:
                b = vi + 1
                if jitter and rng:
                    b = max(1, min(len(self.values) - 1,
                                   b + rng.randint(-8, 8)))
                bounds.append(b)
                ti += 1
        while len(bounds) < 25:
            bounds.append(len(self.values))
        return sorted(bounds)

    def fit(self, restarts=8, sweeps=6, seed=0):
        rng = random.Random(seed)
        best = (-1e18, None)
        for r in range(restarts):
            bounds = self.init_bounds(rng, jitter=0.0 if r == 0 else 1.0)
            sc = self.score(bounds)
            for _ in range(sweeps):
                improved = False
                for bi in range(25):
                    lo = bounds[bi - 1] if bi else 0
                    hi = bounds[bi + 1] if bi < 24 else len(self.values)
                    cand = range(max(lo, bounds[bi] - 12),
                                 min(hi, bounds[bi] + 13))
                    cur_b = bounds[bi]
                    for c in cand:
                        if c == cur_b:
                            continue
                        bounds[bi] = c
                        s2 = self.score(bounds)
                        if s2 > sc:
                            sc, cur_b = s2, c
                        bounds[bi] = cur_b
                    bounds[bi] = cur_b
                    improved = improved or cur_b != bounds[bi]
                if not improved:
                    break
            if sc > best[0]:
                best = (sc, list(bounds))
        return best

    def decode(self, bounds) -> str:
        return "".join(A2Z[c] for c in self.letters_for(bounds))


def synth_dictionary_cipher(plaintext: str, rng) -> list[int]:
    """Alphabetized key: number = index into a sorted word list, drawn from
    the needed letter's alphabetical range (ascending-biased)."""
    import json
    from pathlib import Path

    toks = json.loads(Path("corpus/keytexts/normalized/common_sense.json")
                      .read_text())["tokens"]
    wl = sorted(set(t for t in toks if t.isalpha()))  # full alphabetized list
    ranges = {}
    for i, w in enumerate(wl):
        ranges.setdefault(w[0], []).append(i + 1)
    out = []
    for ch in plaintext:
        pool = ranges.get(ch)
        if not pool:
            return None
        out.append(rng.choice(pool))
    return out


def fit_with_null(numbers, qtab4, qtab5, n_nulls=30, seed=0,
                  restarts=6):
    fitter = DictFit(numbers, qtab4, qtab5)
    real_sc, bounds = fitter.fit(restarts=restarts, seed=seed)
    rng = random.Random(seed + 1)
    nulls = []
    t = list(numbers)
    for i in range(n_nulls):
        rng.shuffle(t)
        f = DictFit(t, qtab4, qtab5)
        s, _ = f.fit(restarts=2, seed=seed + 10 + i)
        nulls.append(s)
    mu, sd = statistics.mean(nulls), statistics.stdev(nulls)
    z = (real_sc - mu) / sd if sd else 0.0
    return real_sc, bounds, z, fitter


def main() -> None:
    data = load_beale()
    quad = Quadgrams.load()
    qtab4 = flat_quadgram_table(quad)
    qtab5 = quintgram_table()
    crit = Criteria("dict-key", "c3",
                    ("hit requires z>=4 vs 30-shuffle null fits AND visible "
                     "English; synthetic must recover >=80%; C2 negative "
                     "control must not beat its null",))
    rec = start_run("dict-key", "c3", {"restarts": 6}, criteria=crit)

    # positive control
    rng = random.Random(3)
    from .synth import sample_plaintext

    pt = sample_plaintext(list(data.doi_words), 600, rng)
    for ch in "xyz":
        pt = pt.replace(ch, "e")
    nums = synth_dictionary_cipher(pt, rng)
    f = DictFit(nums, qtab4, qtab5)
    sc, bounds = f.fit(restarts=6, seed=2)
    acc = sum(a == b for a, b in zip(f.decode(bounds), pt)) / len(pt)
    print(f"positive control: synthetic dictionary cipher recovered "
          f"{acc:.0%} {'PASS' if acc >= 0.8 else 'FAIL'}")

    results = {"synthetic_acc": acc}
    for name in ("C2", "C3", "C1"):
        numbers = data.cipher_for(name)
        sc, bounds, z, fitter = fit_with_null(numbers, qtab4, qtab5)
        text = fitter.decode(bounds)
        tag = ("negative control - must NOT hit" if name == "C2" else "")
        print(f"\n{name}: fit score {sc:.0f}  null z={z:+.2f} "
              f"{'HIT?!' if z >= 4 else 'no hit'} {tag}")
        print(f"  decode: {text[:100]}")
        results[name] = {"z": z, "decode_head": text[:200]}
    rec.finish(**results)


if __name__ == "__main__":
    main()
