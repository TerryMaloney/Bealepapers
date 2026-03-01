"""
Phase 92 Sweep: comprehensive test of offset, transposition, digit-split,
position-dependent extraction, and 'placement' (sentence/line indexing)
hypotheses against top key texts.

Combines:
  A) Additive offsets on DOI and top texts (-500 to +500)
  B) Columnar transposition of cipher number sequence (widths 2-20)
  C) Digit-split extraction (word index + letter position from number)
  D) Position-dependent letter extraction
  E) MY HYPOTHESIS: 'Placement cipher' - numbers index lines/sentences, not words

Uses adaptive thresholds from output/phase92/calibration.json.
"""

import json
import csv
import sys
import re
import time
import math
from pathlib import Path
from datetime import datetime
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus.keytexts.loader import load_all_keytexts, load_normalized
from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score

OUT = Path("output/phase92")
OUT.mkdir(parents=True, exist_ok=True)

# =========================================================================
# LOAD CALIBRATION
# =========================================================================

def load_calibration():
    cal_path = OUT / "calibration.json"
    with open(cal_path) as f:
        return json.load(f)

# =========================================================================
# DOI LOADER
# =========================================================================

def get_doi_words():
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    doi = text[start:end + len("honor(1322) .")]
    return [m.group(1) for m in re.finditer(r'(\w[\w\'-]*)\(\d+\)', doi)]

