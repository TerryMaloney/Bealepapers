"""
Phase 101 Task 1: Gillogly Block Deep Dive.

For the top 20 anomalies from phase100/gillogly_scan.csv:
- Record cipher position range, decoded letters, underlying cipher numbers
- Map to DOI words and DOI positions
- Characterize: are the DOI positions contiguous? scattered? what pattern?

Task 2A: Planted marker test.
- Probability of 17-letter near-alpha run under (i) DOI word sampling, (ii) letter freq
- 100k simulations.

Outputs:
  phase101/gillogly_top20.json
  phase101/gillogly_top20.md
  phase101/gillogly_marker_test.txt
"""

import csv
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher
from corpus.beale_doi_adjusted import get_adjusted_tokens

OUT = PROJECT_ROOT / "output" / "phase101"
SEED = 101000
N_SIM_MARKER = 100_000


def decode_c1_with_doi(tokens, c1):
    """Return list of dicts: one per C1 position."""
    result = []
    for pos, n in enumerate(c1):
        idx = n - 1
        in_range = 0 <= idx < len(tokens)
        word = tokens[idx] if in_range else None
        fl = word[0].upper() if word else "?"
        result.append({
            "cipher_pos": pos,
            "cipher_num": n,
            "doi_idx": idx if in_range else None,
            "doi_word": word,
            "first_letter": fl,
            "in_range": in_range,
        })
    return result


