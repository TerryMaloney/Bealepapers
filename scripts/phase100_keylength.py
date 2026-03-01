"""
Phase 100 Task B: Key length inference via occupancy models.

For each cipher, estimate the effective index-space size L (number of distinct
positions in the key text that could be drawn from) using the observed
repeat/unique structure under several sampling models:

  1. Uniform with replacement (classical occupancy)
  2. Biased (Zipf/power-law) selection
  3. Mixture: fraction p drawn from "common" pool of size L_c, rest from L_r

Validated by simulating book-cipher-like draws and confirming recovery of L.

Outputs: output/phase100/keylength_fit.csv
"""

import csv
import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher

OUT = PROJECT_ROOT / "output" / "phase100"
SEED = 100042


# --- Model 1: Uniform occupancy ---
def expected_unique_uniform(n: int, L: int) -> float:
    """E[unique values] when drawing n items uniformly from {1..L} with replacement."""
    if L <= 0:
        return 0.0
    return L * (1 - (1 - 1 / L) ** n)


def fit_uniform(n: int, k_observed: int) -> Tuple[int, int, int]:
    """Binary search for L such that E[unique] ~ k_observed. Returns (L_best, L_lo, L_hi)."""
    lo, hi = k_observed, max(k_observed * 20, n * 5)
    best_L = lo
    best_err = float("inf")
    for L in range(lo, hi + 1):
        e = expected_unique_uniform(n, L)
        err = abs(e - k_observed)
        if err < best_err:
            best_err = err
            best_L = L
        if e > k_observed + 1:
            break
    # Confidence: find L where E[unique] = k ± sqrt(k) (rough Poisson approx)
    margin = math.sqrt(k_observed)
    L_lo = best_L
    L_hi = best_L
    for L in range(max(k_observed, 1), best_L * 3):
        e = expected_unique_uniform(n, L)
        if abs(e - (k_observed - margin)) < 1.5:
            L_lo = L
        if abs(e - (k_observed + margin)) < 1.5:
            L_hi = L
    return best_L, min(L_lo, best_L), max(L_hi, best_L)


# --- Model 2: Power-law (Zipf) biased selection ---
def sim_zipf_unique(n: int, L: int, alpha: float = 1.0, trials: int = 500) -> float:
    """Simulate Zipf-biased draws and return mean unique count."""
    weights = [1.0 / (i ** alpha) for i in range(1, L + 1)]
    total_w = sum(weights)
    probs = [w / total_w for w in weights]
    cum = []
    s = 0.0
    for p in probs:
        s += p
        cum.append(s)
    uniques = []
    rng = random.Random(SEED)
    for _ in range(trials):
        seen = set()
        for _ in range(n):
            r = rng.random()
            # bisect
            lo_b, hi_b = 0, L - 1
            while lo_b < hi_b:
                mid = (lo_b + hi_b) // 2
                if cum[mid] < r:
                    lo_b = mid + 1
                else:
                    hi_b = mid
            seen.add(lo_b)
        uniques.append(len(seen))
    return sum(uniques) / len(uniques)


def fit_zipf(n: int, k_observed: int, alpha: float = 1.0) -> Tuple[int, int, int]:
    """Grid search for L under Zipf(alpha)."""
    best_L = k_observed
    best_err = float("inf")
    step = max(5, k_observed // 15)
    candidates = list(range(max(k_observed, 10), k_observed * 6, step))
    for L in candidates:
        e = sim_zipf_unique(n, L, alpha, trials=100)
        err = abs(e - k_observed)
        if err < best_err:
            best_err = err
            best_L = L
    margin = max(1, k_observed // 15)
    return best_L, max(k_observed, best_L - margin * 5), best_L + margin * 5


# --- Model 3: Mixture (common + rare pool) ---
def sim_mixture_unique(n: int, L_common: int, L_rare: int, p_common: float = 0.7,
                       trials: int = 500) -> float:
    """Simulate mixture: with prob p_common draw from {1..L_common}, else {L_common+1..L_common+L_rare}."""
    rng = random.Random(SEED + 7)
    uniques = []
    for _ in range(trials):
        seen = set()
        for _ in range(n):
            if rng.random() < p_common:
                seen.add(rng.randint(1, L_common))
            else:
                seen.add(rng.randint(L_common + 1, L_common + L_rare))
        uniques.append(len(seen))
    return sum(uniques) / len(uniques)


def fit_mixture(n: int, k_observed: int) -> Dict:
    """Coarse grid search over (L_common, L_rare, p_common)."""
    best = {"L_common": 0, "L_rare": 0, "p_common": 0.5, "L_total": 0, "error": 1e9}
    step_c = max(10, k_observed // 5)
    step_r = max(20, k_observed // 4)
    for p_common in [0.6, 0.7, 0.8]:
        for L_common in range(max(10, k_observed // 4), k_observed * 2, step_c):
            for L_rare in range(max(20, k_observed // 2), k_observed * 3, step_r):
                e = sim_mixture_unique(n, L_common, L_rare, p_common, trials=50)
                err = abs(e - k_observed)
                if err < best["error"]:
                    best = {"L_common": L_common, "L_rare": L_rare, "p_common": p_common,
                            "L_total": L_common + L_rare, "error": round(err, 2)}
    return best


# --- Validation: simulate and recover ---
def validate_fitter() -> List[Dict]:
    """Simulate book-cipher draws with known L, verify fitter recovers it."""
    rng = random.Random(SEED + 99)
    results = []
    for true_L in [200, 500, 1000, 1500, 3000]:
        for n_draws in [520, 763]:
            draws = [rng.randint(1, true_L) for _ in range(n_draws)]
            k = len(set(draws))
            fit_L, lo, hi = fit_uniform(n_draws, k)
            results.append({
                "true_L": true_L, "n": n_draws, "observed_unique": k,
                "fitted_L": fit_L, "L_lo": lo, "L_hi": hi,
                "recovered": lo <= true_L <= hi,
            })
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ciphers = {"c1": load_cipher(1), "c2": load_cipher(2), "c3": load_cipher(3)}

    rows = []
    for name, nums in ciphers.items():
        n = len(nums)
        k = len(set(nums))
        # Model 1: Uniform
        L_u, L_u_lo, L_u_hi = fit_uniform(n, k)
        # Model 2: Zipf (alpha=1.0)
        L_z, L_z_lo, L_z_hi = fit_zipf(n, k, alpha=1.0)
        # Model 3: Mixture
        mix = fit_mixture(n, k)

        rows.append({
            "cipher": name, "n": n, "observed_unique": k, "observed_max": max(nums),
            "uniform_L": L_u, "uniform_L_lo": L_u_lo, "uniform_L_hi": L_u_hi,
            "zipf_L": L_z, "zipf_L_lo": L_z_lo, "zipf_L_hi": L_z_hi,
            "mixture_L_total": mix["L_total"], "mixture_L_common": mix["L_common"],
            "mixture_L_rare": mix["L_rare"], "mixture_p_common": mix["p_common"],
        })
        print(f"  {name}: uniform_L={L_u} [{L_u_lo}-{L_u_hi}], zipf_L={L_z}, "
              f"mix_L={mix['L_total']} (common={mix['L_common']}, rare={mix['L_rare']})")

    # Validation
    val = validate_fitter()
    print(f"\n  Validation: {sum(v['recovered'] for v in val)}/{len(val)} recovered within CI")

    # Save
    path = OUT / "keylength_fit.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Save validation
    val_path = OUT / "keylength_validation.json"
    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(val, f, indent=2)

    print(f"Saved {path}, {val_path}")
    return rows, val


if __name__ == "__main__":
    main()
