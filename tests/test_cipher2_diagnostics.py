"""
Cipher 2 Diagnostic Test Suite

Triangulates why Cipher 2 oracle is ~27% despite 100% pamphlet marker validation.
Run from project root: python tests/test_cipher2_diagnostics.py
Single test: python tests/test_cipher2_diagnostics.py --test N
"""

import argparse
import sys
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure cwd is project root for beale_papers.txt
_project_root = Path(__file__).resolve().parent.parent
if Path.cwd() != _project_root:
    import os
    os.chdir(_project_root)

from corpus.beale_pamphlet_pdf import load_and_tokenize
from corpus.beale_doi_adjusted import get_adjusted_tokens
from corpus.doi_editions import DOICorpusLoader
from oracle.cipher2_evaluator import (
    Cipher2Oracle,
    load_cipher2,
    load_cipher2_known_plaintext,
)

BEALE_OVERRIDES = {95: "U", 811: "Y", 1005: "X"}

# Golden index assertions (adjusted DOI) - fail loudly if broken
# 807/810/811 from pamphlet PDF; 115/154/466/1005 from FSU
GOLDEN_CHECKS = {
    807: "valuable",
    810: "altering",
    811: "fundamentally",
    115: "instituted",
    154: "institute",
    466: "houses",
    1005: "have",
}


def _get_tokens(edition: str = "adjusted"):
    """Get DOI tokens for the given edition."""
    if edition == "adjusted":
        return get_adjusted_tokens()
    tokens, _ = load_and_tokenize()
    return tokens


def _extract_letter(word: str, cipher_num: int, overrides: dict) -> str:
    """Extract first letter with overrides (matches oracle logic)."""
    if cipher_num in overrides:
        return overrides[cipher_num]
    if word:
        return word[0].upper()
    return "?"


def test_prefix_decode(edition: str = "adjusted"):
    """Test 1: Decode first 60 chars and compare to expected plaintext."""
    print("\n" + "=" * 80)
    print(f"TEST 1: PREFIX DECODE SANITY CHECK (edition={edition})")
    print("=" * 80)

    tokens = _get_tokens(edition)
    cipher2 = load_cipher2()
    known = load_cipher2_known_plaintext()
    known_clean = "".join(c.upper() for c in known if c.isalpha())

    n = min(60, len(cipher2), len(known_clean))
    decoded_chars = []
    print(f"\nFirst {n} positions: cipher_num | DOI token | extracted | expected | match")
    print("-" * 70)

    for i in range(n):
        cnum = cipher2[i]
        word_idx = cnum - 1
        if 0 <= word_idx < len(tokens):
            word = tokens[word_idx]
            word_display = str(word)[:12]
        else:
            word = ""
            word_display = "(OOR)"
        letter = _extract_letter(word if isinstance(word, str) else "", cnum, BEALE_OVERRIDES)
        if not (0 <= word_idx < len(tokens)):
            letter = "?"
        expected = known_clean[i] if i < len(known_clean) else ""
        match = "OK" if letter == expected else "MISMATCH"
        decoded_chars.append(letter)
        print(f"  {i+1:3}: {cnum:4} | {word_display:12} | {letter:^9} | {expected:^8} | {match}")

    decoded_str = "".join(decoded_chars)
    print(f"\nDecoded (first {n}): {decoded_str}")
    print(f"Expected (first {n}): {known_clean[:n]}")
    align = "".join("^" if decoded_str[i] != known_clean[i] else " " for i in range(min(len(decoded_str), len(known_clean))))
    print(f"Mismatches:          {align[:n]}")


def test_cipher2_line_verification():
    """Test 2: Verify load_cipher2 reads correct line from beale_papers.txt."""
    print("\n" + "=" * 80)
    print("TEST 2: CIPHER 2 NUMBER LIST LINE VERIFICATION")
    print("=" * 80)

    path = Path("beale_papers.txt")
    if not path.exists():
        print("  [ERROR] beale_papers.txt not found")
        return

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for idx in [56, 57, 58, 59]:
        line = lines[idx] if idx < len(lines) else ""
        preview = (line.strip()[:80] + "...") if len(line.strip()) > 80 else line.strip()
        print(f"  lines[{idx}]: {repr(preview)}")

    cipher2 = load_cipher2()
    print(f"\n  load_cipher2() count: {len(cipher2)}")
    print(f"  First 10: {cipher2[:10]}")
    print(f"  Last 10:  {cipher2[-10:]}")

    ok = True
    if len(cipher2) != 763:
        print(f"  [FLAG] Expected 763 numbers, got {len(cipher2)}")
        ok = False
    if cipher2[0] != 115:
        print(f"  [FLAG] Expected first=115, got {cipher2[0]}")
        ok = False
    if cipher2[-1] != 288:
        print(f"  [FLAG] Expected last=288, got {cipher2[-1]}")
        ok = False
    if ok:
        print("  [OK] Count and boundaries look correct")


