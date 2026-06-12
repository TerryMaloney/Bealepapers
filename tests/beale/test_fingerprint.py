"""Ground-truth test: the C2 skeleton must identify the DOI and its drift."""

import pytest

from beale.data import load_beale
from beale.fingerprint import drift_align, rank_documents, slide_match
from beale.keytable import reconstruct
from beale.keytext import from_doi
from beale.skeleton import Crib, Skeleton, build_skeleton, c2_table_cribs


@pytest.fixture(scope="module")
def data():
    return load_beale()


@pytest.fixture(scope="module")
def pins(data):
    kt = reconstruct(data)
    return {n: e.letter for n, e in kt.entries.items()}


def test_skeleton_from_c2_cribs(data):
    sk = build_skeleton(c2_table_cribs(data), {"c2": data.cipher2})
    assert len(sk.votes) == 180
    assert sk.consistency() > 0.98
    assert sk.pin(115) == "i"   # word 115 "instituted"


def test_doi_slide_match_is_overwhelming(data, pins):
    doi = from_doi(data)
    hit = slide_match(pins, doi)
    assert hit is not None
    assert hit.offset == 0
    assert hit.z > 15


def test_doi_ranks_first_in_corpus(data, pins):
    from beale.corpus import iter_corpus

    docs = [from_doi(data)] + list(iter_corpus(min_tokens=400))
    ranked = rank_documents(pins, docs, top=5)
    # any DOI edition may win (the corpus's pre-adjusted edition matches
    # Beale's key even better than the raw embedded one — correctly so)
    assert "doi" in ranked[0].doc_id.lower()
    best_non_doi = next(h for h in ranked if "doi" not in h.doc_id.lower())
    assert ranked[0].z > best_non_doi.z + 5


def test_drift_alignment_recovers_known_band(data, pins):
    doi = from_doi(data)
    al = drift_align(pins, doi, offset=0)
    assert al.matches / al.pins > 0.9
    # Beale's numbering runs one ahead of ours in the 158-241 band
    # (his copy had an extra word near 155): drift must dip to -1 there
    # and recover, then jump positive after the ~467 deletions.
    deltas = dict(al.drift_profile)
    assert any(155 <= idx <= 250 and delta == -1
               for idx, delta in al.drift_profile)
    assert any(idx >= 480 and delta >= 9 for idx, delta in al.drift_profile)


def test_skeleton_conflict_detection():
    sk = Skeleton()
    sk.add(10, "a", "crib1")
    sk.add(10, "a", "crib2")
    sk.add(10, "b", "crib3")
    assert sk.pin(10) is None          # 2/3 < 0.8 share
    assert 10 in sk.conflicts()
    assert sk.consistency() < 1.0
