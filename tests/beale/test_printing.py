"""E1 gate: the poster must reproduce the keytable anchors and the known
variant sites."""

import pytest

from beale.data import load_beale
from beale.exp_printing import placement_sweep, variant_sites
from beale.keytable import reconstruct


@pytest.fixture(scope="module")
def data():
    return load_beale()


def test_keytable_anchors_bracket_the_edits(data):
    kt = reconstruct(data)
    # anchors that pin the variant placements (Beale-numbering -> letter)
    for num, want in [(154, "i"), (158, "l"), (241, "i"), (466, "h"),
                      (485, "b"), (620, "e"), (647, "i")]:
        assert kt.letter(num) == want, (num, kt.letter(num), want)


def test_variant_sites_match_known_profile(data):
    sites = variant_sites(data)
    ops = [(s.op, s.words) for s in sites]
    assert ("extra", ("a",)) in ops                     # institute A new
    assert ("missing", ("the",)) in ops                 # invariably [the] same
    assert ("missing", ("out",)) in ops                 # eat [out] their
    assert ("missing", ("of",)) in ops                  # independent [of] and
    ten = [s for s in sites if s.op == "missing" and len(s.words) == 10]
    assert len(ten) == 1
    assert ten[0].words[0] == "repeatedly"
    assert ten[0].words[-1] == "the"


def test_placement_sweep_explains_505(data):
    sweep = placement_sweep(data)
    assert sweep["oracle_max"] == 755
    assert 467 in sweep["block_starts"]
    assert sweep["explains_505"] is True
