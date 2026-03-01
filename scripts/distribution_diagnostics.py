"""
Distribution diagnostics: compare C1/C2/C3 number streams statistically.

If C1/C3 are book ciphers like C2, their number distributions should be
similar (many unique values, low repetition, similar entropy). If they're
a different cipher class or fabricated, the statistics will diverge.
"""

import sys
import math
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher

OUT_DIR = Path("output/phase90")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def analyze_cipher(name, nums):
    """Compute distribution statistics for a cipher number stream."""
    n = len(nums)
    unique = len(set(nums))
    counts = Counter(nums)

    # Repetition profile
    max_val = max(nums)
    min_val = min(nums)
    mean_val = sum(nums) / n
    median_val = sorted(nums)[n // 2]

    # Entropy (Shannon)
    entropy = 0
    for c in counts.values():
        p = c / n
        entropy -= p * math.log2(p)

    # Max entropy for this many symbols
    max_entropy = math.log2(unique) if unique > 1 else 0

    # IC on symbol stream (index of coincidence)
    ic = sum(c * (c - 1) for c in counts.values()) / (n * (n - 1)) if n > 1 else 0

    # Bigram repetition
    bigrams = Counter()
    for i in range(n - 1):
        bigrams[(nums[i], nums[i+1])] += 1
    repeated_bigrams = sum(1 for c in bigrams.values() if c > 1)

    # Singleton rate
    singletons = sum(1 for c in counts.values() if c == 1)

    # Digit distribution
    all_digits = ''.join(str(n) for n in nums)
    digit_counts = Counter(all_digits)

    # Numbers by length
    len_dist = Counter(len(str(n)) for n in nums)

    return {
        "name": name,
        "count": n,
        "unique": unique,
        "unique_pct": unique / n * 100,
        "min": min_val,
        "max": max_val,
        "mean": mean_val,
        "median": median_val,
        "entropy": entropy,
        "max_entropy": max_entropy,
        "entropy_ratio": entropy / max_entropy if max_entropy > 0 else 0,
        "ic": ic,
        "top20": counts.most_common(20),
        "singletons": singletons,
        "singleton_pct": singletons / unique * 100,
        "repeated_bigrams": repeated_bigrams,
        "total_bigrams": len(bigrams),
        "bigram_repeat_pct": repeated_bigrams / len(bigrams) * 100 if bigrams else 0,
        "digit_dist": dict(sorted(digit_counts.items())),
        "len_dist": dict(sorted(len_dist.items())),
    }


def main():
    c1 = load_cipher(1)
    c2 = load_cipher(2)
    c3 = load_cipher(3)

    analyses = [
        analyze_cipher("Cipher 1 (location)", c1),
        analyze_cipher("Cipher 2 (contents, SOLVED)", c2),
        analyze_cipher("Cipher 3 (names)", c3),
    ]

    report_path = OUT_DIR / "number_distribution_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("NUMBER DISTRIBUTION DIAGNOSTICS\n")
        f.write(f"Command: python scripts/distribution_diagnostics.py\n")
        f.write("=" * 80 + "\n\n")

        # Comparison table
        f.write(f"{'Metric':30s} {'Cipher 1':>12s} {'Cipher 2':>12s} {'Cipher 3':>12s}\n")
        f.write("-" * 70 + "\n")

        metrics = [
            ("Count", "count", "d"),
            ("Unique symbols", "unique", "d"),
            ("Unique %", "unique_pct", ".1f"),
            ("Min value", "min", "d"),
            ("Max value", "max", "d"),
            ("Mean value", "mean", ".1f"),
            ("Median value", "median", "d"),
            ("Shannon entropy (bits)", "entropy", ".2f"),
            ("Max entropy (bits)", "max_entropy", ".2f"),
            ("Entropy ratio", "entropy_ratio", ".3f"),
            ("Index of coincidence", "ic", ".5f"),
            ("Singletons", "singletons", "d"),
            ("Singleton %", "singleton_pct", ".1f"),
            ("Repeated bigrams", "repeated_bigrams", "d"),
            ("Total unique bigrams", "total_bigrams", "d"),
            ("Bigram repeat %", "bigram_repeat_pct", ".1f"),
        ]

        for label, key, fmt in metrics:
            vals = [a[key] for a in analyses]
            line = f"{label:30s}"
            for v in vals:
                line += f" {v:>12{fmt}}"
            f.write(line + "\n")

        # Number length distributions
        f.write("\n\nNUMBER LENGTH DISTRIBUTION:\n")
        f.write("-" * 70 + "\n")
        for a in analyses:
            f.write(f"\n{a['name']}:\n")
            for length, count in sorted(a["len_dist"].items()):
                pct = count / a["count"] * 100
                f.write(f"  {length}-digit: {count:4d} ({pct:5.1f}%)\n")

        # Digit frequency
        f.write("\n\nDIGIT FREQUENCY:\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'Digit':>6s}")
        for a in analyses:
            f.write(f" {a['name'][:10]:>12s}")
        f.write("\n")
        for d in "0123456789":
            f.write(f"{d:>6s}")
            for a in analyses:
                c = a["digit_dist"].get(d, 0)
                total = sum(a["digit_dist"].values())
                f.write(f" {c/total*100:>11.1f}%")
            f.write("\n")

        # Top 20 most frequent numbers
        f.write("\n\nTOP 20 MOST FREQUENT NUMBERS:\n")
        f.write("-" * 70 + "\n")
        for a in analyses:
            f.write(f"\n{a['name']}:\n")
            for num, cnt in a["top20"]:
                f.write(f"  {num:5d} x {cnt:2d}\n")

        # Diagnostic verdict
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("DIAGNOSTIC VERDICT\n")
        f.write("=" * 80 + "\n")

        a1, a2, a3 = analyses

        f.write(f"\nC2 (known book cipher) profile:\n")
        f.write(f"  unique%={a2['unique_pct']:.1f}, entropy_ratio={a2['entropy_ratio']:.3f}, ")
        f.write(f"IC={a2['ic']:.5f}, bigram_repeat%={a2['bigram_repeat_pct']:.1f}\n")

        for a in [a1, a3]:
            f.write(f"\n{a['name']} vs C2:\n")
            diffs = []
            if abs(a["unique_pct"] - a2["unique_pct"]) > 10:
                diffs.append(f"unique% differs: {a['unique_pct']:.1f} vs {a2['unique_pct']:.1f}")
            if abs(a["entropy_ratio"] - a2["entropy_ratio"]) > 0.1:
                diffs.append(f"entropy_ratio differs: {a['entropy_ratio']:.3f} vs {a2['entropy_ratio']:.3f}")
            if abs(a["ic"] - a2["ic"]) > 0.005:
                diffs.append(f"IC differs: {a['ic']:.5f} vs {a2['ic']:.5f}")

            if diffs:
                f.write("  DIVERGENCES:\n")
                for d in diffs:
                    f.write(f"    - {d}\n")
            else:
                f.write("  Consistent with book-cipher class.\n")

    print(f"Report: {report_path}")

    # Also print summary
    print(f"\n{'Metric':30s} {'C1':>8s} {'C2':>8s} {'C3':>8s}")
    print("-" * 58)
    for label, key, fmt in metrics[:11]:
        vals = [a[key] for a in analyses]
        print(f"{label:30s}" + "".join(f" {v:>8{fmt}}" for v in vals))


if __name__ == "__main__":
    main()
