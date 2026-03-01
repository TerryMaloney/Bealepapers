"""
Full unconstrained Cipher 1 scan over ALL extractors x ALL transpositions.

Scores each strategy with a composite Englishness heuristic:
  - Index of Coincidence (IC) — penalized if > 0.080 or < 0.050
  - Bigram hit rate (top-30 English bigrams)
  - Vowel ratio deviation from 0.38
  - Chi-squared letter frequency distance (inverted)

Also reports which strategies pass Cipher 2 constraints (i.e., would
survive the constrained search) vs which are unconstrained-only.

Output: output/phase89/cipher1_full_scan.txt
"""

import sys
import time
from collections import Counter
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus.canonical import CanonicalCorpus
from constraints.overlap_engine import CrossCipherConstraints, load_cipher
from extractors import ALL_EXTRACTORS
from transposition import ALL_TRANSPOSITIONS
from scoring.word_pattern_scorer import score_word_patterns


ENGLISH_BIGRAMS_TOP = set([
    'TH', 'HE', 'IN', 'ER', 'AN', 'RE', 'ON', 'AT', 'EN', 'ND',
    'TI', 'ES', 'OR', 'TE', 'OF', 'ED', 'IS', 'IT', 'AL', 'AR',
    'ST', 'TO', 'NT', 'NG', 'SE', 'HA', 'AS', 'OU', 'IO', 'LE',
])

ENGLISH_LETTER_FREQ = {
    'E': 12.70, 'T': 9.06, 'A': 8.17, 'O': 7.51, 'I': 6.97,
    'N': 6.75, 'S': 6.33, 'H': 6.09, 'R': 5.99, 'D': 4.25,
    'L': 4.03, 'C': 2.78, 'U': 2.76, 'M': 2.41, 'W': 2.36,
    'F': 2.23, 'G': 2.02, 'Y': 1.97, 'P': 1.93, 'B': 1.29,
    'V': 0.98, 'K': 0.77, 'J': 0.15, 'X': 0.15, 'Q': 0.10,
    'Z': 0.07,
}

ANCHOR_WORDS = [
    'THE', 'AND', 'FOR', 'WAS', 'NOT', 'WITH', 'THIS', 'THAT',
    'HAVE', 'FROM', 'THEY', 'BEEN', 'SAID', 'EACH', 'WHICH',
    'THEIR', 'WILL', 'OTHER', 'ABOUT', 'MANY',
    'BEDFORD', 'VIRGINIA', 'COUNTY', 'TREASURE', 'VAULT',
    'DEPOSITED', 'GOLD', 'SILVER', 'IRON',
]


def englishness_score(stream: str) -> dict:
    """Compute composite Englishness heuristic. Higher = more English."""
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    n = len(letters)
    if n < 20:
        return {'total': 0.0, 'ic': 0.0, 'bigram': 0.0, 'vowel': 0.0, 'chi2_inv': 0.0}

    counts = Counter(letters)

    # IC
    ic = sum(c * (c - 1) for c in counts.values()) / (n * (n - 1)) if n > 1 else 0
    # Score: penalize if too far from 0.065 (English)
    ic_score = max(0, 1.0 - abs(ic - 0.065) / 0.030) * 25  # max 25

    # Bigram
    bigrams = sum(1 for i in range(n - 1) if letters[i:i+2] in ENGLISH_BIGRAMS_TOP)
    bigram_pct = bigrams / (n - 1) if n > 1 else 0
    bigram_score = min(bigram_pct / 0.25, 1.0) * 35  # max 35, English ~0.25

    # Vowel ratio
    vowels = sum(1 for c in letters if c in 'AEIOU')
    vr = vowels / n
    vowel_score = max(0, 1.0 - abs(vr - 0.38) / 0.15) * 15  # max 15

    # Chi-squared (inverted: lower chi2 = higher score)
    chi2 = 0.0
    for letter, expected_pct in ENGLISH_LETTER_FREQ.items():
        observed = counts.get(letter, 0)
        expected = expected_pct / 100.0 * n
        if expected > 0:
            chi2 += (observed - expected) ** 2 / expected
    chi2_score = max(0, (300 - chi2) / 300) * 25  # max 25

    total = ic_score + bigram_score + chi2_score + vowel_score
    return {
        'total': total,
        'ic': ic,
        'ic_score': ic_score,
        'bigram_pct': bigram_pct,
        'bigram_score': bigram_score,
        'vowel_ratio': vr,
        'vowel_score': vowel_score,
        'chi2': chi2,
        'chi2_score': chi2_score,
    }


