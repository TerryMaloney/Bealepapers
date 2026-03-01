"""
C1 Dragnet v2: Sweep all eligible texts against Cipher 1.
Same battery as C3 sweep but with C1 numbers (max=2906).
"""

import csv
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from corpus.keytexts.loader import load_all_keytexts

OUT = Path("output/c1_dragnet_v2")
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "top_streams").mkdir(exist_ok=True)


EXTRACTORS = {
    "first": lambda w: w[0].upper() if w else "?",
    "last": lambda w: w[-1].upper() if w else "?",
    "second": lambda w: w[1].upper() if len(w) > 1 else w[0].upper() if w else "?",
    "middle": lambda w: w[len(w)//2].upper() if w else "?",
}

CONSONANTS = set("BCDFGHJKLMNPQRSTVWXYZ")

def first_consonant(w):
    for c in w.upper():
        if c in CONSONANTS:
            return c
    return w[0].upper() if w else "?"


def decode(cipher_nums, tokens, extractor_fn, offset=0):
    tc = len(tokens)
    stream = ""
    valid = 0
    for cn in cipher_nums:
        idx = cn - 1 + offset
        if 0 <= idx < tc:
            stream += extractor_fn(tokens[idx])
            valid += 1
        else:
            stream += "?"
    return stream, valid


def score_stream(stream, label=""):
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    n = len(letters)
    if n < 10:
        return {"label": label, "len": n, "cov": 0.0, "long": 0, "qg": -99.0,
                "preview": "", "signal": False}
    wp = score_word_patterns(letters)
    qg = quadgram_score(letters)
    return {"label": label, "len": n, "cov": wp["word_coverage"],
            "long": wp["long_word_count"], "qg": qg,
            "preview": letters[:150], "signal": False}


def main():
    print("=" * 70)
    print("C1 DRAGNET v2: Sweep")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    c1 = load_cipher(1)
    c1_max = max(c1)
    print(f"C1: {len(c1)} numbers, max={c1_max}")

    cal_path = Path("output/phase92/calibration.json")
    if cal_path.exists():
        with open(cal_path) as f:
            cal = json.load(f)
        cov_min = cal.get("coverage_min", 0.10)
        long_min = cal.get("long_words_min", 2)
    else:
        cov_min, long_min = 0.10, 2

    all_texts = load_all_keytexts(min_tokens=c1_max)
    print(f"Eligible texts: {len(all_texts)}")

    all_results = []
    total = 0

    for i, text_data in enumerate(all_texts):
        kid = text_data["id"]
        tokens = text_data["tokens"]

        if i % 20 == 0:
            print(f"  Processing {i+1}/{len(all_texts)} ({kid})...")

        for ename, efn in EXTRACTORS.items():
            for offset in [0, -1, 1]:
                stream, valid = decode(c1, tokens, efn, offset)
                if valid < len(c1) * 0.8:
                    continue
                off_label = f"+{offset}" if offset > 0 else str(offset)
                r = score_stream(stream, f"{kid}|{ename}|off={off_label}")
                if r["long"] >= long_min and r["cov"] >= cov_min:
                    r["signal"] = True
                all_results.append(r)
                total += 1

        for offset in [0, -1, 1]:
            stream, valid = decode(c1, tokens, first_consonant, offset)
            if valid < len(c1) * 0.8:
                continue
            off_label = f"+{offset}" if offset > 0 else str(offset)
            r = score_stream(stream, f"{kid}|first_cons|off={off_label}")
            if r["long"] >= long_min and r["cov"] >= cov_min:
                r["signal"] = True
            all_results.append(r)
            total += 1

    for r in all_results:
        r["composite"] = r["cov"] * 100 + r["long"] * 20 + max(0, r["qg"] + 7) * 5

    all_results.sort(key=lambda r: r["composite"], reverse=True)

    signals = [r for r in all_results if r["signal"]]

    csv_path = OUT / "c1_sweep_ranked.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fields = ["label", "len", "cov", "long", "qg", "composite", "signal", "preview"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in all_results[:500]:
            writer.writerow({k: r.get(k, "") for k in fields})

    for i, r in enumerate(all_results[:20]):
        safe_label = r["label"].replace("|", "_").replace("=", "")[:60]
        sp = OUT / "top_streams" / f"c1_rank{i+1}_{safe_label}.txt"
        with open(sp, "w", encoding="utf-8") as f:
            f.write(f"Label: {r['label']}\n")
            f.write(f"Coverage: {r['cov']:.4f}, Long words: {r['long']}, Quadgram: {r['qg']:.3f}\n")
            f.write(f"Composite: {r['composite']:.2f}, Signal: {r['signal']}\n\n")
            f.write(r["preview"] + "\n")

    print(f"\nTotal attempts: {total}")
    print(f"Signals: {len(signals)}")
    print(f"\nTop 15:")
    for i, r in enumerate(all_results[:15]):
        sig = " *** SIGNAL ***" if r["signal"] else ""
        print(f"  {i+1:3d}. cov={r['cov']:.4f} long={r['long']} qg={r['qg']:.3f} "
              f"comp={r['composite']:.1f} {r['label'][:60]}{sig}")

    if not signals:
        print(f"\nNO SIGNAL across {total} attempts on {len(all_texts)} texts.")
    print(f"\nOutputs: {csv_path}")


if __name__ == "__main__":
    main()
