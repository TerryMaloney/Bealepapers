import random

import pytest

from beale.ngrams import Quadgrams, count_quadgrams
from beale.scoring import (
    chi_squared,
    dictionary_coverage,
    index_of_coincidence,
    score_text,
)

ENGLISH = (
    "ihavedepositedinthecountyofbedfordaboutfourmilesfrombufordsinan"
    "excavationorvaultsixfeetbelowthesurfaceofthegroundthefollowing"
    "articlesbelongingjointlytothepartieswhosenamesaregiveninnumberthree"
)


@pytest.fixture(scope="module")
def quad():
    return Quadgrams.load()


def test_english_beats_shuffled_on_quadgrams(quad):
    shuffled = "".join(random.Random(1).sample(ENGLISH, len(ENGLISH)))
    assert quad.score(ENGLISH) > quad.score(shuffled) + 1.0


def test_ioc_separates_english_from_uniform():
    uniform = "".join(random.Random(2).choices("abcdefghijklmnopqrstuvwxyz", k=500))
    assert index_of_coincidence(ENGLISH) > 0.055
    assert index_of_coincidence(uniform) < 0.05


def test_chi2_lower_for_english():
    uniform = "".join(random.Random(3).choices("abcdefghijklmnopqrstuvwxyz", k=500))
    assert chi_squared(ENGLISH) < chi_squared(uniform)


def test_dictionary_coverage():
    words = frozenset({"have", "deposited", "county", "bedford", "the"})
    assert dictionary_coverage("ihavedepositedinthecounty", words) > 0.5
    assert dictionary_coverage("zqxjwvkpzqxjwvkp", words) == 0.0


def test_count_quadgrams_does_not_span_breaks():
    counts = count_quadgrams("abc?defg")
    assert "ABCD" not in counts
    assert counts["DEFG"] == 1


def test_score_text_report_fields(quad):
    rep = score_text(ENGLISH, quad, frozenset({"have", "the"}))
    assert rep.quadgram > -6
    assert 0 <= rep.dict_coverage <= 1
