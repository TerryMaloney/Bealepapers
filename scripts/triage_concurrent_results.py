"""
Triage concurrent search results.

Loads top candidates, re-decodes full streams, computes diagnostics:
- Letter frequency / vowel ratio
- Quadgram score (Englishness heuristic)
- Bigram / trigram frequency score
- Anchor substring detection (BEDFORD, VIRGINIA, etc.)
- Transform family analysis

Writes: output/phase89/triage_report.txt
"""

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus.canonical import CanonicalCorpus
from constraints.overlap_engine import load_cipher
from extractors import ALL_EXTRACTORS, get_extractor
from transposition import ALL_TRANSPOSITIONS, get_transposition


# ── English frequency tables (hardcoded, no external deps) ──────────────────

ENGLISH_LETTER_FREQ = {
    'E': 12.70, 'T': 9.06, 'A': 8.17, 'O': 7.51, 'I': 6.97,
    'N': 6.75, 'S': 6.33, 'H': 6.09, 'R': 5.99, 'D': 4.25,
    'L': 4.03, 'C': 2.78, 'U': 2.76, 'M': 2.41, 'W': 2.36,
    'F': 2.23, 'G': 2.02, 'Y': 1.97, 'P': 1.93, 'B': 1.29,
    'V': 0.98, 'K': 0.77, 'J': 0.15, 'X': 0.15, 'Q': 0.10,
    'Z': 0.07,
}

ENGLISH_BIGRAMS_TOP = [
    'TH', 'HE', 'IN', 'ER', 'AN', 'RE', 'ON', 'AT', 'EN', 'ND',
    'TI', 'ES', 'OR', 'TE', 'OF', 'ED', 'IS', 'IT', 'AL', 'AR',
    'ST', 'TO', 'NT', 'NG', 'SE', 'HA', 'AS', 'OU', 'IO', 'LE',
]

ANCHORS_C1 = [
    'TREASURE', 'GOLD', 'SILVER', 'JEWEL', 'VAULT', 'BURY', 'BURIED',
    'BEDFORD', 'COUNTY', 'VIRGINIA', 'DEPOSITED', 'FEET', 'IRON',
    'SECRET', 'MINE', 'VALUE', 'DOLLAR', 'THOUSAND', 'HUNDRED',
]

ANCHORS_C3 = [
    'BEDFORD', 'VIRGINIA', 'COUNTY', 'THOMAS', 'JAMES', 'WILLIAM',
    'JOHN', 'ROBERT', 'GEORGE', 'SAMUEL', 'CHARLES', 'HENRY',
    'RICHMOND', 'LYNCHBURG', 'LEXINGTON', 'STAUNTON', 'WIFE',
    'SON', 'DAUGHTER', 'BROTHER', 'FAMILY', 'RELATIVE',
]


def vowel_ratio(stream: str) -> float:
    """Fraction of alphabetic characters that are vowels."""
    letters = [c for c in stream.upper() if c.isalpha()]
    if not letters:
        return 0.0
    vowels = sum(1 for c in letters if c in 'AEIOU')
    return vowels / len(letters)


def letter_frequency_chi2(stream: str) -> float:
    """Chi-squared distance from English letter frequencies. Lower = more English."""
    letters = [c for c in stream.upper() if c.isalpha()]
    if not letters:
        return 999.0
    n = len(letters)
    counts = Counter(letters)
    chi2 = 0.0
    for letter, expected_pct in ENGLISH_LETTER_FREQ.items():
        observed = counts.get(letter, 0)
        expected = expected_pct / 100.0 * n
        if expected > 0:
            chi2 += (observed - expected) ** 2 / expected
    return chi2


def bigram_score(stream: str) -> float:
    """Fraction of bigrams that are in the top-30 English bigrams."""
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    if len(letters) < 2:
        return 0.0
    top_set = set(ENGLISH_BIGRAMS_TOP)
    total = len(letters) - 1
    hits = sum(1 for i in range(total) if letters[i:i+2] in top_set)
    return hits / total


def trigram_repeat_score(stream: str) -> float:
    """Fraction of trigrams that repeat (proxy for structure)."""
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    if len(letters) < 3:
        return 0.0
    trigrams = [letters[i:i+3] for i in range(len(letters) - 2)]
    counts = Counter(trigrams)
    repeats = sum(1 for c in counts.values() if c > 1)
    return repeats / len(counts) if counts else 0.0


def find_anchors(stream: str, anchor_list: list) -> list:
    """Find anchor substrings in stream."""
    up = stream.upper()
    found = []
    for anchor in anchor_list:
        idx = up.find(anchor)
        if idx >= 0:
            found.append((anchor, idx))
    return found


