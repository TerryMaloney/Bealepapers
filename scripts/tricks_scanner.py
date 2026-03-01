"""
'Simple Tricks' scanner: test all plausible cipher-class tricks that
invalidate the standard book-cipher framing.

Think like an 1820s Virginia treasure-hider:
  - They PROVED they know book ciphers (Cipher 2 works with DOI)
  - They'd use something the intended recipient could figure out
  - They'd want the OTHER ciphers to resist casual crackers
  - The 'key' was supposed to arrive by mail but never did

HYPOTHESIS CLASSES TESTED:
  A: DOI but with a different indexing scheme (letter-count, modular wrap, reverse)
  B: The pamphlet narrative itself (Beale's letter) as key text
  C: Cipher 2's decoded plaintext as a self-referential key
  D: Direct numeric transforms (no key text at all)
  E: Number manipulation tricks (pairs, differences, digit ops, null removal)
  F: Homophonic substitution (hillclimb, no key text)
"""

import sys
import time
import random
import math
from pathlib import Path
from collections import Counter
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score

OUT_DIR = Path("output/phase90")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================================
# LOAD RAW DATA
# =========================================================================

def load_doi_raw():
    """Load DOI text from beale_papers.txt, return (raw_text, word_list, char_string)."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    # Extract DOI section: between "DECLARATION OF INDEPENDENCE" and the period at end
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    if start < 0 or end < 0:
        raise ValueError("Cannot find DOI in beale_papers.txt")
    doi_section = text[start:end + len("honor(1322) .")]

    # Extract words in order (strip the numbering)
    import re
    words = []
    for m in re.finditer(r'(\w[\w\'-]*)\(\d+\)', doi_section):
        words.append(m.group(1))

    # Build character-only string (letters only, preserving case)
    chars_raw = ''.join(c for c in ' '.join(words) if c.isalpha())

    return doi_section, words, chars_raw


def load_pamphlet_letter():
    """Load Beale's letter from beale_papers.txt as a word list."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Beale's letter runs from about line 11 to line 43
    letter_lines = []
    in_letter = False
    for line in lines:
        if "My Dear Friend Morriss" in line:
            in_letter = True
        if in_letter:
            letter_lines.append(line.strip())
        if "Your friend, T.J.B." in line:
            break
    letter_text = ' '.join(letter_lines)
    import re
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", letter_text)
    return words, letter_text


def load_pamphlet_full():
    """Load the entire pamphlet narrative as words."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    # Everything that's not cipher numbers
    import re
    # Get all lines that aren't cipher number lines
    lines = text.split('\n')
    narrative = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that are mostly numbers/commas (cipher lines)
        if stripped and not re.match(r'^[\d,\s.]+$', stripped):
            narrative.append(stripped)
    narrative_text = ' '.join(narrative)
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", narrative_text)
    return words, narrative_text


def load_c2_plaintext():
    """Load Cipher 2 decoded plaintext as word list."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Plaintext is on lines 63-67 approximately
    pt_lines = []
    for i, line in enumerate(lines):
        if "I have deposited in the county" in line:
            pt_lines.append(line.strip())
        elif "The first deposit consisted" in line:
            pt_lines.append(line.strip())
        elif "The above is securely packed" in line:
            pt_lines.append(line.strip())
    pt_text = ' '.join(pt_lines)
    import re
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", pt_text)
    return words, pt_text


# =========================================================================
# SCORING HELPER
# =========================================================================

def score_stream(stream, label=""):
    """Score a decoded stream. Returns dict with all metrics."""
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    n = len(letters)
    if n < 10:
        return {"label": label, "length": n, "word_coverage": 0, "long_words": 0,
                "quadgram": -99, "preview": stream[:80], "SIGNAL": False}
    wp = score_word_patterns(letters)
    qg = quadgram_score(letters)
    signal = wp["long_word_count"] >= 3 and wp["word_coverage"] >= 0.20
    return {
        "label": label,
        "length": n,
        "word_coverage": wp["word_coverage"],
        "long_words": wp["long_word_count"],
        "quadgram": qg,
        "preview": letters[:100],
        "SIGNAL": signal,
    }


