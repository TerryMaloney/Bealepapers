"""
Phase 102 Task 4: Candidate generation (merge/split at 4-digit positions).

Beam search over 19 four-digit positions. Pruning: only splits where both parts in DOI range (1-1322).
Output: c1_candidates_ranked_by_confidence.csv, corpus/cipher_variants/c1_candidate_001..050.txt
"""

import csv
import sys
from pathlib import Path
from typing import List, Tuple, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher
from corpus.beale_doi_adjusted import get_adjusted_tokens
from scoring.quadgram_scorer import quadgram_score

VARIANTS_DIR = PROJECT_ROOT / "corpus" / "cipher_variants"
OUT = PROJECT_ROOT / "output" / "phase102"
DOI_MAX = 1322
K_CANDIDATES = 50


def get_fourdigit_positions(nums: List[int]) -> List[Tuple[int, int]]:
    return [(i, n) for i, n in enumerate(nums) if n >= 1000]


def apply_choice_at(nums: List[int], pos: int, fourdigit_val: int, choice: str) -> List[int]:
    """choice: keep, 1_3, 2_2, 3_1, drop."""
    if choice == "keep":
        return nums[:]
    s = str(fourdigit_val)
    if choice == "1_3":
        a, b = int(s[0]), int(s[1:])
    elif choice == "2_2":
        a, b = int(s[:2]), int(s[2:])
    elif choice == "3_1":
        a, b = int(s[:3]), int(s[3:])
    elif choice == "drop":
        return nums[:pos] + nums[pos + 1:]
    else:
        return nums[:]
    if a < 1 or b < 1 or a > DOI_MAX or b > DOI_MAX:
        return nums[:]
    return nums[:pos] + [a, b] + nums[pos + 1:]


def decode_first_letter(tokens: List[str], nums: List[int]) -> str:
    out = []
    for n in nums:
        idx = n - 1
        if 0 <= idx < len(tokens) and tokens[idx]:
            out.append(tokens[idx][0].upper())
        else:
            out.append("?")
    return "".join(out)


def split_fourdigit_uniform(nums: List[int], strategy: str) -> List[int]:
    """Uniform strategy: apply same split to all 4-digit numbers."""
    result = []
    for n in nums:
        if n >= 1000 and strategy != "keep":
            s = str(n)
            if strategy == "1_3":
                a, b = int(s[0]), int(s[1:])
            elif strategy == "2_2":
                a, b = int(s[:2]), int(s[2:])
            elif strategy == "3_1":
                a, b = int(s[:3]), int(s[3:])
            elif strategy == "drop":
                continue
            else:
                result.append(n)
                continue
            if a > 0:
                result.append(a)
            if b > 0:
                result.append(b)
        else:
            result.append(n)
    return result


def main():
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    c1 = load_cipher(1)
    tokens = get_adjusted_tokens()
    fourdigit_pos = get_fourdigit_positions(c1)

    # Uniform baselines
    candidates = []
    for strategy in ["keep", "1_3", "2_2", "3_1", "drop"]:
        seq = split_fourdigit_uniform(c1, strategy)
        stream = decode_first_letter(tokens, seq)
        qg = quadgram_score(stream)
        candidates.append({
            "seq": seq,
            "strategy_description": f"uniform_{strategy}",
            "num_changes": 19 if strategy != "keep" else 0,
            "changed_positions": "all" if strategy != "keep" else "",
            "sequence_length": len(seq),
            "max_value": max(seq) if seq else 0,
            "quadgram": qg,
        })

    # Single-position variants: for each 4-digit position, try each valid choice
    for pos, val in fourdigit_pos:
        for choice in ["1_3", "2_2", "3_1", "drop"]:
            seq = apply_choice_at(c1, pos, val, choice)
            if seq == c1 and choice != "keep":
                continue
            stream = decode_first_letter(tokens, seq)
            qg = quadgram_score(stream)
            candidates.append({
                "seq": seq,
                "strategy_description": f"pos{pos}_{val}_{choice}",
                "num_changes": 1,
                "changed_positions": str(pos),
                "sequence_length": len(seq),
                "max_value": max(seq),
                "quadgram": qg,
            })

    # Sort by quadgram descending (higher = better)
    candidates.sort(key=lambda x: x["quadgram"], reverse=True)
    top50 = candidates[:K_CANDIDATES]

    # Build ranked CSV and write candidate files
    rows = []
    for rank, c in enumerate(top50, 1):
        cid = f"c1_candidate_{rank:03d}"
        rows.append({
            "rank": rank,
            "candidate_id": cid,
            "strategy_description": c["strategy_description"],
            "num_changes": c["num_changes"],
            "changed_positions": c["changed_positions"],
            "sequence_length": c["sequence_length"],
            "max_value": c["max_value"],
        })
        path = VARIANTS_DIR / f"{cid}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(str(x) for x in c["seq"]))
    with open(OUT / "c1_candidates_ranked_by_confidence.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "candidate_id", "strategy_description", "num_changes", "changed_positions", "sequence_length", "max_value"])
        w.writeheader()
        w.writerows(rows)

    # Consensus list (canonical = candidate 001 if keep won, else first in list)
    consensus = top50[0]["seq"]
    with open(VARIANTS_DIR / "c1_consensus.txt", "w", encoding="utf-8") as f:
        f.write(",".join(str(x) for x in consensus))

    print(f"Task 4: wrote c1_candidates_ranked_by_confidence.csv and c1_candidate_001..{K_CANDIDATES:03d}.txt ({len(top50)} candidates)")
    print(f"  Top 3: {[c['strategy_description'] for c in top50[:3]]}")


if __name__ == "__main__":
    main()
