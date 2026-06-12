"""Workstream G2/G3: treasure-crib bootstrap with sealed arms, and the
same-pamphlet verdict.

Each crib word is slid over every position of a cipher. A placement is
accepted only if (A) it conflicts with no existing pins, (B) propagating
its letters through repeated numbers completes other windows at >= 3x the
null rate (binomial p < 0.01). Accepted placements pin key-document
indices; the two ciphers run as SEALED arms (no cross-propagation), and
G3 asks afterwards whether the arms' pins agree on shared numbers.

Positive-control gate (must pass before real runs are interpreted):
a synthetic treasure message book-encoded against a held-out document
must yield >= 15 correct pins at >= 80% precision and rank its document #1.

Run:  python -m beale.exp_cribs
"""

from __future__ import annotations

import math
import random
from collections import Counter

from .data import load_beale
from .keytable import reconstruct
from .runlog import Criteria, start_run

CRIBS = sorted(set("""
bedford county virginia vault feet north south ridge creek mile degrees
chestnut oak rock buford tavern iron pot stone buried deposit treasure
excavation located distance southwest northeast branch fork hollow cave
hill mountain thousand hundred twenty thirty forty fifty paces yards east
west northwest southeast beale morriss lynchburg botetourt roanoke
fincastle goose peaks otter names residences wife
""".split()))


def null_rate(pins: dict[int, str]) -> float:
    """Chance two random English-initial letters agree (~0.09-0.11)."""
    from .scoring import ENGLISH_FREQ

    return sum(f * f for f in ENGLISH_FREQ.values())


def bootstrap(numbers, start_pins: dict[int, str], rng,
              max_rounds: int = 5, p_thresh: float = 0.01):
    """Returns (accepted placements, final pins)."""
    pins = dict(start_pins)
    rho0 = 0.105
    accepted = []
    positions_of: dict[int, list[int]] = {}
    for i, n in enumerate(numbers):
        positions_of.setdefault(n, []).append(i)
    for rnd in range(max_rounds):
        new = 0
        for crib in CRIBS:
            L = len(crib)
            for start in range(0, len(numbers) - L + 1):
                window_nums = numbers[start:start + L]
                # (A) hard consistency with existing pins
                ok = True
                implied: dict[int, str] = {}
                for n, ch in zip(window_nums, crib):
                    want = pins.get(n) or implied.get(n)
                    if want is not None and want != ch:
                        ok = False
                        break
                    implied[n] = ch
                if not ok:
                    continue
                # (B) propagation cross-checks at remote occurrences
                checks = hits = 0
                for n, ch in zip(window_nums, crib):
                    if n in pins:
                        continue  # already-pinned letters are not evidence
                    for j in positions_of[n]:
                        if start <= j < start + L:
                            continue
                        # neighbor agreement: does a pinned neighbor pair
                        # (j-1 or j+1) form a plausible bigram with ch?
                        for k in (j - 1, j + 1):
                            if 0 <= k < len(numbers) and numbers[k] in pins:
                                checks += 1
                                if _bigram_ok(pins[numbers[k]], ch, k < j):
                                    hits += 1
                if checks < 4:
                    continue
                p = _binom_tail(hits, checks, rho0 * 3)
                if hits >= 3 * rho0 * checks and \
                        _binom_tail(hits, checks, rho0) < p_thresh:
                    for n, ch in implied.items():
                        pins[n] = ch
                    accepted.append((crib, start, hits, checks))
                    new += 1
        if new == 0:
            break
    return accepted, pins


_BIGRAM_CACHE = {}


def _bigram_ok(a: str, b: str, a_first: bool) -> bool:
    global _BIGRAM_CACHE
    if not _BIGRAM_CACHE:
        from .ngrams import Quadgrams
        from .scanhmm import bigram_logprobs

        _BIGRAM_CACHE["t"] = bigram_logprobs(Quadgrams.load())
    big = _BIGRAM_CACHE["t"]
    x, y = (a, b) if a_first else (b, a)
    return big[ord(x) - 97][ord(y) - 97] > math.log10(1 / 26)


def _binom_tail(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i)
               for i in range(k, n + 1))