def print_result(r, f=None):
    """Print a result to console and optionally to file."""
    flag = "*** SIGNAL ***" if r["SIGNAL"] else ""
    line = (f"  {r['label']:45s}  len={r['length']:4d}  "
            f"cov={r['word_coverage']:.3f}  long={r['long_words']:2d}  "
            f"qg={r['quadgram']:.3f}  {flag}")
    print(line)
    if f:
        f.write(line + "\n")
    if r.get("preview"):
        prev = f"    preview: {r['preview']}"
        print(prev)
        if f:
            f.write(prev + "\n")


# =========================================================================
# TRICK CLASSES
# =========================================================================

def trick_a_doi_variants(cipher_nums, doi_words, doi_chars):
    """Class A: DOI with different indexing schemes."""
    results = []

    # A1: Standard first-letter (baseline, should be noise for C1)
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(doi_words):
            stream += doi_words[idx][0].upper()
        else:
            stream += "?"
    results.append(score_stream(stream, "A1: DOI first-letter (baseline)"))

    # A2: LETTER INDEXING - treat number as character position
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(doi_chars):
            stream += doi_chars[idx].upper()
        else:
            stream += "?"
    results.append(score_stream(stream, "A2: DOI letter-index (char position)"))

    # A3: MODULAR WRAP - number mod word_count
    wc = len(doi_words)
    stream = ""
    for cn in cipher_nums:
        idx = ((cn - 1) % wc)
        stream += doi_words[idx][0].upper()
    results.append(score_stream(stream, f"A3: DOI mod-wrap (mod {wc})"))

    # A4: REVERSE DOI - count from end
    stream = ""
    rev_words = list(reversed(doi_words))
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(rev_words):
            stream += rev_words[idx][0].upper()
        else:
            stream += "?"
    results.append(score_stream(stream, "A4: DOI reversed word order"))

    # A5: Last letter of word
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(doi_words):
            w = doi_words[idx]
            stream += w[-1].upper() if w else "?"
        else:
            stream += "?"
    results.append(score_stream(stream, "A5: DOI last-letter"))

    # A6: Second letter of word
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(doi_words):
            w = doi_words[idx]
            stream += w[1].upper() if len(w) > 1 else "_"
        else:
            stream += "?"
    results.append(score_stream(stream, "A6: DOI second-letter"))

    # A7: Modular wrap + last letter
    stream = ""
    for cn in cipher_nums:
        idx = ((cn - 1) % wc)
        w = doi_words[idx]
        stream += w[-1].upper() if w else "?"
    results.append(score_stream(stream, "A7: DOI mod-wrap last-letter"))

    # A8: Letter index mod charcount (wrap chars)
    cc = len(doi_chars)
    stream = ""
    for cn in cipher_nums:
        idx = ((cn - 1) % cc)
        stream += doi_chars[idx].upper()
    results.append(score_stream(stream, f"A8: DOI char-wrap (mod {cc})"))

    # A9: Every other word (number*2 indexing)
    stream = ""
    for cn in cipher_nums:
        idx = (cn * 2) - 1
        if 0 <= idx < len(doi_words):
            stream += doi_words[idx][0].upper()
        else:
            stream += "?"
    results.append(score_stream(stream, "A9: DOI double-index (n*2)"))

    # A10: First vowel in word
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(doi_words):
            w = doi_words[idx].upper()
            vowel = next((c for c in w if c in "AEIOU"), "?")
            stream += vowel
        else:
            stream += "?"
    results.append(score_stream(stream, "A10: DOI first-vowel"))

    return results


def trick_b_pamphlet_as_key(cipher_nums):
    """Class B: Use Beale's letter or full pamphlet as key text."""
    results = []

    # B1: Beale's letter, first letter
    letter_words, _ = load_pamphlet_letter()
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(letter_words):
            stream += letter_words[idx][0].upper()
        else:
            stream += "?"
    results.append(score_stream(stream,
        f"B1: Beale's letter first-letter ({len(letter_words)} words)"))

    # B2: Beale's letter mod-wrap
    wc = len(letter_words)
    if wc > 0:
        stream = ""
        for cn in cipher_nums:
            idx = ((cn - 1) % wc)
            stream += letter_words[idx][0].upper()
        results.append(score_stream(stream, f"B2: Beale's letter mod-wrap (mod {wc})"))

    # B3: Full pamphlet, first letter
    pamphlet_words, _ = load_pamphlet_full()
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(pamphlet_words):
            stream += pamphlet_words[idx][0].upper()
        else:
            stream += "?"
    results.append(score_stream(stream,
        f"B3: Full pamphlet first-letter ({len(pamphlet_words)} words)"))

    # B4: Full pamphlet mod-wrap
    wc = len(pamphlet_words)
    if wc > 0:
        stream = ""
        for cn in cipher_nums:
            idx = ((cn - 1) % wc)
            stream += pamphlet_words[idx][0].upper()
        results.append(score_stream(stream, f"B4: Full pamphlet mod-wrap (mod {wc})"))

    return results


