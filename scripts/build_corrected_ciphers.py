"""
Build corrected canonical cipher files.

Cipher 2 - Wikipedia documents 6 transcription errors:
- 96 should be 95 (varlt -> vault)
- 84 should be 85 x2 (thc -> the, consistcd -> consisted)
- 440 should be 40 (uith -> with)
- 108 should be 10,8 (itron -> in iron) - beale_papers already has 10,8
- 53 should be 54 (rhousand -> thousand)

Cipher 3 - FSU vs beale_papers divergence (2 values):
- position 91: beale_papers has 151, FSU has 154 → adopt FSU 154
- position ~580: beale_papers has 63, FSU has 73 → adopt FSU 73

Run from project root: python scripts/build_corrected_ciphers.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_bp_cipher(n: int) -> list:
    with open(PROJECT_ROOT / "beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    idx = {1: 2, 2: 58, 3: 6}[n]
    line = lines[idx].strip()
    return [int(x.strip()) for x in line.split(",") if x.strip().replace(".", "").isdigit()]


def apply_wikipedia_corrections_c2(nums: list) -> list:
    """Apply Wikipedia's 6 documented Cipher 2 corrections."""
    nums = list(nums)
    n = len(nums)

    # 1. 96 -> 95 in context "807, 81, 96, 405" (vault)
    for i in range(n - 3):
        if nums[i] == 807 and nums[i + 1] == 81 and nums[i + 2] == 96 and nums[i + 3] == 405:
            nums[i + 2] = 95
            break

    # 2. 440 -> 40 in context before 370 (with). Find "440, 370"
    for i in range(n - 1):
        if nums[i] == 440 and nums[i + 1] == 370:
            nums[i] = 40
            break
    # Also "118, 440" if followed by 370 - we might have 40 already. Check "84, 440, 42"
    for i in range(n - 2):
        if nums[i] == 84 and nums[i + 1] == 440 and nums[i + 2] == 42:
            nums[i + 1] = 40
            break

    # 3. 53 -> 54 in context "53, 20, 125, 371" (thousand)
    for i in range(n - 3):
        if nums[i] == 53 and nums[i + 1] == 20 and nums[i + 2] == 125 and nums[i + 3] == 371:
            nums[i] = 54
            break

    # 4. First 84->85 for "thc" (the): context "14, 73, 84" near start
    for i in range(min(150, n - 2)):
        if nums[i] == 14 and nums[i + 1] == 73 and nums[i + 2] == 84:
            nums[i + 2] = 85
            break

    # 5. Second 84->85 for "consistcd": context "57, 540, 217, 115, 71, 29, 84, 63"
    for i in range(n - 7):
        if (nums[i] == 57 and nums[i + 1] == 540 and nums[i + 2] == 217 and
                nums[i + 3] == 115 and nums[i + 4] == 71 and nums[i + 5] == 29 and
                nums[i + 6] == 84 and nums[i + 7] == 63):
            nums[i + 6] = 85
            break

    return nums


def apply_fsu_corrections_c3(nums: list) -> list:
    """Apply FSU-sourced corrections for Cipher 3 (2 mismatches)."""
    nums = list(nums)
    n = len(nums)

    # 1. Position 91 (0-indexed): 151 -> 154
    #    Context: ...136, 48, 151, 99, 175...
    for i in range(n - 2):
        if nums[i] == 48 and nums[i + 1] == 151 and nums[i + 2] == 99:
            nums[i + 1] = 154
            print(f"  C3 correction: idx {i+1}: 151 -> 154 (FSU)")
            break

    # 2. Near position 580 (0-indexed): 63 -> 73
    #    Context: ...32, 47, 63, 96, 124...  (near end of cipher)
    for i in range(max(0, n - 50), n - 2):
        if nums[i] == 47 and nums[i + 1] == 63 and nums[i + 2] == 96:
            nums[i + 1] = 73
            print(f"  C3 correction: idx {i+1}: 63 -> 73 (FSU)")
            break

    return nums


def main():
    # Cipher 1: use beale_papers as-is (no Wikipedia corrections)
    c1 = load_bp_cipher(1)
    path1 = PROJECT_ROOT / "corpus" / "cipher1_numbers_canonical.txt"
    path1.parent.mkdir(parents=True, exist_ok=True)
    with open(path1, "w", encoding="utf-8") as f:
        f.write("# Cipher 1 canonical - beale_papers.txt line 3\n")
        f.write(", ".join(str(x) for x in c1) + "\n")
    print(f"Wrote {path1} ({len(c1)} numbers)")

    # Cipher 2: apply Wikipedia corrections
    c2 = load_bp_cipher(2)
    c2_corrected = apply_wikipedia_corrections_c2(c2)
    path2 = PROJECT_ROOT / "corpus" / "cipher2_numbers_canonical.txt"
    with open(path2, "w", encoding="utf-8") as f:
        f.write("# Cipher 2 canonical - beale_papers + Wikipedia corrections (96->95, 440->40, 53->54, 84->85 x2)\n")
        f.write(", ".join(str(x) for x in c2_corrected) + "\n")
    print(f"Wrote {path2} ({len(c2_corrected)} numbers)")

    # Cipher 3: apply FSU-sourced corrections
    c3 = load_bp_cipher(3)
    c3_corrected = apply_fsu_corrections_c3(c3)
    path3 = PROJECT_ROOT / "corpus" / "cipher3_numbers_canonical.txt"
    with open(path3, "w", encoding="utf-8") as f:
        f.write("# Cipher 3 canonical - beale_papers + FSU corrections (151->154, 63->73)\n")
        f.write(", ".join(str(x) for x in c3_corrected) + "\n")
    print(f"Wrote {path3} ({len(c3_corrected)} numbers)")

    # Note: beale_papers.txt is kept as original source. Canonical files are the
    # corrected references used by load_cipher2() and diagnostics.


if __name__ == "__main__":
    main()
