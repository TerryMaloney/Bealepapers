"""Workstream A experiment: pinned homophonic attack on Ciphers 1 and 3.

Pins come from Beale's reconstructed C2 key table (shared-key hypothesis).
Protocol (preregistered):
  1. Calibration: synthetic ciphers matched to each target's profile with the
     same pin coverage; measures what free-position accuracy the solver
     achieves when a message IS present. This is what makes real results
     interpretable.
  2. Real runs, hard pins: best decodes rendered plaintext-first.
  3. Real runs, soft pins: pin-violation rate tests the shared-key
     hypothesis itself (<=10% consistent; >=30% rejected).

Run:  python -m beale.exp_pinned
"""

from __future__ import annotations

import random

from .data import load_beale
from .homophonic import HomophonicProblem, SolverConfig, iphc_ratchet, solve
from .keytable import reconstruct
from .keytext import KeyText
from .ngrams import Quadgrams
from .report import Tier, from_decode, render
from .runlog import Criteria, start_run
from .scoring import score_text
from .synth import encode_book_cipher, names_list_plaintext, sample_plaintext

CFG = SolverConfig(iters=900_000, restarts=16, t0=12.0, tf=0.3,
                   stall_limit=160_000, use_quint=True)


def _solve_and_ratchet(prob, quad, seed=0, processes=4):
    cfg = SolverConfig(**{**CFG.__dict__, "seed": seed})
    res = solve(prob, quad, cfg, processes=processes)
    best = res.finalists[0]
    ratcheted = iphc_ratchet(prob, best.assign, quad, rounds=120, seed=seed + 1,
                             cfg=cfg)
    return ratcheted if ratcheted.score > best.score else best


def synth_calibration(data, quad, cipher: str, trials: int = 4) -> list[float]:
    """Encode period plaintext against the DOI mimicking Beale's number
    habits (prefer his known homophone pool) so synthetic pin coverage
    matches the real cipher's; measure free-position accuracy."""
    kt = reconstruct(data)
    real_nums = data.cipher_for(cipher)
    target_cov = kt.coverage(real_nums)
    pool_by_letter: dict[str, list[int]] = {}
    for n, e in kt.entries.items():
        pool_by_letter.setdefault(e.letter, []).append(n)
    doi_by_letter: dict[str, list[int]] = {}
    for i, w in enumerate(data.doi_words):
        doi_by_letter.setdefault(w[0], []).append(i + 1)
    accs = []
    for t in range(trials):
        rng = random.Random(1000 + t)
        if cipher == "C3":
            pt = names_list_plaintext(rng, len(real_nums))
        else:
            pt = sample_plaintext(list(data.doi_words), len(real_nums), rng)
        for ch in "xyz":
            pt = pt.replace(ch, "e")
        nums = []
        ok = True
        for ch in pt:
            beale_pool = pool_by_letter.get(ch)
            doi_pool = doi_by_letter.get(ch)
            if beale_pool and rng.random() < target_cov:
                nums.append(rng.choice(beale_pool))
            elif doi_pool:
                nums.append(rng.choice(doi_pool))
            else:
                ok = False
                break
        if not ok:
            continue
        pin_letters = {n: kt.letter(n) for n in set(nums) if kt.letter(n)}
        prob = HomophonicProblem.build(nums, pin_letters=pin_letters)
        sol = _solve_and_ratchet(prob, quad, seed=2000 + t)
        free_pos = [i for i, n in enumerate(nums) if n not in pin_letters]
        acc = sum(1 for i in free_pos if sol.text[i] == pt[i]) / len(free_pos)
        accs.append(acc)
        print(f"  {cipher} calib trial {t}: free-position acc {acc:.1%} "
              f"(coverage {1 - len(free_pos)/len(nums):.0%})", flush=True)
    return accs


def real_run(data, quad, cipher: str, soft: bool) -> None:
    kt = reconstruct(data)
    crit = Criteria(
        "homophonic-pinned", cipher.lower(),
        ("interpret free-position text only against the synthetic calibration",
         "soft-pin violation <=10% supports shared key; >=30% rejects it",
         "no solution claim without quadgram z>=4 vs shuffled null AND "
         "visible English in the rendered text"))
    rec = start_run("homophonic-pinned", cipher.lower(),
                    {"cfg": str(CFG), "soft": soft}, seed=CFG.seed, criteria=crit)
    prob = HomophonicProblem.build(
        data.cipher_for(cipher), pin_letters=kt.as_overrides())
    cfg_d = {**CFG.__dict__, "soft_pins": soft}
    global CFG_RUN
    cfg = SolverConfig(**cfg_d)
    res = solve(prob, quad, cfg, processes=4)
    best = res.finalists[0]
    ratcheted = iphc_ratchet(prob, best.assign, quad, rounds=120, seed=99, cfg=cfg)
    if ratcheted.score > best.score:
        best = ratcheted
    label = f"{cipher} pinned({'soft' if soft else 'hard'})"
    at = from_decode(best.text, tier=Tier.SOLVER, label=label, conf=0.6,
                     scores=score_text(best.text.replace("?", ""), quad))
    pin_pos = {i: kt.letter(n) for i, n in enumerate(data.cipher_for(cipher))
               if kt.letter(n)}
    if not soft:
        from .report import merge_pins
        at = merge_pins(at, pin_pos)
    print(render(at))
    if soft:
        print(f"  PIN VIOLATION RATE: {best.pin_violations:.1%}")
    rec.finish(score=best.score, pin_violations=best.pin_violations,
               text=best.text)


def main() -> None:
    data = load_beale()
    quad = Quadgrams.load()
    print("=== calibration (synthetic, message present) ===")
    for cipher in ("C3", "C1"):
        synth_calibration(data, quad, cipher, trials=3)
    print("\n=== real runs, hard pins ===")
    for cipher in ("C3", "C1"):
        real_run(data, quad, cipher, soft=False)
    print("\n=== real runs, soft pins (shared-key test) ===")
    for cipher in ("C3", "C1"):
        real_run(data, quad, cipher, soft=True)


if __name__ == "__main__":
    main()