def test_range_and_boundaries(edition: str = "adjusted"):
    """Test 3: Out-of-range and special-token analysis."""
    print("\n" + "=" * 80)
    print(f"TEST 3: OUT-OF-RANGE AND BOUNDARY ANALYSIS (edition={edition})")
    print("=" * 80)

    tokens = _get_tokens(edition)
    cipher2 = load_cipher2()

    max_idx = len(tokens)
    out_of_range = [(i, n) for i, n in enumerate(cipher2) if n < 1 or n > max_idx]
    print(f"  Out-of-range [1,{max_idx}]: {len(out_of_range)}")
    if out_of_range:
        for i, (pos, n) in enumerate(out_of_range[:20]):
            print(f"    position {pos}: cipher_num={n}")
        if len(out_of_range) > 20:
            print(f"    ... and {len(out_of_range) - 20} more")

    special_positions = {908: "&", 47: "nature's"}
    print(f"\n  Special tokens:")
    for pos, label in special_positions.items():
        tok = tokens[pos - 1] if 1 <= pos <= len(tokens) else "(OOR)"
        first = tok[0] if tok and isinstance(tok, str) else "?"
        print(f"    position {pos} ({label}): token={repr(tok)}, first_char={repr(first)}")

    and_positions = [i for i, n in enumerate(cipher2) if n == 908]
    if and_positions:
        known = load_cipher2_known_plaintext()
        known_clean = "".join(c.upper() for c in known if c.isalpha())
        print(f"\n  Cipher number 908 (&) appears at decoded positions: {and_positions[:10]}...")
        for idx in and_positions[:5]:
            exp = known_clean[idx] if idx < len(known_clean) else "?"
            print(f"    decoded pos {idx}: expected letter '{exp}'")


def test_edition_comparison(edition: str = "adjusted"):
    """Test 4: beale_embedded vs beale_pamphlet_pdf vs beale_adjusted_doi decode comparison."""
    print("\n" + "=" * 80)
    print("TEST 4: EDITION DECODE COMPARISON")
    print("=" * 80)

    loader = DOICorpusLoader()
    cipher2 = load_cipher2()
    known = load_cipher2_known_plaintext()
    oracle = Cipher2Oracle(known)

    emb_ed = loader.load_edition("beale_embedded")
    pam_ed = loader.load_edition("beale_pamphlet_pdf")
    adj_tokens = get_adjusted_tokens()

    emb_tokens = emb_ed.source_text.split()
    pam_tokens = pam_ed.source_text.split()

    print(f"  beale_embedded tokens: {len(emb_tokens)}")
    print(f"  beale_pamphlet_pdf tokens: {len(pam_tokens)}")
    print(f"  beale_adjusted_doi tokens: {len(adj_tokens)}")

    r_emb = oracle.evaluate(emb_tokens, cipher2, letter_overrides=BEALE_OVERRIDES)
    r_pam = oracle.evaluate(pam_tokens, cipher2, letter_overrides=BEALE_OVERRIDES)
    r_adj = oracle.evaluate(adj_tokens, cipher2, letter_overrides=BEALE_OVERRIDES)

    print(f"\n  beale_embedded oracle:    {r_emb.char_match_pct:.2f}%")
    print(f"  beale_pamphlet_pdf oracle: {r_pam.char_match_pct:.2f}%")
    print(f"  beale_adjusted_doi oracle: {r_adj.char_match_pct:.2f}%")

    print(f"\n  First 80 decoded (adjusted): {r_adj.decoded_sample[:80]}")

    diffs = []
    for i in range(min(len(r_emb.decoded_sample), len(r_pam.decoded_sample), len(cipher2))):
        if r_emb.decoded_sample[i] != r_pam.decoded_sample[i]:
            cnum = cipher2[i]
            emb_word = emb_tokens[cnum - 1] if 0 <= cnum - 1 < len(emb_tokens) else "(OOR)"
            pam_word = pam_tokens[cnum - 1] if 0 <= cnum - 1 < len(pam_tokens) else "(OOR)"
            diffs.append((i, cnum, emb_word, pam_word, r_emb.decoded_sample[i], r_pam.decoded_sample[i]))

    print(f"\n  Positions where embedded vs pamphlet decode differently (first 10):")
    for i, (pos, cnum, ew, pw, el, pl) in enumerate(diffs[:10]):
        print(f"    pos {pos}: cipher_num={cnum} | emb={repr(ew)[:12]}->'{el}' | pam={repr(pw)[:12]}->'{pl}'")
    if len(diffs) > 10:
        print(f"    ... and {len(diffs) - 10} more")


