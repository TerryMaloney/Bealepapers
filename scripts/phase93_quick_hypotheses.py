"""
Phase 93: Quick tests for hypotheses that were never tried.
H11: Remove outlier numbers
H12: Reversed word indexing
H13: Bigram/trigram extraction
H14: Modular wrap-around
H16: C2 hidden message analysis
H9: Occurrence-dependent extraction
"""

import re
import sys
import csv
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from corpus.keytexts.loader import load_normalized

OUT = Path("output/phase93")
(OUT / "quick_hypothesis_streams").mkdir(parents=True, exist_ok=True)

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
        return {"label": label, "len": n, "cov": 0, "long": 0, "qg": -99, "preview": ""}
    wp = score_word_patterns(letters)
    qg = quadgram_score(letters)
    return {"label": label, "len": n, "cov": wp["word_coverage"],
            "long": wp["long_word_count"], "qg": qg,
            "preview": letters[:150]}


def main():
    c1 = load_cipher(1)
    c2 = load_cipher(2)
    c3 = load_cipher(3)
    doi = get_doi_words()
    doi_len = len(doi)

    results = []

    # Load all eligible key texts
    keytexts = {"doi": doi}
    for kid in ["webb_freemason_monitor", "anderson_constitutions", "hening_statutes_v1",
                "hening_statutes_v7", "preston_illustrations_masonry",
                "common_sense", "us_constitution", "notes_virginia",
                "federalist_papers", "king_james_genesis"]:
        norm = load_normalized(kid)
        if norm:
            keytexts[kid] = norm["tokens"]

    print("=" * 70)
    print("QUICK HYPOTHESIS TESTS")
    print("=" * 70)

    # ===========================================
    # H14: Modular wrap-around (NEVER TESTED)
    # ===========================================
    print("\n[H14] Modular wrap-around...")
    for cname, cnums in [("c1", c1), ("c3", c3)]:
        for kid, tokens in keytexts.items():
            tc = len(tokens)
            if tc < 100:
                continue
            stream = ""
            for cn in cnums:
                idx = (cn - 1) % tc
                stream += tokens[idx][0].upper()
            r = score_stream(stream, f"H14|{cname}|{kid}|mod_{tc}")
            results.append(r)
            if r["cov"] > 0.03 or r["long"] > 0:
                print(f"  {r['label']}: cov={r['cov']:.4f} long={r['long']}")

    # ===========================================
    # H12: Reversed word indexing (NEVER TESTED)
    # ===========================================
    print("\n[H12] Reversed word indexing...")
    for cname, cnums in [("c1", c1), ("c3", c3)]:
        for kid, tokens in keytexts.items():
            tc = len(tokens)
            if tc < max(cnums):
                continue
            rev_tokens = list(reversed(tokens))
            stream = ""
            for cn in cnums:
                idx = cn - 1
                if 0 <= idx < tc:
                    stream += rev_tokens[idx][0].upper()
                else:
                    stream += "?"
            r = score_stream(stream, f"H12|{cname}|{kid}|reversed")
            results.append(r)
            if r["cov"] > 0.03 or r["long"] > 0:
                print(f"  {r['label']}: cov={r['cov']:.4f} long={r['long']}")

    # ===========================================
    # H13: Bigram/trigram extraction (NEVER TESTED)
    # ===========================================
    print("\n[H13] Bigram/trigram extraction...")
    for cname, cnums in [("c1", c1), ("c3", c3)]:
        for kid, tokens in keytexts.items():
            tc = len(tokens)
            if tc < max(cnums):
                continue
            for n_letters, label in [(2, "bigram"), (3, "trigram")]:
                stream = ""
                for cn in cnums:
                    idx = cn - 1
                    if 0 <= idx < tc:
                        w = tokens[idx]
                        stream += w[:n_letters].upper()
                    else:
                        stream += "?" * n_letters
                r = score_stream(stream, f"H13|{cname}|{kid}|{label}")
                results.append(r)
                if r["cov"] > 0.05 or r["long"] > 0:
                    print(f"  {r['label']}: cov={r['cov']:.4f} long={r['long']}")

    # ===========================================
    # H11: Remove outlier numbers (NEVER TESTED)
    # ===========================================
    print("\n[H11] Remove outlier four-digit numbers from C1...")
    c1_filtered = [n for n in c1 if n < 1000]
    print(f"  C1 original: {len(c1)} numbers, filtered (< 1000): {len(c1_filtered)}")
    print(f"  Removed {len(c1) - len(c1_filtered)} four-digit numbers")

    for kid, tokens in keytexts.items():
        tc = len(tokens)
        if tc < max(c1_filtered, default=0):
            continue
        stream = ""
        for cn in c1_filtered:
            idx = cn - 1
            if 0 <= idx < tc:
                stream += tokens[idx][0].upper()
            else:
                stream += "?"
        r = score_stream(stream, f"H11|c1_no4digit|{kid}|first_letter")
        results.append(r)
        if r["cov"] > 0.03 or r["long"] > 0:
            print(f"  {r['label']}: cov={r['cov']:.4f} long={r['long']}")

    # Also try: remove numbers above 500 (since 88.7% are below 726)
    c1_tight = [n for n in c1 if n <= 500]
    print(f"  C1 tight (<=500): {len(c1_tight)} numbers")
    stream = ""
    for cn in c1_tight:
        idx = cn - 1
        if 0 <= idx < doi_len:
            stream += doi[idx][0].upper()
        else:
            stream += "?"
    r = score_stream(stream, "H11|c1_le500|doi|first_letter")
    results.append(r)
    print(f"  {r['label']}: cov={r['cov']:.4f} long={r['long']}")

    # ===========================================
    # H9: Occurrence-dependent extraction (NEVER TESTED)
    # ===========================================
    print("\n[H9] Occurrence-dependent extraction...")
    for cname, cnums in [("c1", c1), ("c3", c3)]:
        for kid, tokens in keytexts.items():
            tc = len(tokens)
            if tc < max(cnums):
                continue
            occurrence_count = Counter()
            stream = ""
            for cn in cnums:
                idx = cn - 1
                occurrence_count[cn] += 1
                occ = occurrence_count[cn]
                if 0 <= idx < tc:
                    w = tokens[idx]
                    letter_idx = (occ - 1) % len(w)
                    stream += w[letter_idx].upper()
                else:
                    stream += "?"
            r = score_stream(stream, f"H9|{cname}|{kid}|occurrence_dependent")
            results.append(r)
            if r["cov"] > 0.03 or r["long"] > 0:
                print(f"  {r['label']}: cov={r['cov']:.4f} long={r['long']}")

    # ===========================================
    # H16: C2 hidden message analysis
    # ===========================================
    print("\n[H16] C2 hidden message analysis...")
    c2_decoded = ""
    for cn in c2:
        idx = cn - 1
        if 0 <= idx < doi_len:
            c2_decoded += doi[idx][0].upper()
        else:
            c2_decoded += "?"

    c2_full_words = []
    for cn in c2:
        idx = cn - 1
        if 0 <= idx < doi_len:
            c2_full_words.append(doi[idx])

    # Acrostic: first letter of each "sentence" (every 20 words as proxy)
    for chunk_size in [10, 15, 20, 25, 30, 50]:
        acrostic = ""
        for i in range(0, len(c2_full_words), chunk_size):
            if i < len(c2_full_words):
                acrostic += c2_full_words[i][0].upper()
        r = score_stream(acrostic, f"H16|c2_acrostic_every{chunk_size}")
        results.append(r)
        if r["cov"] > 0.05 or r["long"] > 0:
            print(f"  {r['label']}: cov={r['cov']:.4f} long={r['long']}")

    # Every Nth word of C2 decoded text
    for n in [2, 3, 4, 5, 7, 10]:
        stream = ""
        for i in range(0, len(c2_full_words), n):
            stream += c2_full_words[i][0].upper()
        r = score_stream(stream, f"H16|c2_everyNth_n={n}")
        results.append(r)

    # First letter of each word in C2 plaintext (the actual decoded paragraph)
    print(f"  C2 decoded first 80 letters: {c2_decoded[:80]}")
    print(f"  C2 decoded first 30 words: {' '.join(c2_full_words[:30])}")

    # ===========================================
    # SUMMARY
    # ===========================================
    results.sort(key=lambda r: r["cov"] * 100 + r["long"] * 20 + max(0, r["qg"] + 7) * 5, reverse=True)

    csv_path = OUT / "quick_hypotheses_ranked.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fields = ["label", "len", "cov", "long", "qg", "preview"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r[k] for k in fields})

    signals = [r for r in results if r["long"] >= 2 and r["cov"] >= 0.08]
    print(f"\nTotal quick tests: {len(results)}")
    print(f"Signals: {len(signals)}")
    print(f"\nTop 20:")
    for i, r in enumerate(results[:20]):
        sig = " ***" if r in signals else ""
        print(f"  {i+1:3d}. cov={r['cov']:.4f} long={r['long']} qg={r['qg']:.3f} {r['label'][:65]}{sig}")

    # Dump top 5 streams
    for i, r in enumerate(results[:5]):
        sp = OUT / "quick_hypothesis_streams" / f"rank{i+1}.txt"
        with open(sp, "w", encoding="utf-8") as f:
            f.write(f"Label: {r['label']}\n")
            f.write(f"Coverage: {r['cov']:.4f}, Long words: {r['long']}, Quadgram: {r['qg']:.3f}\n\n")
            f.write(r["preview"] + "\n")


if __name__ == "__main__":
    main()