def enhanced_englishness_score(stream: str) -> dict:
    """
    Enhanced Englishness score that includes word-pattern detection.
    This discriminates genuine English from DOI extraction artifacts.
    
    Components (out of 100):
      - IC proximity to 0.065:    15 pts
      - Bigram hit rate:          20 pts
      - Vowel ratio:              10 pts
      - Chi-squared (inverted):   15 pts
      - Word coverage:            30 pts  (NEW — the key discriminator)
      - Long word count (6+):     10 pts  (NEW)
    """
    base = englishness_score(stream)
    wp = score_word_patterns(stream)
    
    # Rescale base components to fit new budget (60 pts instead of 100)
    base_rescaled = base['total'] * 0.60
    
    # Word coverage: 30 pts (0.30 coverage = full marks)
    word_cov_score = min(wp['word_coverage'] / 0.30, 1.0) * 30
    
    # Long word bonus: 10 pts (5 long words = full marks)
    long_word_score = min(wp['long_word_count'] / 5, 1.0) * 10
    
    total = base_rescaled + word_cov_score + long_word_score
    
    result = dict(base)
    result['total'] = total
    result['word_coverage'] = wp['word_coverage']
    result['long_word_count'] = wp['long_word_count']
    result['word_cov_score'] = word_cov_score
    result['long_word_score'] = long_word_score
    return result


def find_anchor_words(stream: str, min_len: int = 3) -> list:
    """Find common English words in stream (no spaces, so look for substrings)."""
    up = stream.upper()
    found = []
    for word in ANCHOR_WORDS:
        if len(word) >= min_len:
            idx = up.find(word)
            if idx >= 0:
                found.append((word, idx))
    return found


