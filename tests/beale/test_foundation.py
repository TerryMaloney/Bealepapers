"""Workstream 0 tests: key table, report rendering, runlog, synth."""

import random

import pytest

from beale.data import load_beale
from beale.keytable import reconstruct
from beale.keytext import KeyText
from beale.report import Tier, from_decode, merge_pins, render, render_compare
from beale.runlog import Criteria, PreregistrationError, start_run
from beale.synth import (
    encode_book_cipher,
    encode_scan_forward,
    profile_of,
    sample_plaintext,
)


@pytest.fixture(scope="module")
def data():
    return load_beale()


def test_keytable_reconstruction(data):
    kt = reconstruct(data)
    assert len(kt.entries) == 180
    assert len(kt.verified) == 137
    # the three known one-off conflicts still majority-vote correctly
    assert kt.letter(53) == "r" and kt.entries[53].confidence > 0.85
    assert kt.letter(84) == "c"
    assert kt.letter(96) == "r"
    # homophone overrides present
    assert kt.letter(811) == "y" and kt.letter(1005) == "x"


def test_keytable_cross_cipher_coverage(data):
    kt = reconstruct(data)
    assert 0.50 < kt.coverage(data.cipher1) < 0.56
    assert 0.54 < kt.coverage(data.cipher3) < 0.60


def test_keytable_decodes_c2_perfectly(data):
    # By construction the table reproduces the majority letter everywhere;
    # only the 4 one-off copy-error positions differ.
    from beale.engine import DecodeConfig, decode
    from beale.oracle import known_c2_plaintext

    kt = reconstruct(data)
    res = decode(data.cipher2, [], DecodeConfig(overrides=kt.as_overrides()))
    gt = known_c2_plaintext()
    mismatches = sum(a != b for a, b in zip(res.text, gt))
    assert mismatches == 4


def test_report_render_marks_tiers(data):
    at = from_decode("ihave?depos", tier=Tier.SOLVER, label="test")
    at = merge_pins(at, {0: "i", 1: "h"})
    out = render(at, words=frozenset({"have"}))
    assert "IH" in out          # pins uppercase
    assert "·" in out           # unknown dot
    assert "|---" in out        # dictionary span marking for 'have'


def test_render_compare_divergence():
    a = from_decode("abc", label="a")
    b = from_decode("abd", label="b")
    out = render_compare([a, b], words=frozenset())
    assert "^" in out


def test_runlog_requires_criteria_for_real_targets(tmp_path, monkeypatch):
    import beale.runlog as rl

    monkeypatch.setattr(rl, "RUNS_DIR", tmp_path)
    with pytest.raises(PreregistrationError):
        start_run("solver", "c3", {})
    rec = start_run("solver", "synthetic", {"x": 1})
    path = rec.finish(ok=True)
    assert path.exists()
    crit = Criteria("solver", "c3", ("quadgram >= 4 sigma over shuffled null",))
    rec = start_run("solver", "c3", {}, criteria=crit)
    assert rec.criteria["digest"]


def test_synth_book_cipher_roundtrip(data):
    rng = random.Random(7)
    key = KeyText(id="doi", tokens=data.doi_words, source="test")
    pt = sample_plaintext(list(data.doi_words), 200, rng)
    pt = pt.replace("x", "e").replace("y", "e").replace("z", "e")  # DOI lacks x/y/z
    nums = encode_book_cipher(pt, key, rng)
    assert nums is not None
    decoded = "".join(data.doi_words[n - 1][0] for n in nums)
    assert decoded == pt


def test_synth_scan_forward_is_ascending_and_decodable(data):
    rng = random.Random(7)
    key = KeyText(id="doi", tokens=data.doi_words[:1000], source="test")
    # no x/y/z: the DOI has no words with those initials (hence Beale's
    # 811->y / 1005->x homophones)
    pt = "thetreasureisburiedundergroundnearthecreek"
    nums = encode_scan_forward(pt, key, rng)
    assert nums is not None
    decoded = "".join(key.tokens[n - 1][0] for n in nums)
    assert decoded == pt
    ups = sum(1 for a, b in zip(nums, nums[1:]) if b > a)
    assert ups / (len(nums) - 1) > 0.6  # mostly ascending: the C3 signature


def test_profile_of(data):
    p1 = profile_of(data, "C1")
    assert p1.length == 520 and p1.distinct == 298
    assert 0.30 < p1.singleton_frac < 0.38
