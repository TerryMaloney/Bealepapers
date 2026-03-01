"""
Comprehensive diff: Beale ciphers 1, 2, 3 vs FSU dataset.

Run from project root: python scripts/cipher_diff_all.py

Outputs:
- Length and value mismatches for each cipher
- First mismatch index and 40-char window (for cipher 2)
- Repeat-number invariance check
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _parse_csv_numbers(text: str) -> list:
    """Parse comma-separated numbers from text (handles multi-line)."""
    combined = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return [int(n.strip()) for n in combined.replace(",", " ").split() if n.strip().isdigit() or n.strip().lstrip("-").isdigit()]


def _parse_line_csv(text: str) -> list:
    """Parse comma-separated integers from a single block of text."""
    return [int(n.strip()) for n in text.replace("\n", ",").split(",") if n.strip() and n.strip().replace(".", "").isdigit()]


def load_beale_papers_cipher(n: int) -> list:
    """Load cipher n (1, 2, or 3) from beale_papers.txt."""
    with open(PROJECT_ROOT / "beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Cipher 1 = line 3 (index 2), Cipher 2 = line 59 (index 58), Cipher 3 = line 7 (index 6)
    idx = {1: 2, 2: 58, 3: 6}[n]
    line = lines[idx].strip()
    return [int(x.strip()) for x in line.split(",") if x.strip().replace(".", "").isdigit()]


def load_fsu_cipher(n: int) -> list:
    """Load cipher n from FSU raw file."""
    path = PROJECT_ROOT / "corpus" / "raw_sources" / "fsu" / f"beale_cipher{n}.txt"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # FSU uses comma-separated, possibly multi-line
    nums = []
    for part in text.replace("\n", ",").split(","):
        s = part.strip().rstrip(".")
        if s and s.isdigit():
            nums.append(int(s))
    return nums


def diff_lists(a: list, b: list, name: str) -> dict:
    """Return diff stats between two lists."""
    mismatches = []
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            mismatches.append((i, a[i], b[i]))
    return {
        "len_a": len(a),
        "len_b": len(b),
        "len_diff": abs(len(a) - len(b)),
        "mismatches": mismatches[:30],
        "total_mismatches": len(mismatches),
    }


def repeat_number_invariance(cipher: list, expected_letters: str) -> list:
    """
    For repeated cipher numbers, check if expected letters agree.
    Returns list of (cipher_num, positions, expected_chars) where chars disagree.
    """
    from collections import defaultdict
    positions_by_num = defaultdict(list)
    for i, n in enumerate(cipher):
        positions_by_num[n].append(i)
    violations = []
    for num, positions in positions_by_num.items():
        if len(positions) < 2:
            continue
        chars = [expected_letters[p] if p < len(expected_letters) else "?" for p in positions]
        if len(set(chars)) > 1:
            violations.append((num, positions[:5], chars[:5]))
    return violations


def main():
    from oracle.cipher2_evaluator import load_cipher2, load_cipher2_known_plaintext
    from corpus.beale_doi_adjusted import get_adjusted_tokens

    print("=" * 75)
    print("BEALE CIPHER DIFF: beale_papers vs FSU (Burkardt dataset)")
    print("=" * 75)

    # Load all
    bp1 = load_beale_papers_cipher(1)
    bp2 = load_beale_papers_cipher(2)
    bp3 = load_beale_papers_cipher(3)
    fsu1 = load_fsu_cipher(1)
    fsu2 = load_fsu_cipher(2)
    fsu3 = load_fsu_cipher(3)

    for n, (bp, fsu) in [(1, (bp1, fsu1)), (2, (bp2, fsu2)), (3, (bp3, fsu3))]:
        d = diff_lists(bp, fsu, f"Cipher {n}")
        print(f"\n--- Cipher {n} ---")
        print(f"  beale_papers: {d['len_a']} numbers")
        print(f"  FSU:         {d['len_b']} numbers")
        print(f"  Length diff: {d['len_diff']}")
        print(f"  Value mismatches: {d['total_mismatches']}")
        if d["mismatches"]:
            print(f"  First 10 mismatches (idx, bp_val, fsu_val):")
            for t in d["mismatches"][:10]:
                print(f"    {t}")

    # Cipher 2: first mismatch index + 40-char window
    print("\n" + "=" * 75)
    print("CIPHER 2: FIRST MISMATCH DIAGNOSTIC")
    print("=" * 75)

    tokens = get_adjusted_tokens()
    known = load_cipher2_known_plaintext()
    known_clean = "".join(c.upper() for c in known if c.isalpha())
    overrides = {95: "U", 811: "Y", 1005: "X"}

    def decode(cipher: list) -> str:
        out = []
        for cnum in cipher:
            idx = cnum - 1
            if cnum in overrides:
                out.append(overrides[cnum])
            elif 0 <= idx < len(tokens) and tokens[idx]:
                out.append(tokens[idx][0].upper())
            else:
                out.append("?")
        return "".join(out)

    decoded_bp = decode(bp2)
    first_mismatch = -1
    for i in range(min(len(decoded_bp), len(known_clean))):
        if decoded_bp[i] != known_clean[i]:
            first_mismatch = i
            break

    print(f"\nFirst mismatch position: {first_mismatch}")
    if first_mismatch >= 0:
        cnum = bp2[first_mismatch] if first_mismatch < len(bp2) else None
        print(f"Cipher number at position {first_mismatch}: {cnum}")
        print(f"Decoded char: '{decoded_bp[first_mismatch]}'")
        print(f"Expected char: '{known_clean[first_mismatch]}'")
        start = max(0, first_mismatch - 20)
        end = min(len(decoded_bp), len(known_clean), first_mismatch + 21)
        print(f"\n40-char window around first mismatch:")
        print(f"  Decoded:  ...{decoded_bp[start:end]}...")
        print(f"  Expected: ...{known_clean[start:end]}...")
        print(f"  Position:  {start} to {end} (mismatch at {first_mismatch})")

    # Repeat-number invariance
    print("\n" + "=" * 75)
    print("REPEAT-NUMBER INVARIANCE CHECK (Cipher 2)")
    print("=" * 75)
    violations = repeat_number_invariance(bp2, known_clean)
    print(f"\nRepeated cipher numbers where expected letters disagree: {len(violations)}")
    for num, positions, chars in violations[:10]:
        print(f"  Cipher num {num}: positions {positions}, expected chars {chars}")
    if violations and first_mismatch >= 0:
        mismatch_num = bp2[first_mismatch]
        if any(v[0] == mismatch_num for v in violations):
            print(f"\n  [NOTE] First mismatch cipher number {mismatch_num} is in violation list")

    print("\n" + "=" * 75)


if __name__ == "__main__":
    main()
