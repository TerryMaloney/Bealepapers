"""
Cheap decode sweep with controls (Phase 98 Step 3).

For each bundle B in {B1, B2, B3} and cipher in {C1, C3}:
- Extractors: E1 first_letter, E2 last_letter, E3 position_mod_wordlen
- Scoring: score_word_patterns, quadgram_score, Cipher3DomainScorer (C3 only)
- Controls: 20x shuffled keystream (K), 20x shuffled cipher (C). z = (real - mean) / std
- Decision gate: z_quadgram >= 4 OR long_words >= adaptive_threshold -> flag as signal

Outputs: bundle_decode_ranked_c1.csv, bundle_decode_ranked_c3.csv,
         top_streams/bundle_<B>_<cipher>_<extractor>.txt, control_comparison_summary.txt
"""

import csv
import json
import random
import sys
from pathlib import Path
from typing import List, Tuple, Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from scoring.cipher3_domain_scorer import Cipher3DomainScorer

OUT_DIR = PROJECT_ROOT / "output" / "phase98"
TOP_STREAMS_DIR = OUT_DIR / "top_streams"
N_CONTROL = 20
SEED_BASE = 98123


def load_bundle_tokens(bundle_path: Path) -> List[str]:
    with open(bundle_path, "r", encoding="utf-8") as f:
        return json.load(f)["tokens"]


def extract_first_letter(tokens: List[str], n: int) -> str:
    idx = n - 1
    if 0 <= idx < len(tokens):
        w = tokens[idx]
        return (w[0].upper() if w else "?")
    return "?"


def extract_last_letter(tokens: List[str], n: int) -> str:
    idx = n - 1
    if 0 <= idx < len(tokens):
        w = tokens[idx]
        return (w[-1].upper() if len(w) > 0 else "?")
    return "?"


def extract_position_mod_wordlen(tokens: List[str], cipher_nums: List[int], position: int, n: int) -> str:
    idx = n - 1
    if 0 <= idx < len(tokens):
        w = tokens[idx]
        if w:
            i = position % len(w)
            return w[i].upper()
    return "?"


def decode(tokens: List[str], cipher_nums: List[int], extractor: str) -> str:
    if extractor == "first_letter":
        return "".join(extract_first_letter(tokens, n) for n in cipher_nums)
    if extractor == "last_letter":
        return "".join(extract_last_letter(tokens, n) for n in cipher_nums)
    if extractor == "position_mod_wordlen":
        return "".join(
            extract_position_mod_wordlen(tokens, cipher_nums, i, n)
            for i, n in enumerate(cipher_nums)
        )
    raise ValueError(f"Unknown extractor: {extractor}")


def score_stream(stream: str, use_c3_domain: bool = False) -> dict:
    wp = score_word_patterns(stream)
    qg = quadgram_score(stream)
    out = {
        "word_coverage": wp["word_coverage"],
        "long_word_count": wp["long_word_count"],
        "quadgram": qg,
    }
    if use_c3_domain:
        c3_scorer = Cipher3DomainScorer()
        domain_score, _ = c3_scorer.score(stream)
        out["c3_domain"] = domain_score
    return out


def run_control_k(tokens: List[str], cipher_nums: List[int], extractor: str,
                  use_c3_domain: bool, n_runs: int) -> Tuple[List[dict], List[dict]]:
    qgs, longs, domains = [], [], []
    for run in range(n_runs):
        shuffled = tokens.copy()
        random.seed(SEED_BASE + run)
        random.shuffle(shuffled)
        stream = decode(shuffled, cipher_nums, extractor)
        s = score_stream(stream, use_c3_domain)
        qgs.append(s["quadgram"])
        longs.append(s["long_word_count"])
        if use_c3_domain:
            domains.append(s["c3_domain"])
    mean_qg = sum(qgs) / len(qgs)
    std_qg = (sum((x - mean_qg) ** 2 for x in qgs) / len(qgs)) ** 0.5 or 1e-10
    mean_long = sum(longs) / len(longs)
    std_long = (sum((x - mean_long) ** 2 for x in longs) / len(longs)) ** 0.5 or 1e-10
    result = {"quadgram_mean": mean_qg, "quadgram_std": std_qg, "long_mean": mean_long, "long_std": std_long}
    if use_c3_domain:
        mean_d = sum(domains) / len(domains)
        std_d = (sum((x - mean_d) ** 2 for x in domains) / len(domains)) ** 0.5 or 1e-10
        result["domain_mean"] = mean_d
        result["domain_std"] = std_d
    return result, [{"quadgram": q, "long": l} for q, l in zip(qgs, longs)]