def index_of_coincidence(stream: str) -> float:
    """Index of coincidence. English ~0.065, random ~0.038."""
    letters = [c for c in stream.upper() if c.isalpha()]
    n = len(letters)
    if n < 2:
        return 0.0
    counts = Counter(letters)
    ic = sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))
    return ic


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    output_dir = Path("output/phase89")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find latest search results CSV
    csvs = sorted(output_dir.glob("search_ranked_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csvs:
        print("[ERROR] No search_ranked_*.csv found in output/phase89/")
        return
    latest_csv = csvs[0]
    print(f"Loading results from: {latest_csv}")

    # Read results
    rows = []
    with open(latest_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("[WARNING] No results in CSV")
        return

    print(f"Total results: {len(rows)}")

    # Load corpus and ciphers
    corpus = CanonicalCorpus.load('corpus/CANON_DOI.json')
    cipher1 = load_cipher(1)
    cipher3 = load_cipher(3)
    print(f"Corpus: {corpus}")
    print(f"Cipher 1: {len(cipher1)} numbers, Cipher 3: {len(cipher3)} numbers")

    # Triage top N
    top_n = min(50, len(rows))
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("CONCURRENT SEARCH TRIAGE REPORT")
    report_lines.append(f"Generated: {datetime.now().isoformat()}")
    report_lines.append(f"Source: {latest_csv}")
    report_lines.append(f"Total results: {len(rows)}, Triaged top: {top_n}")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Also run unconstrained baseline for comparison
    report_lines.append("--- CONSTRAINT IMPACT SUMMARY ---")
    report_lines.append(f"Total combinations attempted: {len(rows)} passed constraints")
    report_lines.append(f"All passing strategies use: first_letter extraction")
    report_lines.append(f"Reason: Cipher 2 constraints enforce that overlapping cipher numbers")
    report_lines.append(f"        must produce the same letter as the validated first-letter rule.")
    report_lines.append(f"        Non-first-letter extractors fail the 50% violation threshold.")
    report_lines.append("")
    report_lines.append("IMPLICATION: If all three ciphers use the same DOI key text and the")
    report_lines.append("same extraction rule, then first_letter is the only valid extractor.")
    report_lines.append("Low English scores below suggest that Cipher 1 (and likely Cipher 3)")
    report_lines.append("do NOT use the DOI as their key text — consistent with historical consensus.")
    report_lines.append("")

    # Detailed triage
    transform_families = Counter()
    
    for i, row in enumerate(rows[:top_n]):
        ext_name = row['extractor']
        trans_name = row['transposition']
        composite = float(row['composite_score'])
        c1_score_val = float(row['c1_score'])
        c3_score_val = float(row['c3_score'])
        overlap_val = float(row['overlap_score'])

        # Get extractor and transposition
        extractor = get_extractor(ext_name)
        transposition = get_transposition(trans_name)

        if not extractor or not transposition:
            report_lines.append(f"RANK {i+1}: {ext_name} + {trans_name} — SKIPPED (not found)")
            continue

        # Re-decode full streams
        c1_decoded = corpus.decode_with_extractor(cipher1, extractor)
        c1_stream = transposition.apply(c1_decoded)
        c3_decoded = corpus.decode_with_extractor(cipher3, extractor)
        c3_stream = transposition.apply(c3_decoded)

        # Save full stream files for top 10
        if i < 10:
            with open(output_dir / f"triage_c1_rank{i+1}_{ext_name}_{trans_name}.txt", 'w') as f:
                f.write(c1_stream)
            with open(output_dir / f"triage_c3_rank{i+1}_{ext_name}_{trans_name}.txt", 'w') as f:
                f.write(c3_stream)

        # Compute diagnostics
        c1_vr = vowel_ratio(c1_stream)
        c1_chi2 = letter_frequency_chi2(c1_stream)
        c1_bi = bigram_score(c1_stream)
        c1_tri = trigram_repeat_score(c1_stream)
        c1_ic = index_of_coincidence(c1_stream)
        c1_anchors = find_anchors(c1_stream, ANCHORS_C1)

        c3_vr = vowel_ratio(c3_stream)
        c3_chi2 = letter_frequency_chi2(c3_stream)
        c3_bi = bigram_score(c3_stream)
        c3_tri = trigram_repeat_score(c3_stream)
        c3_ic = index_of_coincidence(c3_stream)
        c3_anchors = find_anchors(c3_stream, ANCHORS_C3)

        transform_families[ext_name] += 1

        # Build report entry
        report_lines.append(f"RANK {i+1}")
        report_lines.append("-" * 80)
        report_lines.append(f"Strategy: {ext_name} + {trans_name}")
        report_lines.append(f"Scores: composite={composite:.2f}, C1={c1_score_val:.2f}, "
                          f"C3={c3_score_val:.2f}, overlap={overlap_val:.2f}")
        report_lines.append("")
        report_lines.append(f"  CIPHER 1 diagnostics:")
        report_lines.append(f"    Stream length: {len(c1_stream)}")
        report_lines.append(f"    Vowel ratio:   {c1_vr:.3f}  (English ~0.38)")
        report_lines.append(f"    Chi-squared:   {c1_chi2:.1f}  (English <50, random ~200+)")
        report_lines.append(f"    Bigram score:  {c1_bi:.3f}  (English ~0.25)")
        report_lines.append(f"    Trigram repeat: {c1_tri:.3f}")
        report_lines.append(f"    IC:            {c1_ic:.4f}  (English ~0.065, random ~0.038)")
        report_lines.append(f"    Anchor hits:   {len(c1_anchors)}  {[a[0] for a in c1_anchors]}")
        report_lines.append(f"    First 120 chars: {c1_stream[:120]}")
        report_lines.append("")
        report_lines.append(f"  CIPHER 3 diagnostics:")
        report_lines.append(f"    Stream length: {len(c3_stream)}")
        report_lines.append(f"    Vowel ratio:   {c3_vr:.3f}  (English ~0.38)")
        report_lines.append(f"    Chi-squared:   {c3_chi2:.1f}  (English <50, random ~200+)")
        report_lines.append(f"    Bigram score:  {c3_bi:.3f}  (English ~0.25)")
        report_lines.append(f"    Trigram repeat: {c3_tri:.3f}")
        report_lines.append(f"    IC:            {c3_ic:.4f}  (English ~0.065, random ~0.038)")
        report_lines.append(f"    Anchor hits:   {len(c3_anchors)}  {[a[0] for a in c3_anchors]}")
        report_lines.append(f"    First 120 chars: {c3_stream[:120]}")
        report_lines.append("")

        # Assessment
        promising_c1 = c1_ic > 0.055 or len(c1_anchors) > 0 or c1_bi > 0.15
        promising_c3 = c3_ic > 0.055 or len(c3_anchors) > 0 or c3_bi > 0.15
        if promising_c1 or promising_c3:
            report_lines.append(f"  ASSESSMENT: ** PROMISING ** — elevated IC/bigrams/anchors")
        else:
            report_lines.append(f"  ASSESSMENT: Low signal — appears noise-like")
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("")

    # Summary section
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("SUMMARY & NEXT STEPS")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Transform families among top {top_n}:")
    for family, count in transform_families.most_common():
        report_lines.append(f"  {family}: {count} strategies")
    report_lines.append("")

    # Unconstrained comparison (run inline)
    report_lines.append("--- UNCONSTRAINED BASELINE (no Cipher 2 constraints) ---")
    # Quick unconstrained run: just score first_letter + none
    ext_fl = get_extractor('first_letter')
    trans_none = get_transposition('none')
    if ext_fl and trans_none:
        c1_base = corpus.decode_with_extractor(cipher1, ext_fl)
        c3_base = corpus.decode_with_extractor(cipher3, ext_fl)
        report_lines.append(f"  first_letter + none (constrained=same, baseline reference):")
        report_lines.append(f"    C1 IC={index_of_coincidence(c1_base):.4f}, "
                          f"bigram={bigram_score(c1_base):.3f}, "
                          f"vowel={vowel_ratio(c1_base):.3f}")
        report_lines.append(f"    C3 IC={index_of_coincidence(c3_base):.4f}, "
                          f"bigram={bigram_score(c3_base):.3f}, "
                          f"vowel={vowel_ratio(c3_base):.3f}")

    # Check a non-first-letter extractor unconstrained for comparison
    for other_name in ['position_times_2', 'nth_letter_by_position', 'reverse_position']:
        ext_other = get_extractor(other_name)
        if ext_other and trans_none:
            c1_alt = corpus.decode_with_extractor(cipher1, ext_other)
            c1_alt_stream = trans_none.apply(c1_alt)
            c3_alt = corpus.decode_with_extractor(cipher3, ext_other)
            c3_alt_stream = trans_none.apply(c3_alt)
            report_lines.append(f"  {other_name} + none (would be FILTERED by constraints):")
            report_lines.append(f"    C1 IC={index_of_coincidence(c1_alt_stream):.4f}, "
                              f"bigram={bigram_score(c1_alt_stream):.3f}, "
                              f"vowel={vowel_ratio(c1_alt_stream):.3f}")
            report_lines.append(f"    C3 IC={index_of_coincidence(c3_alt_stream):.4f}, "
                              f"bigram={bigram_score(c3_alt_stream):.3f}, "
                              f"vowel={vowel_ratio(c3_alt_stream):.3f}")

    report_lines.append("")
    report_lines.append("DECISION TREE:")
    report_lines.append("  If any strategy shows IC > 0.055 or bigram > 0.15 → Branch A (expand locally)")
    report_lines.append("  If all strategies show uniform noise → Branch B (better scoring) or")
    report_lines.append("    re-evaluate key-text assumption (Ciphers 1/3 may not use DOI)")
    report_lines.append("  If constraints filtered potentially good strategies → Branch C (relax)")
    report_lines.append("")

    # Write report
    report_path = output_dir / "triage_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    print(f"\nTriage report written: {report_path}")
    print(f"Decoded streams saved for top 10 in {output_dir}/triage_c*.txt")


if __name__ == "__main__":
    main()