def trick_c_self_referential(cipher_nums):
    """Class C: Use Cipher 2's decoded plaintext as key."""
    results = []

    c2_words, c2_text = load_c2_plaintext()

    # C1: first letter
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(c2_words):
            stream += c2_words[idx][0].upper()
        else:
            stream += "?"
    results.append(score_stream(stream,
        f"C1: C2-plaintext first-letter ({len(c2_words)} words)"))

    # C2: mod-wrap
    wc = len(c2_words)
    if wc > 0:
        stream = ""
        for cn in cipher_nums:
            idx = ((cn - 1) % wc)
            stream += c2_words[idx][0].upper()
        results.append(score_stream(stream, f"C2: C2-plaintext mod-wrap (mod {wc})"))

    # C3: letter-index in plaintext
    c2_chars = ''.join(c for c in c2_text if c.isalpha())
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(c2_chars):
            stream += c2_chars[idx].upper()
        else:
            stream += "?"
    results.append(score_stream(stream,
        f"C3: C2-plaintext char-index ({len(c2_chars)} chars)"))

    return results


def trick_d_numeric_transforms(cipher_nums):
    """Class D: Direct number-to-letter transforms (no key text)."""
    results = []

    def nums_to_stream(nums, label):
        stream = ""
        for n in nums:
            if 1 <= n <= 26:
                stream += chr(64 + n)
            else:
                stream += "?"
        return score_stream(stream, label)

    # D1: n mod 26
    mapped = [(n % 26) if (n % 26) != 0 else 26 for n in cipher_nums]
    results.append(nums_to_stream(mapped, "D1: n mod 26"))

    # D2: digit sum mod 26
    mapped = [sum(int(d) for d in str(n)) for n in cipher_nums]
    mapped = [(m % 26) if (m % 26) != 0 else 26 for m in mapped]
    results.append(nums_to_stream(mapped, "D2: digit-sum mod 26"))

    # D3: last two digits mod 26
    mapped = [(n % 100) for n in cipher_nums]
    mapped = [(m % 26) if (m % 26) != 0 else 26 for m in mapped]
    results.append(nums_to_stream(mapped, "D3: last-2-digits mod 26"))

    # D4: first digit only
    mapped = [int(str(n)[0]) for n in cipher_nums]
    mapped = [(m % 26) if (m % 26) != 0 else 26 for m in mapped]
    results.append(nums_to_stream(mapped, "D4: first-digit mod 26"))

    # D5: differences between successive numbers mod 26
    diffs = [abs(cipher_nums[i] - cipher_nums[i-1]) for i in range(1, len(cipher_nums))]
    mapped = [(d % 26) if (d % 26) != 0 else 26 for d in diffs]
    results.append(nums_to_stream(mapped, "D5: diff-successive mod 26"))

    # D6: n mod 27 (with 27=space)
    stream = ""
    for n in cipher_nums:
        m = n % 27
        if m == 0:
            stream += " "
        elif 1 <= m <= 26:
            stream += chr(64 + m)
    results.append(score_stream(stream, "D6: n mod 27 (27=space)"))

    # D7: reversed digits then mod 26
    mapped = [int(str(n)[::-1]) for n in cipher_nums]
    mapped = [(m % 26) if (m % 26) != 0 else 26 for m in mapped]
    results.append(nums_to_stream(mapped, "D7: reverse-digits mod 26"))

    # D8: n // 100 (hundreds digit as letter)
    mapped = [(n // 100) for n in cipher_nums]
    mapped = [(m % 26) if (m % 26) != 0 else 26 for m in mapped]
    results.append(nums_to_stream(mapped, "D8: hundreds-digit mod 26"))

    # D9: XOR successive
    xors = [cipher_nums[i] ^ cipher_nums[i-1] for i in range(1, len(cipher_nums))]
    mapped = [(x % 26) if (x % 26) != 0 else 26 for x in xors]
    results.append(nums_to_stream(mapped, "D9: XOR-successive mod 26"))

    # D10: sqrt(n) mod 26
    mapped = [int(math.sqrt(n)) for n in cipher_nums]
    mapped = [(m % 26) if (m % 26) != 0 else 26 for m in mapped]
    results.append(nums_to_stream(mapped, "D10: sqrt(n) mod 26"))

    return results


def trick_e_number_manipulation(cipher_nums, doi_words):
    """Class E: Manipulate the number sequence itself before lookup."""
    results = []
    wc = len(doi_words)

    def decode_nums(nums, label):
        stream = ""
        for cn in nums:
            idx = cn - 1
            if 0 <= idx < wc:
                stream += doi_words[idx][0].upper()
            else:
                stream += "?"
        return score_stream(stream, label)

    # E1: Every other number (odds only)
    results.append(decode_nums(cipher_nums[::2], "E1: every-other (odds)"))

    # E2: Every other number (evens only)
    results.append(decode_nums(cipher_nums[1::2], "E2: every-other (evens)"))

    # E3: Read pairs as single numbers (71,194 -> 71194)
    # Actually try pairs as two-digit concatenation is too large
    # Try: adjacent pairs summed
    paired = [cipher_nums[i] + cipher_nums[i+1]
              for i in range(0, len(cipher_nums) - 1, 2)]
    results.append(decode_nums(paired, "E3: pairs summed"))

    # E4: Adjacent differences (absolute)
    diffs = [abs(cipher_nums[i] - cipher_nums[i-1])
             for i in range(1, len(cipher_nums))]
    results.append(decode_nums(diffs, "E4: adjacent differences"))

    # E5: Remove numbers > 1322 (out of DOI range)
    filtered = [n for n in cipher_nums if n <= wc]
    results.append(decode_nums(filtered,
        f"E5: remove >DOI range ({len(filtered)}/{len(cipher_nums)})"))

    # E6: Numbers > 1322 mod 1322
    remapped = []
    for n in cipher_nums:
        if n <= wc:
            remapped.append(n)
        else:
            remapped.append(((n - 1) % wc) + 1)
    results.append(decode_nums(remapped, "E6: large nums mod-wrapped"))

    # E7: Digit reversal then lookup
    reversed_nums = [int(str(n)[::-1]) for n in cipher_nums]
    results.append(decode_nums(reversed_nums, "E7: digit-reversed nums"))

    # E8: Number minus its position (n - i)
    shifted = [max(1, cn - i) for i, cn in enumerate(cipher_nums)]
    results.append(decode_nums(shifted, "E8: n minus position"))

    # E9: Running sum mod 1322
    running = []
    s = 0
    for cn in cipher_nums:
        s = ((s + cn - 1) % wc) + 1
        running.append(s)
    results.append(decode_nums(running, "E9: running-sum mod DOI"))

    # E10: Split 4-digit numbers (e.g., 1701 -> 17, 01)
    split_nums = []
    for cn in cipher_nums:
        s = str(cn)
        if len(s) == 4:
            split_nums.append(int(s[:2]))
            split_nums.append(int(s[2:]))
        elif len(s) == 3:
            split_nums.append(int(s[0]))
            split_nums.append(int(s[1:]))
        else:
            split_nums.append(cn)
    results.append(decode_nums(split_nums,
        f"E10: split multi-digit ({len(split_nums)} nums)"))

    # E11: Remove every 3rd number
    filtered = [n for i, n in enumerate(cipher_nums) if (i + 1) % 3 != 0]
    results.append(decode_nums(filtered,
        f"E11: remove every 3rd ({len(filtered)})"))

    # E12: Remove multiples of some number
    for divisor in [5, 7, 10, 13]:
        filtered = [n for n in cipher_nums if n % divisor != 0]
        results.append(decode_nums(filtered,
            f"E12: remove multiples of {divisor} ({len(filtered)})"))

    return results


def trick_f_homophonic(cipher_nums, iterations=50000):
    """Class F: Homophonic substitution solver using hillclimb."""
    results = []
    unique_nums = sorted(set(cipher_nums))
    num_to_idx = {n: i for i, n in enumerate(unique_nums)}
    symbol_stream = [num_to_idx[n] for n in cipher_nums]
    n_symbols = len(unique_nums)

    random.seed(42)

    # Build overlap constraint map from C2
    try:
        from constraints.cipher2_keyletter_map import build_keyletter_map, get_stable_constraints
        klmap = build_keyletter_map()
        stable = get_stable_constraints(klmap)
        overlap_set = set(cipher_nums) & set(stable.keys())
        fixed_map = {}
        for num in overlap_set:
            if num in stable:
                fixed_map[num_to_idx[num]] = ord(stable[num]) - ord('A')
    except:
        fixed_map = {}

    def random_mapping(constrained=False):
        m = [random.randint(0, 25) for _ in range(n_symbols)]
        if constrained:
            for sym_idx, letter_idx in fixed_map.items():
                m[sym_idx] = letter_idx
        return m

    def decode_with_mapping(mapping):
        return ''.join(chr(65 + mapping[s]) for s in symbol_stream)

    def score_mapping(mapping):
        text = decode_with_mapping(mapping)
        return quadgram_score(text)

    def hillclimb(constrained=False, n_iter=50000):
        best_mapping = random_mapping(constrained)
        best_score = score_mapping(best_mapping)

        for _ in range(n_iter):
            new_mapping = list(best_mapping)
            idx = random.randint(0, n_symbols - 1)
            if constrained and idx in fixed_map:
                continue
            new_mapping[idx] = random.randint(0, 25)
            new_score = score_mapping(new_mapping)
            if new_score > best_score:
                best_score = new_score
                best_mapping = new_mapping

        return best_mapping, best_score

    # F1: Unconstrained homophonic
    print("  [F1] Hillclimbing unconstrained homophonic...")
    best_m, best_s = None, -99
    for trial in range(5):
        m, s = hillclimb(constrained=False, n_iter=iterations)
        if s > best_s:
            best_m, best_s = m, s
    text = decode_with_mapping(best_m)
    results.append(score_stream(text, f"F1: homophonic unconstrained (best of 5)"))

    # F2: Constrained (C2 overlap fixed)
    if fixed_map:
        print(f"  [F2] Hillclimbing with {len(fixed_map)} fixed constraints...")
        best_m2, best_s2 = None, -99
        for trial in range(5):
            m, s = hillclimb(constrained=True, n_iter=iterations)
            if s > best_s2:
                best_m2, best_s2 = m, s
        text2 = decode_with_mapping(best_m2)
        results.append(score_stream(text2,
            f"F2: homophonic constrained ({len(fixed_map)} fixed)"))

    return results


# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 80)
    print("SIMPLE TRICKS SCANNER")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)

    # Load data
    doi_section, doi_words, doi_chars = load_doi_raw()
    print(f"\nDOI: {len(doi_words)} words, {len(doi_chars)} characters")

    c1 = load_cipher(1)
    c3 = load_cipher(3)
    c2 = load_cipher(2)
    print(f"C1: {len(c1)} numbers, max={max(c1)}")
    print(f"C2: {len(c2)} numbers, max={max(c2)}")
    print(f"C3: {len(c3)} numbers, max={max(c3)}")

    letter_words, _ = load_pamphlet_letter()
    pamphlet_words, _ = load_pamphlet_full()
    c2_words, _ = load_c2_plaintext()
    print(f"Beale's letter: {len(letter_words)} words")
    print(f"Full pamphlet: {len(pamphlet_words)} words")
    print(f"C2 plaintext: {len(c2_words)} words")

    # Calibration
    print("\n" + "=" * 80)
    print("CALIBRATION CHECK")
    print("=" * 80)
    cal_stream = ""
    for cn in c2:
        idx = cn - 1
        if 0 <= idx < len(doi_words):
            cal_stream += doi_words[idx][0].upper()
        else:
            cal_stream += "?"
    cal = score_stream(cal_stream, "CALIBRATION: C2+DOI (known correct)")
    print_result(cal)

    # Random baseline
    random.seed(42)
    rand_stream = ''.join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(520))
    rand = score_stream(rand_stream, "CALIBRATION: random 520 chars")
    print_result(rand)

    all_results = [cal, rand]

    # Run all tricks for both C1 and C3
    for cipher_name, cipher_nums in [("CIPHER 1", c1), ("CIPHER 3", c3)]:
        print(f"\n{'='*80}")
        print(f"{cipher_name} TRICKS")
        print(f"{'='*80}")

        print(f"\n--- Class A: DOI indexing variants ---")
        ra = trick_a_doi_variants(cipher_nums, doi_words, doi_chars)
        for r in ra:
            print_result(r)
        all_results.extend(ra)

        print(f"\n--- Class B: Pamphlet as key ---")
        rb = trick_b_pamphlet_as_key(cipher_nums)
        for r in rb:
            print_result(r)
        all_results.extend(rb)

        print(f"\n--- Class C: Self-referential (C2 plaintext as key) ---")
        rc = trick_c_self_referential(cipher_nums)
        for r in rc:
            print_result(r)
        all_results.extend(rc)

        print(f"\n--- Class D: Numeric transforms ---")
        rd = trick_d_numeric_transforms(cipher_nums)
        for r in rd:
            print_result(r)
        all_results.extend(rd)

        print(f"\n--- Class E: Number manipulation ---")
        re_results = trick_e_number_manipulation(cipher_nums, doi_words)
        for r in re_results:
            print_result(r)
        all_results.extend(re_results)

        print(f"\n--- Class F: Homophonic substitution ---")
        rf = trick_f_homophonic(cipher_nums, iterations=80000)
        for r in rf:
            print_result(r)
        all_results.extend(rf)

    # Write comprehensive report
    report_path = OUT_DIR / "tricks_scanner_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("SIMPLE TRICKS SCANNER - COMPREHENSIVE REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Command: python scripts/tricks_scanner.py\n")
        f.write("=" * 80 + "\n\n")

        # Sort by quadgram score (best first)
        ranked = sorted(all_results, key=lambda r: r["quadgram"], reverse=True)

        f.write("ALL RESULTS RANKED BY QUADGRAM SCORE:\n")
        f.write("-" * 80 + "\n")
        for r in ranked:
            print_result(r, f)
            f.write("\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("SIGNAL CHECK\n")
        f.write("=" * 80 + "\n")
        signals = [r for r in all_results if r["SIGNAL"]]
        if signals:
            f.write(f"\n*** {len(signals)} SIGNALS DETECTED ***\n")
            for s in signals:
                f.write(f"  {s['label']}\n")
                f.write(f"    coverage={s['word_coverage']:.3f}, "
                        f"long_words={s['long_words']}, "
                        f"quadgram={s['quadgram']:.3f}\n")
                f.write(f"    preview: {s['preview']}\n")
        else:
            f.write("\nNO SIGNALS. Zero tricks produced English-like output.\n")
            f.write(f"Threshold: word_coverage >= 0.20 AND long_word_count >= 3\n")
            f.write(f"Best coverage: {max(r['word_coverage'] for r in all_results):.3f}\n")
            f.write(f"Best quadgram: {max(r['quadgram'] for r in all_results):.3f}\n")
            f.write(f"Calibration (C2 correct): coverage={cal['word_coverage']:.3f}, "
                    f"qg={cal['quadgram']:.3f}\n")

    print(f"\n{'='*80}")
    print(f"REPORT: {report_path}")
    print(f"{'='*80}")

    # Print signal summary
    signals = [r for r in all_results if r["SIGNAL"]]
    if signals:
        print(f"\n*** {len(signals)} SIGNALS DETECTED ***")
        for s in signals:
            print(f"  {s['label']}: cov={s['word_coverage']:.3f}, long={s['long_words']}")
    else:
        best_qg = max(all_results, key=lambda r: r["quadgram"])
        best_cov = max(all_results, key=lambda r: r["word_coverage"])
        print(f"\nNO SIGNALS DETECTED across {len(all_results)} trick variants.")
        print(f"Best quadgram: {best_qg['label']} = {best_qg['quadgram']:.3f}")
        print(f"Best coverage: {best_cov['label']} = {best_cov['word_coverage']:.3f}")
        print(f"Calibration:   C2+DOI = qg={cal['quadgram']:.3f}, cov={cal['word_coverage']:.3f}")


if __name__ == "__main__":
    main()
