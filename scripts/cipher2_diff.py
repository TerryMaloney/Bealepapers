"""
Cipher 2 diff diagnostic: compare cipher2 number lists (e.g. current vs canonical).

Run from project root: python scripts/cipher2_diff.py
Compare specific files: python scripts/cipher2_diff.py --current beale_papers.txt --canonical corpus/cipher2_numbers_canonical.txt

Output format suitable for sharing to diagnose transcription corruption.
"""

import argparse
import sys
from pathlib import Path

# Add project root for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oracle.cipher2_evaluator import load_cipher2


def _load_from_path(path: Path) -> list:
    """Load Cipher 2 from file. Handles beale_papers and canonical formats."""
    p = path if path.is_absolute() else PROJECT_ROOT / path
    return load_cipher2(path=p)


def main():
    parser = argparse.ArgumentParser(description="Diff Cipher 2 number lists")
    parser.add_argument(
        "--current",
        default="beale_papers.txt",
        help="Path to 'current' list (default: beale_papers.txt)",
    )
    parser.add_argument(
        "--canonical",
        default="corpus/cipher2_numbers_canonical.txt",
        help="Path to canonical/list B (default: corpus/cipher2_numbers_canonical.txt)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print(f"Cipher 2 diff: current ({args.current}) vs canonical ({args.canonical})")
    print("=" * 70)

    curr = _load_from_path(Path(args.current))
    canon = _load_from_path(Path(args.canonical))

    len_curr = len(curr)
    len_canon = len(canon)
    len_mismatch = abs(len_curr - len_canon)

    print(f"\nLength: current={len_curr}, canonical={len_canon}, mismatch={len_mismatch}")

    # Value mismatches by index (align by position)
    value_mismatches = []
    for i in range(min(len_curr, len_canon)):
        if curr[i] != canon[i]:
            value_mismatches.append((i, curr[i], canon[i]))
    value_mismatches = value_mismatches[:20]

    print(f"\nValue mismatches (first 20): {value_mismatches}")
    if len(value_mismatches) < 20 and len(curr) != len(canon):
        extra = max(0, len_curr - len_canon)
        if extra > 0:
            print(f"  (+ {len_curr - len_canon} extra numbers in current at end)")
        else:
            print(f"  (+ {len_canon - len_curr} extra numbers in canonical at end)")

    # Suspicious merges
    merge_count = 0
    for i in range(min(len_curr, len_canon) - 1):
        # Check: canonical has A, B that could merge to AB in current
        a, b = canon[i], canon[i + 1]
        if a < 100 and b < 100 and 10 <= a and 10 <= b:
            merged = a * 10 + b if b < 10 else int(str(a) + str(b))
            if merged >= 100 and merged <= 999:
                for j in range(max(0, i - 2), min(len_curr, i + 3)):
                    if j < len(curr) and curr[j] == merged:
                        merge_count += 1
                        break

    # Simpler: count occurrences of 108 in curr but 10,8 in canon
    def _seq_str(lst):
        return ",".join(str(x) for x in lst)

    curr_str = _seq_str(curr)
    canon_str = _seq_str(canon)
    suspicious_108 = "108" in curr_str and "10, 8" in canon_str
    print(f"\nSuspicious merges (e.g. 108 vs 10,8): {merge_count}")
    if suspicious_108:
        print("  [NOTE] Canonical has 10,8; check if current has 108 at same region")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
