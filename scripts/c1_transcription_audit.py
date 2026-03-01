"""
Track 5: C1 Transcription Audit.

Analyzes C1's structural anomalies and checks for potential transcription errors.
- Identifies the 19 four-digit numbers (potential misreads)
- Checks for suspicious patterns (repeated digits, near-duplicates)
- Compares C1 vs C2 vs C3 number properties
- Checks if removing/correcting suspect numbers changes structural profile
"""

import sys
import json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher

OUT = Path("output/phase93")
OUT.mkdir(parents=True, exist_ok=True)


def digit_analysis(nums, name):
    """Detailed digit-level analysis of a cipher number list."""
    results = {"name": name, "count": len(nums)}

    # Four-digit numbers
    four_digit = [(i, n) for i, n in enumerate(nums) if n >= 1000]
    results["four_digit_count"] = len(four_digit)
    results["four_digit_positions"] = four_digit

    # Numbers that could be misreads (e.g., 2906 could be 290 + 6, or 29 + 06)
    suspect = []
    for i, n in enumerate(nums):
        s = str(n)
        # Check for obvious digit patterns
        if len(set(s)) == 1 and len(s) > 1:  # repeated digit (111, 222, etc.)
            suspect.append((i, n, "repeated_digit"))
        if n >= 1000 and s[0] == '1':  # 1xxx could be a leading 1 error
            suspect.append((i, n, "leading_1_fourdigit"))
        if n >= 1000 and s[:2] in ['10', '20', '30']:  # round thousands
            suspect.append((i, n, "round_thousand"))
    results["suspects"] = suspect

    # Near-duplicates: numbers that differ by exactly 1
    nums_set = set(nums)
    near_dupes = []
    for n in sorted(nums_set):
        if n + 1 in nums_set:
            near_dupes.append((n, n + 1))
    results["near_duplicate_pairs"] = len(near_dupes)

    # Gap analysis: consecutive cipher positions with large number changes
    big_jumps = []
    for i in range(1, len(nums)):
        diff = abs(nums[i] - nums[i-1])
        if diff > 500:
            big_jumps.append((i-1, i, nums[i-1], nums[i], diff))
    results["big_jumps_count"] = len(big_jumps)
    results["big_jumps_top10"] = sorted(big_jumps, key=lambda x: x[4], reverse=True)[:10]

    return results


def main():
    c1 = load_cipher(1)
    c2 = load_cipher(2)
    c3 = load_cipher(3)

    print("=" * 70)
    print("C1 TRANSCRIPTION AUDIT")
    print("=" * 70)

    c1_analysis = digit_analysis(c1, "Cipher 1")
    c2_analysis = digit_analysis(c2, "Cipher 2")
    c3_analysis = digit_analysis(c3, "Cipher 3")

    # Report
    report = []
    report.append("C1 TRANSCRIPTION AUDIT")
    report.append("=" * 70)

    for analysis in [c1_analysis, c2_analysis, c3_analysis]:
        name = analysis["name"]
        report.append(f"\n{name}:")
        report.append(f"  Total numbers: {analysis['count']}")
        report.append(f"  Four-digit numbers: {analysis['four_digit_count']}")
        if analysis['four_digit_positions']:
            report.append(f"  Four-digit positions and values:")
            for pos, val in analysis['four_digit_positions']:
                report.append(f"    Position {pos}: {val}")
        report.append(f"  Suspect numbers: {len(analysis['suspects'])}")
        for pos, val, reason in analysis['suspects']:
            report.append(f"    Position {pos}: {val} ({reason})")
        report.append(f"  Near-duplicate pairs: {analysis['near_duplicate_pairs']}")
        report.append(f"  Big jumps (>500): {analysis['big_jumps_count']}")
        if analysis['big_jumps_top10']:
            report.append(f"  Top 5 biggest jumps:")
            for p1, p2, v1, v2, diff in analysis['big_jumps_top10'][:5]:
                report.append(f"    pos {p1}->{p2}: {v1} -> {v2} (diff={diff})")

    # C1 specific deep dive
    report.append(f"\n{'='*70}")
    report.append("C1 DEEP DIVE: Four-digit numbers")
    report.append("=" * 70)

    four_digit_nums = [n for _, n in c1_analysis['four_digit_positions']]
    report.append(f"\nThe 19 four-digit C1 numbers: {sorted(four_digit_nums)}")
    report.append(f"Range: {min(four_digit_nums)}-{max(four_digit_nums)}")

    # What if these are split numbers (e.g., 2906 = 290, 6)?
    report.append(f"\nHYPOTHESIS: Four-digit numbers are misread two-number pairs:")
    for pos, val in c1_analysis['four_digit_positions']:
        s = str(val)
        splits = [
            (f"{s[0]},{s[1:]}", int(s[0]), int(s[1:])),
            (f"{s[:2]},{s[2:]}", int(s[:2]), int(s[2:])),
            (f"{s[:3]},{s[3:]}", int(s[:3]), int(s[3:])),
        ]
        report.append(f"  {val} at pos {pos} could be:")
        for label, a, b in splits:
            if a > 0 and b > 0:
                report.append(f"    {label} (max would be {max(a,b)})")

    # Context around four-digit numbers
    report.append(f"\nContext around four-digit numbers (5 numbers before/after):")
    for pos, val in c1_analysis['four_digit_positions']:
        start = max(0, pos - 3)
        end = min(len(c1), pos + 4)
        context = c1[start:end]
        marker = ['  '] * len(context)
        marker[pos - start] = '>>'
        report.append(f"  pos {pos}: {' '.join(f'{m}{n}' for m, n in zip(marker, context))}")

    # What C1 looks like without four-digit numbers
    report.append(f"\nC1 WITHOUT four-digit numbers:")
    c1_no4 = [n for n in c1 if n < 1000]
    report.append(f"  Length: {len(c1_no4)} (was {len(c1)})")
    report.append(f"  Max: {max(c1_no4)}")
    report.append(f"  Mean: {sum(c1_no4)/len(c1_no4):.1f}")
    report.append(f"  Median: {sorted(c1_no4)[len(c1_no4)//2]}")
    unique_no4 = set(c1_no4)
    singleton_no4 = sum(1 for c in Counter(c1_no4).values() if c == 1)
    report.append(f"  Unique: {len(unique_no4)}, Singletons: {singleton_no4} ({singleton_no4/len(unique_no4)*100:.1f}%)")

    # Compare to C2/C3 range
    report.append(f"\n  Compare: C2 max={max(c2)}, C3 max={max(c3)}")
    report.append(f"  C1 (no 4-digit) max={max(c1_no4)} — now comparable to C2/C3 range!")

    report_text = "\n".join(report)
    print(report_text)

    with open(OUT / "c1_transcription_audit.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\nSaved to: {OUT / 'c1_transcription_audit.txt'}")


if __name__ == "__main__":
    main()
