"""Survey/deed-notation language model and the C1 survey attack.

Hypothesis (user-driven): C1 is "the locality of the vault" — an 1820s
locality description is plausibly metes-and-bounds / surveyor language
("beginning at a white oak thence north thirty two degrees east forty
poles..."), heavily abbreviated and number-dense. Such text defeats
ordinary English language models while being exactly what a recipient
could follow. This module builds a quadgram model of period survey
language (real samples mined from Hening's statutes land grants +
template-generated metes-and-bounds), validates that it separates survey
text from prose, then asks three questions:

  1. Does C1's keyed decode look more like survey notation than English,
     relative to shuffles?  (LM-comparison verdict)
  2. Does any corpus key text produce a survey-like decode of C1?
     (re-sweep under the survey LM)
  3. Where do survey words fit C1's verified pins better than chance?
     (the "one word as a ping" list, human-reviewable)

Run:  python -m beale.exp_survey
"""

from __future__ import annotations

import json
import math
import random
import re
import statistics
from array import array
from collections import Counter
from pathlib import Path

from .data import load_beale
from .keytable import reconstruct
from .runlog import Criteria, start_run

# ---------------------------------------------------------------- lexicon --

DIRECTIONS = ["north", "south", "east", "west", "northeast", "northwest",
              "southeast", "southwest", "northerly", "southerly", "easterly",
              "westerly", "n", "s", "e", "w", "ne", "nw", "se", "sw"]
UNITS = ["poles", "pole", "perches", "chains", "links", "rods", "paces",
         "feet", "foot", "yards", "miles", "degrees", "deg", "minutes"]
NUMBERS = ["one", "two", "three", "four", "five", "six", "seven", "eight",
           "nine", "ten", "eleven", "twelve", "fifteen", "twenty",
           "twentyfive", "thirty", "thirtytwo", "forty", "fifty", "sixty",
           "eighty", "hundred"]
LANDMARKS = ["white oak", "red oak", "black oak", "spanish oak", "hickory",
             "pine", "poplar", "chestnut", "walnut", "gum", "dogwood",
             "stone", "rock", "large rock", "creek", "branch", "run",
             "spring", "ford", "ridge", "gap", "hollow", "knob", "corner",
             "stake", "pointers", "mouth", "fork", "bank", "road", "path",
             "line", "house", "cabin", "mill", "tavern", "plantation",
             "survey", "patent", "tract"]
CONNECTORS = ["beginning at", "thence", "running thence", "to a", "to the",
              "near the", "under a", "by the", "along the", "crossing the",
              "at the foot of", "on the side of", "binding on", "with the",
              "same course", "down the", "up the", "containing"]

SURVEY_CRIBS = sorted(set(
    [w for w in DIRECTIONS if len(w) >= 4]
    + [w for w in UNITS if len(w) >= 4]
    + [w for w in NUMBERS if len(w) >= 4]
    + [w.replace(" ", "") for w in LANDMARKS if len(w.replace(" ", "")) >= 4]
    + ["thence", "beginning", "containing", "neart", "undera"]
))

_KEYWORDS = re.compile(
    r"\b(thence|poles|perches|chains|degrees|acres|beginning|courses)\b")


def _mined_survey_text(max_chars: int = 400_000) -> str:
    """Windows around survey keywords in Hening's statutes (period land
    law full of metes-and-bounds descriptions)."""
    out = []
    total = 0
    for name in ("hening_statutes_v1.json", "hening_statutes_v7.json",
                 "virginia_code_1819.json"):
        p = Path("corpus/keytexts/normalized") / name
        if not p.exists():
            continue
        toks = json.loads(p.read_text(encoding="utf-8"))["tokens"]
        i = 0
        while i < len(toks):
            if _KEYWORDS.fullmatch(toks[i] or ""):
                window = toks[max(0, i - 25): i + 25]
                out.append("".join(window))
                total += sum(len(w) for w in window)
                i += 25
                if total > max_chars:
                    return " ".join(out)
            i += 1
    return " ".join(out)


