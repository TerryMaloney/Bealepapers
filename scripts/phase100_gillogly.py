"""
Phase 100 Task C: Gillogly anomaly replication.

Detect near-alphabetical runs, long monotone segments, and low-entropy blocks
in C1 decoded with DOI first-letter mapping across multiple editions.

Uses Monte Carlo shuffles to compute p-values for each anomaly.

Output: output/phase100/gillogly_scan.csv
"""

import csv
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher
from corpus.beale_pamphlet_pdf import clean_pamphlet_text, tokenize_pamphlet

OUT = PROJECT_ROOT / "output" / "phase100"
N_SHUFFLE = 10000
SEED_GIL = 77700


# --- DOI edition loaders ---

def load_edition_tokens(edition_id: str) -> List[str]:
    """Load DOI edition and tokenize consistently with pamphlet tokenizer."""
    if edition_id == "beale_adjusted_doi":
        from corpus.beale_doi_adjusted import get_adjusted_tokens
        return get_adjusted_tokens()

    editions_dir = PROJECT_ROOT / "corpus" / "editions"
    path = editions_dir / f"{edition_id}.txt"
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8", errors="replace")
    cleaned = clean_pamphlet_text(raw)
    return tokenize_pamphlet(cleaned)


def decode_first_letter(tokens: List[str], cipher_nums: List[int]) -> str:
    """Decode cipher numbers to first letters of DOI tokens (1-indexed)."""
    out = []
    for n in cipher_nums:
        idx = n - 1
        if 0 <= idx < len(tokens) and tokens[idx]:
            out.append(tokens[idx][0].upper())
        else:
            out.append("?")
    return "".join(out)


# --- Anomaly detectors ---

def find_alphabetical_runs(stream: str, min_len: int = 4) -> List[Dict]:
    """Find runs where consecutive decoded letters are in ascending alphabetical order."""
    runs = []
    run_start = 0
    for i in range(1, len(stream)):
        if stream[i] >= stream[i - 1]:
            continue
        run_len = i - run_start
        if run_len >= min_len:
            runs.append({
                "type": "alpha_ascending",
                "start": run_start,
                "length": run_len,
                "text": stream[run_start:i],
            })
        run_start = i
    # Check final run
    run_len = len(stream) - run_start
    if run_len >= min_len:
        runs.append({
            "type": "alpha_ascending",
            "start": run_start,
            "length": run_len,
            "text": stream[run_start:],
        })
    return runs


def find_monotone_number_runs(nums: List[int], min_len: int = 5) -> List[Dict]:
    """Find runs where cipher numbers are monotonically increasing or decreasing."""
    runs = []
    for direction, label in [(1, "num_ascending"), (-1, "num_descending")]:
        run_start = 0
        for i in range(1, len(nums)):
            if direction == 1 and nums[i] > nums[i - 1]:
                continue
            if direction == -1 and nums[i] < nums[i - 1]:
                continue
            run_len = i - run_start
            if run_len >= min_len:
                runs.append({
                    "type": label,
                    "start": run_start,
                    "length": run_len,
                    "text": str(nums[run_start:i]),
                })
            run_start = i
        run_len = len(nums) - run_start
        if run_len >= min_len:
            runs.append({
                "type": label,
                "start": run_start,
                "length": run_len,
                "text": str(nums[run_start:]),
            })
    return runs


def find_low_entropy_windows(stream: str, window: int = 20, threshold: float = 2.5) -> List[Dict]:
    """Find windows with unusually low Shannon entropy (few distinct letters)."""
    results = []
    for i in range(len(stream) - window + 1):
        chunk = stream[i:i + window]
        counts = Counter(chunk)
        n = len(chunk)
        ent = -sum((c / n) * math.log2(c / n) for c in counts.values())
        if ent < threshold:
            results.append({
                "type": "low_entropy",
                "start": i,
                "length": window,
                "text": chunk,
                "entropy": round(ent, 4),
            })
    # Deduplicate overlapping windows: keep only local minima
    if not results:
        return []
    deduped = [results[0]]
    for r in results[1:]:
        if r["start"] > deduped[-1]["start"] + window // 2:
            deduped.append(r)
        elif r["entropy"] < deduped[-1]["entropy"]:
            deduped[-1] = r
    return deduped