def test_hot_number_analysis(edition: str = "adjusted"):
    """Test 5: High-frequency number analysis (The 807 Test)."""
    print("\n" + "=" * 80)
    print(f"TEST 5: HIGH-FREQUENCY NUMBER ANALYSIS (edition={edition})")
    print("=" * 80)

    from collections import Counter

    tokens = _get_tokens(edition)
    cipher2 = load_cipher2()
    known = load_cipher2_known_plaintext()
    known_clean = "".join(c.upper() for c in known if c.isalpha())

    freq = Counter(cipher2)
    top15 = freq.most_common(15)

    print("  Top 15 most frequent cipher numbers:")
    print("  " + "-" * 50)
    for num, count in top15:
        word_idx = num - 1
        word = tokens[word_idx] if 0 <= word_idx < len(tokens) else "(OOR)"
        first = _extract_letter(word if isinstance(word, str) else "", num, BEALE_OVERRIDES)
        print(f"    {num:4} x{count:3}  token={str(word)[:15]:15}  first_letter={first}")

    print("\n  Per-number hit rate (top 5):")
    for num, count in top15[:5]:
        positions = [i for i, n in enumerate(cipher2) if n == num]
        word = tokens[num - 1] if 0 <= num - 1 < len(tokens) else ""
        decoded_letter = _extract_letter(word if isinstance(word, str) else "", num, BEALE_OVERRIDES)
        matches = sum(1 for p in positions if p < len(known_clean) and decoded_letter == known_clean[p])
        print(f"    {num}: appears {count}x, decoded='{decoded_letter}', matches {matches}/{count}")


def test_normalization_check(edition: str = "adjusted"):
    """Test 6: Known plaintext normalization check."""
    print("\n" + "=" * 80)
    print(f"TEST 6: KNOWN PLAINTEXT NORMALIZATION CHECK (edition={edition})")
    print("=" * 80)

    tokens = _get_tokens(edition)
    cipher2 = load_cipher2()
    known = load_cipher2_known_plaintext()
    oracle = Cipher2Oracle(known)
    result = oracle.evaluate(tokens, cipher2, letter_overrides=BEALE_OVERRIDES)

    # Rebuild full decoded string to match oracle logic
    decoded_chars = []
    for cnum in cipher2:
        word_idx = cnum - 1
        if 0 <= word_idx < len(tokens):
            word = tokens[word_idx]
            letter = _extract_letter(word if word else "", cnum, BEALE_OVERRIDES)
            decoded_chars.append(letter if letter else "?")
        else:
            decoded_chars.append("?")
    decoded = "".join(decoded_chars)
    known_clean = oracle.known_clean

    n = min(120, len(decoded), len(known_clean))
    print(f"  Decoded (first {n}): {decoded[:n]}")
    print(f"  Known_clean (first {n}): {known_clean[:n]}")
    print(f"  len(decoded)={len(decoded)}, len(known_clean)={len(known_clean)}")

    align = "".join("|" if decoded[i] == known_clean[i] else "X" for i in range(n))
    print(f"  Alignment (| = match, X = mismatch):\n  {align[:n]}")

    prefix_matches = sum(1 for i in range(n) if decoded[i] == known_clean[i])
    prefix_pct = (prefix_matches / n * 100) if n > 0 else 0
    full_pct = result.char_match_pct
    align_pct = getattr(result, "alignment_pct", 0.0)
    print(f"\n  Match over first 120 chars: {prefix_matches}/{n} = {prefix_pct:.1f}%")
    print(f"  Match over full length (strict): {result.char_matches}/{result.total_chars} = {full_pct:.2f}%")
    if align_pct > 0:
        print(f"  Match over full length (alignment/LCS): {align_pct:.2f}%")
    if prefix_pct > full_pct + 5:
        print("  [NOTE] Prefix matches much better than tail -> suggests cumulative drift/shift")


