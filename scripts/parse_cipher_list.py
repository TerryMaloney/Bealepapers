"""
Phase 102 Task 2: Robust parsing + normalization of cipher number lists.

Accepts commas, spaces, newlines, stray punctuation.
Emits clean list of ints.
Flags: 4-digit runs (>=1000), non-numeric fragments, adjacent merge candidates.
Writes output/phase102/parse_warnings_<cipher>.txt
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUT = PROJECT_ROOT / "output" / "phase102"


def parse_cipher_list(raw: str) -> Tuple[List[int], List[str]]:
    """
    Parse raw text into list of integers. Return (numbers, warnings).
    Handles commas, spaces, newlines, stray punctuation.
    """
    warnings = []
    # Normalize: replace various separators with space, then split
    combined = raw.replace(",", " ").replace("\n", " ").replace("\r", " ")
    combined = re.sub(r"[\s]+", " ", combined).strip()
    parts = combined.split()
    numbers = []
    for i, p in enumerate(parts):
        s = p.strip().rstrip(".")
        if not s:
            continue
        if s.isdigit():
            n = int(s)
            numbers.append(n)
            if n >= 1000:
                warnings.append(f"four_digit pos={len(numbers)-1} value={n}")
        else:
            # Non-numeric fragment
            cleaned = re.sub(r"[^0-9]", "", s)
            if cleaned:
                numbers.append(int(cleaned))
                warnings.append(f"non_numeric_fragment pos={len(numbers)-1} raw={s!r} parsed={cleaned}")
            else:
                warnings.append(f"skip_non_numeric pos={i} raw={s!r}")

    # Adjacent pairs that could be merged into 4-digit (e.g. 17, 01 -> 1701)
    merge_count = 0
    for j in range(len(numbers) - 1):
        a, b = numbers[j], numbers[j + 1]
        if a < 1000 and b < 1000:
            merged_1_3 = a * 1000 + b if a < 10 and b >= 100 else None
            merged_2_2 = a * 100 + b if a < 100 and b < 100 else None
            merged_3_1 = a * 10 + b if a >= 100 and b < 10 else None
            for val, label in [(merged_1_3, "1_3"), (merged_2_2, "2_2"), (merged_3_1, "3_1")]:
                if val and 1000 <= val <= 9999:
                    if merge_count < 30:
                        warnings.append(f"merge_candidate pos={j},{j+1} values=({a},{b}) could_be_{label}={val}")
                    merge_count += 1
                    break
    if merge_count > 30:
        warnings.append(f"(merge_candidate total={merge_count}, showing first 30)")

    return numbers, warnings


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    from constraints.overlap_engine import load_cipher

    for cipher_num in [1, 3]:
        nums = load_cipher(cipher_num)
        # Represent as comma-separated string (simulating raw input) then re-parse to get warnings
        raw = ",".join(str(x) for x in nums)
        parsed, warnings = parse_cipher_list(raw)
        # Also parse from file to catch any file-level quirks
        if cipher_num == 1:
            path = PROJECT_ROOT / "corpus" / "cipher1_numbers_canonical.txt"
        else:
            path = PROJECT_ROOT / "corpus" / "cipher3_numbers_canonical.txt"
        with open(path, "r", encoding="utf-8") as f:
            file_raw = f.read()
        _, file_warnings = parse_cipher_list(file_raw)
        all_warnings = list(dict.fromkeys(warnings + file_warnings))

        out_path = OUT / f"parse_warnings_c{cipher_num}.txt"
        lines = [
            f"Parse warnings for Cipher {cipher_num}",
            f"Total numbers: {len(parsed)}",
            f"Min: {min(parsed)}, Max: {max(parsed)}",
            "",
            f"Warnings ({len(all_warnings)}):",
        ]
        for w in all_warnings:
            lines.append(f"  {w}")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Task 2: wrote {out_path} ({len(all_warnings)} warnings)")


if __name__ == "__main__":
    main()
