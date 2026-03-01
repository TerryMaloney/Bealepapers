"""
HIGH-VALUE TEST: What if C1's four-digit numbers are merged pairs?

If "1701" was actually "170, 1" (comma lost in transcription), then
C1 becomes 539 numbers with max ~985, structurally identical to C2/C3.

Tests all plausible split strategies and decodes against top key texts.
"""

import re
import sys
import csv
from pathlib import Path
from itertools import product

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from corpus.keytexts.loader import load_normalized

OUT = Path("output/c1_split_test")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "top_streams").mkdir(exist_ok=True)


def get_doi_words():
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    doi = text[start:end + len("honor(1322) .")]
    return [m.group(1) for m in re.finditer(r'(\w[\w\'-]*)\(\d+\)', doi)]


def split_fourdigit(nums, strategy):
    """
    Replace four-digit numbers with two numbers based on split strategy.
    strategy: "1_3" means first 1 digit, last 3 digits
              "2_2" means first 2 digits, last 2 digits
              "3_1" means first 3 digits, last 1 digit
              "keep" means don't split (control)
    """
    result = []
    for n in nums:
        if n >= 1000 and strategy != "keep":
            s = str(n)
            if strategy == "1_3":
                a, b = int(s[0]), int(s[1:])
            elif strategy == "2_2":
                a, b = int(s[:2]), int(s[2:])
            elif strategy == "3_1":
                a, b = int(s[:3]), int(s[3:])
            else:
                result.append(n)
                continue
            if a > 0:
                result.append(a)
            if b > 0:
                result.append(b)
        else:
            result.append(n)
    return result


def score_stream(stream, label=""):
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    n = len(letters)
    if n < 10:
        return {"label": label, "len": n, "cov": 0.0, "long": 0, "qg": -99.0, "preview": ""}
    wp = score_word_patterns(letters)
    qg = quadgram_score(letters)
    return {"label": label, "len": n, "cov": wp["word_coverage"],
            "long": wp["long_word_count"], "qg": qg,
            "preview": letters[:150]}


def main():
    c1 = load_cipher(1)

    doi = get_doi_words()
    doi_adjusted = None
    try:
        from corpus.beale_doi_adjusted import get_adjusted_tokens
        doi_adjusted = get_adjusted_tokens()
    except Exception:
        pass

    print("=" * 70)
    print("C1 FOUR-DIGIT SPLIT TEST")
    print("=" * 70)

    # Show split stats
    for strategy in ["keep", "1_3", "2_2", "3_1"]:
        split = split_fourdigit(c1, strategy)
        print(f"  Strategy {strategy}: {len(split)} numbers, max={max(split)}, "
              f"min={min(split)}, mean={sum(split)/len(split):.0f}")

    # Load key texts for testing
    keytexts = {"doi": doi}
    if doi_adjusted:
        keytexts["doi_adjusted"] = doi_adjusted

    for kid in ["webb_freemason_monitor", "hening_statutes_v1", "hening_statutes_v7",
                "anderson_constitutions", "preston_illustrations_masonry",
                "common_sense", "us_constitution", "notes_virginia",
                "federalist_papers", "king_james_genesis",
                "virginia_code_1819", "letters_jefferson",
                "masonic_trestle", "virginia_bill_rights",
                "rights_of_man", "washington_farewell"]:
        norm = load_normalized(kid)
        if norm:
            keytexts[kid] = norm["tokens"]

    print(f"\nKey texts loaded: {len(keytexts)}")

    all_results = []
    total = 0

    for strategy in ["1_3", "2_2", "3_1"]:
        split_nums = split_fourdigit(c1, strategy)
        split_max = max(split_nums)

        for kid, tokens in keytexts.items():
            tc = len(tokens)
            if tc < split_max:
                continue

            # First letter extraction
            stream = ""
            for cn in split_nums:
                idx = cn - 1
                if 0 <= idx < tc:
                    stream += tokens[idx][0].upper()
                else:
                    stream += "?"

            r = score_stream(stream, f"split_{strategy}|{kid}|first_letter")
            all_results.append(r)
            total += 1

            # Also test with offsets -1, +1
            for offset in [-1, 1]:
                stream = ""
                for cn in split_nums:
                    idx = cn - 1 + offset
                    if 0 <= idx < tc:
                        stream += tokens[idx][0].upper()
                    else:
                        stream += "?"
                r = score_stream(stream, f"split_{strategy}|{kid}|first_letter|off={offset}")
                all_results.append(r)
                total += 1

            # Last letter
            stream = ""
            for cn in split_nums:
                idx = cn - 1
                if 0 <= idx < tc:
                    stream += tokens[idx][-1].upper()
                else:
                    stream += "?"
            r = score_stream(stream, f"split_{strategy}|{kid}|last_letter")
            all_results.append(r)
            total += 1

    # Also test: remove four-digit numbers entirely (truncated C1)
    c1_no4 = [n for n in c1 if n < 1000]
    for kid, tokens in keytexts.items():
        tc = len(tokens)
        if tc < max(c1_no4):
            continue
        stream = ""
        for cn in c1_no4:
            idx = cn - 1
            if 0 <= idx < tc:
                stream += tokens[idx][0].upper()
            else:
                stream += "?"
        r = score_stream(stream, f"no_4digit|{kid}|first_letter")
        all_results.append(r)
        total += 1

    # Sort
    for r in all_results:
        r["composite"] = r["cov"] * 100 + r["long"] * 20 + max(0, r["qg"] + 7) * 5

    all_results.sort(key=lambda r: r["composite"], reverse=True)

    signals = [r for r in all_results if r["long"] >= 2 and r["cov"] >= 0.08]

    # Write CSV
    csv_path = OUT / "c1_split_ranked.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fields = ["label", "len", "cov", "long", "qg", "composite", "preview"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in all_results:
            writer.writerow({k: r.get(k, "") for k in fields})

    # Dump top streams
    for i, r in enumerate(all_results[:10]):
        safe_label = r["label"].replace("|", "_").replace("=", "")[:60]
        sp = OUT / "top_streams" / f"rank{i+1}_{safe_label}.txt"
        with open(sp, "w", encoding="utf-8") as f:
            f.write(f"Label: {r['label']}\n")
            f.write(f"Coverage: {r['cov']:.4f}, Long words: {r['long']}, Quadgram: {r['qg']:.3f}\n\n")
            f.write(r["preview"] + "\n")

    print(f"\nTotal split tests: {total}")
    print(f"Signals: {len(signals)}")
    print(f"\nTop 20:")
    for i, r in enumerate(all_results[:20]):
        sig = " *** SIGNAL ***" if r in signals else ""
        print(f"  {i+1:3d}. cov={r['cov']:.4f} long={r['long']} qg={r['qg']:.3f} "
              f"len={r['len']} {r['label'][:60]}{sig}")

    print(f"\nOutputs: {csv_path}")


if __name__ == "__main__":
    main()