# --- Monte Carlo p-value for longest alphabetical run ---

def longest_alpha_run(stream: str) -> int:
    """Length of longest ascending alphabetical run in stream."""
    if not stream:
        return 0
    best = 1
    run = 1
    for i in range(1, len(stream)):
        if stream[i] >= stream[i - 1]:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def pvalue_alpha_run(observed_len: int, stream: str, n_shuffle: int = N_SHUFFLE) -> float:
    """P-value: fraction of shuffled streams with longest alpha run >= observed."""
    rng = random.Random(SEED_GIL)
    letters = list(stream)
    count_ge = 0
    for _ in range(n_shuffle):
        rng.shuffle(letters)
        if longest_alpha_run("".join(letters)) >= observed_len:
            count_ge += 1
    return count_ge / n_shuffle


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    c1 = load_cipher(1)
    c2 = load_cipher(2)

    editions = [
        "beale_adjusted_doi",
        "nara_beale_patched",
        "avalon_yale",
        "ushistory_org",
        "stone_1823",
        "beale_embedded",
    ]

    rows = []
    for edition in editions:
        tokens = load_edition_tokens(edition)
        if len(tokens) < 100:
            print(f"  {edition}: skipped (only {len(tokens)} tokens)")
            continue

        stream = decode_first_letter(tokens, c1)
        q_count = stream.count("?")
        pct_valid = round(100 * (1 - q_count / len(stream)), 1)

        # Alpha runs
        alpha_runs = find_alphabetical_runs(stream, min_len=6)
        longest = max((r["length"] for r in alpha_runs), default=0)
        p_longest = pvalue_alpha_run(longest, stream) if longest >= 6 else 1.0

        for r in alpha_runs:
            r_pval = pvalue_alpha_run(r["length"], stream) if r["length"] >= 8 else -1
            rows.append({
                "edition": edition,
                "pct_valid": pct_valid,
                "anomaly_type": r["type"],
                "start": r["start"],
                "run_length": r["length"],
                "run_text": r["text"][:60],
                "p_value": round(r_pval, 8) if r_pval >= 0 else "",
            })

        # Monotone number runs
        mono_runs = find_monotone_number_runs(c1, min_len=6)
        for r in mono_runs:
            rows.append({
                "edition": edition,
                "pct_valid": pct_valid,
                "anomaly_type": r["type"],
                "start": r["start"],
                "run_length": r["length"],
                "run_text": r["text"][:60],
                "p_value": "",
            })

        # Low-entropy windows
        le_windows = find_low_entropy_windows(stream, window=20, threshold=2.8)
        for r in le_windows[:10]:
            rows.append({
                "edition": edition,
                "pct_valid": pct_valid,
                "anomaly_type": r["type"],
                "start": r["start"],
                "run_length": r["length"],
                "run_text": r["text"],
                "p_value": "",
            })

        print(f"  {edition}: {pct_valid}% valid, longest_alpha_run={longest}, p={p_longest:.6f}, "
              f"alpha_runs(>=6)={len(alpha_runs)}, mono_runs(>=6)={len(mono_runs)}, "
              f"low_entropy_windows={len(le_windows)}")

    # Also run on C2 as a control baseline
    tokens_adj = load_edition_tokens("beale_adjusted_doi")
    if tokens_adj:
        stream_c2 = decode_first_letter(tokens_adj, c2)
        longest_c2 = longest_alpha_run(stream_c2)
        p_c2 = pvalue_alpha_run(longest_c2, stream_c2)
        rows.append({
            "edition": "beale_adjusted_doi_C2_CONTROL",
            "pct_valid": 100.0,
            "anomaly_type": "alpha_ascending_longest",
            "start": -1,
            "run_length": longest_c2,
            "run_text": f"C2_longest_alpha_run={longest_c2}",
            "p_value": round(p_c2, 8),
        })
        print(f"  C2 control: longest_alpha_run={longest_c2}, p={p_c2:.6f}")

    path = OUT / "gillogly_scan.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        cols = ["edition", "pct_valid", "anomaly_type", "start", "run_length", "run_text", "p_value"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"Saved {path} ({len(rows)} rows)")
    return rows


if __name__ == "__main__":
    main()
