"""
Overlap constraints for arbitrary key texts against Cipher 2-derived letter map.

Given that Cipher 2 is solved with the DOI, this module computes the subset of
cipher numbers shared between Cipher 1 (or 3) and Cipher 2, then scores any
candidate key text by checking whether word[N] in the candidate starts with the
same letter as word[N] in the DOI.

This is a powerful prefilter for "DOI-family" texts (extended editions, related
documents with shared prefix). For unrelated texts, the expected pass rate is
~1/26 per constraint (~3.8%), so any text scoring significantly above that
threshold is noteworthy.
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from constraints.cipher2_keyletter_map import (
    build_keyletter_map,
    get_stable_constraints,
    score_keytext_against_constraints,
)


def build_overlap_constraint_set(target_cipher: int = 1) -> Dict[int, str]:
    """
    Build the constraint set: cipher numbers that appear in BOTH the target
    cipher and Cipher 2, mapped to the required first letter from the DOI.

    Returns {cipher_number -> expected_letter} for stable entries only.
    """
    target_nums = set(load_cipher(target_cipher))
    c2_nums = set(load_cipher(2))
    overlap = target_nums & c2_nums

    klmap = build_keyletter_map()
    stable = get_stable_constraints(klmap)

    return {cn: letter for cn, letter in stable.items() if cn in overlap}


def screen_keytext(tokens: List[str], target_cipher: int = 1,
                   constraints: Dict[int, str] = None) -> dict:
    """
    Screen a candidate key text against the overlap constraints.

    Returns dict with passed, total, pass_rate, failures, and
    a diagnostic flag 'above_chance' (pass_rate > 2x random expectation).
    """
    if constraints is None:
        constraints = build_overlap_constraint_set(target_cipher)

    result = score_keytext_against_constraints(tokens, constraints)
    expected_random = 1.0 / 26.0
    result["expected_random_rate"] = expected_random
    result["above_chance"] = result["pass_rate"] > (2 * expected_random)
    return result


if __name__ == "__main__":
    print("=== Overlap Constraint Screening ===")
    constraints = build_overlap_constraint_set(1)
    print(f"Cipher 1 vs Cipher 2 overlap constraints: {len(constraints)}")
    print(f"Expected random pass rate: {1/26:.3f} ({1/26*100:.1f}%)")
    print(f"Threshold for 'above chance': {2/26:.3f} ({2/26*100:.1f}%)")