def _template_survey_text(rng: random.Random, n_calls: int = 3000) -> str:
    """Generated metes-and-bounds in the standard period formula."""
    out = []
    for _ in range(n_calls):
        call = rng.choice([
            "{c} {d} {num} {u} to a {lm}",
            "thence {d} {num} degrees {d2} {num2} {u} to a {lm}",
            "beginning at a {lm} {c} {d} {num} {u}",
            "{c} {lm} thence {d} {num} {u}",
        ]).format(
            c=rng.choice(CONNECTORS), d=rng.choice(DIRECTIONS[:12]),
            d2=rng.choice(DIRECTIONS[:4]), num=rng.choice(NUMBERS),
            num2=rng.choice(NUMBERS), u=rng.choice(UNITS[:8]),
            lm=rng.choice(LANDMARKS),
        )
        out.append(call.replace(" ", ""))
    return " ".join(out)


def survey_quadgrams() -> array:
    """26^4 log-prob table from mined + generated survey text."""
    rng = random.Random(11)
    stream = re.sub(r"[^a-z]", "",
                    (_mined_survey_text() + _template_survey_text(rng)))
    counts: Counter = Counter()
    idx = [ord(c) - 97 for c in stream]
    for i in range(len(idx) - 3):
        counts[((idx[i] * 26 + idx[i + 1]) * 26 + idx[i + 2]) * 26
               + idx[i + 3]] += 1
    total = sum(counts.values())
    tab = array("f", [math.log10(0.01 / total)]) * (26 ** 4)
    for q, c in counts.items():
        tab[q] = math.log10(c / total)
    return tab


def stream_score(text: str, tab: array) -> float:
    t = re.sub(r"[^a-z]", "", text.lower())
    idx = [ord(c) - 97 for c in t]
    if len(idx) < 4:
        return -99.0
    s = sum(tab[((idx[i] * 26 + idx[i + 1]) * 26 + idx[i + 2]) * 26
                + idx[i + 3]] for i in range(len(idx) - 3))
    return s / (len(idx) - 3)


# ------------------------------------------------------------ experiment --

def lm_verdict(decode_letters: list[str | None], tab_survey, tab_eng,
               numbers, n_null=60, seed=5) -> dict:
    """Survey-vs-English preference of a keyed decode, vs shuffled nulls."""
    known = "".join(c for c in decode_letters if c)
    pref = stream_score(known, tab_survey) - stream_score(known, tab_eng)
    rng = random.Random(seed)
    base = []
    letters = [c for c in decode_letters if c]
    for _ in range(n_null):
        rng.shuffle(letters)
        t = "".join(letters)
        base.append(stream_score(t, tab_survey) - stream_score(t, tab_eng))
    mu, sd = statistics.mean(base), statistics.stdev(base)
    return {"preference": pref, "null_mu": mu,
            "z": (pref - mu) / sd if sd else 0.0}


def crib_pings(numbers, kt, cribs, min_pinned=3) -> list[tuple]:
    """Placements where a survey word agrees with >=min_pinned verified
    pins and contradicts none — human-reviewable signal candidates."""
    pings = []
    pins = [kt.letter(n) for n in numbers]
    for crib in cribs:
        L = len(crib)
        for s in range(len(numbers) - L + 1):
            hits = 0
            ok = True
            seen: dict[int, str] = {}
            for j, ch in enumerate(crib):
                p = pins[s + j]
                n = numbers[s + j]
                if p is not None:
                    if p != ch:
                        ok = False
                        break
                    hits += 1
                if n in seen and seen[n] != ch:
                    ok = False
                    break
                seen[n] = ch
            if ok and hits >= min_pinned:
                pings.append((crib, s, hits, L))
    pings.sort(key=lambda x: (-x[2], x[0]))
    return pings


def ping_null_rate(numbers, kt, cribs, min_pinned, n_null=40, seed=9):
    """How many pings does chance produce? Same search on letter-shuffled
    pin tables (preserves pin density, kills letter identities)."""
    rng = random.Random(seed)
    letters = [e.letter for e in kt.entries.values()]
    nums = list(kt.entries)
    counts = []
    for _ in range(n_null):
        rng.shuffle(letters)
        fake = dict(zip(nums, letters))

        class FakeKT:
            def letter(self, n, _f=fake):
                return _f.get(n)

        counts.append(len(crib_pings(numbers, FakeKT(), cribs, min_pinned)))
    return statistics.mean(counts), statistics.stdev(counts)


