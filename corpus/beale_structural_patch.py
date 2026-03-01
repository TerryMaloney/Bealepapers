"""
Beale DOI Structural Patch - Search engine for the 5 structural edits.

Applies insert + 4 delete windows via sequential greedy search.
Each configuration is scored with Cipher 2 oracle (with letter overrides).
"""

from typing import List, Tuple, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import (
    Cipher2Oracle,
    load_cipher2,
    load_cipher2_known_plaintext,
)


# Beale letter overrides: cipher_num -> letter (1-indexed)
# Word 95: pamphlet treats as 'u' (unalienable); some editions have "inalienable"
BEALE_LETTER_OVERRIDES = {
    95: 'u',
    811: 'y',
    1005: 'x',
}


def make_extraction_rule_with_overrides(overrides: dict):
    """Return extraction rule that applies overrides before default first-letter."""

    def extract(word: str, cipher_num: int):
        if cipher_num in overrides:
            return overrides[cipher_num]
        return word[0].upper() if word else '?'

    return extract


def apply_insert(tokens: List[str], position: int, word: str = "a") -> List[str]:
    """Insert one word at position (0-indexed)."""
    return tokens[:position] + [word] + tokens[position:]


def apply_delete(tokens: List[str], start: int, length: int = 1) -> List[str]:
    """Delete length tokens starting at start (0-indexed)."""
    return tokens[:start] + tokens[start + length:]


def find_token_indices(tokens: List[str], words: List[str]) -> dict:
    """Return dict of word -> list of 1-based indices where word appears."""
    result = {w: [] for w in words}
    for i, t in enumerate(tokens):
        t_lower = t.lower()
        if t_lower in result:
            result[t_lower].append(i + 1)
    return result


def score_tokens(tokens: List[str], cipher2: List[int], known_plaintext: str) -> float:
    """Score token list with Cipher 2 oracle (with Beale overrides)."""
    oracle = Cipher2Oracle(known_plaintext)
    extractor = make_extraction_rule_with_overrides(BEALE_LETTER_OVERRIDES)
    result = oracle.evaluate(tokens, cipher2, extraction_rule=extractor)
    return result.char_match_pct


# Structural edit windows (0-indexed positions in token list)
# Edit 1: Insert 1 word after position 154 (before token at 155)
INSERT_POSITION = 155
INSERT_WORD = "a"

# Edit 2: Delete 1 word between 240 and 246 (exclusive of 246)
DELETE1_START, DELETE1_END = 240, 246  # try 240, 241, 242, 243, 244, 245

# Edit 3: Delete 10 words between 466 and 495 (slide window)
DELETE10_START, DELETE10_END = 466, 496  # range ensures we can delete 10
DELETE10_LENGTH = 10

# Edit 4: Delete 1 word between 630 and 654
DELETE2_START, DELETE2_END = 630, 654

# Edit 5: Delete 1 word between 677 and 819
DELETE3_START, DELETE3_END = 677, 820  # 677..819 inclusive = 143 positions

ANCHOR_WORDS = ["houses", "valuable", "fundamentally", "have"]


def _log_delete_context(log, tokens: List[str], start: int, length: int, deleted: List[str]):
    """Log deletion context: 5 tokens before/after, deleted tokens, anchor positions."""
    idx_before = max(0, start - 5)
    before = tokens[idx_before:start]
    after = tokens[start + length:min(len(tokens), start + length + 5)]
    log(f"  Deleted: {deleted}")
    log(f"  Before: ... {' '.join(before)}")
    log(f"  After:  {' '.join(after)} ...")
    anchors = find_token_indices(tokens, ANCHOR_WORDS)
    parts = [f"{w}@{anchors[w][0] if anchors[w] else '?'}" for w in ANCHOR_WORDS]
    log(f"  Anchors: {', '.join(parts)}")


