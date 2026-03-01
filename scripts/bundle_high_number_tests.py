"""
High-number hypothesis tests (Phase 98 Step 4) on best bundle only.

4A) Modulo wrap: idx = ((n-1) % L) + 1, L = bundle length or 1311. Decode C1/C3, score vs controls.
4B) Character accumulator: char stream (A) letters-only, (B) letters+space. Decode by char index.
4C) Numbers > T as separators (T in {1005, 1322, 2000}); decode remaining. Columnar width variant.

Outputs: modwrap_ranked.csv, char_index_ranked_letters.csv, char_index_ranked_letters_space.csv,
         nulls_ranked.csv
"""

import csv
import json
import random
import sys
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from scoring.cipher3_domain_scorer import Cipher3DomainScorer

OUT_DIR = PROJECT_ROOT / "output" / "phase98"
N_CONTROL = 20
SEED_BASE = 49876
BEST_BUNDLE = "b3"  # best bundle from Step 3 (highest quadgram / largest bundle)
DOI_LEN = 1311


def load_bundle_tokens(bundle_path: Path) -> List[str]:
    with open(bundle_path, "r", encoding="utf-8") as f:
        return json.load(f)["tokens"]


def score_stream(stream: str, use_c3_domain: bool = False) -> dict:
    wp = score_word_patterns(stream)
    qg = quadgram_score(stream)
    out = {"word_coverage": wp["word_coverage"], "long_word_count": wp["long_word_count"], "quadgram": qg}
    if use_c3_domain:
        out["c3_domain"] = Cipher3DomainScorer().score(stream)[0]
    return out


