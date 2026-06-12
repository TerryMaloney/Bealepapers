"""PRIMARY ACCEPTANCE GATE: the engine must reproduce the known C2 solution."""

import pytest

from beale.data import load_beale
from beale.edits import load_overrides
from beale.oracle import known_c2_plaintext, verify_cipher2


@pytest.fixture(scope="module")
def data():
    return load_beale()


def test_ground_truth_is_763_letters():
    assert len(known_c2_plaintext()) == 763


def test_c2_reproduces_plaintext(data):
    report = verify_cipher2(data)
    assert report.n_oor == 0
    assert report.exact_pct >= 0.90, (
        f"C2 oracle regressed: {report.exact_pct:.1%} "
        f"({len(report.mismatches)} mismatches)"
    )


def test_opening_phrase_decodes_exactly(data):
    report = verify_cipher2(data)
    assert report.decoded.startswith("ihavedeposited")


def test_baseline_without_edits_still_strong(data):
    # Guards against an engine that only "works" because of the edit list.
    report = verify_cipher2(data, use_edits=False)
    assert report.exact_pct >= 0.80


def test_overrides_fix_y_and_x(data):
    plain = known_c2_plaintext()
    without = verify_cipher2(data, use_overrides=False)
    with_ov = verify_cipher2(data, use_overrides=True)
    y_positions = [i for i, n in enumerate(data.cipher2) if n == 811]
    x_positions = [i for i, n in enumerate(data.cipher2) if n == 1005]
    assert y_positions and x_positions
    for i in y_positions + x_positions:
        assert with_ov.decoded[i] == plain[i]
        assert without.decoded[i] != plain[i]


def test_override_map_is_small():
    assert len(load_overrides()) <= 5


def test_mismatches_are_scattered_not_clustered(data):
    # A correct alignment leaves transcription noise spread thin; a block of
    # consecutive mismatches would mean the alignment broke somewhere.
    report = verify_cipher2(data)
    positions = [p for p, _, _ in report.mismatches]
    longest_run = run = 1
    for a, b in zip(positions, positions[1:]):
        run = run + 1 if b == a + 1 else 1
        longest_run = max(longest_run, run)
    assert longest_run <= 5
