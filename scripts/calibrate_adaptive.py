"""
Adaptive calibration: compute thresholds from Cipher 2 baseline and random,
write calibration.json for use by other scripts.
"""

import json
import math
import random
import re
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from constraints.overlap_engine import load_cipher

OUT = Path("output/phase92")
OUT.mkdir(parents=True, exist_ok=True)


def get_doi_words():
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    doi = text[start:end + len("honor(1322) .")]
    return [m.group(1) for m in re.finditer(r'(\w[\w\'-]*)\(\d+\)', doi)]


def main():
    words = get_doi_words()
    c2 = load_cipher(2)

    # C2 decode
    c2_stream = ''.join(
        words[cn - 1][0].upper() if 0 <= cn - 1 < len(words) else '?'
        for cn in c2
    )
    c2_letters = ''.join(c for c in c2_stream if c.isalpha())
    c2_wp = score_word_patterns(c2_letters)
    c2_qg = quadgram_score(c2_letters)

    # Random baselines (multiple samples for std estimation)
    rand_covs, rand_longs, rand_qgs = [], [], []
    for seed in range(50):
        rng = random.Random(seed)
        rs = ''.join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(520))
        wp = score_word_patterns(rs)
        rand_covs.append(wp["word_coverage"])
        rand_longs.append(wp["long_word_count"])
        rand_qgs.append(quadgram_score(rs))

    rand_cov_mean = sum(rand_covs) / len(rand_covs)
    rand_cov_std = (sum((x - rand_cov_mean)**2 for x in rand_covs) / len(rand_covs))**0.5
    rand_qg_mean = sum(rand_qgs) / len(rand_qgs)
    rand_qg_std = (sum((x - rand_qg_mean)**2 for x in rand_qgs) / len(rand_qgs))**0.5

    # Adaptive thresholds
    cov_min = max(rand_cov_mean + 8 * rand_cov_std, 0.60 * c2_wp["word_coverage"])
    long_min = max(3, math.ceil(0.5 * c2_wp["long_word_count"]))
    qg_min = (rand_qg_mean + c2_qg) / 2  # midpoint

    cal = {
        "generated": datetime.now().isoformat(),
        "c2_baseline": {
            "coverage": c2_wp["word_coverage"],
            "long_words_6plus": c2_wp["long_word_count"],
            "quadgram": round(c2_qg, 4),
            "length": len(c2_letters),
        },
        "random_baseline": {
            "coverage_mean": round(rand_cov_mean, 5),
            "coverage_std": round(rand_cov_std, 5),
            "long_words_mean": round(sum(rand_longs) / len(rand_longs), 2),
            "quadgram_mean": round(rand_qg_mean, 4),
            "quadgram_std": round(rand_qg_std, 4),
        },
        "adaptive_thresholds": {
            "coverage_min": round(cov_min, 4),
            "long_words_min": long_min,
            "quadgram_min": round(qg_min, 4),
            "notes": "coverage_min = max(rand+8sigma, 0.60*C2); long_min = max(3, ceil(0.5*C2)); qg_min = midpoint(rand, C2)"
        },
    }

    json_path = OUT / "calibration.json"
    with open(json_path, "w") as f:
        json.dump(cal, f, indent=2)

    txt_path = OUT / "calibration.txt"
    with open(txt_path, "w") as f:
        f.write(f"Phase 92 Adaptive Calibration\n{'='*50}\n")
        f.write(f"Generated: {cal['generated']}\n\n")
        f.write(f"C2 Baseline:\n")
        f.write(f"  coverage:    {cal['c2_baseline']['coverage']:.4f}\n")
        f.write(f"  long_words:  {cal['c2_baseline']['long_words_6plus']}\n")
        f.write(f"  quadgram:    {cal['c2_baseline']['quadgram']}\n\n")
        f.write(f"Random Baseline (50 samples):\n")
        f.write(f"  coverage:    {cal['random_baseline']['coverage_mean']:.5f} +/- {cal['random_baseline']['coverage_std']:.5f}\n")
        f.write(f"  quadgram:    {cal['random_baseline']['quadgram_mean']} +/- {cal['random_baseline']['quadgram_std']}\n\n")
        f.write(f"Adaptive Thresholds:\n")
        f.write(f"  coverage_min:   {cal['adaptive_thresholds']['coverage_min']:.4f}\n")
        f.write(f"  long_words_min: {cal['adaptive_thresholds']['long_words_min']}\n")
        f.write(f"  quadgram_min:   {cal['adaptive_thresholds']['quadgram_min']}\n")
        f.write(f"  formula:        {cal['adaptive_thresholds']['notes']}\n")

    print(f"Calibration: {json_path}")
    print(f"  C2 coverage={cal['c2_baseline']['coverage']:.4f}, long={cal['c2_baseline']['long_words_6plus']}, qg={cal['c2_baseline']['quadgram']}")
    print(f"  Rand coverage={cal['random_baseline']['coverage_mean']:.5f}+/-{cal['random_baseline']['coverage_std']:.5f}")
    print(f"  Thresholds: cov>={cal['adaptive_thresholds']['coverage_min']:.4f}, long>={cal['adaptive_thresholds']['long_words_min']}, qg>={cal['adaptive_thresholds']['quadgram_min']:.3f}")


if __name__ == "__main__":
    main()
