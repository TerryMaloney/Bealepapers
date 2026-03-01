"""
Control test: is trigram extraction an artifact?
If C2 trigram extraction scores similarly high, the H13 results are meaningless.
"""

import re
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from corpus.keytexts.loader import load_normalized


def get_doi_words():
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    doi = text[start:end + len("honor(1322) .")]
    return [m.group(1) for m in re.finditer(r'(\w[\w\'-]*)\(\d+\)', doi)]


def score_it(stream, label):
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    n = len(letters)
    if n < 10:
        return
    wp = score_word_patterns(letters)
    qg = quadgram_score(letters)
    print(f"  {label}: cov={wp['word_coverage']:.4f} long={wp['long_word_count']} "
          f"qg={qg:.3f} len={n} preview={letters[:80]}")
    return wp, qg


c2 = load_cipher(2)
doi = get_doi_words()

print("=== TRIGRAM ARTIFACT CONTROL TEST ===\n")

# C2 normal (first letter) — known baseline
stream = ''.join(doi[cn-1][0].upper() if 0 <= cn-1 < len(doi) else '?' for cn in c2)
print("Control baselines:")
score_it(stream, "C2 first-letter (known correct)")

# C2 trigram — control
stream = ''.join(doi[cn-1][:3].upper() if 0 <= cn-1 < len(doi) else '???' for cn in c2)
score_it(stream, "C2 trigram (same method as H13)")

# C2 bigram
stream = ''.join(doi[cn-1][:2].upper() if 0 <= cn-1 < len(doi) else '??' for cn in c2)
score_it(stream, "C2 bigram")

# Random cipher trigram against KJV Genesis
norm = load_normalized("king_james_genesis")
if norm:
    tokens = norm["tokens"]
    tc = len(tokens)
    print(f"\nRandom cipher trigram against KJV Genesis ({tc} tokens):")
    rng = random.Random(42)
    for trial in range(3):
        fake_nums = [rng.randint(1, min(tc, 975)) for _ in range(520)]
        stream = ''.join(tokens[cn-1][:3].upper() if 0 <= cn-1 < tc else '???' for cn in fake_nums)
        score_it(stream, f"Random trial {trial+1} trigram KJV")

# Random against DOI trigram
print(f"\nRandom cipher trigram against DOI ({len(doi)} tokens):")
for trial in range(3):
    fake_nums = [rng.randint(1, len(doi)) for _ in range(520)]
    stream = ''.join(doi[cn-1][:3].upper() if 0 <= cn-1 < len(doi) else '???' for cn in fake_nums)
    score_it(stream, f"Random trial {trial+1} trigram DOI")

print("\nVERDICT: If random trigram scores are similarly high, H13 is an artifact of method, not a signal.")
