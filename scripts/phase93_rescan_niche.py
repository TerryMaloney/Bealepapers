"""
Phase 93: Re-scan corrected niche texts (post HTML-fix) with all extraction
rules + sequence transforms. This is the scan that should have been Phase 92
but was invalidated by HTML contamination.
"""

import csv
import json
import sys
import math
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from corpus.keytexts.loader import load_normalized

OUT = Path("output/phase93")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "top_streams_niche").mkdir(exist_ok=True)

NICHE_IDS = [
    "webb_freemason_monitor",
    "anderson_constitutions",
    "hening_statutes_v1",
    "hening_statutes_v7",
    "preston_illustrations_masonry",
]

EXTRACTORS = {
    "first_letter": lambda w: w[0].upper() if w else "?",
    "second_letter": lambda w: w[1].upper() if len(w) > 1 else w[0].upper() if w else "?",
    "third_letter": lambda w: w[2].upper() if len(w) > 2 else w[0].upper() if w else "?",
    "last_letter": lambda w: w[-1].upper() if w else "?",
    "middle_letter": lambda w: w[len(w)//2].upper() if w else "?",
}


def extract_consonant(word, first=True):
    consonants = "BCDFGHJKLMNPQRSTVWXYZ"
    w = word.upper()
    if first:
        for c in w:
            if c in consonants:
                return c
    else:
        for c in reversed(w):
            if c in consonants:
                return c
    return w[0] if w else "?"


def decode_basic(cipher_nums, tokens, extractor_fn):
    stream = ""
    tc = len(tokens)
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < tc:
            stream += extractor_fn(tokens[idx])
        else:
            stream += "?"
    return stream


def decode_offset(cipher_nums, tokens, offset, extractor_fn):
    stream = ""
    tc = len(tokens)
    for cn in cipher_nums:
        idx = cn - 1 + offset
        if 0 <= idx < tc:
            stream += extractor_fn(tokens[idx])
        else:
            stream += "?"
    return stream


def columnar_reorder(nums, width, serpentine=False):
    n = len(nums)
    rows = math.ceil(n / width)
    grid = [None] * (rows * width)
    for i, v in enumerate(nums):
        grid[i] = v
    reordered = []
    for col in range(width):
        for row in range(rows):
            if serpentine and col % 2 == 1:
                r = rows - 1 - row
            else:
                r = row
            idx = r * width + col
            if idx < n and grid[idx] is not None:
                reordered.append(grid[idx])
    return reordered


def score_stream(stream, label=""):
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    n = len(letters)
    if n < 10:
        return {"label": label, "len": n, "cov": 0.0, "long": 0, "qg": -99.0, "preview": "", "signal": False}
    wp = score_word_patterns(letters)
    qg = quadgram_score(letters)
    sig = wp["long_word_count"] >= 2 and wp["word_coverage"] >= 0.08
    return {"label": label, "len": n, "cov": wp["word_coverage"],
            "long": wp["long_word_count"], "qg": qg,
            "preview": letters[:120], "signal": sig}


def main():
    print("=" * 70)
    print("PHASE 93: RE-SCAN CORRECTED NICHE TEXTS")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    c1 = load_cipher(1)
    c3 = load_cipher(3)

    # Load calibration thresholds
    cal_path = Path("output/phase92/calibration.json")
    if cal_path.exists():
        with open(cal_path) as f:
            cal = json.load(f)
        cov_min = cal.get("coverage_min", 0.10)
        long_min = cal.get("long_words_min", 2)
        qg_min = cal.get("quadgram_min", -6.5)
        print(f"Loaded adaptive thresholds: cov>={cov_min:.3f}, long>={long_min}, qg>={qg_min:.2f}")
    else:
        cov_min, long_min, qg_min = 0.10, 2, -6.5
        print("Using default thresholds (calibration not found)")

    # Load niche texts
    texts = {}
    for kid in NICHE_IDS:
        norm = load_normalized(kid)
        if norm:
            tc = norm["token_count"]
            texts[kid] = norm["tokens"]
            c1_ok = tc >= max(c1)
            c3_ok = tc >= max(c3)
            print(f"  {kid}: {tc} tokens (C1={'OK' if c1_ok else 'SHORT'}, C3={'OK' if c3_ok else 'SHORT'})")

    all_results = []
    total = 0

    for cname, cnums in [("c1", c1), ("c3", c3)]:
        for kid, tokens in texts.items():
            if len(tokens) < max(cnums):
                continue

            # Basic extractors
            for ename, efn in EXTRACTORS.items():
                stream = decode_basic(cnums, tokens, efn)
                r = score_stream(stream, f"{cname}|{kid}|basic|{ename}")
                r["cipher"] = cname
                all_results.append(r)
                total += 1

            # First/last consonant
            for ctype in ["first_consonant", "last_consonant"]:
                is_first = ctype == "first_consonant"
                stream = decode_basic(cnums, tokens, lambda w, f=is_first: extract_consonant(w, f))
                r = score_stream(stream, f"{cname}|{kid}|basic|{ctype}")
                r["cipher"] = cname
                all_results.append(r)
                total += 1

            # Position-dependent: letter index = (position_in_cipher mod word_length)
            stream = ""
            for i, cn in enumerate(cnums):
                idx = cn - 1
                if 0 <= idx < len(tokens):
                    w = tokens[idx]
                    li = i % max(len(w), 1)
                    stream += w[li].upper()
                else:
                    stream += "?"
            r = score_stream(stream, f"{cname}|{kid}|pos_mod_wordlen")
            r["cipher"] = cname
            all_results.append(r)
            total += 1

            # Additive offsets (DOI was tested with -500..+500; niche with targeted set)
            for offset in list(range(-50, 51, 5)) + [-100, 100, -200, 200]:
                stream = decode_offset(cnums, tokens, offset, EXTRACTORS["first_letter"])
                r = score_stream(stream, f"{cname}|{kid}|offset={offset}|first_letter")
                r["cipher"] = cname
                all_results.append(r)
                total += 1

            # Columnar transposition
            for width in [5, 7, 10, 13, 15, 17, 20]:
                for serp in [False, True]:
                    reordered = columnar_reorder(cnums, width, serpentine=serp)
                    stream = decode_basic(reordered, tokens, EXTRACTORS["first_letter"])
                    s = "serp" if serp else "flat"
                    r = score_stream(stream, f"{cname}|{kid}|col_w={width}_{s}|first_letter")
                    r["cipher"] = cname
                    all_results.append(r)
                    total += 1

            # Digit-split: various ways to split number into (word_idx, letter_idx)
            for split_name, split_fn in [
                ("n_div10_mod10", lambda n: (n // 10, n % 10)),
                ("n_div100_mod100", lambda n: (n // 100, n % 100)),
                ("digsum_mod_wlen", lambda n: (n, sum(int(d) for d in str(n)))),
                ("last_digit", lambda n: (n, n % 10)),
            ]:
                stream = ""
                for cn in cnums:
                    if split_name in ("digsum_mod_wlen", "last_digit"):
                        widx = cn - 1
                        if 0 <= widx < len(tokens):
                            w = tokens[widx]
                            _, letter_hint = split_fn(cn)
                            if split_name == "digsum_mod_wlen":
                                li = letter_hint % max(len(w), 1)
                            else:
                                li = letter_hint % max(len(w), 1)
                            stream += w[li].upper()
                        else:
                            stream += "?"
                    else:
                        widx, lidx = split_fn(cn)
                        widx -= 1
                        if 0 <= widx < len(tokens):
                            w = tokens[widx]
                            li = lidx % max(len(w), 1) if lidx < len(w) else 0
                            stream += w[li].upper()
                        else:
                            stream += "?"
                r = score_stream(stream, f"{cname}|{kid}|dsplit|{split_name}")
                r["cipher"] = cname
                all_results.append(r)
                total += 1

    # Sort by composite score
    for r in all_results:
        r["composite"] = r["cov"] * 100 + r["long"] * 20 + max(0, r["qg"] + 7) * 5

    all_results.sort(key=lambda r: r["composite"], reverse=True)

    # Write CSV
    csv_path = OUT / "niche_rescan_ranked.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fields = ["label", "cipher", "len", "cov", "long", "qg", "composite", "signal", "preview"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in all_results:
            writer.writerow({k: r.get(k, "") for k in fields})

    # Dump top streams
    for i, r in enumerate(all_results[:20]):
        stream_path = OUT / "top_streams_niche" / f"rank{i+1}_{r['label'].replace('|','_')[:60]}.txt"
        with open(stream_path, "w", encoding="utf-8") as f:
            f.write(f"Label: {r['label']}\n")
            f.write(f"Coverage: {r['cov']:.4f}, Long words: {r['long']}, Quadgram: {r['qg']:.3f}\n")
            f.write(f"Signal: {r['signal']}\n\n")
            f.write(r["preview"] + "\n")

    # Summary
    signals = [r for r in all_results if r["signal"]]
    print(f"\nTotal attempts: {total}")
    print(f"Signals found: {len(signals)}")
    print(f"\nTop 15 results:")
    for i, r in enumerate(all_results[:15]):
        sig_marker = " ***" if r["signal"] else ""
        print(f"  {i+1:3d}. cov={r['cov']:.4f} long={r['long']} qg={r['qg']:.3f} "
              f"comp={r['composite']:.1f} {r['label'][:65]}{sig_marker}")

    if signals:
        print(f"\n*** SIGNAL DETECTED in {len(signals)} candidates! ***")
        for s in signals:
            print(f"  {s['label']}: cov={s['cov']:.4f} long={s['long']}")
    else:
        print(f"\nNO SIGNAL across {total} attempts on corrected niche texts.")

    print(f"\nOutputs: {csv_path}")


if __name__ == "__main__":
    main()
