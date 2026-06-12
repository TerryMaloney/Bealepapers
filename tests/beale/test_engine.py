from beale.edits import WordEdit, apply_edits
from beale.engine import DecodeConfig, decode

KEY = ["alpha", "bravo", "charlie", "delta", "echo"]


def test_first_letter_one_indexed():
    res = decode([1, 2, 5], KEY)
    assert res.text == "abe"
    assert res.n_oor == 0


def test_out_of_range_emits_placeholder():
    res = decode([1, 6, 99, 2], KEY)
    assert res.text == "a??b"
    assert res.n_oor == 2
    assert res.oor_fraction == 0.5


def test_last_and_nth_extraction():
    assert decode([1, 2], KEY, DecodeConfig(extraction="last")).text == "ao"
    assert decode([1, 2], KEY, DecodeConfig(extraction="nth", nth=2)).text == "lr"
    # nth beyond word length is out-of-range, not an exception
    res = decode([5], KEY, DecodeConfig(extraction="nth", nth=5))
    assert res.text == "?"


def test_offset():
    res = decode([1, 2], KEY, DecodeConfig(offset=1))
    assert res.text == "bc"


def test_overrides_win_and_do_not_shift():
    res = decode([1, 3, 2], KEY, DecodeConfig(overrides={3: "z"}))
    assert res.text == "azb"


def test_apply_edits_insert_delete_replace():
    toks = apply_edits(KEY, [WordEdit("delete", 2)])
    assert toks == ("alpha", "charlie", "delta", "echo")
    toks = apply_edits(KEY, [WordEdit("insert", 1, "zulu")])
    assert toks[0] == "zulu" and len(toks) == 6
    toks = apply_edits(KEY, [WordEdit("replace", 5, "xray")])
    assert toks[4] == "xray"