def get_doi_raw_text():
    """Get the DOI as raw continuous text (for line-layout hypothesis)."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    doi = text[start:end + len("honor(1322) .")]
    # Strip number annotations
    clean = re.sub(r'\(\d+\)', '', doi)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# =========================================================================
# SCORING
# =========================================================================

def score(stream, label=""):
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    n = len(letters)
    if n < 15:
        return {"label": label, "len": n, "cov": 0, "long": 0, "qg": -99, "preview": "", "signal": False}
    wp = score_word_patterns(letters)
    qg = quadgram_score(letters)
    return {
        "label": label,
        "len": n,
        "cov": wp["word_coverage"],
        "long": wp["long_word_count"],
        "qg": qg,
        "preview": letters[:120],
        "signal": False,  # set later by threshold check
    }

# =========================================================================
# A) ADDITIVE OFFSET SCANNER
# =========================================================================

def scan_offsets(cipher_nums, tokens, keytext_id, offsets):
    """Test additive offsets: shift all cipher numbers by a constant."""
    results = []
    wc = len(tokens)
    for offset in offsets:
        shifted = [cn + offset for cn in cipher_nums]
        stream = ""
        valid = 0
        for sn in shifted:
            idx = sn - 1
            if 0 <= idx < wc:
                stream += tokens[idx][0].upper()
                valid += 1
            else:
                stream += "?"
        if valid < len(cipher_nums) * 0.5:
            continue
        r = score(stream, f"offset({keytext_id}, {offset:+d})")
        results.append(r)
    return results

# =========================================================================
# B) COLUMNAR TRANSPOSITION OF CIPHER STREAM
# =========================================================================

def columnar_decipher(nums, width, serpentine=False):
    """Read numbers into a grid of given width, read out column-by-column."""
    n = len(nums)
    rows = math.ceil(n / width)
    grid = []
    for r in range(rows):
        row = nums[r * width : (r + 1) * width]
        if serpentine and r % 2 == 1:
            row = list(reversed(row))
        grid.append(row)
    reordered = []
    for c in range(width):
        for r in range(rows):
            if c < len(grid[r]):
                reordered.append(grid[r][c])
    return reordered

def scan_columnar(cipher_nums, tokens, keytext_id, widths):
    """Test columnar transposition of the cipher number sequence."""
    results = []
    wc = len(tokens)
    for w in widths:
        for serp in [False, True]:
            reordered = columnar_decipher(cipher_nums, w, serp)
            stream = ""
            for cn in reordered:
                idx = cn - 1
                if 0 <= idx < wc:
                    stream += tokens[idx][0].upper()
                else:
                    stream += "?"
            label = f"columnar({keytext_id}, w={w}{'_serp' if serp else ''})"
            results.append(score(stream, label))
    return results

# =========================================================================
# C) DIGIT-SPLIT EXTRACTION
# =========================================================================

def scan_digit_split(cipher_nums, tokens, keytext_id):
    """Digit-split: use part of the number as word index, rest as letter index."""
    results = []
    wc = len(tokens)

    # C1: word = n, letter_pos = last_digit (0->whole word first letter)
    for mode_name, letter_fn in [
        ("last_digit", lambda n: n % 10),
        ("digit_sum_mod", lambda n: sum(int(d) for d in str(n)) % 10),
        ("first_digit", lambda n: int(str(n)[0])),
    ]:
        stream = ""
        for cn in cipher_nums:
            idx = cn - 1
            if 0 <= idx < wc:
                word = tokens[idx]
                lpos = letter_fn(cn)
                if lpos == 0:
                    stream += word[0].upper()
                elif lpos < len(word):
                    stream += word[lpos].upper()
                else:
                    stream += word[lpos % len(word)].upper()
            else:
                stream += "?"
        results.append(score(stream, f"dsplit({keytext_id}, word=n, let={mode_name})"))

    # C2: word = floor(n/10), letter = n%10
    stream = ""
    for cn in cipher_nums:
        widx = cn // 10 - 1
        lpos = cn % 10
        if 0 <= widx < wc:
            word = tokens[widx]
            if lpos < len(word):
                stream += word[lpos].upper()
            else:
                stream += word[lpos % len(word)].upper() if word else "?"
        else:
            stream += "?"
    results.append(score(stream, f"dsplit({keytext_id}, word=n/10, let=n%10)"))

    # C3: word = n%1000 (for 4-digit nums), letter = n//1000
    stream = ""
    for cn in cipher_nums:
        widx = (cn % 1000) - 1
        lpos = cn // 1000
        if 0 <= widx < wc:
            word = tokens[widx]
            if lpos < len(word):
                stream += word[lpos].upper()
            else:
                stream += word[0].upper()
        else:
            stream += "?"
    results.append(score(stream, f"dsplit({keytext_id}, word=n%1000, let=n//1000)"))

    return results

# =========================================================================
# D) POSITION-DEPENDENT EXTRACTION
# =========================================================================

def scan_position_dependent(cipher_nums, tokens, keytext_id):
    """Letter extraction depends on the position of the number in the stream."""
    results = []
    wc = len(tokens)

    # D1: letter_index = (position_in_stream mod len(word))
    stream = ""
    for i, cn in enumerate(cipher_nums):
        idx = cn - 1
        if 0 <= idx < wc:
            word = tokens[idx]
            lpos = i % len(word) if word else 0
            stream += word[lpos].upper()
        else:
            stream += "?"
    results.append(score(stream, f"posdep({keytext_id}, pos_mod_wordlen)"))

    # D2: first consonant
    stream = ""
    vowels = set("AEIOUaeiou")
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < wc:
            word = tokens[idx]
            cons = [c for c in word if c.isalpha() and c not in vowels]
            stream += cons[0].upper() if cons else word[0].upper()
        else:
            stream += "?"
    results.append(score(stream, f"posdep({keytext_id}, first_consonant)"))

    # D3: last consonant
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < wc:
            word = tokens[idx]
            cons = [c for c in word if c.isalpha() and c not in vowels]
            stream += cons[-1].upper() if cons else word[-1].upper()
        else:
            stream += "?"
    results.append(score(stream, f"posdep({keytext_id}, last_consonant)"))

    # D4: alternating first/last by position
    stream = ""
    for i, cn in enumerate(cipher_nums):
        idx = cn - 1
        if 0 <= idx < wc:
            word = tokens[idx]
            if i % 2 == 0:
                stream += word[0].upper()
            else:
                stream += word[-1].upper()
        else:
            stream += "?"
    results.append(score(stream, f"posdep({keytext_id}, alt_first_last)"))

    return results

# =========================================================================
# E) MY HYPOTHESIS: PLACEMENT CIPHER
#    Numbers index into lines/sentences of a specific text layout,
#    not individual words. The Nth character of a fixed-width line layout.
# =========================================================================

def scan_placement(cipher_nums, raw_text, keytext_id):
    """
    HYPOTHESIS: Numbers don't count words — they count positions in a
    physical text layout. Test multiple line widths (30-80 chars) and
    indexing schemes: nth-character, nth-line-first-char, etc.
    """
    results = []
    chars_only = ''.join(c for c in raw_text if c.isalpha() or c == ' ')

    # E1: Direct character index into alphabetic-only text
    alpha_only = ''.join(c for c in raw_text.upper() if c.isalpha())
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(alpha_only):
            stream += alpha_only[idx]
        else:
            stream += "?"
    results.append(score(stream, f"placement({keytext_id}, char_index_alpha)"))

    # E2: Direct char index into full text (including spaces)
    full_text = raw_text.upper()
    stream = ""
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < len(full_text):
            ch = full_text[idx]
            stream += ch if ch.isalpha() else ""
        else:
            stream += "?"
    results.append(score(stream, f"placement({keytext_id}, char_index_full)"))

    # E3: Line-based: number = line_number, extract first letter of that line
    for line_width in [40, 50, 60, 70, 80]:
        lines = [chars_only[i:i+line_width] for i in range(0, len(chars_only), line_width)]
        stream = ""
        for cn in cipher_nums:
            idx = cn - 1
            if 0 <= idx < len(lines):
                line = lines[idx].strip()
                if line:
                    first_alpha = next((c for c in line if c.isalpha()), "?")
                    stream += first_alpha.upper()
                else:
                    stream += "?"
            else:
                stream += "?"
        results.append(score(stream, f"placement({keytext_id}, line{line_width}_first)"))

    # E4: Sentence indexing — number = sentence_number, extract first letter
    sentences = re.split(r'[.!?]+', raw_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if len(sentences) > 100:
        stream = ""
        for cn in cipher_nums:
            idx = cn - 1
            if 0 <= idx < len(sentences):
                s = sentences[idx]
                first_alpha = next((c for c in s if c.isalpha()), "?")
                stream += first_alpha.upper()
            else:
                stream += "?"
        results.append(score(stream, f"placement({keytext_id}, sentence_first)"))

    return results

# =========================================================================
# MAIN SWEEP
# =========================================================================

def main():
    t0 = time.time()
    cal = load_calibration()
    thresh = cal["adaptive_thresholds"]
    print(f"Adaptive thresholds: cov>={thresh['coverage_min']}, long>={thresh['long_words_min']}, qg>={thresh['quadgram_min']}")

    # Load cipher numbers
    c1 = load_cipher(1)
    c3 = load_cipher(3)
    doi_words = get_doi_words()
    doi_raw = get_doi_raw_text()

    # Select key texts for sweep: niche + top 10 from dragnet
    NICHE_IDS = [
        "webb_freemason_monitor", "anderson_constitutions",
        "preston_illustrations_masonry",
        "hening_statutes_v1", "hening_statutes_v7",
    ]
    TOP10_IDS = [
        "blackstone_bk2", "don_juan_byron", "age_of_reason_p1",
        "two_treatises_govt", "blackstone_bk4", "marshall_washington_v1",
        "marshall_washington_v5", "common_sense", "king_james_full",
        "blackstone_bk1",
    ]
    DOI_ID = "doi_words"  # special handling

    # Load key texts
    all_kt = load_all_keytexts(min_tokens=0)
    kt_by_id = {kt["id"]: kt for kt in all_kt}

    target_ids = NICHE_IDS + TOP10_IDS
    target_kts = [(kid, kt_by_id[kid]["tokens"]) for kid in target_ids if kid in kt_by_id]
    target_kts.append((DOI_ID, doi_words))  # DOI as special entry

    print(f"Key texts loaded: {len(target_kts)}")

    # ============================================
    # RUN SWEEPS FOR EACH CIPHER
    # ============================================

    for cipher_name, cipher_nums in [("c1", c1), ("c3", c3)]:
        max_cn = max(cipher_nums)
        print(f"\n{'='*70}")
        print(f"SWEEP: {cipher_name.upper()} ({len(cipher_nums)} nums, max={max_cn})")
        print(f"{'='*70}")

        all_results = []

        for kid, tokens in target_kts:
            wc = len(tokens)
            if wc < 100:
                continue

            # A) Offset scan (only for texts where DOI-sized or relevant)
            if kid == DOI_ID:
                offsets = list(range(-500, 501, 1))
                print(f"  [A] Offsets on {kid}: {len(offsets)} offsets...")
                res = scan_offsets(cipher_nums, tokens, kid, offsets)
                all_results.extend(res)
            elif wc >= max_cn:
                # Smaller offset range for non-DOI texts
                offsets = list(range(-100, 101, 5))
                res = scan_offsets(cipher_nums, tokens, kid, offsets)
                all_results.extend(res)

            # B) Columnar transposition (on DOI and niche texts)
            if kid in [DOI_ID] + NICHE_IDS and wc >= max_cn:
                widths = list(range(2, 21))
                print(f"  [B] Columnar on {kid}: {len(widths)} widths...")
                res = scan_columnar(cipher_nums, tokens, kid, widths)
                all_results.extend(res)

            # C) Digit-split extraction
            if wc >= max_cn // 10:  # word=n/10 needs at least max/10 words
                res = scan_digit_split(cipher_nums, tokens, kid)
                all_results.extend(res)

            # D) Position-dependent extraction
            if wc >= max_cn:
                res = scan_position_dependent(cipher_nums, tokens, kid)
                all_results.extend(res)

        # E) Placement hypothesis (on DOI raw text and niche texts)
        print(f"  [E] Placement hypothesis on DOI...")
        res = scan_placement(cipher_nums, doi_raw, DOI_ID)
        all_results.extend(res)

        # Also on raw niche texts
        for kid in NICHE_IDS:
            raw_path = Path(f"corpus/keytexts/raw_sources/{kid}.txt")
            if raw_path.exists():
                raw = raw_path.read_text(encoding="utf-8", errors="replace")
                if len(raw) > 5000:
                    print(f"  [E] Placement on {kid}...")
                    res = scan_placement(cipher_nums, raw[:500000], kid)
                    all_results.extend(res)

        # Mark signals
        for r in all_results:
            r["signal"] = (
                r["long"] >= thresh["long_words_min"]
                and r["cov"] >= thresh["coverage_min"]
                and r["qg"] >= thresh["quadgram_min"]
            )

        # Sort by composite score
        for r in all_results:
            r["composite"] = r["cov"] * 100 + r["long"] * 10 + max(0, r["qg"] + 7) * 5
        all_results.sort(key=lambda r: r["composite"], reverse=True)

        # Write CSV
        csv_path = OUT / f"{cipher_name}_ranked.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["rank", "label", "len", "cov", "long", "qg", "composite", "signal", "preview"])
            writer.writeheader()
            for i, r in enumerate(all_results[:500]):
                writer.writerow({"rank": i+1, **{k: r[k] for k in ["label", "len", "cov", "long", "qg", "composite", "signal", "preview"]}})

        # Print top 20
        signals = [r for r in all_results if r["signal"]]
        print(f"\n  Total candidates tested: {len(all_results)}")
        print(f"  SIGNALS: {len(signals)}")
        print(f"\n  TOP 20:")
        for i, r in enumerate(all_results[:20]):
            flag = "***" if r["signal"] else "   "
            print(f"  {flag} #{i+1:3d}  cov={r['cov']:.4f}  long={r['long']:2d}  qg={r['qg']:.3f}  {r['label'][:60]}")

        # Write top streams
        streams_dir = OUT / "top_streams"
        streams_dir.mkdir(exist_ok=True)
        for i, r in enumerate(all_results[:30]):
            with open(streams_dir / f"{cipher_name}_rank{i+1}.txt", "w") as f:
                f.write(f"Rank: {i+1}\n")
                f.write(f"Label: {r['label']}\n")
                f.write(f"Coverage: {r['cov']:.4f}\n")
                f.write(f"Long words: {r['long']}\n")
                f.write(f"Quadgram: {r['qg']:.4f}\n")
                f.write(f"Signal: {r['signal']}\n")
                f.write(f"\nDecoded stream:\n{r['preview']}\n")

    elapsed = time.time() - t0
    print(f"\nTotal sweep time: {elapsed:.1f}s")
    print(f"Outputs in {OUT}/")


if __name__ == "__main__":
    main()
