"""
Phase 101 Task 2B: Alphabetized keystream test.

Build alternative keystreams from validated DOI tokens:
  K_raw: normal token order
  K_alpha: tokens sorted alphabetically (preserving duplicates)
  K_alpha_unique: unique tokens sorted alphabetically

Decode C1 (in-DOI-range only) with first_letter and last_letter extractors.
Score with quadgram + word_pattern. Controls: 20x shuffled keystream.

Output: phase101/alpha_keystream_ranked.csv, top_streams/
"""

import csv
import json
import random
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher
from corpus.beale_doi_adjusted import get_adjusted_tokens
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score

OUT = PROJECT_ROOT / "output" / "phase101"
TOP_DIR = OUT / "top_streams"
SEED = 101200
N_CONTROL = 20


def build_keystreams(tokens: List[str]):
    k_raw = tokens[:]
    k_alpha = sorted(tokens, key=lambda t: t.lower())
    seen = set()
    unique_sorted = []
    for t in sorted(set(tokens), key=lambda t: t.lower()):
        unique_sorted.append(t)
    k_alpha_unique = unique_sorted
    return {"K_raw": k_raw, "K_alpha": k_alpha, "K_alpha_unique": k_alpha_unique}


def decode(keystream: List[str], cipher_nums: List[int], extractor: str) -> str:
    out = []
    for n in cipher_nums:
        idx = n - 1
        if 0 <= idx < len(keystream) and keystream[idx]:
            w = keystream[idx]
            if extractor == "first_letter":
                out.append(w[0].upper())
            elif extractor == "last_letter":
                out.append(w[-1].upper())
            elif extractor == "second_letter":
                out.append(w[1].upper() if len(w) > 1 else w[0].upper())
            else:
                out.append(w[0].upper())
        else:
            out.append("?")
    return "".join(out)


def score_stream(stream: str) -> dict:
    wp = score_word_patterns(stream)
    qg = quadgram_score(stream)
    return {
        "quadgram": round(qg, 4),
        "word_coverage": round(wp["word_coverage"], 4),
        "long_word_count": wp["long_word_count"],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TOP_DIR.mkdir(parents=True, exist_ok=True)

    tokens = get_adjusted_tokens()
    c1 = load_cipher(1)
    keystreams = build_keystreams(tokens)

    extractors = ["first_letter", "last_letter", "second_letter"]
    rng = random.Random(SEED)
    rows = []

    for ks_name, ks_tokens in keystreams.items():
        for ext in extractors:
            stream = decode(ks_tokens, c1, ext)
            s = score_stream(stream)

            # Controls: shuffle keystream 20x
            ctrl_qgs = []
            for i in range(N_CONTROL):
                shuffled = ks_tokens[:]
                rng.shuffle(shuffled)
                ctrl_stream = decode(shuffled, c1, ext)
                ctrl_qgs.append(quadgram_score(ctrl_stream))
            ctrl_mean = sum(ctrl_qgs) / len(ctrl_qgs)
            ctrl_std = (sum((x - ctrl_mean) ** 2 for x in ctrl_qgs) / len(ctrl_qgs)) ** 0.5 or 1e-10
            z = (s["quadgram"] - ctrl_mean) / ctrl_std

            row = {
                "keystream": ks_name,
                "extractor": ext,
                "stream_len": len(stream),
                "quadgram": s["quadgram"],
                "word_coverage": s["word_coverage"],
                "long_word_count": s["long_word_count"],
                "ctrl_qg_mean": round(ctrl_mean, 4),
                "ctrl_qg_std": round(ctrl_std, 4),
                "z_vs_ctrl": round(z, 4),
            }
            rows.append(row)

            # Save top stream
            label = f"{ks_name}_{ext}"
            with open(TOP_DIR / f"alpha_ks_{label}.txt", "w", encoding="utf-8") as f:
                f.write(f"Label: {label}\n")
                f.write(f"Quadgram: {s['quadgram']:.4f}  z={z:.2f}\n")
                f.write(stream + "\n")

    rows.sort(key=lambda r: r["quadgram"], reverse=True)
    path = OUT / "alpha_keystream_ranked.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Task 2B: wrote {path} ({len(rows)} rows)")
    for r in rows[:5]:
        print(f"  {r['keystream']:18s} {r['extractor']:14s} qg={r['quadgram']:7.4f} z={r['z_vs_ctrl']:+.2f}")


if __name__ == "__main__":
    main()
