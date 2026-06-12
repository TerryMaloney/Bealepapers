"""Workstream F: extended-stack / signers test for C1's high numbers.

Preregistered framing: shared-key is already rejected for C1; this tests
the weaker fallback that the key NUMBERING continues into appendix texts,
and adjudicates the legacy "1701 -> lewis" anecdote with an honest null
(zero-trust rule for legacy claims). C1 has only ~10 numbers beyond the
DOI, so outcomes are graded supportive/unsupportive, never conclusive.

Run:  python -m beale.exp_stack
"""

from __future__ import annotations

import math
import random
import statistics
from collections import Counter
from pathlib import Path

from .c1_twostage import WILD, build_marginals, wildcard_quad_score
from .data import load_beale, normalize_word
from .edits import apply_edits
from .homophonic import flat_quadgram_table
from .keytable import reconstruct
from .ngrams import Quadgrams
from .oracle import load_doi_edits
from .runlog import Criteria, start_run

GAPS = range(0, 61)  # unknown front-matter words between base and appendix


def _tokens(path: str) -> tuple[str, ...]:
    raw = Path(path).read_text(encoding="utf-8")
    return tuple(t for t in (normalize_word(w) for w in raw.split()) if t)


def signers_orderings() -> dict[str, tuple[str, ...]]:
    raw = Path("texts/signers.txt").read_text(encoding="utf-8")
    blocks = [b.strip().splitlines() for b in raw.strip().split("\n\n")]
    states = [(normalize_word(b[0]), [normalize_word(w) for line in b[1:]
                                      for w in line.split()]) for b in blocks]
    o1 = tuple(w for st, names in states for w in ([st] + names) if w)
    o4 = tuple(w for _, names in states for w in names if w)
    # alphabetical by surname (last token of each name line)
    lines = [line for b in blocks for line in b[1:]]
    by_surname = sorted(lines, key=lambda ln: ln.split()[-1].lower())
    o3 = tuple(normalize_word(w) for ln in by_surname for w in ln.split())
    # engrossed-parchment approximation: Hancock first, then states south
    # to north (GA first) — flagged approximation
    rev = list(reversed(states))
    o2 = ("john", "hancock") + tuple(
        w for st, names in rev for w in ([st] + names) if w)
    return {"signers_geo": o1, "signers_parchment_approx": o2,
            "signers_alpha": o3, "signers_namesonly": o4}


def try_fetch_va_constitution() -> tuple[str, ...] | None:
    import re

    from .fetch import _get

    urls = [
        "https://en.wikisource.org/wiki/Constitution_of_Virginia,_1776",
        "https://en.wikisource.org/wiki/Virginia_Constitution_of_1776",
        "https://avalon.law.yale.edu/18th_century/jul05.asp",
    ]
    for url in urls:
        try:
            h = _get(url)
            h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
            text = re.sub(r"<[^>]+>", " ", h)
            toks = tuple(t for t in (normalize_word(w) for w in text.split()) if t)
            joined = " ".join(toks)
            if "house of delegates" in joined and len(toks) > 800:
                return toks
        except Exception:
            continue
    return None


def build_stacks(data) -> dict[str, tuple[str, ...]]:
    pam = data.doi_words
    adj = apply_edits(data.doi_words, load_doi_edits())
    vdr = _tokens("texts/vdr.txt")
    articles = _tokens("texts/articles.txt")
    sig = signers_orderings()
    appendices: dict[str, tuple[str, ...]] = dict(sig)
    appendices["vdr"] = vdr
    appendices["articles"] = articles
    vac = try_fetch_va_constitution()
    if vac:
        appendices["va_constitution"] = vac
    from .corpus import iter_corpus

    for kt in iter_corpus():
        if kt.id == "us_constitution":
            appendices["us_constitution"] = kt.tokens
    stacks = {}
    for bn, base in (("pam", pam), ("adj", adj)):
        for an, app in appendices.items():
            stacks[f"{bn}|{an}"] = (base, app)
    # legacy-style VDR-first stacks
    stacks["vdr|pam|signers_geo"] = (vdr + pam, sig["signers_geo"])
    stacks["vdr|pam|sig|articles"] = (vdr + pam + sig["signers_geo"], articles)
    return stacks


# ---------------------------------------------------------- (a) initials --

NAME_POOL = None


def name_initial_dist() -> dict[str, float]:
    global NAME_POOL
    sig = signers_orderings()["signers_namesonly"]
    from .synth import names_list_plaintext

    extra = []  # first letters from the synthetic period-name pools
    import random as _r

    pool_text = names_list_plaintext(_r.Random(1), 4000)
    counts = Counter(w[0] for w in sig)
    # complementary mass from generic name text starts is unreliable;
    # signers + period first/last names from synth pools:
    from .synth import names_list_plaintext as _n  # noqa
    c = Counter(w[0] for w in sig)
    total = sum(c.values())
    return {ch: (c.get(ch, 0) + 0.5) / (total + 13) for ch in
            "abcdefghijklmnopqrstuvwxyz"}


def initials_llr(letters: list[str], p_name, p_eng) -> float:
    return sum(math.log(p_name.get(ch, 1e-3) / max(p_eng.get(ch, 1e-3), 1e-3))
               for ch in letters)


def high_positions(numbers, base_len: int):
    return [(i, n) for i, n in enumerate(numbers) if n > base_len]


def appendix_letters(numbers, base, app, gap: int):
    out = []
    for i, n in high_positions(numbers, len(base)):
        j = n - len(base) - gap - 1
        out.append((i, app[j][0] if 0 <= j < len(app) else None))
    return out


# -------------------------------------------------- (c) lewis adjudication --

