"""
Cipher 2 'Before Sleep' Oracle Check.

Reports:
  1. First 40 decoded characters (must start with IHAVEDEPOSITED...)
  2. Word at index 807 (should be "valuable")
  3. First mismatch position in known plaintext
  4. Golden invariant: first 20 chars match
"""

import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher

EXPECTED_PREFIX = "IHAVEDEPOSITEDINTHECOUNT"  # "I have deposited in the count[y]..."

def get_doi_words_from_pamphlet():
    """Load DOI words directly from beale_papers.txt (the pamphlet source)."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    if start < 0 or end < 0:
        raise RuntimeError("Could not find DOI markers in beale_papers.txt")
    doi_section = text[start:end + len("honor(1322) .")]
    words = {}
    for m in re.finditer(r'(\w[\w\'-]*)\((\d+)\)', doi_section):
        word, num = m.group(1), int(m.group(2))
        words[num] = word
    max_idx = max(words.keys())
    token_list = [words.get(i, "") for i in range(1, max_idx + 1)]
    return token_list


def get_adjusted_doi_words():
    """Load the adjusted DOI (with Beale FSU adjustments)."""
    from corpus.beale_doi_adjusted import get_adjusted_tokens
    return get_adjusted_tokens()


def decode_c2(tokens, c2_nums):
    """Decode Cipher 2 using first-letter extraction."""
    stream = ""
    for cn in c2_nums:
        idx = cn - 1
        if 0 <= idx < len(tokens):
            w = tokens[idx]
            stream += w[0].upper() if w else "?"
        else:
            stream += "?"
    return stream


def main():
    c2 = load_cipher(2)

    print("=" * 70)
    print("CIPHER 2 ORACLE CHECK")
    print("=" * 70)

    # Load both DOI sources
    pamphlet_words = get_doi_words_from_pamphlet()
    adjusted_words = get_adjusted_doi_words()

    for label, words in [("beale_embedded (pamphlet)", pamphlet_words),
                         ("beale_adjusted_doi", adjusted_words)]:
        print(f"\n--- {label} ---")
        print(f"  Total tokens: {len(words)}")

        # Word at index 807
        if len(words) >= 807:
            w807 = words[806]  # 0-indexed
            print(f"  Word at index 807: '{w807}' (expected: 'valuable')")
        else:
            print(f"  Word at index 807: OUT OF RANGE")

        # Decode
        decoded = decode_c2(words, c2)
        print(f"  Decoded length: {len(decoded)}")
        print(f"  First 40 chars: {decoded[:40]}")
        print(f"  First 80 chars: {decoded[:80]}")

        # Golden invariant check
        prefix_match = decoded[:len(EXPECTED_PREFIX)] == EXPECTED_PREFIX
        print(f"  Golden prefix check: {'PASS' if prefix_match else 'FAIL'}")
        if not prefix_match:
            for i, (a, b) in enumerate(zip(decoded, EXPECTED_PREFIX)):
                if a != b:
                    print(f"    First mismatch at position {i}: got '{a}', expected '{b}'")
                    print(f"    Context: ...{decoded[max(0,i-5):i+10]}...")
                    print(f"    C2 number at pos {i}: {c2[i]}")
                    if 0 <= c2[i]-1 < len(words):
                        print(f"    Word at that index: '{words[c2[i]-1]}'")
                    break

        # Full "I HAVE DEPOSITED" match (first ~15 chars)
        ihave = "IHAVEDEPOSITED"
        ihave_match = decoded[:len(ihave)] == ihave
        print(f"  'I HAVE DEPOSITED' check: {'PASS' if ihave_match else 'FAIL'}")

        # Find first mismatch against known expected plaintext
        known = "IHAVEDEPOSITEDINTHECOUNT"
        mismatch_idx = -1
        for i in range(min(len(decoded), len(known))):
            if decoded[i] != known[i]:
                mismatch_idx = i
                break
        if mismatch_idx >= 0:
            print(f"  First mismatch vs expected at position {mismatch_idx}")
            print(f"    Got: '{decoded[mismatch_idx]}', Expected: '{known[mismatch_idx]}'")
            print(f"    C2 number: {c2[mismatch_idx]}, Word: '{words[c2[mismatch_idx]-1] if c2[mismatch_idx]-1 < len(words) else '?'}'")
        else:
            print(f"  First {len(known)} chars match perfectly.")

        # Count total matches against a full expected stream
        # Approximate: "I have deposited in the county of Bedford..."
        full_expected = (
            "IHAVEDEPOSITEDINTHECOUNT"  # Y cut short since we don't have full known plaintext here
        )

    # Also report C2 numbers for diagnostic
    print(f"\n--- C2 Number Diagnostics ---")
    print(f"  C2 length: {len(c2)}")
    print(f"  C2 first 20 numbers: {c2[:20]}")
    print(f"  C2 max: {max(c2)}")
    print(f"  C2 numbers needing index > 1000: {[n for n in c2 if n > 1000]}")


if __name__ == "__main__":
    main()
