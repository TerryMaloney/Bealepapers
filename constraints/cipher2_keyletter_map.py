"""
Build a map {cipher_number -> required_first_letter} from Cipher 2's validated
decryption using the DOI.

This map represents the ground truth: for each cipher number N that appears in
Cipher 2, word N of the DOI starts with letter L. Under the "same key text"
hypothesis, word N of any candidate key text must also start with letter L.

If a cipher number maps to multiple letters (due to transcription noise in C2
or ambiguous corrections), it is flagged as ambiguous and excluded from hard
constraints.
"""

import sys
from pathlib import Path
from typing import Dict, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus.canonical import CanonicalCorpus
from constraints.overlap_engine import load_cipher


def build_keyletter_map(corpus: CanonicalCorpus = None,
                        cipher2_nums: list = None) -> Dict[int, dict]:
    """
    Build {cipher_number -> {letter, ambiguous, occurrences}} from Cipher 2.

    Returns dict where each key is a cipher number and value has:
      letter: str (uppercase) - the required first letter
      ambiguous: bool - True if the number decodes to different letters
      occurrences: int - how many times this number appears in C2
    """
    if corpus is None:
        corpus = CanonicalCorpus.load("corpus/CANON_DOI.json")
    if cipher2_nums is None:
        cipher2_nums = load_cipher(2)

    letter_sets = defaultdict(set)
    counts = defaultdict(int)

    for cn in cipher2_nums:
        word = corpus.get_word(cn)
        if word:
            letter_sets[cn].add(word[0].upper())
            counts[cn] += 1

    result = {}
    ambiguous_count = 0
    for cn, letters in sorted(letter_sets.items()):
        amb = len(letters) > 1
        if amb:
            ambiguous_count += 1
        result[cn] = {
            "letter": sorted(letters)[0] if not amb else sorted(letters)[0],
            "letters_seen": sorted(letters),
            "ambiguous": amb,
            "occurrences": counts[cn],
        }

    return result


def get_stable_constraints(keyletter_map: Dict[int, dict]) -> Dict[int, str]:
    """Return only non-ambiguous entries as {cipher_number -> letter}."""
    return {cn: info["letter"] for cn, info in keyletter_map.items()
            if not info["ambiguous"]}


def score_keytext_against_constraints(tokens: list,
                                      constraints: Dict[int, str]) -> dict:
    """
    Score a candidate key text's tokens against Cipher 2 letter constraints.

    For each constrained cipher number N, checks if tokens[N-1][0].upper()
    matches the required letter from the DOI.

    Returns:
      passed: int
      total: int
      pass_rate: float
      failures: list of (cipher_number, expected_letter, got_letter_or_None)
    """
    passed = 0
    total = 0
    failures = []
    max_idx = len(tokens)

    for cn, expected in sorted(constraints.items()):
        idx = cn - 1
        if idx >= max_idx:
            continue
        total += 1
        tok = tokens[idx]
        if tok and tok[0].upper() == expected:
            passed += 1
        else:
            got = tok[0].upper() if tok else None
            failures.append((cn, expected, got))

    return {
        "passed": passed,
        "total": total,
        "pass_rate": passed / total if total > 0 else 0.0,
        "failures": failures,
    }


if __name__ == "__main__":
    print("=== Cipher 2 Key-Letter Map ===")
    klmap = build_keyletter_map()
    stable = get_stable_constraints(klmap)
    ambig = sum(1 for v in klmap.values() if v["ambiguous"])
    print(f"Total entries: {len(klmap)}")
    print(f"Stable (non-ambiguous): {len(stable)}")
    print(f"Ambiguous: {ambig}")
    print(f"\nSample stable constraints (first 10):")
    for cn, letter in list(stable.items())[:10]:
        print(f"  cipher_num={cn:4d} -> letter={letter}")

    print(f"\nSelf-check: DOI should pass 100%...")
    corpus = CanonicalCorpus.load("corpus/CANON_DOI.json")
    result = score_keytext_against_constraints(corpus.tokens, stable)
    print(f"  DOI pass rate: {result['pass_rate']:.1%} ({result['passed']}/{result['total']})")
    if result["failures"]:
        print(f"  Failures: {result['failures'][:5]}")