def main():
    output_dir = Path("output/phase89")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load corpus
    corpus = CanonicalCorpus.load('corpus/CANON_DOI.json')
    cipher1 = load_cipher(1)
    print(f"Corpus: {corpus}")
    print(f"Cipher 1: {len(cipher1)} numbers")
    print(f"Extractors: {len(ALL_EXTRACTORS)}")
    print(f"Transpositions: {len(ALL_TRANSPOSITIONS)}")
    total = len(ALL_EXTRACTORS) * len(ALL_TRANSPOSITIONS)
    print(f"Total combinations: {total}")

    # Also set up constraints for comparison
    constraints = CrossCipherConstraints(corpus)
    oracle_constraints = constraints.derive_cipher2_oracle_constraints()
    print(f"Oracle constraints: {len(oracle_constraints)}")

    # Run full scan
    print(f"\nScanning...")
    t0 = time.time()
    results = []

    for ei, extractor in enumerate(ALL_EXTRACTORS):
        # Pre-decode (same for all transpositions)
        c1_decoded = corpus.decode_with_extractor(cipher1, extractor)

        # Check constraint pass/fail for this extractor (transposition-independent)
        passes_constraint, violation_rate = constraints.validate_strategy(
            extractor, ALL_TRANSPOSITIONS[0], oracle_constraints
        )

        for transposition in ALL_TRANSPOSITIONS:
            c1_stream = transposition.apply(c1_decoded)
            scores = enhanced_englishness_score(c1_stream)
            anchors = find_anchor_words(c1_stream, min_len=4)

            results.append({
                'extractor': extractor.name,
                'transposition': transposition.name,
                'total_score': scores['total'],
                'ic': scores['ic'],
                'bigram_pct': scores.get('bigram_pct', 0),
                'vowel_ratio': scores.get('vowel_ratio', 0),
                'chi2': scores.get('chi2', 999),
                'word_coverage': scores.get('word_coverage', 0),
                'long_word_count': scores.get('long_word_count', 0),
                'anchor_count': len(anchors),
                'anchors': [a[0] for a in anchors],
                'passes_c2_constraint': passes_constraint,
                'violation_rate': violation_rate,
                'sample': c1_stream[:150],
            })

        if (ei + 1) % 10 == 0:
            elapsed = time.time() - t0
            print(f"  {ei+1}/{len(ALL_EXTRACTORS)} extractors done ({elapsed:.1f}s)")

    elapsed = time.time() - t0
    print(f"\nScan complete: {len(results)} strategies in {elapsed:.1f}s")

    # Sort by Englishness score
    results.sort(key=lambda r: r['total_score'], reverse=True)

    # Write report
    report_path = output_dir / "cipher1_full_scan.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CIPHER 1 FULL SCAN — ALL EXTRACTORS x ALL TRANSPOSITIONS\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total combinations: {len(results)}\n")
        f.write(f"Corpus: {corpus}\n")
        f.write("=" * 80 + "\n\n")

        # Constraint summary
        n_pass = sum(1 for r in results if r['passes_c2_constraint'])
        n_fail = len(results) - n_pass
        f.write(f"Cipher 2 constraint pass/fail: {n_pass} pass / {n_fail} filtered\n")
        f.write(f"  (Passing = same extraction produces same letter for overlapping cipher numbers)\n\n")

        # Top 30 overall
        f.write("--- TOP 30 BY ENHANCED ENGLISHNESS (includes word-pattern detection) ---\n\n")
        for i, r in enumerate(results[:30]):
            marker = "C2-OK" if r['passes_c2_constraint'] else "C2-X "
            f.write(f"{i+1:3d}. [{marker}] {r['extractor']:30s} + {r['transposition']:25s}\n")
            f.write(f"     score={r['total_score']:5.1f}  IC={r['ic']:.4f}  "
                   f"bigram={r['bigram_pct']:.3f}  words={r['word_coverage']:.3f}  "
                   f"long_words={r['long_word_count']}  anchors={r['anchors']}\n")
            f.write(f"     {r['sample'][:120]}\n\n")

        # Top 20 that PASS constraints
        passing = [r for r in results if r['passes_c2_constraint']]
        f.write("\n--- TOP 20 BY ENHANCED ENGLISHNESS (Cipher 2 CONSTRAINED) ---\n\n")
        for i, r in enumerate(passing[:20]):
            f.write(f"{i+1:3d}. {r['extractor']:30s} + {r['transposition']:25s}\n")
            f.write(f"     score={r['total_score']:5.1f}  IC={r['ic']:.4f}  "
                   f"bigram={r['bigram_pct']:.3f}  words={r['word_coverage']:.3f}  "
                   f"long_words={r['long_word_count']}  anchors={r['anchors']}\n")
            f.write(f"     {r['sample'][:120]}\n\n")

        # Score distribution
        f.write("\n--- SCORE DISTRIBUTION ---\n")
        thresholds = [60, 50, 40, 30, 20, 10]
        for t in thresholds:
            count = sum(1 for r in results if r['total_score'] >= t)
            count_c = sum(1 for r in results if r['total_score'] >= t and r['passes_c2_constraint'])
            f.write(f"  score >= {t}: {count} total, {count_c} constrained\n")

        # Anchor analysis
        f.write("\n--- ANCHOR WORD HITS ---\n")
        anchor_results = [r for r in results if r['anchor_count'] > 0]
        anchor_results.sort(key=lambda r: r['anchor_count'], reverse=True)
        if anchor_results:
            for r in anchor_results[:20]:
                marker = "C2-OK" if r['passes_c2_constraint'] else "C2-X "
                f.write(f"  [{marker}] {r['extractor']:30s} + {r['transposition']:25s}: "
                       f"{r['anchors']}\n")
        else:
            f.write("  No anchor words found in any strategy.\n")

        # Best IC (closest to English 0.065)
        f.write("\n--- BEST IC (closest to 0.065) ---\n")
        by_ic = sorted(results, key=lambda r: abs(r['ic'] - 0.065))
        for r in by_ic[:10]:
            marker = "C2-OK" if r['passes_c2_constraint'] else "C2-X "
            f.write(f"  [{marker}] IC={r['ic']:.4f}  {r['extractor']:30s} + {r['transposition']:25s}  "
                   f"bigram={r['bigram_pct']:.3f}\n")

        # Diagnosis
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("DIAGNOSIS\n")
        f.write("=" * 80 + "\n\n")

        best = results[0]
        best_constrained = passing[0] if passing else None

        f.write(f"Best overall:    score={best['total_score']:.1f} ({best['extractor']} + {best['transposition']})\n")
        if best_constrained:
            f.write(f"Best constrained: score={best_constrained['total_score']:.1f} "
                   f"({best_constrained['extractor']} + {best_constrained['transposition']})\n")

        if best['total_score'] < 40:
            f.write("\nVERDICT: No strategy produces strong English signal on Cipher 1 using DOI.\n")
            f.write("The DOI is likely NOT the key text for Cipher 1.\n")
            f.write("NEXT: Key-text discovery or alternate-document exploration.\n")
        elif best['total_score'] >= 40 and best['total_score'] < 60:
            f.write("\nVERDICT: Weak English signal detected. Possible partial decryption.\n")
            f.write("NEXT: Expand search around top strategy family (Branch A).\n")
        else:
            f.write("\nVERDICT: Strong English signal detected!\n")
            f.write("NEXT: Validate top strategy, expand locally (Branch A).\n")

    print(f"Report: {report_path}")
    print(f"\nQuick summary:")
    print(f"  Best overall:     score={results[0]['total_score']:.1f} "
          f"({results[0]['extractor']} + {results[0]['transposition']})")
    if passing:
        print(f"  Best constrained: score={passing[0]['total_score']:.1f} "
              f"({passing[0]['extractor']} + {passing[0]['transposition']})")
    print(f"  Strategies with anchors: {sum(1 for r in results if r['anchor_count'] > 0)}")


if __name__ == "__main__":
    main()
