"""
Cross-cipher n-gram overlap (Phase 98 Step 5).

Compute shared 2- through 5-grams across C1/C2/C3. Compare against 1000 shuffled
sequences (preserve unigram counts). Report significance (p-value) and list top
shared n-grams with their decoded letters from DOI.

Outputs: ngram_overlap_report.txt, ngram_overlap_tables.csv
"""

import csv
import random
import sys
from pathlib import Path
from typing import List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher
from corpus.beale_doi_adjusted import get_adjusted_tokens

OUT_DIR = PROJECT_ROOT / "output" / "phase98"
N_SHUFFLE = 1000
SEED_NGRAM = 88765


def ngrams(seq: List[int], n: int) -> Set[Tuple[int, ...]]:
    out = set()
    for i in range(len(seq) - n + 1):
        out.add(tuple(seq[i : i + n]))
    return out


def count_shared_3way(s1: Set, s2: Set, s3: Set) -> int:
    return len(s1 & s2 & s3)


def count_shared_any2(s1: Set, s2: Set, s3: Set) -> int:
    return len((s1 & s2) | (s1 & s3) | (s2 & s3))


def decode_ngram_doi(ng: Tuple[int, ...], tokens: List[str]) -> str:
    return "".join(
        tokens[n - 1][0].upper() if 0 <= n - 1 < len(tokens) and tokens[n - 1] else "?"
        for n in ng
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c1 = load_cipher(1)
    c2 = load_cipher(2)
    c3 = load_cipher(3)
    doi_tokens = get_adjusted_tokens()

    report = []
    table_rows = []

    for n in range(2, 6):
        g1 = ngrams(c1, n)
        g2 = ngrams(c2, n)
        g3 = ngrams(c3, n)
        shared_3 = count_shared_3way(g1, g2, g3)
        shared_any2 = count_shared_any2(g1, g2, g3)
        report.append(f"--- {n}-grams ---")
        report.append(f"  C1: {len(g1)} unique  C2: {len(g2)}  C3: {len(g3)}")
        report.append(f"  Shared (all 3): {shared_3}")
        report.append(f"  Shared (any 2): {shared_any2}")

        # Null: shuffle each cipher (preserve unigram), recompute
        random.seed(SEED_NGRAM + n)
        null_3 = []
        null_any2 = []
        for _ in range(N_SHUFFLE):
            s1 = c1.copy()
            s2 = c2.copy()
            s3 = c3.copy()
            random.shuffle(s1)
            random.shuffle(s2)
            random.shuffle(s3)
            ng1 = ngrams(s1, n)
            ng2 = ngrams(s2, n)
            ng3 = ngrams(s3, n)
            null_3.append(count_shared_3way(ng1, ng2, ng3))
            null_any2.append(count_shared_any2(ng1, ng2, ng3))

        mean_3 = sum(null_3) / len(null_3)
        mean_any2 = sum(null_any2) / len(null_any2)
        # p-value: fraction of null >= observed (one-sided, "more overlap than chance")
        p_3 = sum(1 for x in null_3 if x >= shared_3) / len(null_3)
        p_any2 = sum(1 for x in null_any2 if x >= shared_any2) / len(null_any2)
        report.append(f"  Null (3-way): mean={mean_3:.2f}  p(observed >= null)={p_3:.4f}")
        report.append(f"  Null (any-2): mean={mean_any2:.2f}  p={p_any2:.4f}")

        # Top shared n-grams (all 3) with DOI decoded letters
        common = g1 & g2 & g3
        top_ng = sorted(common, key=lambda ng: decode_ngram_doi(ng, doi_tokens))[:30]
        report.append(f"  Sample shared {n}-grams (DOI decoded):")
        for ng in top_ng[:10]:
            report.append(f"    {ng} -> {decode_ngram_doi(ng, doi_tokens)}")
        for ng in top_ng:
            table_rows.append({
                "n": n,
                "ngram": str(ng),
                "doi_decoded": decode_ngram_doi(ng, doi_tokens),
                "shared_3": shared_3,
                "p_value_3": round(p_3, 4),
                "shared_any2": shared_any2,
                "p_value_any2": round(p_any2, 4),
            })
        report.append("")

    with open(OUT_DIR / "ngram_overlap_report.txt", "w", encoding="utf-8") as f:
        f.write("Phase 98 Cross-Cipher N-gram Overlap\n")
        f.write("=" * 50 + "\n\n")
        f.write("\n".join(report))

    with open(OUT_DIR / "ngram_overlap_tables.csv", "w", newline="", encoding="utf-8") as f:
        if table_rows:
            w = csv.DictWriter(f, fieldnames=["n", "ngram", "doi_decoded", "shared_3", "p_value_3", "shared_any2", "p_value_any2"])
            w.writeheader()
            w.writerows(table_rows)

    print(f"Wrote {OUT_DIR / 'ngram_overlap_report.txt'}, ngram_overlap_tables.csv")


if __name__ == "__main__":
    main()
