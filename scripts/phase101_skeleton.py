"""
Phase 101 Task 4: Function-word skeleton inference.

For each cipher:
- Identify top 20 most frequent numbers and their spacing distributions
- Map to abstract tokens (A, B, C...) and search for repeated patterns
  consistent with English scaffolding (e.g., A B A, A A, A B C A)
- Compare pattern rates to controls (shuffled sequences)

Output: phase101/skeleton_patterns_report.txt
"""

import random
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher

OUT = PROJECT_ROOT / "output" / "phase101"
SEED = 101600
N_CONTROL = 10_000


def get_top_n(nums: List[int], n: int = 20) -> List[Tuple[int, int]]:
    return Counter(nums).most_common(n)


def spacing_distribution(nums: List[int], target: int) -> List[int]:
    positions = [i for i, n in enumerate(nums) if n == target]
    if len(positions) < 2:
        return []
    return [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]


def abstract_sequence(nums: List[int], top_set: set) -> str:
    """Map top numbers to A,B,C,... and others to '.'"""
    mapping = {}
    label = ord('A')
    for n, _ in Counter(nums).most_common():
        if n in top_set and label <= ord('Z'):
            mapping[n] = chr(label)
            label += 1
    out = []
    for n in nums:
        out.append(mapping.get(n, '.'))
    return "".join(out)


def count_patterns(abstract: str, patterns: List[str]) -> Dict[str, int]:
    """Count occurrences of each pattern template.
    Patterns use uppercase as wildcards for abstract tokens:
    'XYX' matches any ABA, BCB, etc. where X != Y"""
    results = {}
    for pat in patterns:
        count = 0
        plen = len(pat)
        for i in range(len(abstract) - plen + 1):
            segment = abstract[i:i + plen]
            if '.' in segment:
                continue
            # Check pattern: same letters in pattern map to same abstract chars
            mapping = {}
            ok = True
            for j, p_ch in enumerate(pat):
                s_ch = segment[j]
                if p_ch in mapping:
                    if mapping[p_ch] != s_ch:
                        ok = False
                        break
                else:
                    mapping[p_ch] = s_ch
            # Also check: different pattern chars -> different abstract chars
            if ok:
                reverse_map = {}
                for p_ch, s_ch in mapping.items():
                    if s_ch in reverse_map and reverse_map[s_ch] != p_ch:
                        ok = False
                        break
                    reverse_map[s_ch] = p_ch
            if ok:
                count += 1
        results[pat] = count
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    ciphers = {"C1": load_cipher(1), "C2": load_cipher(2), "C3": load_cipher(3)}
    # English-like scaffold patterns
    patterns = ["XYX", "XX", "XYZ", "XYXY", "XYZX", "XYXZ", "XXY", "XYY", "XYYZ", "XYZYZ"]

    report = ["Phase 101 Task 4: Function-Word Skeleton Inference", "=" * 55, ""]

    for cname, nums in ciphers.items():
        report.append(f"--- {cname} ({len(nums)} numbers) ---")
        top20 = get_top_n(nums, 20)
        report.append(f"Top 20 most frequent numbers:")
        for num, cnt in top20:
            spacings = spacing_distribution(nums, num)
            mean_sp = round(sum(spacings) / len(spacings), 1) if spacings else 0
            report.append(f"  {num:>5d} ×{cnt:>2d}  mean_spacing={mean_sp:>6.1f}  spacings={spacings[:8]}")

        # Build abstract sequence
        top_set = {n for n, _ in top20}
        abstract = abstract_sequence(nums, top_set)
        report.append(f"Abstract sequence (first 100): {abstract[:100]}")
        report.append("")

        # Count patterns
        observed = count_patterns(abstract, patterns)

        # Control: shuffle numbers, rebuild abstract, count patterns
        ctrl_counts = {p: [] for p in patterns}
        for _ in range(N_CONTROL):
            shuffled = nums[:]
            rng.shuffle(shuffled)
            abs_shuf = abstract_sequence(shuffled, top_set)
            ctrl = count_patterns(abs_shuf, patterns)
            for p in patterns:
                ctrl_counts[p].append(ctrl[p])

        report.append("Pattern analysis (observed vs 10k shuffled controls):")
        for pat in patterns:
            obs = observed[pat]
            ctrl_vals = ctrl_counts[pat]
            mean_c = sum(ctrl_vals) / len(ctrl_vals)
            std_c = (sum((x - mean_c) ** 2 for x in ctrl_vals) / len(ctrl_vals)) ** 0.5 or 1e-10
            z = (obs - mean_c) / std_c
            p_ge = sum(1 for x in ctrl_vals if x >= obs) / len(ctrl_vals)
            marker = " ***" if abs(z) > 3 else ""
            report.append(f"  {pat:8s}: observed={obs:>4d}  null_mean={mean_c:>6.1f}  "
                          f"null_std={std_c:>5.1f}  z={z:>+6.2f}  p={p_ge:.4f}{marker}")
        report.append("")

    with open(OUT / "skeleton_patterns_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"Task 4: wrote skeleton_patterns_report.txt")


if __name__ == "__main__":
    main()
