"""
Beale DOI Control Patch - Deterministic Wikipedia-suggested edits.

Applies the exact 5 edits by content lookup (not fixed indices).
Used to verify that correct edits produce high oracle score.
"""

from typing import List, Tuple
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.beale_structural_patch import (
    apply_insert,
    apply_delete,
    score_tokens,
    BEALE_LETTER_OVERRIDES,
)
from oracle.cipher2_evaluator import load_cipher2, load_cipher2_known_plaintext


def _find_phrase(tokens: List[str], phrase: List[str]) -> int:
    """Return 0-based start index of first occurrence of phrase, or -1."""
    if len(phrase) > len(tokens):
        return -1
    for i in range(len(tokens) - len(phrase) + 1):
        if all(tokens[i + j].lower() == phrase[j].lower() for j in range(len(phrase))):
            return i
    return -1


def _find_word(tokens: List[str], word: str) -> int:
    """Return 0-based index of first occurrence of word (case-insensitive), or -1."""
    w = word.lower()
    for i, t in enumerate(tokens):
        if t.lower() == w:
            return i
    return -1


def _find_word_after(tokens: List[str], word: str, after: int) -> int:
    """Return 0-based index of first occurrence of word after position `after`."""
    w = word.lower()
    for i in range(after + 1, len(tokens)):
        if tokens[i].lower() == w:
            return i
    return -1


def run_control_patch(base_tokens: List[str]) -> Tuple[List[str], float]:
    """
    Apply the exact Wikipedia-suggested edits by content.

    Edit 1: Insert "a" before "new government"
    Edit 2: Delete "a" between invariably and design
    Edit 3: Delete "He has refused for a long time after such dissolutions" (10 words)
    Edit 4: Delete "the" between eat and to
    Edit 5: Delete "their" between foreign and valuable

    Returns:
        (patched_tokens, oracle_score)
    """
    cipher2 = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()

    current = list(base_tokens)

    # Edit 1: Insert "a" before "new government"
    # Find "institute" then "new" then "government"
    idx_institute = _find_word(current, "institute")
    if idx_institute >= 0:
        idx_new = _find_word_after(current, "new", idx_institute)
        if idx_new >= 0 and idx_new + 1 < len(current) and current[idx_new + 1].lower() == "government":
            current = apply_insert(current, idx_new, "a")

    # Edit 2: Delete "a" between invariably and design
    idx_invariably = _find_word(current, "invariably")
    if idx_invariably >= 0:
        idx_design = _find_word_after(current, "design", idx_invariably)
        if idx_design >= 0:
            for k in range(idx_invariably + 1, idx_design):
                if current[k].lower() == "a":
                    current = apply_delete(current, k, 1)
                    break

    # Edit 3: Delete 10 words - "he has refused for a long time after such dissolutions"
    phrase10 = ["he", "has", "refused", "for", "a", "long", "time", "after", "such", "dissolutions"]
    start10 = _find_phrase(current, phrase10)
    if start10 >= 0:
        current = apply_delete(current, start10, 10)

    # Edit 4: Delete "the" between eat and to
    idx_eat = _find_word(current, "eat")
    if idx_eat >= 0:
        idx_to = _find_word_after(current, "to", idx_eat)
        if idx_to >= 0:
            for k in range(idx_eat + 1, idx_to):
                if current[k].lower() == "the":
                    current = apply_delete(current, k, 1)
                    break

    # Edit 5: Delete "their" between foreign and valuable
    idx_foreign = _find_word(current, "foreign")
    if idx_foreign >= 0:
        idx_valuable = _find_word_after(current, "valuable", idx_foreign)
        if idx_valuable >= 0:
            for k in range(idx_foreign + 1, idx_valuable):
                if current[k].lower() == "their":
                    current = apply_delete(current, k, 1)
                    break

    score = score_tokens(current, cipher2, known_plaintext)
    return current, score