def test_oracle_normalization():
    """Test 8: Oracle normalization - decoded and expected are letters only (A-Z or ?)."""
    print("\n" + "=" * 80)
    print("TEST 8: ORACLE NORMALIZATION VERIFICATION")
    print("=" * 80)

    tokens = _get_tokens("adjusted")
    cipher2 = load_cipher2()
    known = load_cipher2_known_plaintext()
    oracle = Cipher2Oracle(known)
    result = oracle.evaluate(tokens, cipher2, letter_overrides=BEALE_OVERRIDES)

    decoded_chars = []
    for cnum in cipher2:
        word_idx = cnum - 1
        if 0 <= word_idx < len(tokens):
            word = tokens[word_idx]
            letter = _extract_letter(word if word else "", cnum, BEALE_OVERRIDES)
            decoded_chars.append(letter if letter else "?")
        else:
            decoded_chars.append("?")
    decoded = "".join(decoded_chars)

    # Decoded must contain only A-Z or '?'
    bad_decoded = [c for c in decoded if c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ?"]
    # known_clean must contain only A-Z
    bad_known = [c for c in oracle.known_clean if c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]

    print(f"  Decoded length: {len(decoded)}, known_clean length: {len(oracle.known_clean)}")
    print(f"  Decoded has only A-Z or '?': {len(bad_decoded) == 0} (bad chars: {bad_decoded[:10] or 'none'})")
    print(f"  known_clean has only A-Z: {len(bad_known) == 0} (bad chars: {bad_known[:10] or 'none'})")

    assert not bad_decoded, f"Decoded contains non-letter chars: {bad_decoded[:20]}"
    assert not bad_known, f"known_clean contains non-letter chars: {bad_known[:20]}"
    print("  [OK] Oracle normalization verified: both streams are letters-only (or ?)")


def test_golden_assertions():
    """Test 7: Golden index assertions - fail loudly if indices don't match pamphlet."""
    print("\n" + "=" * 80)
    print("TEST 7: GOLDEN INDEX ASSERTIONS")
    print("=" * 80)

    tokens = get_adjusted_tokens()
    failures = []
    for pos, expected in GOLDEN_CHECKS.items():
        idx = pos - 1
        actual = tokens[idx] if 0 <= idx < len(tokens) else "(OOR)"
        if actual.lower() != expected.lower():
            failures.append((pos, expected, actual))
            print(f"  [FAIL] Position {pos}: expected '{expected}', got '{actual}'")
        else:
            print(f"  [OK]   Position {pos}: '{actual}'")

    if failures:
        msg = f"GOLDEN ASSERTIONS FAILED: {len(failures)} mismatches - {failures}"
        raise AssertionError(msg)
    print(f"\n  All {len(GOLDEN_CHECKS)} golden checks PASSED")


def main():
    parser = argparse.ArgumentParser(description="Cipher 2 Diagnostic Tests")
    parser.add_argument("--test", type=int, choices=range(1, 9), metavar="N",
                        help="Run only test N (1-8)")
    parser.add_argument("--edition", choices=["pamphlet", "adjusted"], default="adjusted",
                        help="DOI edition for tests (default: adjusted)")
    args = parser.parse_args()

    edition = args.edition
    tests = [
        lambda: test_prefix_decode(edition),
        test_cipher2_line_verification,
        lambda: test_range_and_boundaries(edition),
        lambda: test_edition_comparison(edition),
        lambda: test_hot_number_analysis(edition),
        lambda: test_normalization_check(edition),
        test_golden_assertions,
        lambda: test_oracle_normalization(),
    ]

    if args.test is not None:
        tests[args.test - 1]()
    else:
        for t in tests:
            t()

    print("\n" + "=" * 80)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
