"""
Phase 100 Task A: Cipher stream structural profiler (no key text).

Computes: length, unique count, singleton rate, repetition histogram,
first-digit / last-digit distributions, entropy proxies, autocorrelation,
repeated n-grams in number space.  Compares C1 vs C2 vs C3.

Outputs: output/phase100/c1_profile.json, c2_profile.json, c3_profile.json
"""

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher

OUT = PROJECT_ROOT / "output" / "phase100"


def first_digit(n: int) -> int:
    return int(str(abs(n))[0])


def last_digit(n: int) -> int:
    return int(str(abs(n))[-1])


def shannon_entropy(nums: List[int]) -> float:
    n = len(nums)
    if n == 0:
        return 0.0
    counts = Counter(nums)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def index_of_coincidence(nums: List[int]) -> float:
    n = len(nums)
    if n < 2:
        return 0.0
    counts = Counter(nums)
    return sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))


def autocorrelation(nums: List[int], max_lag: int = 30) -> Dict[int, float]:
    n = len(nums)
    mean = sum(nums) / n
    var = sum((x - mean) ** 2 for x in nums) / n
    if var == 0:
        return {lag: 0.0 for lag in range(1, max_lag + 1)}
    result = {}
    for lag in range(1, min(max_lag + 1, n)):
        cov = sum((nums[i] - mean) * (nums[i + lag] - mean) for i in range(n - lag)) / (n - lag)
        result[lag] = round(cov / var, 6)
    return result


def repeated_ngrams(nums: List[int], max_n: int = 5) -> Dict[str, int]:
    result = {}
    for n in range(2, max_n + 1):
        grams = Counter()
        for i in range(len(nums) - n + 1):
            grams[tuple(nums[i:i + n])] += 1
        repeated = sum(1 for c in grams.values() if c > 1)
        total = len(grams)
        result[f"{n}gram_unique"] = total
        result[f"{n}gram_repeated"] = repeated
        result[f"{n}gram_repeated_pct"] = round(100 * repeated / total, 2) if total else 0
    return result


def repetition_histogram(nums: List[int]) -> Dict[int, int]:
    counts = Counter(nums)
    freq_of_freq = Counter(counts.values())
    return {int(k): v for k, v in sorted(freq_of_freq.items())}


def digit_distribution(nums: List[int], func) -> Dict[str, float]:
    digits = [func(n) for n in nums]
    n = len(digits)
    counts = Counter(digits)
    return {str(d): round(counts.get(d, 0) / n, 4) for d in range(10)}


def consecutive_diffs(nums: List[int]) -> Dict[str, float]:
    if len(nums) < 2:
        return {}
    diffs = [nums[i + 1] - nums[i] for i in range(len(nums) - 1)]
    abs_diffs = [abs(d) for d in diffs]
    return {
        "mean_abs_diff": round(sum(abs_diffs) / len(abs_diffs), 2),
        "median_abs_diff": sorted(abs_diffs)[len(abs_diffs) // 2],
        "pct_ascending": round(100 * sum(1 for d in diffs if d > 0) / len(diffs), 2),
        "pct_descending": round(100 * sum(1 for d in diffs if d < 0) / len(diffs), 2),
        "pct_equal": round(100 * sum(1 for d in diffs if d == 0) / len(diffs), 2),
        "longest_monotone_up": _longest_monotone(diffs, positive=True),
        "longest_monotone_down": _longest_monotone(diffs, positive=False),
    }


def _longest_monotone(diffs: List[int], positive: bool) -> int:
    best = 0
    run = 0
    for d in diffs:
        if (positive and d > 0) or (not positive and d < 0):
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def number_length_dist(nums: List[int]) -> Dict[str, float]:
    lengths = [len(str(n)) for n in nums]
    n = len(lengths)
    counts = Counter(lengths)
    return {str(k): round(v / n, 4) for k, v in sorted(counts.items())}


def build_profile(name: str, nums: List[int]) -> Dict:
    counts = Counter(nums)
    singletons = sum(1 for c in counts.values() if c == 1)
    return {
        "cipher": name,
        "length": len(nums),
        "unique_count": len(set(nums)),
        "unique_pct": round(100 * len(set(nums)) / len(nums), 2),
        "singleton_count": singletons,
        "singleton_pct": round(100 * singletons / len(nums), 2),
        "min": min(nums),
        "max": max(nums),
        "mean": round(sum(nums) / len(nums), 2),
        "median": sorted(nums)[len(nums) // 2],
        "shannon_entropy": round(shannon_entropy(nums), 4),
        "max_entropy_log2_unique": round(math.log2(len(set(nums))), 4) if len(set(nums)) > 1 else 0,
        "entropy_ratio": round(shannon_entropy(nums) / math.log2(len(set(nums))), 4) if len(set(nums)) > 1 else 0,
        "index_of_coincidence": round(index_of_coincidence(nums), 6),
        "repetition_histogram": repetition_histogram(nums),
        "first_digit_dist": digit_distribution(nums, first_digit),
        "last_digit_dist": digit_distribution(nums, last_digit),
        "number_length_dist": number_length_dist(nums),
        "consecutive_diffs": consecutive_diffs(nums),
        "autocorrelation": autocorrelation(nums, 30),
        "repeated_ngrams": repeated_ngrams(nums, 5),
        "top_10_most_frequent": [
            {"number": num, "count": cnt}
            for num, cnt in counts.most_common(10)
        ],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ciphers = {"c1": load_cipher(1), "c2": load_cipher(2), "c3": load_cipher(3)}
    profiles = {}
    for name, nums in ciphers.items():
        p = build_profile(name, nums)
        profiles[name] = p
        path = OUT / f"{name}_profile.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)
        print(f"  {name}: {p['length']} nums, {p['unique_count']} unique ({p['unique_pct']}%), "
              f"IC={p['index_of_coincidence']:.6f}, entropy_ratio={p['entropy_ratio']:.4f}")
    print(f"Profiles saved to {OUT}")
    return profiles


if __name__ == "__main__":
    main()
