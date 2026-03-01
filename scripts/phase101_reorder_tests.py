"""
Phase 101 Task 2C: Sorting/reorder step test.

Around each anomaly window (from top 5 Gillogly runs), try bounded reorderings:
  - sort decoded letters by cipher number
  - sort decoded letters by DOI position of referenced word
  - sort letters within fixed block sizes (5, 10, 17)

Score reorder outputs vs controls (shuffled stream segments).

Output: phase101/reorder_tests_ranked.csv, phase101/reorder_examples.txt
"""

import csv
import json
import random
import sys
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher
from corpus.beale_doi_adjusted import get_adjusted_tokens
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score

OUT = PROJECT_ROOT / "output" / "phase101"
SEED = 101300
N_CONTROL = 200


def decode_detailed(tokens, c1):
    result = []
    for pos, n in enumerate(c1):
        idx = n - 1
        in_range = 0 <= idx < len(tokens)
        word = tokens[idx] if in_range else None
        fl = word[0].upper() if word else "?"
        result.append({
            "pos": pos, "num": n, "doi_idx": idx if in_range else -1,
            "word": word, "letter": fl,
        })
    return result


def reorder_by_cipher_num(entries: List[Dict]) -> str:
    return "".join(e["letter"] for e in sorted(entries, key=lambda e: e["num"]))


def reorder_by_doi_position(entries: List[Dict]) -> str:
    return "".join(e["letter"] for e in sorted(entries, key=lambda e: e["doi_idx"] if e["doi_idx"] >= 0 else 99999))


def reorder_blocks(stream: str, block_size: int) -> str:
    out = []
    for i in range(0, len(stream), block_size):
        block = sorted(stream[i:i + block_size])
        out.extend(block)
    return "".join(out)


def reverse_blocks(stream: str, block_size: int) -> str:
    out = []
    for i in range(0, len(stream), block_size):
        out.extend(reversed(stream[i:i + block_size]))
    return "".join(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tokens = get_adjusted_tokens()
    c1 = load_cipher(1)
    decoded = decode_detailed(tokens, c1)
    full_stream = "".join(d["letter"] for d in decoded)

    # Load top anomaly windows from gillogly_top20.json
    top20_path = OUT / "gillogly_top20.json"
    with open(top20_path, "r", encoding="utf-8") as f:
        top20 = json.load(f)

    rng = random.Random(SEED)
    rows = []
    examples = ["Phase 101 Task 2C: Reorder Test Examples", "=" * 50, ""]

    # === Global reorder tests ===
    global_tests = [
        ("global_sort_by_ciphernum", reorder_by_cipher_num(decoded)),
        ("global_sort_by_doipos", reorder_by_doi_position(decoded)),
    ]
    for block_size in [5, 10, 17, 20]:
        global_tests.append((f"global_block_sort_{block_size}", reorder_blocks(full_stream, block_size)))
        global_tests.append((f"global_block_reverse_{block_size}", reverse_blocks(full_stream, block_size)))

    for label, stream in global_tests:
        s = score_word_patterns(stream)
        qg = quadgram_score(stream)
        # Control: shuffle full stream, apply same transform, score
        ctrl_qgs = []
        letters = list(full_stream)
        for _ in range(N_CONTROL):
            rng.shuffle(letters)
            ctrl_qgs.append(quadgram_score("".join(letters)))
        ctrl_mean = sum(ctrl_qgs) / len(ctrl_qgs)
        ctrl_std = (sum((x - ctrl_mean) ** 2 for x in ctrl_qgs) / len(ctrl_qgs)) ** 0.5 or 1e-10
        z = (qg - ctrl_mean) / ctrl_std

        rows.append({
            "scope": "global",
            "reorder": label,
            "window": "full",
            "quadgram": round(qg, 4),
            "word_coverage": round(s["word_coverage"], 4),
            "long_words": s["long_word_count"],
            "ctrl_qg_mean": round(ctrl_mean, 4),
            "z_vs_ctrl": round(z, 4),
            "stream_preview": stream[:80],
        })

    # === Window-local reorder tests around top 5 anomalies ===
    for rec in top20[:5]:
        s_start = max(0, rec["cipher_pos_start"] - 20)
        s_end = min(len(decoded), rec["cipher_pos_end"] + 21)
        window_entries = decoded[s_start:s_end]
        window_stream = "".join(e["letter"] for e in window_entries)
        window_label = f"pos{rec['cipher_pos_start']}-{rec['cipher_pos_end']}"

        local_tests = [
            (f"window_sort_ciphernum_{window_label}", reorder_by_cipher_num(window_entries)),
            (f"window_sort_doipos_{window_label}", reorder_by_doi_position(window_entries)),
        ]
        for bsz in [5, 10, 17]:
            local_tests.append((f"window_block_sort_{bsz}_{window_label}",
                                reorder_blocks(window_stream, bsz)))

        for label, stream_seg in local_tests:
            # Embed reordered window back into full stream
            full_reordered = full_stream[:s_start] + stream_seg + full_stream[s_end:]
            qg = quadgram_score(full_reordered)
            s = score_word_patterns(full_reordered)
            # Control: shuffle just the window, embed, score
            ctrl_qgs = []
            win_letters = list(window_stream)
            for _ in range(N_CONTROL):
                rng.shuffle(win_letters)
                ctrl_full = full_stream[:s_start] + "".join(win_letters) + full_stream[s_end:]
                ctrl_qgs.append(quadgram_score(ctrl_full))
            ctrl_mean = sum(ctrl_qgs) / len(ctrl_qgs)
            ctrl_std = (sum((x - ctrl_mean) ** 2 for x in ctrl_qgs) / len(ctrl_qgs)) ** 0.5 or 1e-10
            z = (qg - ctrl_mean) / ctrl_std

            rows.append({
                "scope": "window",
                "reorder": label,
                "window": window_label,
                "quadgram": round(qg, 4),
                "word_coverage": round(s["word_coverage"], 4),
                "long_words": s["long_word_count"],
                "ctrl_qg_mean": round(ctrl_mean, 4),
                "z_vs_ctrl": round(z, 4),
                "stream_preview": stream_seg[:80],
            })

            examples.append(f"--- {label} ---")
            examples.append(f"  qg={qg:.4f}  z={z:.2f}")
            examples.append(f"  {stream_seg[:80]}")
            examples.append("")

    rows.sort(key=lambda r: r["z_vs_ctrl"], reverse=True)
    path = OUT / "reorder_tests_ranked.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    with open(OUT / "reorder_examples.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(examples))

    print(f"Task 2C: wrote {path} ({len(rows)} rows)")
    print("Top 5 by z-score:")
    for r in rows[:5]:
        print(f"  z={r['z_vs_ctrl']:+.2f}  qg={r['quadgram']:.4f}  {r['reorder']}")


if __name__ == "__main__":
    main()
