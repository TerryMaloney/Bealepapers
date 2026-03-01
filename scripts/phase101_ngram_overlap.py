"""
Phase 101 Task 3: Cross-cipher n-gram overlap with strong controls.

Shared 2–5-grams in number space across (C1,C2), (C1,C3), (C2,C3), (all three).
Significance: >= 10,000 shuffles preserving unigram counts.
Optional stronger control: preserve run-length distribution.

Output: phase101/ngram_overlap_report.txt, ngram_overlap_tables.csv
"""

import csv
import random
import sys
from pathlib import Path
from typing import List, Set, Tuple
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher

OUT = PROJECT_ROOT / "output" / "phase101"
N_SHUFFLE = 10_000
SEED = 101500


def ngrams(seq: List[int], n: int) -> Set[Tuple[int, ...]]:
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


def ngram_counts(seq: List[int], n: int) -> Counter:
    return Counter(tuple(seq[i:i + n]) for i in range(len(seq) - n + 1))


def pairwise_overlap(s1: Set, s2: Set) -> int:
    return len(s1 & s2)


def triple_overlap(s1: Set, s2: Set, s3: Set) -> int:
    return len(s1 & s2 & s3)


def any2_overlap(s1: Set, s2: Set, s3: Set) -> int:
    return len((s1 & s2) | (s1 & s3) | (s2 & s3))


def shuffle_preserving_unigram(seq: List[int], rng: random.Random) -> List[int]:
    s = seq[:]
    rng.shuffle(s)
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c1 = load_cipher(1)
    c2 = load_cipher(2)
    c3 = load_cipher(3)

    rng = random.Random(SEED)
    report = ["Phase 101 Task 3: Cross-Cipher N-gram Overlap", "=" * 50, ""]
    table_rows = []

    pairs = [("C1", "C2", c1, c2), ("C1", "C3", c1, c3), ("C2", "C3", c2, c3)]

    for n in range(2, 6):
        report.append(f"--- {n}-grams ---")
        g1 = ngrams(c1, n)
        g2 = ngrams(c2, n)
        g3 = ngrams(c3, n)

        # Pairwise overlaps
        for name_a, name_b, seq_a, seq_b in pairs:
            ga = ngrams(seq_a, n)
            gb = ngrams(seq_b, n)
            observed = pairwise_overlap(ga, gb)

            null_dist = []
            for _ in range(N_SHUFFLE):
                sa = shuffle_preserving_unigram(seq_a, rng)
                sb = shuffle_preserving_unigram(seq_b, rng)
                null_dist.append(pairwise_overlap(ngrams(sa, n), ngrams(sb, n)))

            mean_null = sum(null_dist) / len(null_dist)
            std_null = (sum((x - mean_null) ** 2 for x in null_dist) / len(null_dist)) ** 0.5 or 1e-10
            z = (observed - mean_null) / std_null
            p_ge = sum(1 for x in null_dist if x >= observed) / len(null_dist)

            report.append(f"  {name_a} ∩ {name_b}: observed={observed}, null_mean={mean_null:.2f}, "
                          f"null_std={std_null:.2f}, z={z:.2f}, p(>=obs)={p_ge:.4f}")

            table_rows.append({
                "n": n, "pair": f"{name_a}_{name_b}", "observed": observed,
                "null_mean": round(mean_null, 2), "null_std": round(std_null, 2),
                "z": round(z, 2), "p_ge_observed": round(p_ge, 4),
            })

        # Triple overlap
        obs_3 = triple_overlap(g1, g2, g3)
        obs_any2 = any2_overlap(g1, g2, g3)
        null_3 = []
        null_any2 = []
        for _ in range(N_SHUFFLE):
            s1 = shuffle_preserving_unigram(c1, rng)
            s2 = shuffle_preserving_unigram(c2, rng)
            s3 = shuffle_preserving_unigram(c3, rng)
            ng1 = ngrams(s1, n)
            ng2 = ngrams(s2, n)
            ng3 = ngrams(s3, n)
            null_3.append(triple_overlap(ng1, ng2, ng3))
            null_any2.append(any2_overlap(ng1, ng2, ng3))

        mean_3 = sum(null_3) / len(null_3)
        std_3 = (sum((x - mean_3) ** 2 for x in null_3) / len(null_3)) ** 0.5 or 1e-10
        z_3 = (obs_3 - mean_3) / std_3
        p_3 = sum(1 for x in null_3 if x >= obs_3) / len(null_3)

        mean_a2 = sum(null_any2) / len(null_any2)
        std_a2 = (sum((x - mean_a2) ** 2 for x in null_any2) / len(null_any2)) ** 0.5 or 1e-10
        z_a2 = (obs_any2 - mean_a2) / std_a2
        p_a2 = sum(1 for x in null_any2 if x >= obs_any2) / len(null_any2)

        report.append(f"  ALL THREE: observed={obs_3}, null_mean={mean_3:.2f}, z={z_3:.2f}, p={p_3:.4f}")
        report.append(f"  ANY TWO:   observed={obs_any2}, null_mean={mean_a2:.2f}, z={z_a2:.2f}, p={p_a2:.4f}")
        report.append("")

        table_rows.append({
            "n": n, "pair": "ALL_THREE", "observed": obs_3,
            "null_mean": round(mean_3, 2), "null_std": round(std_3, 2),
            "z": round(z_3, 2), "p_ge_observed": round(p_3, 4),
        })
        table_rows.append({
            "n": n, "pair": "ANY_TWO", "observed": obs_any2,
            "null_mean": round(mean_a2, 2), "null_std": round(std_a2, 2),
            "z": round(z_a2, 2), "p_ge_observed": round(p_a2, 4),
        })

    # Summary
    report.append("Summary:")
    sig = [r for r in table_rows if r["p_ge_observed"] < 0.01]
    if sig:
        report.append(f"  {len(sig)} results with p < 0.01:")
        for r in sig:
            report.append(f"    {r['n']}-gram {r['pair']}: obs={r['observed']}, z={r['z']}, p={r['p_ge_observed']}")
    else:
        report.append("  No n-gram overlaps are significant at p < 0.01.")
        report.append("  Cross-cipher n-gram structure is consistent with independent sampling.")

    with open(OUT / "ngram_overlap_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    with open(OUT / "ngram_overlap_tables.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(table_rows[0].keys()))
        w.writeheader()
        w.writerows(table_rows)

    print(f"Task 3: wrote ngram_overlap_report.txt + tables.csv ({len(table_rows)} rows)")
    for r in table_rows:
        if r["n"] == 2:
            print(f"  2-gram {r['pair']}: obs={r['observed']}, z={r['z']:.2f}, p={r['p_ge_observed']:.4f}")


if __name__ == "__main__":
    main()