def control_mean_std(scores: List[float]) -> Tuple[float, float]:
    if not scores:
        return 0.0, 1e-10
    m = sum(scores) / len(scores)
    v = sum((x - m) ** 2 for x in scores) / len(scores)
    return m, (v ** 0.5) or 1e-10


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "bundle_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
    p = Path(manifest["bundles"][BEST_BUNDLE]["path"])
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    tokens = load_bundle_tokens(p)
    L_bundle = len(tokens)
    c1 = load_cipher(1)
    c3 = load_cipher(3)

    # ---- 4A: Modulo wrap ----
    modwrap_rows = []
    for cipher_name, cipher_nums in [("c1", c1), ("c3", c3)]:
        use_c3 = cipher_name == "c3"
        for L in [DOI_LEN, L_bundle]:
            def decode_modwrap(nums: List[int], tok: List[str], length: int) -> str:
                out = []
                for n in nums:
                    idx = ((n - 1) % length) + 1  # 1-indexed position in keystream
                    i = idx - 1
                    if 0 <= i < len(tok) and tok[i]:
                        out.append(tok[i][0].upper())
                    else:
                        out.append("?")
                return "".join(out)

            stream = decode_modwrap(cipher_nums, tokens, L)
            s = score_stream(stream, use_c3)
            # Control: shuffle tokens
            qg_controls = []
            for run in range(N_CONTROL):
                t = tokens.copy()
                random.seed(SEED_BASE + run)
                random.shuffle(t)
                qg_controls.append(score_stream(decode_modwrap(cipher_nums, t, L), use_c3)["quadgram"])
            mean_c, std_c = control_mean_std(qg_controls)
            z = (s["quadgram"] - mean_c) / std_c if std_c else 0
            row = {
                "cipher": cipher_name,
                "L": L,
                "quadgram": round(s["quadgram"], 4),
                "long_word_count": s["long_word_count"],
                "z_control": round(z, 4),
            }
            if use_c3:
                row["c3_domain"] = round(s["c3_domain"], 4)
            modwrap_rows.append(row)
    with open(OUT_DIR / "modwrap_ranked.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cipher", "L", "quadgram", "long_word_count", "z_control", "c3_domain"], extrasaction="ignore")
        w.writeheader()
        w.writerows(modwrap_rows)

    # ---- 4B: Character index decode ----
    # (A) letters only: concat tokens, take alpha only
    letters_only = "".join("".join(c for c in w if c.isalpha()) for w in tokens).upper()
    # (B) letters + space: token1 + " " + token2 + ...
    letters_space = " ".join(tokens).replace(" ", " ").upper()
    letters_space_flat = "".join(c if c.isalpha() or c.isspace() else "" for c in letters_space)

    char_index_rows = []
    for variant, char_stream in [("letters", letters_only), ("letters_space", letters_space_flat)]:
        stream_len = len(char_stream)
        for cipher_name, cipher_nums in [("c1", c1), ("c3", c3)]:
            use_c3 = cipher_name == "c3"

            def decode_char_index(nums: List[int], cs: str) -> str:
                out = []
                for n in nums:
                    # n is 1-based character index
                    i = n - 1
                    if 0 <= i < len(cs):
                        ch = cs[i]
                        if ch.isalpha():
                            out.append(ch.upper())
                        elif ch.isspace():
                            out.append(" ")
                        else:
                            out.append("?")
                    else:
                        out.append("?")
                return "".join(out)

            stream = decode_char_index(cipher_nums, char_stream)
            s = score_stream(stream, use_c3)
            qg_controls = []
            for run in range(N_CONTROL):
                # Shuffle character stream (preserve length)
                lst = list(char_stream)
                random.seed(SEED_BASE + 2000 + run)
                random.shuffle(lst)
                qg_controls.append(score_stream(decode_char_index(cipher_nums, "".join(lst)), use_c3)["quadgram"])
            mean_c, std_c = control_mean_std(qg_controls)
            z = (s["quadgram"] - mean_c) / std_c if std_c else 0
            row = {
                "variant": variant,
                "cipher": cipher_name,
                "char_stream_len": stream_len,
                "quadgram": round(s["quadgram"], 4),
                "long_word_count": s["long_word_count"],
                "z_control": round(z, 4),
            }
            if use_c3:
                row["c3_domain"] = round(s["c3_domain"], 4)
            char_index_rows.append(row)
    with open(OUT_DIR / "char_index_ranked_letters.csv", "w", newline="", encoding="utf-8") as f:
        rows = [r for r in char_index_rows if r["variant"] == "letters"]
        w = csv.DictWriter(f, fieldnames=["variant", "cipher", "char_stream_len", "quadgram", "long_word_count", "z_control", "c3_domain"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(OUT_DIR / "char_index_ranked_letters_space.csv", "w", newline="", encoding="utf-8") as f:
        rows = [r for r in char_index_rows if r["variant"] == "letters_space"]
        w = csv.DictWriter(f, fieldnames=["variant", "cipher", "char_stream_len", "quadgram", "long_word_count", "z_control", "c3_domain"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # ---- 4C: Null/separator (numbers > T) ----
    nulls_rows = []
    for T in [1005, 1322, 2000]:
        for cipher_name, cipher_nums in [("c1", c1), ("c3", c3)]:
            use_c3 = cipher_name == "c3"
            # Filter: keep only numbers <= T, decode with first_letter
            filtered = [n for n in cipher_nums if n <= T]
            stream = "".join(
                (tokens[n - 1][0].upper() if 0 <= n - 1 < len(tokens) and tokens[n - 1] else "?")
                for n in filtered
            )
            s = score_stream(stream, use_c3)
            qg_controls = []
            for run in range(N_CONTROL):
                t = tokens.copy()
                random.seed(SEED_BASE + 4000 + run)
                random.shuffle(t)
                stream_c = "".join(
                    (t[n - 1][0].upper() if 0 <= n - 1 < len(t) and t[n - 1] else "?")
                    for n in filtered
                )
                qg_controls.append(score_stream(stream_c, use_c3)["quadgram"])
            mean_c, std_c = control_mean_std(qg_controls)
            z = (s["quadgram"] - mean_c) / std_c if std_c else 0
            row = {
                "T": T,
                "cipher": cipher_name,
                "n_kept": len(filtered),
                "quadgram": round(s["quadgram"], 4),
                "long_word_count": s["long_word_count"],
                "z_control": round(z, 4),
            }
            if use_c3:
                row["c3_domain"] = round(s["c3_domain"], 4)
            nulls_rows.append(row)
    with open(OUT_DIR / "nulls_ranked.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["T", "cipher", "n_kept", "quadgram", "long_word_count", "z_control", "c3_domain"], extrasaction="ignore")
        w.writeheader()
        w.writerows(nulls_rows)

    print(f"Step 4 outputs: modwrap_ranked.csv, char_index_ranked_*.csv, nulls_ranked.csv")


if __name__ == "__main__":
    main()