def positive_control(rng) -> dict:
    """Encode a treasure-style message against a held-out doc; the
    bootstrap must recover >=15 correct pins at >=80% precision and the
    fingerprint must rank the doc #1."""
    from .corpus import iter_corpus
    from .fingerprint import rank_documents
    from .keytext import from_normalized_json
    from .synth import encode_book_cipher

    doc = from_normalized_json(
        "corpus/keytexts/normalized/last_of_mohicans.json")
    msg = ("ihaveburiedthetreasureinavaultfourmilesfrombufordstavernunder"
           "alargechestnutoakonthenorthridgeabovethecreektwentyfeetdeep"
           "thedepositisironpotsofgoldandsilverandstonescoverthevaulttake"
           "thesouthforkatthebranchandgothirtypacesnortheastpastthecave")
    nums = encode_book_cipher(msg, doc, rng)
    accepted, pins = bootstrap(tuple(nums), {}, rng)
    correct = sum(1 for n, ch in pins.items()
                  if doc.tokens[n - 1][0] == ch)
    precision = correct / max(1, len(pins))
    docs = list(iter_corpus(min_tokens=2000))
    ranked = rank_documents(pins, docs, top=3) if len(pins) >= 10 else []
    rank1 = ranked[0].doc_id if ranked else None
    return {"accepted": len(accepted), "pins": len(pins),
            "precision": precision, "top_doc": rank1,
            "pass": len(pins) >= 15 and precision >= 0.8
                    and rank1 == doc.id}


def main() -> None:
    data = load_beale()
    kt = reconstruct(data)
    rng = random.Random(1885)

    print("=== positive control ===")
    pc = positive_control(rng)
    print(f"  accepted={pc['accepted']} pins={pc['pins']} "
          f"precision={pc['precision']:.0%} top_doc={pc['top_doc']} "
          f"-> {'PASS' if pc['pass'] else 'FAIL'}")

    crit = Criteria("crib-bootstrap", "c1",
                    ("interpret only if positive control passed",
                     "sealed arms; G3 agreement on shared numbers vs "
                     "binomial null ~0.105; SAME KEY only at p<0.001",
                     "null bootstraps on shuffles bound the accept rate"))
    rec = start_run("crib-bootstrap", "c1", {"cribs": CRIBS}, criteria=crit)

    print("\n=== real arms (sealed; start pins = C2 key table) ===")
    arms = {}
    for cipher in ("C1", "C3"):
        nums = data.cipher_for(cipher)
        accepted, pins = bootstrap(tuple(nums), kt.as_overrides(),
                                   random.Random(7))
        new_pins = {n: ch for n, ch in pins.items()
                    if kt.letter(n) is None}
        arms[cipher] = (accepted, new_pins)
        print(f"  {cipher}: accepted {len(accepted)} cribs, "
              f"{len(new_pins)} NEW pins beyond the key table")
        for crib, start, h, c in accepted[:8]:
            print(f"    '{crib}' @ {start} (cross-checks {h}/{c})")

    # null bound: same bootstrap on shuffles
    null_counts = []
    for s in range(20):
        r = random.Random(100 + s)
        shuf = list(data.cipher1)
        r.shuffle(shuf)
        a, p = bootstrap(tuple(shuf), kt.as_overrides(), r, max_rounds=2)
        null_counts.append(len(a))
    print(f"  null accept counts (20 shuffles of C1): "
          f"max={max(null_counts)} mean={sum(null_counts)/20:.1f}")

    # G3: agreement between arms on shared numbers
    p1, p3 = arms["C1"][1], arms["C3"][1]
    shared = set(p1) & set(p3)
    agree = sum(1 for n in shared if p1[n] == p3[n])
    print(f"\n=== G3 same-pamphlet ===")
    if len(shared) >= 8:
        p = _binom_tail(agree, len(shared), 0.105)
        verdict = ("SAME KEY" if p < 0.001 else
                   "suggestive" if p < 0.05 else "no evidence")
        print(f"  shared new pins {len(shared)}, agree {agree}, "
              f"binom p={p:.4g} -> {verdict}")
    else:
        verdict = "UNDETERMINED - insufficient pins"
        print(f"  only {len(shared)} shared new pins -> {verdict}")
    rec.finish(positive_control=pc,
               c1={"accepted": len(arms['C1'][0]), "new_pins": len(p1)},
               c3={"accepted": len(arms['C3'][0]), "new_pins": len(p3)},
               null_max=max(null_counts), g3_verdict=verdict)


if __name__ == "__main__":
    main()
