"""Homophonic solver tests: small synthetic recovery + pinned modes."""

import random

import pytest

from beale.data import load_beale
from beale.homophonic import (
    HomophonicProblem,
    SolverConfig,
    flat_quadgram_table,
    quintgram_table,
    solve,
)
from beale.keytable import reconstruct
from beale.keytext import KeyText
from beale.ngrams import Quadgrams
from beale.synth import encode_book_cipher, sample_plaintext


@pytest.fixture(scope="module")
def data():
    return load_beale()


@pytest.fixture(scope="module")
def quad():
    return Quadgrams.load()


def test_problem_build(data):
    prob = HomophonicProblem.build(data.cipher2)
    assert prob.n_symbols == 180
    assert len(prob.singleton_syms) == 43
    assert len(prob.sym_of) == 763


def test_problem_pins(data):
    kt = reconstruct(data)
    prob = HomophonicProblem.build(data.cipher1, pin_letters=kt.as_overrides())
    assert len(prob.pins) == 122  # C1 shares 122 numbers with C2


def test_quintgram_table_cached():
    tab = quintgram_table()
    assert len(tab) == 26 ** 5
    # 'their' should be common, 'zzzzz' at floor
    their = (((19 * 26 + 7) * 26 + 4) * 26 + 8) * 26 + 17
    zzzzz = (((25 * 26 + 25) * 26 + 25) * 26 + 25) * 26 + 25
    assert tab[their] > tab[zzzzz]


def test_solver_recovers_easy_synthetic(data, quad):
    """Low-multiplicity synthetic (m ~ 0.1) must solve nearly perfectly."""
    rng = random.Random(3)
    key = KeyText(id="doi", tokens=data.doi_words, source="test")
    pt = sample_plaintext(list(data.doi_words), 700, rng)
    for ch in "xyz":
        pt = pt.replace(ch, "e")
    # restrict homophone pool to force heavy reuse (low multiplicity)
    nums_full = encode_book_cipher(pt, key, rng)
    assert nums_full is not None
    # remap to capped homophone sets: keep only first 3 numbers seen per letter
    seen: dict[str, list[int]] = {}
    nums = []
    for n, ch in zip(nums_full, pt):
        pool = seen.setdefault(ch, [])
        if n in pool:
            nums.append(n)
        elif len(pool) < 3:
            pool.append(n)
            nums.append(n)
        else:
            nums.append(rng.choice(pool))
    prob = HomophonicProblem.build(nums)
    assert prob.n_symbols / len(nums) < 0.15
    cfg = SolverConfig(iters=300_000, restarts=6, seed=5, use_quint=True)
    res = solve(prob, quad, cfg, processes=2)
    acc = sum(a == b for a, b in zip(res.finalists[0].text, pt)) / len(pt)
    assert acc >= 0.85, f"easy synthetic only {acc:.1%}"


def test_hard_pins_are_frozen(data, quad):
    kt = reconstruct(data)
    prob = HomophonicProblem.build(data.cipher3, pin_letters=kt.as_overrides())
    cfg = SolverConfig(iters=20_000, restarts=2, seed=1, use_quint=False)
    res = solve(prob, quad, cfg)
    sol = res.finalists[0]
    for s, want in prob.pins.items():
        assert sol.assign[s] == want
