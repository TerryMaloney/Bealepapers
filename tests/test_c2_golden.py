"""
Golden invariant test for Cipher 2.
This must pass before any C2-derived constraints are trusted.

The beale_adjusted_doi with first-letter extraction must produce a
stream starting with "IHAVEDEPOS" (the known plaintext beginning).
Word at index 807 must be "valuable".
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from corpus.beale_doi_adjusted import get_adjusted_tokens


def test_word_807_is_valuable():
    tokens = get_adjusted_tokens()
    assert tokens[806].lower() == "valuable", f"Word 807 is '{tokens[806]}', expected 'valuable'"


def test_c2_prefix_ihavedepos():
    tokens = get_adjusted_tokens()
    c2 = load_cipher(2)
    decoded = ""
    for cn in c2[:10]:
        idx = cn - 1
        if 0 <= idx < len(tokens):
            decoded += tokens[idx][0].upper()
        else:
            decoded += "?"
    assert decoded == "IHAVEDEPOS", f"C2 first 10 chars: '{decoded}', expected 'IHAVEDEPOS'"


def test_c2_adjusted_token_count():
    tokens = get_adjusted_tokens()
    assert len(tokens) >= 1005, f"Token count {len(tokens)} < 1005 (max C2 number)"


if __name__ == "__main__":
    test_word_807_is_valuable()
    print("PASS: Word 807 = 'valuable'")

    test_c2_prefix_ihavedepos()
    print("PASS: C2 prefix = 'IHAVEDEPOS'")

    test_c2_adjusted_token_count()
    print(f"PASS: Token count = {len(get_adjusted_tokens())} >= 1005")

    print("\nAll golden invariant tests PASSED. C2 oracle is valid.")
