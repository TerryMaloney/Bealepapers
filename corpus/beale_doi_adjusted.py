"""
Beale DOI Adjusted - Applies the 5 documented FSU adjustments to align
standard DOI numbering with the Beale cipher's encoding.

Ref: https://people.sc.fsu.edu/~jburkardt/datasets/beale_cipher/beale_cipher.html
"""

from pathlib import Path
from typing import List, Tuple

from corpus.beale_pamphlet_pdf import clean_pamphlet_text, load_pamphlet_raw, tokenize_pamphlet

_PATH = Path(__file__).resolve().parent
_PROJECT_ROOT = _PATH.parent
_FSU_DOI = _PROJECT_ROOT / "corpus" / "raw_sources" / "fsu_declaration_of_independence.txt"
_BEALE_PAPERS = _PROJECT_ROOT / "beale_papers.txt"

# Cache for get_adjusted_tokens()
_adjusted_tokens_cache: List[str] | None = None


def load_standard_doi_tokens() -> List[str]:
    """
    Load and tokenize the standard DOI from beale_papers.txt line 55.
    Uses the same tokenization as beale_pamphlet_pdf (meantime unsplit, & at 908, etc.).
    """
    if _BEALE_PAPERS.exists():
        with open(_BEALE_PAPERS, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 54:
            raw = lines[54].strip()
            cleaned = clean_pamphlet_text(raw)
            return tokenize_pamphlet(cleaned)
    if _FSU_DOI.exists():
        text = _FSU_DOI.read_text(encoding="utf-8")
        # FSU file has signers - slice to DOI body only (When ... sacred honor)
        end_marker = "and our sacred honor"
        if end_marker.lower() in text.lower():
            idx = text.lower().rfind(end_marker.lower()) + len(end_marker)
            text = text[:idx]
        cleaned = clean_pamphlet_text(text)
        return tokenize_pamphlet(cleaned)
    raise FileNotFoundError("Neither beale_papers.txt nor fsu_declaration_of_independence.txt found")


def apply_beale_adjustments(
    tokens: List[str],
    *,
    adj2_remove_idx: int | None = None,
    adj3_remove_start: int | None = None,
    adj4_remove_idx: int | None = None,
    adj5_remove_idx: int | None = None,
    **kwargs: int | None,
) -> List[str]:
    """
    Apply the 5 FSU-documented Beale DOI adjustments.

    Adjustment 1: Insert "a" after "institute" (index 153) - "institute a new government"
    Adjustment 2: Remove 1 word between invariably(239) and design(245) - default removes index 240 ("the")
    Adjustment 3: Remove 10 words between repeatedly and be - default removes indices 468-477
    Adjustment 4: Remove 1 word between eat and "to" (military line) - default removes index 631
    Adjustment 5: Remove 1 word between foreign and valuable - default removes index 679

    All indices are 0-based and refer to the token list state BEFORE each adjustment is applied.
    """
    t = list(tokens)

    # 1) Insert "a" after institute (index 153)
    t = t[:154] + ["a"] + t[154:]

    # 2) Remove 1 between invariably and design (indices 240-244 in current t)
    # After adj1, originally 239 is still 239, 245 is now 246
    remove_2 = adj2_remove_idx if adj2_remove_idx is not None else 240
    t = t[:remove_2] + t[remove_2 + 1 :]

    # 3) Remove 10 between repeatedly and be
    # Originally 466=repeatedly, 494=be. After adj1: 467, 495. After adj2: 466, 494.
    # Span 468-494 (before be). Remove 10 consecutive. Default: 468-477
    start_3 = adj3_remove_start if adj3_remove_start is not None else 468
    t = t[:start_3] + t[start_3 + 10 :]

    # 4) Remove 1 between eat and "to" in military line
    # eat was ~629, "to" in "superior to" was ~661. After adj1,2,3: eat ~618, to ~650
    # We need to find "eat" and "to" in t. For robustness, search.
    eat_idx = next((i for i, w in enumerate(t) if w == "eat"), 618)
    to_idx = None
    for i in range(eat_idx + 1, min(eat_idx + 50, len(t))):
        if t[i] == "to" and i > eat_idx + 5:
            to_idx = i
            break
    if to_idx is None:
        to_idx = eat_idx + 32
    span4 = list(range(eat_idx + 1, to_idx))
    remove_4 = adj4_remove_idx if adj4_remove_idx is not None and adj4_remove_idx in span4 else (span4[0] if span4 else eat_idx + 1)
    if remove_4 < len(t):
        t = t[:remove_4] + t[remove_4 + 1 :]

    # 5) Remove 1 between foreign and valuable
    # Note: FSU documents this removal, but applying it overshifts (807 becomes "laws" not "valuable").
    # Skipping adj5 gives 1311 tokens with 807=valuable. Enable by setting adj5_remove_idx.
    if adj5_remove_idx is not None:
        foreign_idx = next((i for i, w in enumerate(t) if w == "foreign"), 665)
        valuable_idx = next((i for i, w in enumerate(t) if w == "valuable"), 805)
        span5 = list(range(foreign_idx + 1, valuable_idx))
        remove_5 = adj5_remove_idx if adj5_remove_idx in span5 else (span5[0] if span5 else foreign_idx + 1)
        if remove_5 < len(t):
            t = t[:remove_5] + t[remove_5 + 1 :]

    return t


def _oracle_score(tokens: List[str], cipher2: List[int], known_clean: str, overrides: dict) -> float:
    """Compute character match percentage for given tokens."""
    decoded = []
    for cnum in cipher2:
        idx = cnum - 1
        if 0 <= idx < len(tokens) and tokens[idx]:
            letter = overrides.get(cnum) or tokens[idx][0].upper()
        else:
            letter = "?"
        decoded.append(letter if letter and (letter.isalpha() or letter == "?") else "?")
    decoded_str = "".join(decoded)
    matches = sum(1 for a, b in zip(decoded_str, known_clean) if a == b)
    total = min(len(decoded_str), len(known_clean))
    return (matches / total * 100) if total > 0 else 0.0


def find_optimal_removals(
    tokens: List[str],
    cipher2: List[int] | None = None,
    known_plaintext: str | None = None,
) -> Tuple[List[str], dict]:
    """
    Find the combination of removal indices (adj 2-5) that maximizes cipher 2 oracle score.
    Returns (best_tokens, config_dict). Uses greedy sequential search.
    """
    from oracle.cipher2_evaluator import load_cipher2, load_cipher2_known_plaintext

    if cipher2 is None:
        cipher2 = load_cipher2()
    if known_plaintext is None:
        known_plaintext = load_cipher2_known_plaintext()
    known_clean = "".join(c.upper() for c in known_plaintext if c.isalpha())
    overrides = {95: "U", 811: "Y", 1005: "X"}

    best_tokens = apply_beale_adjustments(tokens)
    best_score = _oracle_score(best_tokens, cipher2, known_clean, overrides)
    best_config = {}

    # Greedy: try varying adj2 (remove index 240-244)
    for r2 in range(240, 245):
        t = apply_beale_adjustments(tokens, adj2_remove_idx=r2)
        score = _oracle_score(t, cipher2, known_clean, overrides)
        if score > best_score:
            best_score = score
            best_tokens = t
            best_config = {"adj2_remove_idx": r2}

    # Try varying adj3 (10-word block start 467-478)
    for start3 in range(467, 479):
        cfg = {**best_config, "adj3_remove_start": start3}
        t = apply_beale_adjustments(tokens, **{k: v for k, v in cfg.items() if v is not None})
        if len(t) < 1310:  # sanity
            continue
        score = _oracle_score(t, cipher2, known_clean, overrides)
        if score > best_score:
            best_score = score
            best_tokens = t
            best_config = cfg

    return best_tokens, best_config


def get_adjusted_tokens(use_optimal: bool = False) -> List[str]:
    """
    Return the Beale-adjusted DOI token list (1322 - 12 + 1 = 1311 tokens).
    Cached for performance. Set use_optimal=True to run find_optimal_removals (slower).
    """
    global _adjusted_tokens_cache
    if _adjusted_tokens_cache is not None:
        return _adjusted_tokens_cache
    standard = load_standard_doi_tokens()
    if use_optimal:
        tokens, _ = find_optimal_removals(standard)
    else:
        tokens = apply_beale_adjustments(standard)
    _adjusted_tokens_cache = tokens
    return tokens

