"""
Calibration check: verify that scoring pipeline still correctly identifies
Cipher 2 as English and random text as noise.

Outputs: output/dragnet_v1/calibration_check.txt
"""

import sys
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score


def calibrate(out_dir="output/dragnet_v1"):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Load DOI words for C2 decode
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    import re
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    doi = text[start:end + len("honor(1322) .")]
    words = [m.group(1) for m in re.finditer(r'(\w[\w\'-]*)\(\d+\)', doi)]

    # Load C2 numbers
    from constraints.overlap_engine import load_cipher
    c2 = load_cipher(2)

    # Decode C2 with DOI
    c2_stream = ""
    for cn in c2:
        idx = cn - 1
        if 0 <= idx < len(words):
            c2_stream += words[idx][0].upper()
        else:
            c2_stream += "?"
    c2_letters = ''.join(c for c in c2_stream if c.isalpha())

    # Score C2
    c2_wp = score_word_patterns(c2_letters)
    c2_qg = quadgram_score(c2_letters)

    # Random baseline
    random.seed(42)
    rand_stream = ''.join(random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(520))
    rand_wp = score_word_patterns(rand_stream)
    rand_qg = quadgram_score(rand_stream)

    # Known English
    eng = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG" * 15
    eng_wp = score_word_patterns(eng)
    eng_qg = quadgram_score(eng)

    report = f"""{'='*70}
SCORING CALIBRATION CHECK
Generated: {datetime.now().isoformat()}
Command: python scripts/calibrate_scoring.py
{'='*70}

1. CIPHER 2 (known correct — DOI first-letter decode):
   Length:          {len(c2_letters)} chars
   Word coverage:   {c2_wp['word_coverage']:.4f}
   Long words (6+): {c2_wp['long_word_count']}
   Quadgram score:  {c2_qg:.4f}
   VERDICT:         {'PASS' if c2_wp['long_word_count'] >= 3 and c2_wp['word_coverage'] >= 0.10 else 'FAIL'}

2. RANDOM BASELINE (uniform A-Z, 520 chars):
   Length:          {len(rand_stream)} chars
   Word coverage:   {rand_wp['word_coverage']:.4f}
   Long words (6+): {rand_wp['long_word_count']}
   Quadgram score:  {rand_qg:.4f}
   VERDICT:         {'PASS (correctly low)' if rand_wp['long_word_count'] == 0 and rand_wp['word_coverage'] < 0.05 else 'FAIL (too high)'}

3. KNOWN ENGLISH (repeated pangram):
   Length:          {len(eng)} chars
   Word coverage:   {eng_wp['word_coverage']:.4f}
   Long words (6+): {eng_wp['long_word_count']}
   Quadgram score:  {eng_qg:.4f}

SEPARATION:
  C2 quadgram vs random: {c2_qg - rand_qg:+.3f} (should be >> 0)
  C2 coverage vs random: {c2_wp['word_coverage'] - rand_wp['word_coverage']:+.4f} (should be >> 0)

CALIBRATION STATUS: {'ALL CHECKS PASS' if (c2_wp['long_word_count'] >= 3 and rand_wp['long_word_count'] == 0 and c2_qg > rand_qg + 1.0) else 'CALIBRATION ISSUE — INVESTIGATE'}
"""

    cal_path = out_path / "calibration_check.txt"
    with open(cal_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"Saved: {cal_path}")
    return c2_wp, rand_wp


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "output/dragnet_v1"
    calibrate(out)
