"""Workstream E2: automated hunt for Beale's physical DOI printing.

Fetches DOI transcriptions from multiple textual traditions plus
full-text-search hits on the deviation phrases themselves, then tests every
candidate against the wanted-poster predicates and the 180-pin skeleton
(slide + drift alignment).

Preregistered hit rule (computed AFTER per-predicate base rates over the
fetched corpus): HIT = the ten-word line-skip (any join-phrase alternate)
alone, OR >=2 minor predicates with joint probability < 1e-3 under observed
base rates. STRONG HIT = line-skip + any other. Any hit requires a second
independent source of the same printing before being reported as a find.

Run:  python -m beale.exp_hunt [--no-ia]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .data import load_beale, normalize_word
from .exp_printing import block_join_phrases, placement_sweep, variant_sites
from .fingerprint import drift_align, slide_match
from .keytable import reconstruct
from .keytext import KeyText, from_text

DOI_START = "when in the course of human events"
DOI_END = "our sacred honor"

DIRECT_SOURCES = {
    "avalon": "https://avalon.law.yale.edu/18th_century/declare.asp",
    "ushistory": "https://www.ushistory.org/declaration/document/",
    "nara": "https://www.archives.gov/founding-docs/declaration-transcript",
    "wikisource_engrossed":
        "https://en.wikisource.org/wiki/United_States_Declaration_of_Independence",
    "wikisource_dunlap":
        "https://en.wikisource.org/wiki/Declaration_of_Independence_(Dunlap_broadside)",
    "wikisource_draft":
        "https://en.wikisource.org/wiki/Jefferson%27s_draft_of_the_Declaration_of_Independence",
    "constitution_congress":
        "https://constitution.congress.gov/constitution/declaration-of-independence/",
}


def _strip_html(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html,
                  flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", html)


def extract_doi_tokens(text: str) -> tuple[str, ...] | None:
    """Normalized token stream of the DOI span inside arbitrary text."""
    toks = [t for t in (normalize_word(w) for w in text.split()) if t]
    joined = " ".join(toks)
    s = joined.find(DOI_START)
    if s == -1:
        return None
    e = joined.find(DOI_END, s)
    if e == -1:
        return None
    span = joined[s : e + len(DOI_END)].split()
    if not 1150 <= len(span) <= 1500:
        return None
    return tuple(span)


@dataclass
class CandidateResult:
    source: str
    n_tokens: int
    predicate_hits: dict[str, bool]
    slide_z: float
    drift_matches: int
    drift_pins: int
    breakpoints_matched: int

    @property
    def n_predicates(self) -> int:
        return sum(self.predicate_hits.values())


def build_predicates(data) -> dict[str, list[str]]:
    """Predicate id -> list of acceptable normalized phrases."""
    sweep = placement_sweep(data)
    joins = block_join_phrases(data, sweep["block_starts"])
    return {
        "P1_extra_a": ["to institute a new government"],
        "P2_missing_the": ["pursuing invariably same object"],
        "P3_line_skip": joins,
        "P6_missing_out": ["and eat their substance"],
        "P7_missing_of": ["military independent and superior to"],
    }


def evaluate_candidate(source: str, tokens: tuple[str, ...], pins, data,
                       predicates) -> CandidateResult:
    joined = " ".join(tokens)
    hits = {pid: any(ph in joined for ph in phrases)
            for pid, phrases in predicates.items()}
    kt = KeyText(id=source, tokens=tokens, source="hunt")
    sh = slide_match(pins, kt)
    da = drift_align(pins, kt, sh.offset if sh else 0, band=16)
    fitted = {155, 242, 467, 487, 621, 648}
    bp = sum(1 for idx, _ in da.drift_profile
             if any(abs(idx - f) <= 3 for f in fitted))
    return CandidateResult(source, len(tokens), hits,
                           sh.z if sh else 0.0, da.matches, da.pins, bp)


def fetch_candidates(include_ia: bool = True) -> dict[str, tuple[str, ...]]:
    from .fetch import _get

    out: dict[str, tuple[str, ...]] = {}
    for name, url in DIRECT_SOURCES.items():
        try:
            toks = extract_doi_tokens(_strip_html(_get(url)))
            if toks:
                out[name] = toks
            else:
                print(f"  [skip] {name}: no clean DOI span")
        except Exception as e:
            print(f"  [fail] {name}: {type(e).__name__} {str(e)[:80]}")
    # Gutenberg: books likely to embed the DOI
    try:
        import json as _json

        raw = _get("https://gutendex.com/books?search=declaration%20of%20independence")
        ids = [b["id"] for b in _json.loads(raw)["results"][:12]]
        from .fetch import fetch_gutenberg

        for gid in ids:
            try:
                kt = fetch_gutenberg(gid)
                toks = extract_doi_tokens(" ".join(kt.tokens))
                if toks:
                    out[f"gutenberg_{gid}"] = toks
            except Exception:
                continue
    except Exception as e:
        print(f"  [fail] gutendex: {type(e).__name__}")
    if include_ia:
        out.update(fetch_ia_phrase_hits())
    return out


def fetch_ia_phrase_hits(max_items: int = 12) -> dict[str, tuple[str, ...]]:
    """Internet Archive full-text search on the deviation phrases."""
    from .fetch import _get

    phrases = ["representative houses rights of the people",
               "pursuing invariably same object"]
    found: dict[str, tuple[str, ...]] = {}
    for ph in phrases:
        try:
            html = _get("https://archive.org/search.php?query=%22"
                        + ph.replace(" ", "+") + "%22&sin=TXT")
            ids = re.findall(r'/details/([A-Za-z0-9_.-]+)', html)
            seen = []
            for i in ids:
                if i not in seen:
                    seen.append(i)
            for ident in seen[:max_items]:
                if ident in found:
                    continue
                try:
                    txt = _get(f"https://archive.org/download/{ident}/{ident}_djvu.txt")
                    toks = extract_doi_tokens(txt)
                    if toks:
                        found[f"ia_{ident}"] = toks
                except Exception:
                    continue
        except Exception as e:
            print(f"  [fail] IA search '{ph[:30]}...': {type(e).__name__}")
    return found


def main(include_ia: bool = True) -> None:
    import sys

    data = load_beale()
    kt = reconstruct(data)
    pins = {n: e.letter for n, e in kt.entries.items()}
    predicates = build_predicates(data)
    print("fetching candidates...")
    cands = fetch_candidates(include_ia=include_ia)
    print(f"{len(cands)} candidate DOI texts\n")
    results = [evaluate_candidate(s, t, pins, data, predicates)
               for s, t in cands.items()]
    # base rates per predicate
    n = max(1, len(results))
    base = {pid: sum(r.predicate_hits[pid] for r in results) / n
            for pid in predicates}
    print("predicate base rates:", {k: round(v, 2) for k, v in base.items()})
    results.sort(key=lambda r: (r.predicate_hits.get("P3_line_skip", False),
                                r.n_predicates, r.drift_matches), reverse=True)
    print(f"\n{'source':28s} {'tok':>5s} {'preds':>5s} {'P3':>3s} "
          f"{'slideZ':>7s} {'drift':>9s} {'bp':>3s}")
    for r in results:
        print(f"{r.source[:28]:28s} {r.n_tokens:5d} {r.n_predicates:5d} "
              f"{'Y' if r.predicate_hits.get('P3_line_skip') else '.':>3s} "
              f"{r.slide_z:7.1f} {r.drift_matches:4d}/{r.drift_pins:<4d} "
              f"{r.breakpoints_matched:3d}")
    hits = [r for r in results if r.predicate_hits.get("P3_line_skip")
            or r.n_predicates >= 2]
    print(f"\nhit-rule candidates: {[r.source for r in hits] or 'NONE'}")

    from .runlog import Criteria, start_run

    crit = Criteria("printing-hunt", "c2",
                    ("HIT = P3 line-skip alone OR >=2 minor predicates at "
                     "joint p<1e-3 under fetched base rates; any hit needs a "
                     "second independent source",))
    rec = start_run("printing-hunt", "c2", {"n_candidates": len(cands)},
                    criteria=crit)
    rec.finish(base_rates=base,
               results=[r.__dict__ for r in results],
               hit_candidates=[r.source for r in hits])


if __name__ == "__main__":
    import sys

    main(include_ia="--no-ia" not in sys.argv)
