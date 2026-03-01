"""
Phase 102 Task 6: Manual verification templates (double-entry).

Blocks of 25 numbers per row. Columns: block_id, position_range, numbers, entry_A, entry_B, auto_diff.
"""

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher

OUT = PROJECT_ROOT / "output" / "phase102" / "manual_verify"
BLOCK_SIZE = 25


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, cipher_num in [("c1", 1), ("c3", 3)]:
        nums = load_cipher(cipher_num)
        rows = []
        for start in range(0, len(nums), BLOCK_SIZE):
            block = nums[start:start + BLOCK_SIZE]
            block_id = start // BLOCK_SIZE + 1
            position_range = f"{start}-{min(start + BLOCK_SIZE, len(nums)) - 1}"
            numbers_str = ",".join(str(n) for n in block)
            rows.append({
                "block_id": block_id,
                "position_range": position_range,
                "numbers": numbers_str,
                "entry_A": "",
                "entry_B": "",
                "auto_diff": "",
            })
        path = OUT / f"{name}_blocks.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["block_id", "position_range", "numbers", "entry_A", "entry_B", "auto_diff"])
            w.writeheader()
            w.writerows(rows)
        print(f"Task 6: wrote {path} ({len(rows)} blocks)")
    # Optional: add a small script that reads entry_A and entry_B and reports diffs
    diff_script = OUT / "diff_instructions.txt"
    diff_script.write_text(
        "Double-entry verification: fill entry_A and entry_B independently from the same source.\n"
        "Then run: python -c \"import csv; f=open('c1_blocks.csv'); r=csv.DictReader(f); "
        "[print(f\"Block {row['block_id']}: A==B\") if row['entry_A']==row['entry_B'] else print(f\"Block {row['block_id']}: MISMATCH\") for row in r]\"\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
