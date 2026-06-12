import pytest

from beale.data import BealeDataError, load_beale, normalize_word, parse_cipher_line


@pytest.fixture(scope="module")
def data():
    return load_beale()


def test_cipher_counts(data):
    assert len(data.cipher1) == 520
    assert len(data.cipher2) == 763
    assert len(data.cipher3) == 618


def test_cipher_maxes(data):
    assert max(data.cipher1) == 2906
    assert max(data.cipher2) == 1005
    assert max(data.cipher3) == 975


def test_doi_word_count(data):
    assert len(data.doi_words) == 1322


def test_doi_sentinel_words(data):
    # 1-indexed words 811, 908, 1005 — the tokenization tripwires
    assert data.doi_words[810] == "taking"
    assert data.doi_words[907] == "and"  # printed as and(&)(908)
    assert data.doi_words[1004] == "petitioned"


def test_doi_first_words(data):
    assert data.doi_words[:4] == ("when", "in", "the", "course")


def test_normalize_word():
    assert normalize_word("Buford's,") == "bufords"
    assert normalize_word("&") == ""


def test_parse_cipher_line():
    assert parse_cipher_line("1, 22,333,  4") == (1, 22, 333, 4)


def test_cipher_for(data):
    assert data.cipher_for("C2") == data.cipher2
    with pytest.raises(BealeDataError):
        data.cipher_for("C9")