def longest_alpha_run(stream: str) -> int:
    if len(stream) < 2:
        return len(stream)
    best = 1
    run = 1
    for i in range(1, len(stream)):
        if stream[i] >= stream[i - 1]:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def find_all_alpha_runs(stream: str, min_len: int = 6):
    runs = []
    start = 0
    for i in range(1, len(stream)):
        if stream[i] >= stream[i - 1]:
            continue
        length = i - start
        if length >= min_len:
            runs.append({"start": start, "end": i - 1, "length": length, "text": stream[start:i]})
        start = i
    length = len(stream) - start
    if length >= min_len:
        runs.append({"start": start, "end": len(stream) - 1, "length": length, "text": stream[start:]})
    return runs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c1 = load_cipher(1)
    tokens = get_adjusted_tokens()
    decoded = decode_c1_with_doi(tokens, c1)
    stream = "".join(d["first_letter"] for d in decoded)

    # === Task 1: Top 20 deep dive ===
    all_runs = find_all_alpha_runs(stream, min_len=5)
    all_runs.sort(key=lambda r: r["length"], reverse=True)
    top20 = all_runs[:20]

    top20_records = []
    for rank, run in enumerate(top20, 1):
        s, e = run["start"], run["end"]
        entries = decoded[s:e + 1]
        nums = [d["cipher_num"] for d in entries]
        doi_positions = [d["doi_idx"] for d in entries if d["doi_idx"] is not None]
        doi_words = [d["doi_word"] for d in entries if d["doi_word"]]

        # Are DOI positions contiguous?
        if len(doi_positions) >= 2:
            diffs = [doi_positions[i + 1] - doi_positions[i] for i in range(len(doi_positions) - 1)]
            is_monotone_up = all(d > 0 for d in diffs)
            is_monotone_down = all(d < 0 for d in diffs)
            mean_gap = sum(abs(d) for d in diffs) / len(diffs)
        else:
            diffs = []
            is_monotone_up = False
            is_monotone_down = False
            mean_gap = 0

        rec = {
            "rank": rank,
            "cipher_pos_start": s,
            "cipher_pos_end": e,
            "run_length": run["length"],
            "decoded_letters": run["text"],
            "cipher_numbers": nums,
            "doi_words": doi_words,
            "doi_positions": doi_positions,
            "doi_pos_diffs": diffs,
            "doi_positions_monotone_up": is_monotone_up,
            "doi_positions_monotone_down": is_monotone_down,
            "doi_mean_gap": round(mean_gap, 1),
            "all_in_doi_range": all(d["in_range"] for d in entries),
            "oob_count": sum(1 for d in entries if not d["in_range"]),
        }
        top20_records.append(rec)

    with open(OUT / "gillogly_top20.json", "w", encoding="utf-8") as f:
        json.dump(top20_records, f, indent=2)

    # Write markdown
    md = ["# Gillogly Top 20 Alpha Runs — Deep Dive", ""]
    for rec in top20_records:
        md.append(f"## Rank {rec['rank']}: length {rec['run_length']} at cipher positions "
                  f"{rec['cipher_pos_start']}–{rec['cipher_pos_end']}")
        md.append(f"**Letters:** `{rec['decoded_letters']}`")
        md.append(f"**Cipher numbers:** `{rec['cipher_numbers']}`")
        if rec["doi_words"]:
            md.append(f"**DOI words:** {', '.join(rec['doi_words'])}")
            md.append(f"**DOI positions (0-indexed):** `{rec['doi_positions']}`")
            md.append(f"**DOI pos diffs:** `{rec['doi_pos_diffs']}`")
            md.append(f"**Monotone up:** {rec['doi_positions_monotone_up']}  "
                      f"**Mean gap:** {rec['doi_mean_gap']}")
        md.append(f"**All in DOI range:** {rec['all_in_doi_range']}  "
                  f"**Out-of-bound:** {rec['oob_count']}")
        md.append("")
    with open(OUT / "gillogly_top20.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Task 1: wrote gillogly_top20.json + .md ({len(top20_records)} records)")

    # === Task 2A: Planted marker test ===
    # Build marginal first-letter frequency from DOI
    first_letters = [t[0].upper() for t in tokens if t]
    fl_counter = Counter(first_letters)
    fl_total = sum(fl_counter.values())
    fl_probs = {ch: cnt / fl_total for ch, cnt in fl_counter.items()}
    alphabet = sorted(fl_probs.keys())
    fl_weights = [fl_probs.get(ch, 0) for ch in alphabet]

    # C1 numbers that are in-range for DOI
    c1_in_range = [n for n in c1 if 1 <= n <= len(tokens)]
    n_in_range = len(c1_in_range)
    observed_longest = 17

    rng = random.Random(SEED)

    # Model (i): random DOI word sampling with same marginal distribution
    # Simulate: pick n_in_range random DOI positions (uniform), decode first letters, find longest alpha run
    count_ge_model_i = 0
    for _ in range(N_SIM_MARKER):
        sample = [rng.randint(0, len(tokens) - 1) for _ in range(n_in_range)]
        s = "".join(tokens[j][0].upper() if tokens[j] else "?" for j in sample)
        if longest_alpha_run(s) >= observed_longest:
            count_ge_model_i += 1
    p_model_i = count_ge_model_i / N_SIM_MARKER

    # Model (ii): random letter stream matching marginal first-letter frequencies
    count_ge_model_ii = 0
    for _ in range(N_SIM_MARKER):
        s = "".join(rng.choices(alphabet, weights=fl_weights, k=len(c1)))
        if longest_alpha_run(s) >= observed_longest:
            count_ge_model_ii += 1
    p_model_ii = count_ge_model_ii / N_SIM_MARKER

    # Also: probability under C1-exact distribution (shuffle C1 decoded stream)
    count_ge_shuffle = 0
    stream_list = list(stream)
    for _ in range(N_SIM_MARKER):
        rng.shuffle(stream_list)
        if longest_alpha_run("".join(stream_list)) >= observed_longest:
            count_ge_shuffle += 1
    p_shuffle = count_ge_shuffle / N_SIM_MARKER

    # Wilson score CI for proportions
    def wilson_ci(p_hat, n, z=1.96):
        if n == 0:
            return (0, 0)
        denom = 1 + z**2 / n
        center = (p_hat + z**2 / (2 * n)) / denom
        spread = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denom
        return (max(0, center - spread), min(1, center + spread))

    ci_i = wilson_ci(p_model_i, N_SIM_MARKER)
    ci_ii = wilson_ci(p_model_ii, N_SIM_MARKER)
    ci_sh = wilson_ci(p_shuffle, N_SIM_MARKER)

    lines = [
        "Phase 101 Task 2A: Planted Marker Test",
        "=" * 50,
        "",
        f"Observed: longest alphabetical run in C1 (DOI first-letter decode) = {observed_longest}",
        f"  Letters: ABCDEFGHIIJKLMMNO at cipher positions 187-203",
        f"  Stream length: {len(stream)} (of which {n_in_range} in DOI range)",
        "",
        f"Simulations: {N_SIM_MARKER:,} per model",
        "",
        f"Model (i): Random uniform DOI position sampling (stream length {n_in_range})",
        f"  P(longest_run >= {observed_longest}) = {p_model_i:.8f}",
        f"  95% CI: [{ci_i[0]:.8f}, {ci_i[1]:.8f}]",
        f"  Hits: {count_ge_model_i}/{N_SIM_MARKER}",
        "",
        f"Model (ii): Random letters from DOI first-letter marginal (stream length {len(c1)})",
        f"  P(longest_run >= {observed_longest}) = {p_model_ii:.8f}",
        f"  95% CI: [{ci_ii[0]:.8f}, {ci_ii[1]:.8f}]",
        f"  Hits: {count_ge_model_ii}/{N_SIM_MARKER}",
        "",
        f"Model (iii): Shuffled C1 decoded stream (exact letter distribution)",
        f"  P(longest_run >= {observed_longest}) = {p_shuffle:.8f}",
        f"  95% CI: [{ci_sh[0]:.8f}, {ci_sh[1]:.8f}]",
        f"  Hits: {count_ge_shuffle}/{N_SIM_MARKER}",
        "",
        "Conclusion:",
    ]
    if p_model_i == 0 and p_model_ii == 0 and p_shuffle == 0:
        lines.append(f"  ALL THREE models: 0 hits in {N_SIM_MARKER:,} simulations.")
        lines.append(f"  Upper bound (95% CI): p < {ci_i[1]:.2e}")
        lines.append("  The 17-letter alphabetical run is EXTREMELY unlikely under any null model.")
    else:
        lines.append(f"  Model i: p={p_model_i:.2e}, Model ii: p={p_model_ii:.2e}, "
                     f"Shuffle: p={p_shuffle:.2e}")

    with open(OUT / "gillogly_marker_test.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Task 2A: p_doi_sample={p_model_i}, p_letter_freq={p_model_ii}, p_shuffle={p_shuffle}")
    print(f"  Wrote gillogly_marker_test.txt")


if __name__ == "__main__":
    main()