def run_control_c(tokens: List[str], cipher_nums: List[int], extractor: str,
                  use_c3_domain: bool, n_runs: int) -> Tuple[dict, List[dict]]:
    qgs, longs, domains = [], [], []
    for run in range(n_runs):
        shuffled_nums = cipher_nums.copy()
        random.seed(SEED_BASE + 1000 + run)
        random.shuffle(shuffled_nums)
        stream = decode(tokens, shuffled_nums, extractor)
        s = score_stream(stream, use_c3_domain)
        qgs.append(s["quadgram"])
        longs.append(s["long_word_count"])
        if use_c3_domain:
            domains.append(s["c3_domain"])
    mean_qg = sum(qgs) / len(qgs)
    std_qg = (sum((x - mean_qg) ** 2 for x in qgs) / len(qgs)) ** 0.5 or 1e-10
    mean_long = sum(longs) / len(longs)
    std_long = (sum((x - mean_long) ** 2 for x in longs) / len(longs)) ** 0.5 or 1e-10
    result = {"quadgram_mean": mean_qg, "quadgram_std": std_qg, "long_mean": mean_long, "long_std": std_long}
    if use_c3_domain:
        mean_d = sum(domains) / len(domains)
        std_d = (sum((x - mean_d) ** 2 for x in domains) / len(domains)) ** 0.5 or 1e-10
        result["domain_mean"] = mean_d
        result["domain_std"] = std_d
    return result, [{"quadgram": q, "long": l} for q, l in zip(qgs, longs)]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TOP_STREAMS_DIR.mkdir(parents=True, exist_ok=True)

    # Calibration
    cal_path = PROJECT_ROOT / "output" / "phase92" / "calibration.json"
    adaptive_long_min = 3
    if cal_path.exists():
        with open(cal_path, "r", encoding="utf-8") as f:
            cal = json.load(f)
        adaptive_long_min = cal.get("adaptive_thresholds", {}).get("long_words_min", 3)

    manifest_path = OUT_DIR / "bundle_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    c1 = load_cipher(1)
    c3 = load_cipher(3)
    bundles = {}
    for bid in ["b1", "b2", "b3"]:
        p = Path(manifest["bundles"][bid]["path"])
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        bundles[bid] = load_bundle_tokens(p)

    extractors = ["first_letter", "last_letter", "position_mod_wordlen"]
    results_c1 = []
    results_c3 = []
    summary_lines = ["Phase 98 Bundle Decode Sweep - Control Comparison Summary", ""]

    for bid, tokens in bundles.items():
        for cipher_name, cipher_nums in [("c1", c1), ("c3", c3)]:
            use_c3_domain = cipher_name == "c3"
            for ext in extractors:
                stream = decode(tokens, cipher_nums, ext)
                s = score_stream(stream, use_c3_domain)
                ck, _ = run_control_k(tokens, cipher_nums, ext, use_c3_domain, N_CONTROL)
                cc, _ = run_control_c(tokens, cipher_nums, ext, use_c3_domain, N_CONTROL)
                z_k_qg = (s["quadgram"] - ck["quadgram_mean"]) / ck["quadgram_std"] if ck["quadgram_std"] else 0
                z_c_qg = (s["quadgram"] - cc["quadgram_mean"]) / cc["quadgram_std"] if cc["quadgram_std"] else 0
                signal = s["long_word_count"] >= adaptive_long_min or z_k_qg >= 4 or z_c_qg >= 4
                row = {
                    "bundle": bid,
                    "cipher": cipher_name,
                    "extractor": ext,
                    "quadgram": round(s["quadgram"], 4),
                    "word_coverage": round(s["word_coverage"], 4),
                    "long_word_count": s["long_word_count"],
                    "z_k_quadgram": round(z_k_qg, 4),
                    "z_c_quadgram": round(z_c_qg, 4),
                    "control_k_qg_mean": round(ck["quadgram_mean"], 4),
                    "control_c_qg_mean": round(cc["quadgram_mean"], 4),
                    "signal": signal,
                    "stream_preview": stream[:80] if len(stream) >= 80 else stream,
                }
                if use_c3_domain:
                    row["c3_domain"] = round(s["c3_domain"], 4)
                if cipher_name == "c1":
                    results_c1.append(row)
                else:
                    results_c3.append(row)
                # Top stream file
                label = f"bundle_{bid}_{cipher_name}_{ext}"
                top_path = TOP_STREAMS_DIR / f"{label}.txt"
                with open(top_path, "w", encoding="utf-8") as f:
                    f.write(f"Label: {label}\n")
                    f.write(f"Quadgram: {s['quadgram']:.4f}  long_words: {s['long_word_count']}  signal: {signal}\n")
                    f.write(stream)

    # Rank C1 by quadgram desc, then by z_k_quadgram desc
    results_c1.sort(key=lambda r: (r["quadgram"], r["z_k_quadgram"]), reverse=True)
    results_c3.sort(key=lambda r: (r["quadgram"], r["z_k_quadgram"]), reverse=True)

    def write_csv(path: Path, rows: List[dict], extra_cols: List[str] = None):
        if not rows:
            return
        cols = ["bundle", "cipher", "extractor", "quadgram", "word_coverage", "long_word_count",
                "z_k_quadgram", "z_c_quadgram", "control_k_qg_mean", "control_c_qg_mean", "signal", "stream_preview"]
        if extra_cols:
            cols = [c for c in cols if c != "stream_preview"] + extra_cols + ["stream_preview"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    write_csv(OUT_DIR / "bundle_decode_ranked_c1.csv", results_c1)
    write_csv(OUT_DIR / "bundle_decode_ranked_c3.csv", results_c3, extra_cols=["c3_domain"])

    # Summary
    signals_c1 = [r for r in results_c1 if r["signal"]]
    signals_c3 = [r for r in results_c3 if r["signal"]]
    summary_lines.append(f"Adaptive long_words_min: {adaptive_long_min}")
    summary_lines.append(f"Signals (decision gate): C1 {len(signals_c1)}, C3 {len(signals_c3)}")
    summary_lines.append("")
    summary_lines.append("Top 5 C1 by quadgram:")
    for r in results_c1[:5]:
        summary_lines.append(f"  {r['bundle']} {r['extractor']}: qg={r['quadgram']:.4f} z_k={r['z_k_quadgram']:.2f} signal={r['signal']}")
    summary_lines.append("")
    summary_lines.append("Top 5 C3 by quadgram:")
    for r in results_c3[:5]:
        summary_lines.append(f"  {r['bundle']} {r['extractor']}: qg={r['quadgram']:.4f} c3_domain={r.get('c3_domain', 0):.2f} z_k={r['z_k_quadgram']:.2f} signal={r['signal']}")
    with open(OUT_DIR / "control_comparison_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    print(f"Wrote {OUT_DIR / 'bundle_decode_ranked_c1.csv'}, ranked_c3, top_streams/, control_comparison_summary.txt")


if __name__ == "__main__":
    main()
