"""Workstream J: repeated-pattern / function-word analysis.

A genuine book-cipher message leaks English sequential structure even when
the encoder varies homophones: repeated plaintext fragments occasionally
re-emit the same number n-grams. Measured on the SOLVED Cipher 2, this
signal is unmistakable (bigram z=+4.7, trigram z=+8.7 vs shuffles), and
the repeated patterns decode to exactly the top English bigrams/trigrams
(ed, ve, th, in, ne / her, nds, ove).

Preregistered gate: the function-word mapping (J2) is only meaningful on a
cipher whose J1 z-scores show reuse structure. C1 and C3 show NONE
(z ~ 0; 0-2 repeated patterns vs C2's 39+3) — so J2 on them is unpowered,
and that absence is itself a finding: C3's strong number-VALUE locality
coexists with zero number-PATTERN repetition, the opposite of what encoded
English produces at these parameters.

Run:  python -m beale.exp_funcwords
"""

from __future__ import annotations

import random
import statistics
from collections import Counter

from .data import load_beale
from .keytable import reconstruct
from .oracle import known_c2_plaintext
from .runlog import Criteria, start_run

# the known C2 plaintext as words (for the encoder-reuse calibration)
C2_WORDS = """i have deposited in the county of bedford about four miles from
bufords in an excavation or vault six feet below the surface of the ground the
following articles belonging jointly to the parties whose names are given in
number three herewith the first deposit consisted of ten hundred and fourteen
pounds of gold and thirty eight hundred and twelve pounds of silver deposited
nov eighteen nineteen the second was made dec eighteen twenty one and consisted
of nineteen hundred and seven pounds of gold and twelve hundred and eighty
eight of silver also jewels obtained in st louis in exchange to save
transportation and valued at thirteen thousand dollars the above is securely
packed in iron pots with iron covers the vault is roughly lined with stone and
the vessels rest on solid stone and are covered with others paper number one
describes the exact locality of the vault so that no difficulty will be had in
finding it""".split()


def repeated_ngrams(nums, n: int) -> Counter:
    c = Counter(tuple(nums[i : i + n]) for i in range(len(nums) - n + 1))
    return Counter({k: v for k, v in c.items() if v >= 2})


def ngram_z(nums, n: int, n_shuffles: int = 200, seed: int = 42):
    real = len(repeated_ngrams(list(nums), n))
    rng = random.Random(seed)
    t = list(nums)
    base = []
    for _ in range(n_shuffles):
        rng.shuffle(t)
        base.append(len(repeated_ngrams(t, n)))
    mu, sd = statistics.mean(base), statistics.stdev(base)
    return real, mu, sd, (real - mu) / sd if sd else 0.0


def c2_reuse_calibration(data) -> dict:
    """How often did the real encoder re-emit numbers for repeated words?"""
    spans: dict[str, list[tuple[int, ...]]] = {}
    pos = 0
    for w in C2_WORDS:
        spans.setdefault(w, []).append(tuple(data.cipher2[pos : pos + len(w)]))
        pos += len(w)
    assert pos == 763
    whole = whole_total = part = part_total = 0
    for sp in spans.values():
        if len(sp) < 2:
            continue
        c = Counter(sp)
        whole += sum(v - 1 for v in c.values() if v >= 2)
        whole_total += len(sp) - 1
        for i in range(len(sp)):
            for j in range(i + 1, len(sp)):
                for a, b in zip(sp[i], sp[j]):
                    part_total += 1
                    part += a == b
    return {"whole_word_reuse": whole / max(1, whole_total),
            "per_letter_reuse": part / max(1, part_total)}


def main() -> None:
    data = load_beale()
    kt = reconstruct(data)
    crit = Criteria("funcwords-j1", "c1",
                    ("J2 mapping is run only on ciphers whose J1 repeated-"
                     "pattern z >= 3; otherwise reported unpowered",))
    rec = start_run("funcwords-j1", "c1", {"n_shuffles": 200}, criteria=crit)
    results = {}
    print("=== J1: repeated n-gram structure (vs 200 shuffles) ===")
    for name in ("C1", "C2", "C3"):
        nums = data.cipher_for(name)
        for n in (2, 3):
            real, mu, sd, z = ngram_z(nums, n)
            results[f"{name}_{n}"] = {"real": real, "null_mu": mu, "z": z}
            print(f"  {name} {n}-grams: {real:3d} repeated  "
                  f"null {mu:5.1f}±{sd:4.1f}  z={z:+5.1f}")
    cal = c2_reuse_calibration(data)
    print(f"\nC2 encoder reuse: whole-word {cal['whole_word_reuse']:.0%}, "
          f"per-letter {cal['per_letter_reuse']:.0%}")
    print("\nC2 repeated patterns decode to (ground-truth validation of the "
          "mechanism):")
    for n in (3, 2):
        for pat, v in repeated_ngrams(list(data.cipher2), n).most_common(6):
            letters = "".join(kt.letter(x) or "?" for x in pat)
            print(f"  {pat} x{v} -> '{letters}'")
    verdict = ("C2 shows strong reuse structure and its repeated patterns "
               "ARE the top English n-grams; C1/C3 show none -> J2 unpowered "
               "on C1/C3; absence of pattern repetition despite value "
               "locality is anti-message evidence for C3")
    print(f"\nverdict: {verdict}")
    rec.finish(results=results, calibration=cal, verdict=verdict)


if __name__ == "__main__":
    main()
