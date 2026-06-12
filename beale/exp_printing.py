"""Workstream E1: the "wanted poster" — Beale's DOI variant profile.

Replays the fitted key edits against the embedded DOI and emits a precise,
human-searchable description of how Beale's physical copy differed from the
pamphlet text, plus machine predicates for the automated printing hunt.

E1b sweeps the placement ambiguity: several edit positions are only pinned
between keytable anchors, so all placements that keep the C2 oracle at its
maximum are reported as equally valid variants (this matters: if the extra
word near #487-515 actually sits after 505, his #505 maps to 'state' and
the "505 = s anomaly" is explained rather than anomalous).

Run:  python -m beale.exp_printing
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from .data import BealeData, load_beale
from .edits import WordEdit, apply_edits, load_overrides
from .engine import DecodeConfig, decode
from .oracle import known_c2_plaintext, load_doi_edits


@dataclass(frozen=True)
class VariantSite:
    op: str                 # "missing" (in Beale's copy) | "extra"
    embedded_index: int     # 1-based word index in the embedded pamphlet DOI
    words: tuple[str, ...]  # the affected pamphlet words (or inserted words)
    pamphlet_context: str
    beale_reading: str      # how Beale's copy reads
    predicate: str          # normalized phrase to search candidate texts


def variant_sites(data: BealeData,
                  edits: list[WordEdit] | None = None) -> list[VariantSite]:
    """Diff the edited (Beale) word list against the embedded pamphlet DOI."""
    edits = edits if edits is not None else load_doi_edits()
    pamphlet = list(data.doi_words)
    beale = list(apply_edits(data.doi_words, edits))
    sm = difflib.SequenceMatcher(a=pamphlet, b=beale, autojunk=False)
    sites = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        ctx_lo, ctx_hi = max(0, i1 - 8), min(len(pamphlet), i2 + 8)
        context = " ".join(
            pamphlet[ctx_lo:i1]) + " [" + " ".join(pamphlet[i1:i2]) + "] " + \
            " ".join(pamphlet[i2:ctx_hi])
        if tag == "delete" or (tag == "replace" and i2 - i1 > j2 - j1):
            words = tuple(pamphlet[i1:i2])
            reading = " ".join(pamphlet[max(0, i1 - 4):i1]
                               + pamphlet[i2:i2 + 4])
            pred = " ".join(pamphlet[max(0, i1 - 2):i1] + pamphlet[i2:i2 + 3])
            sites.append(VariantSite("missing", i1 + 1, words,
                                     context, reading, pred))
        elif tag == "insert" or (tag == "replace" and j2 - j1 > i2 - i1):
            words = tuple(beale[j1:j2])
            reading = " ".join(pamphlet[max(0, i1 - 4):i1]) + \
                f" <{' '.join(words)}> " + " ".join(pamphlet[i1:i1 + 4])
            pred = " ".join(pamphlet[max(0, i1 - 2):i1]
                            + list(words) + pamphlet[i1:i1 + 2])
            sites.append(VariantSite("extra", i1 + 1, words,
                                     context, reading, pred))
    return sites


def render_poster(sites: list[VariantSite]) -> str:
    lines = [
        "# WANTED: a printing of the Declaration of Independence with these variants",
        "",
        "Recovered from Cipher 2's known plaintext (verified key, 99.0% oracle).",
        "Beale's physical copy of the DOI differed from the 1885 pamphlet text:",
        "",
    ]
    for k, s in enumerate(sites, 1):
        what = ("MISSING the word(s)" if s.op == "missing"
                else "has EXTRA word(s)")
        lines += [
            f"## Variant {k} — near word #{s.embedded_index}: {what} "
            f"'{' '.join(s.words)}'",
            f"- pamphlet: …{s.pamphlet_context}…",
            f"- Beale's copy reads: …{s.beale_reading}…",
            f"- search phrase: \"{s.predicate}\"",
            "",
        ]
    lines += [
        "Most diagnostic: the ten-word omission (a dropped typeset line or a",
        "copyist's eye-skip between repeated 'he has' clauses). Any period",
        "printing showing it is a candidate for Beale's actual source.",
        "",
        "NOTE on placement ambiguity: the cipher pins the ten-word block only",
        "between anchor words 466 ('houses') and ~486; any ten consecutive",
        "words in that bracket may be the missing ones. Likewise the extra",
        "word sits anywhere in the 487-510 span — if it falls after word 505,",
        "Beale's word #505 is 'state', which the cipher independently",
        "requires to start with 's'. All join-phrase alternates:",
        "",
    ]
    return "\n".join(lines)


def block_join_phrases(data: BealeData,
                       starts: list[int]) -> list[str]:
    """For each valid ten-word-block start, the phrase a candidate printing
    would show where the line is missing (2 words before + 3 after)."""
    pam = list(data.doi_words)
    out = []
    for s in starts:
        i = s - 1  # 0-based index of first missing word in the current frame
        # current frame ~= embedded frame here (net shift 0 before 467)
        phrase = " ".join(pam[i - 2:i] + pam[i + 10:i + 13])
        out.append(phrase)
    return out


# ------------------------------------------------------------------ E1b ---

def _oracle_matches(data: BealeData, edits: list[WordEdit]) -> int:
    toks = apply_edits(data.doi_words, edits)
    res = decode(data.cipher2, toks, DecodeConfig(overrides=load_overrides()))
    gt = known_c2_plaintext()
    return sum(a == b for a, b in zip(res.text, gt))


def placement_sweep(data: BealeData) -> dict:
    """All edit placements that keep the oracle at its maximum (755/763).

    Frame: edits applied in order insert-a, delete-242-region, ten-block,
    'the'-insert, late deletes; positions for the swept edits are expressed
    in the post-(insert,delete) frame, matching doi_edits_c2.json.
    """
    base_max = _oracle_matches(data, load_doi_edits())
    results = {"oracle_max": base_max, "block_starts": [], "insert_positions": [],
               "explains_505": False}
    for block in range(460, 487):
        edits = ([WordEdit("insert", 155, "a"), WordEdit("delete", 242)]
                 + [WordEdit("delete", block)] * 10
                 + [WordEdit("delete", 648), WordEdit("insert", 487, "the"),
                    WordEdit("delete", 621)])
        if _oracle_matches(data, edits) >= base_max:
            results["block_starts"].append(block)
    for ins in range(480, 525):
        edits = ([WordEdit("insert", 155, "a"), WordEdit("delete", 242)]
                 + [WordEdit("delete", 467)] * 10
                 + [WordEdit("delete", 648), WordEdit("insert", ins, "the"),
                    WordEdit("delete", 621)])
        if _oracle_matches(data, edits) >= base_max:
            results["insert_positions"].append(ins)
    # does any max-equivalent insert position sit past 505, which would map
    # his #505 onto 'state' and dissolve the 505 anomaly?
    results["explains_505"] = any(p > 505 for p in results["insert_positions"])
    return results


def main() -> None:
    data = load_beale()
    sites = variant_sites(data)
    sweep = placement_sweep(data)
    joins = block_join_phrases(data, sweep["block_starts"])
    poster = render_poster(sites)
    poster += "\n".join(f'- "{p}"' for p in joins) + "\n"
    print(poster)
    print("=" * 70)
    print("E1b placement-ambiguity sweep (all positions keeping oracle max):")
    print(f"  oracle max: {sweep['oracle_max']}/763")
    print(f"  ten-word block start: {sweep['block_starts']}")
    print(f"  extra-word position:  {sweep['insert_positions']}")
    print(f"  505 anomaly explained by placement: {sweep['explains_505']}")
    from pathlib import Path
    out = Path("runs/wanted_poster.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text(poster + "\n", encoding="utf-8")
    print(f"\nposter written to {out}")


if __name__ == "__main__":
    main()