def context_gain(data, kt, pos: int, letter: str, qtab, marg1, marg2) -> float:
    """Does `letter` at C1 position `pos` complete keytable-pinned context
    better than the best alternative letter?"""
    window = []
    for j in range(max(0, pos - 3), min(len(data.cipher1), pos + 4)):
        if j == pos:
            window.append(None)
        else:
            ch = kt.letter(data.cipher1[j])
            window.append(ord(ch) - 97 if ch else WILD)
    idx = window.index(None)

    def score_with(li):
        w = window[:]
        w[idx] = li
        return wildcard_quad_score(w, qtab, marg1, marg2)

    target = score_with(ord(letter) - 97)
    best_alt = max(score_with(li) for li in range(26) if li != ord(letter) - 97)
    return target - best_alt


def main() -> None:
    data = load_beale()
    kt = reconstruct(data)
    quad = Quadgrams.load()
    qtab = flat_quadgram_table(quad)
    marg1, marg2 = build_marginals(qtab)
    stacks = build_stacks(data)
    p_name = name_initial_dist()
    from .scoring import ENGLISH_FREQ

    crit = Criteria("extended-stack", "c1",
                    ("initials LLR significant only above 99th pct of "
                     "max-statistic null over all stacks x gaps",
                     "lewis anecdote survives only above 99th pct of "
                     "best-of-alignment null",
                     "graded supportive/unsupportive, never conclusive"))
    rec = start_run("extended-stack", "c1",
                    {"stacks": sorted(stacks), "gaps": [0, 60]}, criteria=crit)

    print(f"{len(stacks)} stacks; C1 high numbers per base: "
          f"pam={len(high_positions(data.cipher1, 1322))} "
          f"adj={len(high_positions(data.cipher1, 1311))}")

    # (a) initials LLR with best-gap freedom, vs max-statistic null
    real_best = (-1e9, None, None)
    for sname, (base, app) in stacks.items():
        for gap in GAPS:
            letters = [ch for _, ch in
                       appendix_letters(data.cipher1, base, app, gap) if ch]
            if len(letters) < 5:
                continue
            llr = initials_llr(letters, p_name, ENGLISH_FREQ)
            if llr > real_best[0]:
                real_best = (llr, sname, gap)
    print(f"\n(a) best initials LLR: {real_best[0]:.2f} "
          f"({real_best[1]}, gap={real_best[2]})")

    rng = random.Random(7)
    null_max = []
    eng_letters = list(ENGLISH_FREQ)
    eng_weights = list(ENGLISH_FREQ.values())
    for _ in range(1000):
        m = -1e9
        # each null draw gets the same stack x gap freedom: approximate by
        # drawing the max over the same number of (stack,gap) combos with
        # random English-marginal letters of matching counts
        for sname, (base, app) in stacks.items():
            n_letters = len([1 for _, n in
                             high_positions(data.cipher1, len(base))])
            if n_letters < 5:
                continue
            ls = rng.choices(eng_letters, weights=eng_weights, k=n_letters)
            m = max(m, initials_llr(ls, p_name, ENGLISH_FREQ))
        null_max.append(m)
    thr = sorted(null_max)[int(0.99 * len(null_max))]
    verdict_a = "SUPPORTIVE" if real_best[0] > thr else "not supported"
    print(f"    null 99th pct (max-statistic): {thr:.2f} -> {verdict_a}")

    # (c) lewis adjudication
    print("\n(c) 1701->lewis adjudication:")
    lewis_hits = []
    for sname, (base, app) in stacks.items():
        if "signers" not in sname:
            continue
        for gap in GAPS:
            j = 1701 - len(base) - gap - 1
            if 0 <= j < len(app) and app[j] == "lewis":
                T = sum(context_gain(data, kt, i, ch, qtab, marg1, marg2)
                        for i, ch in appendix_letters(
                            data.cipher1, base, app, gap)
                        if ch and data.cipher1[i] != 1701)
                lewis_hits.append((sname, gap, T))
    if not lewis_hits:
        print("    NO stack x gap alignment puts 1701 on 'lewis' — "
              "the legacy anecdote does not reproduce")
        verdict_c = "anecdote does not reproduce"
    else:
        best_T = max(t for _, _, t in lewis_hits)
        null_T = []
        sig_names = signers_orderings()["signers_namesonly"]
        for _ in range(1000):
            names = list(sig_names)
            rng.shuffle(names)
            m = -1e9
            for sname, gap, _ in lewis_hits[:5]:
                base, app = stacks[sname]
                T = sum(context_gain(data, kt, i, names[
                    (data.cipher1[i] - len(base) - gap - 1) % len(names)][0],
                    qtab, marg1, marg2)
                    for i, ch in appendix_letters(data.cipher1, base, app, gap)
                    if ch and data.cipher1[i] != 1701)
                m = max(m, T)
            null_T.append(m)
        thr_T = sorted(null_T)[int(0.99 * len(null_T))]
        verdict_c = ("SURVIVES" if best_T > thr_T else "killed by null")
        print(f"    alignments hitting lewis: {len(lewis_hits)}; "
              f"best completion gain {best_T:.2f} vs null 99th {thr_T:.2f} "
              f"-> {verdict_c}")
        for sname, gap, T in sorted(lewis_hits, key=lambda x: -x[2])[:5]:
            print(f"      {sname} gap={gap}  T={T:+.2f}")

    rec.finish(initials_best=dict(llr=real_best[0], stack=real_best[1],
                                  gap=real_best[2], null99=thr,
                                  verdict=verdict_a),
               lewis=dict(n_alignments=len(lewis_hits), verdict=verdict_c))


if __name__ == "__main__":
    main()
