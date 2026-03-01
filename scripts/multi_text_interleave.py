"""
Track 4: Multi-text interleaving hypothesis.

Tests whether C3 (and C1) alternates between two key texts.
For each pair of texts, tries:
  - every-k interleaving (k=1..12): positions 0,k,2k,... from Text A, rest from Text B
  - block interleaving: first N from A, next N from B, repeat

Bounded: only top 20 texts from single-text sweep + DOI.
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime
from itertools import combinations

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from corpus.keytexts.loader import load_normalized
import re

OUT = Path("output/interleave_test")
OUT.mkdir(parents=True, exist_ok=True)

def get_doi_words():
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    doi = text[start:end + len("honor(1322) .")]
    return [m.group(1) for m in re.finditer(r'(\w[\w\'-]*)\(\d+\)', doi)]


def score_stream(stream, label=""):
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    n = len(letters)
    if n < 10:
        return {"label": label, "len": n, "cov": 0.0, "long": 0, "qg": -99.0, "preview": ""}
    wp = score_word_patterns(letters)
    qg = quadgram_score(letters)
    return {"label": label, "len": n, "cov": wp["word_coverage"],
            "long": wp["long_word_count"], "qg": qg, "preview": letters[:150]}


def interleave_decode(cipher_nums, tokens_a, tokens_b, pattern_fn):
    """Decode where pattern_fn(position) returns True for text A, False for B."""
    stream = ""
    for i, cn in enumerate(cipher_nums):
        idx = cn - 1
        if pattern_fn(i):
            tokens = tokens_a
        else:
            tokens = tokens_b
        if 0 <= idx < len(tokens):
            stream += tokens[idx][0].upper()
        else:
            stream += "?"
    return stream


def main():
    print("=" * 70)
    print("MULTI-TEXT INTERLEAVING TEST")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    c3 = load_cipher(3)
    c1 = load_cipher(1)

    # Get top texts for interleaving: DOI + top candidates from surveys
    # Use texts that are thematically relevant to Beale era
    candidate_ids = [
        "doi",
        "common_sense", "us_constitution", "federalist_papers",
        "notes_virginia", "notes_virginia_jeff",
        "virginia_bill_rights", "virginia_code_1819",
        "letters_jefferson", "king_james_genesis",
        "webb_freemason_monitor", "masonic_trestle",
        "hening_statutes_v1", "preston_illustrations_masonry",
        "anderson_constitutions", "washington_farewell",
        "rights_of_man", "age_of_reason_p1",
        "jeffersons_bible", "marshall_life_wash_sel",
    ]

    # Load tokens
    doi_words = get_doi_words()
    texts = {"doi": doi_words}
    for kid in candidate_ids:
        if kid == "doi":
            continue
        norm = load_normalized(kid)
        if norm:
            texts[kid] = norm["tokens"]

    available = list(texts.keys())
    print(f"Available texts for interleaving: {len(available)}")

    all_results = []
    total = 0

    for cname, cnums in [("c3", c3), ("c1", c1)]:
        c_max = max(cnums)
        eligible_pairs = [(a, b) for a, b in combinations(available, 2)
                          if len(texts[a]) >= c_max and len(texts[b]) >= c_max]
        print(f"\n{cname}: {len(eligible_pairs)} eligible pairs")

        for text_a, text_b in eligible_pairs:
            tokens_a = texts[text_a]
            tokens_b = texts[text_b]

            # Every-k interleaving
            for k in [1, 2, 3, 4, 5, 6, 8, 10, 12]:
                # Positions divisible by k go to text A
                stream = interleave_decode(cnums, tokens_a, tokens_b,
                                           lambda i, k=k: i % (k + 1) < k)
                label = f"{cname}|{text_a}+{text_b}|every_{k}"
                r = score_stream(stream, label)
                all_results.append(r)
                total += 1

            # Alternating (odd/even) — simplest case
            stream = interleave_decode(cnums, tokens_a, tokens_b,
                                       lambda i: i % 2 == 0)
            r = score_stream(stream, f"{cname}|{text_a}+{text_b}|odd_even")
            all_results.append(r)
            total += 1

    # Sort
    for r in all_results:
        r["composite"] = r["cov"] * 100 + r["long"] * 20 + max(0, r["qg"] + 7) * 5

    all_results.sort(key=lambda r: r["composite"], reverse=True)

    signals = [r for r in all_results if r["long"] >= 2 and r["cov"] >= 0.10]

    # Write CSV
    csv_path = OUT / "interleave_ranked.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fields = ["label", "len", "cov", "long", "qg", "composite", "preview"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in all_results[:300]:
            writer.writerow({k: r.get(k, "") for k in fields})

    print(f"\nTotal interleave attempts: {total}")
    print(f"Signals: {len(signals)}")
    print(f"\nTop 15:")
    for i, r in enumerate(all_results[:15]):
        sig = " ***" if r in signals else ""
        print(f"  {i+1:3d}. cov={r['cov']:.4f} long={r['long']} qg={r['qg']:.3f} "
              f"comp={r['composite']:.1f} {r['label'][:70]}{sig}")

    print(f"\nOutputs: {csv_path}")


if __name__ == "__main__":
    main()