def main() -> None:
    from .homophonic import flat_quadgram_table
    from .ngrams import Quadgrams

    data = load_beale()
    kt = reconstruct(data)
    quad = Quadgrams.load()
    tab_eng = flat_quadgram_table(quad)
    print("building survey LM...", flush=True)
    tab_survey = survey_quadgrams()

    # LM validation: separation on held-out samples
    rng = random.Random(99)
    sample_survey = _template_survey_text(rng, 80)
    sample_prose = "".join(data.doi_words[200:400])
    s_s = stream_score(sample_survey, tab_survey) - stream_score(sample_survey, tab_eng)
    s_p = stream_score(sample_prose, tab_survey) - stream_score(sample_prose, tab_eng)
    print(f"LM validation: survey-sample preference {s_s:+.3f}, "
          f"prose-sample preference {s_p:+.3f} "
          f"-> {'PASS' if s_s > 0.15 and s_p < 0 else 'FAIL'}")

    crit = Criteria("survey-c1", "c1",
                    ("LM verdict needs |z|>=4 vs shuffled decode",
                     "crib pings reported with chance rate; a ping is a "
                     "LEAD for human review, not a finding",))
    rec = start_run("survey-c1", "c1", {"cribs": SURVEY_CRIBS}, criteria=crit)

    # 1. LM-comparison verdict on C1's keyed decode (and C2 sanity)
    for name, nums in [("C1", data.cipher1), ("C2 (sanity)", data.cipher2),
                       ("C3", data.cipher3)]:
        dec = [kt.letter(n) for n in nums]
        v = lm_verdict(dec, tab_survey, tab_eng, nums)
        print(f"{name}: survey-vs-English preference {v['preference']:+.3f} "
              f"(shuffle {v['null_mu']:+.3f})  z={v['z']:+.2f}")

    # 2. corpus re-sweep of C1 under the survey LM
    print("\ncorpus re-sweep of C1 decodes under survey LM (top 5):")
    from .corpus import iter_corpus
    rows = []
    for ktext in iter_corpus(min_tokens=2906):
        letters = [ktext.tokens[n - 1][0] if n <= len(ktext.tokens) else None
                   for n in data.cipher1]
        known = "".join(c for c in letters if c)
        rows.append((stream_score(known, tab_survey), ktext.id))
    rows.sort(reverse=True)
    for s, kid in rows[:5]:
        print(f"  {s:7.3f}  {kid}")
    # null line for the sweep
    shuf = list(data.cipher1)
    random.Random(3).shuffle(shuf)
    null_rows = []
    for ktext in list(iter_corpus(min_tokens=2906))[:20]:
        letters = [ktext.tokens[n - 1][0] if n <= len(ktext.tokens) else None
                   for n in shuf]
        null_rows.append(stream_score("".join(c for c in letters if c),
                                      tab_survey))
    print(f"  (shuffled-C1 reference over 20 docs: best {max(null_rows):.3f})")

    # 3. survey-crib pings against verified pins
    print(f"\nsurvey-crib pings (>=3 verified pins matched, 0 conflicts), "
          f"{len(SURVEY_CRIBS)} cribs:")
    pings = crib_pings(list(data.cipher1), kt, SURVEY_CRIBS)
    mu, sd = ping_null_rate(list(data.cipher1), kt, SURVEY_CRIBS, 3)
    print(f"  C1: {len(pings)} pings vs chance {mu:.1f}±{sd:.1f}")
    for crib, s, hits, L in pings[:12]:
        print(f"    '{crib}' @ {s} ({hits}/{L} pinned letters match)")
    rec.finish(n_pings=len(pings), ping_null=(mu, sd),
               top_pings=pings[:20])


if __name__ == "__main__":
    main()
