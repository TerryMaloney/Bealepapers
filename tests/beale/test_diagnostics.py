import pytest

from beale.data import load_beale
from beale.diagnostics import (
    detect_alphabetical_runs,
    incremental_fraction,
    randomness_report,
)
from beale.edits import apply_edits, load_overrides
from beale.engine import DecodeConfig
from beale.ngrams import Quadgrams
from beale.oracle import load_doi_edits


@pytest.fixture(scope="module")
def data():
    return load_beale()


@pytest.fixture(scope="module")
def quad():
    return Quadgrams.load()


def test_detect_alphabetical_runs():
    runs = detect_alphabetical_runs("xxabcdefghyy", min_len=5)
    assert any("abcdefgh" in r.text for r in runs)
    assert detect_alphabetical_runs("thequickbrownfox", min_len=6) == []


def test_incremental_fraction():
    assert incremental_fraction("abcde") == 1.0
    assert incremental_fraction("aaaaa") == 0.0


def test_c1_doi_reproduces_gillogly_artifact(data, quad):
    rep = randomness_report(data.cipher1, data.doi_words, quad, n_baseline=10)
    assert any("defghi" in r.text for r in rep.alphabetical_runs), (
        "the famous Gillogly alphabetical string should appear in C1+DOI"
    )
    assert "artifact" in rep.verdict


def test_c3_doi_looks_random(data, quad):
    rep = randomness_report(data.cipher3, data.doi_words, quad, n_baseline=10)
    assert "random" in rep.verdict


def test_c2_control_looks_like_language(data, quad):
    tokens = apply_edits(data.doi_words, load_doi_edits())
    rep = randomness_report(
        data.cipher2, tokens, quad,
        cfg=DecodeConfig(overrides=load_overrides()), n_baseline=10,
    )
    assert rep.quadgram_z > 3
    assert "language" in rep.verdict