def run_structural_patch_search(
    base_tokens: List[str],
    cipher2: Optional[List[int]] = None,
    known_plaintext: Optional[str] = None,
    verbose: bool = True,
) -> Tuple[List[str], float, dict]:
    """
    Run sequential greedy search over the 5 structural edits.

    Returns:
        (best_tokens, best_score, config)
    """
    if cipher2 is None:
        cipher2 = load_cipher2()
    if known_plaintext is None:
        known_plaintext = load_cipher2_known_plaintext()

    def log(msg: str):
        if verbose:
            print(msg)

    config = {}
    current = list(base_tokens)

    # Edit 1: Insert 1 at position 155 (only one option)
    log("\n[Edit 1] Insert 'a' at position 155...")
    current = apply_insert(current, INSERT_POSITION, INSERT_WORD)
    score = score_tokens(current, cipher2, known_plaintext)
    config["insert_155"] = "a"
    log(f"  After insert: {len(current)} tokens, score={score:.2f}%")

    # Edit 2: Delete 1 in [240, 246)
    log("\n[Edit 2] Delete 1 word in window 240-246...")
    best_score = score
    best_delete1 = None
    for k in range(DELETE1_START, min(DELETE1_END, len(current))):
        candidate = apply_delete(current, k, 1)
        s = score_tokens(candidate, cipher2, known_plaintext)
        if s > best_score:
            best_score = s
            best_delete1 = k
    if best_delete1 is not None:
        deleted = current[best_delete1:best_delete1 + 1]
        _log_delete_context(log, current, best_delete1, 1, deleted)
        current = apply_delete(current, best_delete1, 1)
        config["delete1_pos"] = best_delete1
        log(f"  Best: delete at {best_delete1}, score={best_score:.2f}%")
    else:
        log(f"  No improvement, keep as is. score={best_score:.2f}%")

    # Edit 3: Delete 10 in sliding window [466, 495]
    log("\n[Edit 3] Delete 10 words in sliding window 466-495...")
    best_score = score_tokens(current, cipher2, known_plaintext)
    best_start = None
    end_max = min(DELETE10_END - DELETE10_LENGTH + 1, len(current) - DELETE10_LENGTH + 1)
    for start in range(DELETE10_START, end_max):
        if start < 0 or start + DELETE10_LENGTH > len(current):
            continue
        candidate = apply_delete(current, start, DELETE10_LENGTH)
        s = score_tokens(candidate, cipher2, known_plaintext)
        if s > best_score:
            best_score = s
            best_start = start
    if best_start is not None:
        deleted = current[best_start:best_start + DELETE10_LENGTH]
        _log_delete_context(log, current, best_start, DELETE10_LENGTH, deleted)
        current = apply_delete(current, best_start, DELETE10_LENGTH)
        config["delete10_start"] = best_start
        log(f"  Best: delete 10 at start {best_start}, score={best_score:.2f}%")
    else:
        log(f"  No improvement. score={best_score:.2f}%")

    # Edit 4: Delete 1 in [630, 654)
    log("\n[Edit 4] Delete 1 word in window 630-654...")
    best_score = score_tokens(current, cipher2, known_plaintext)
    best_delete2 = None
    for k in range(DELETE2_START, min(DELETE2_END, len(current))):
        candidate = apply_delete(current, k, 1)
        s = score_tokens(candidate, cipher2, known_plaintext)
        if s > best_score:
            best_score = s
            best_delete2 = k
    if best_delete2 is not None:
        deleted = current[best_delete2:best_delete2 + 1]
        _log_delete_context(log, current, best_delete2, 1, deleted)
        current = apply_delete(current, best_delete2, 1)
        config["delete2_pos"] = best_delete2
        log(f"  Best: delete at {best_delete2}, score={best_score:.2f}%")
    else:
        log(f"  No improvement. score={best_score:.2f}%")

    # Edit 5: Delete 1 in [677, 820)
    log("\n[Edit 5] Delete 1 word in window 677-819...")
    best_score = score_tokens(current, cipher2, known_plaintext)
    best_delete3 = None
    for k in range(DELETE3_START, min(DELETE3_END, len(current))):
        candidate = apply_delete(current, k, 1)
        s = score_tokens(candidate, cipher2, known_plaintext)
        if s > best_score:
            best_score = s
            best_delete3 = k
    if best_delete3 is not None:
        deleted = current[best_delete3:best_delete3 + 1]
        _log_delete_context(log, current, best_delete3, 1, deleted)
        current = apply_delete(current, best_delete3, 1)
        config["delete3_pos"] = best_delete3
        log(f"  Best: delete at {best_delete3}, score={best_score:.2f}%")
    else:
        log(f"  No improvement. score={best_score:.2f}%")

    final_score = score_tokens(current, cipher2, known_plaintext)
    log(f"\n[Result] Final: {len(current)} tokens, score={final_score:.2f}%")

    return current, final_score, config
