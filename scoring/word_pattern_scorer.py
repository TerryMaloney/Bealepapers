"""
Word-pattern scorer: detects recognizable English words in spaceless decoded streams.

This discriminator solves the "DOI extraction artifact" problem where extracting
letters from English-word positions produces English-like n-gram statistics without
actually being English.

Scoring:
  - Slide a window across the stream looking for common English words (3-12 chars)
  - Weight longer matches exponentially (to suppress 3-char false positives)
  - Return: word_coverage (fraction of stream covered by word hits)
  - Bonus: count of 6+ letter word hits (strong signal)
"""

# Top ~200 English words by frequency + Beale-domain words
# Restricted to 4+ chars to reduce false positives
COMMON_WORDS = set([
    # Top frequency (4+ chars)
    'THAT', 'WITH', 'HAVE', 'THIS', 'WILL', 'YOUR', 'FROM', 'THEY',
    'BEEN', 'SAID', 'EACH', 'MAKE', 'LIKE', 'LONG', 'LOOK', 'MANY',
    'SOME', 'TIME', 'VERY', 'WHEN', 'COME', 'MADE', 'FIND', 'HERE',
    'KNOW', 'TAKE', 'PEOPLE', 'INTO', 'YEAR', 'THEM', 'THAN', 'THEN',
    'THINK', 'ALSO', 'BACK', 'AFTER', 'ONLY', 'GIVE', 'MOST', 'JUST',
    'OVER', 'SUCH', 'GOOD', 'EVEN', 'MORE', 'MUCH', 'WHAT', 'WELL',
    'DOWN', 'SHOULD', 'THERE', 'THEIR', 'ABOUT', 'COULD', 'WOULD',
    'THESE', 'OTHER', 'FIRST', 'WHICH', 'WHERE', 'THOSE', 'UNDER',
    'WHILE', 'STILL', 'EVERY', 'GREAT', 'NEVER', 'PLACE', 'BEING',
    'SHALL', 'THROUGH', 'BETWEEN', 'BEFORE', 'BECAUSE',
    'FOUND', 'GIVEN', 'ABOVE', 'BELOW', 'AMONG', 'THREE', 'SINCE',
    'STATE', 'WORLD', 'HOUSE', 'AGAIN', 'NIGHT', 'POINT', 'RIGHT',
    'SMALL', 'UNTIL', 'WHOLE', 'MIGHT', 'ALONG', 'NEVER', 'BEGAN',
    'HANDS', 'MONEY', 'PAPER', 'PLAIN', 'ROUND', 'PARTY',
    # Longer common words (strong signal)
    'HUNDRED', 'THOUSAND', 'NOTHING', 'WITHOUT', 'ANOTHER', 'HOWEVER',
    'HIMSELF', 'HERSELF', 'ALREADY', 'GENERAL', 'COUNTRY', 'TOGETHER',
    'AGAINST', 'SEVERAL', 'BELIEVE', 'CERTAIN', 'PERHAPS', 'WHETHER',
    'DURING', 'NUMBER', 'LETTER', 'WITHIN', 'HAVING', 'CALLED',
    'CANNOT', 'LITTLE', 'RETURN', 'FRIEND', 'ENOUGH', 'ALMOST',
    'AROUND', 'FAMILY', 'FOLLOWING', 'CONTAINED', 'RECEIVED',
    # Beale-domain words
    'BEDFORD', 'VIRGINIA', 'COUNTY', 'TREASURE', 'VAULT', 'DEPOSITED',
    'GOLD', 'SILVER', 'IRON', 'JEWEL', 'BURIED', 'BURY', 'CACHE',
    'SECRET', 'MINE', 'VALUE', 'DOLLAR', 'MILES', 'FEET', 'GROUND',
    'SURFACE', 'PAPER', 'CIPHER', 'NUMBER', 'LETTER',
    'LYNCHBURG', 'LEXINGTON', 'STAUNTON', 'RICHMOND',
    'THOMAS', 'JAMES', 'WILLIAM', 'JOHN', 'ROBERT', 'GEORGE',
    'SAMUEL', 'CHARLES', 'HENRY', 'WIFE', 'RELATIVE',
    'DECLARATION', 'INDEPENDENCE',
])

# Also include 3-letter words but with much lower weight
SHORT_WORDS = set([
    'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'ANY',
    'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'HIS', 'HAS', 'HAD',
    'HOW', 'MAN', 'NEW', 'NOW', 'OLD', 'SEE', 'WAY', 'MAY', 'DAY',
    'TOO', 'USE', 'SAY', 'SHE', 'TWO', 'GET', 'DID', 'LET', 'PUT',
])


def score_word_patterns(stream: str, return_hits: bool = False) -> dict:
    """
    Score stream by how much of it is covered by recognizable English words.

    Returns dict with:
      word_coverage: float 0-1, fraction of chars covered by word hits
      long_word_count: int, number of 6+ letter word hits
      word_hits: list of (word, position) if return_hits=True
    """
    up = stream.upper()
    n = len(up)
    if n == 0:
        return {'word_coverage': 0.0, 'long_word_count': 0, 'word_hits': []}

    covered = [False] * n
    hits = []

    # Check long words first (4+ chars), then short words
    for word in COMMON_WORDS:
        wlen = len(word)
        start = 0
        while True:
            idx = up.find(word, start)
            if idx < 0:
                break
            hits.append((word, idx))
            for j in range(idx, min(idx + wlen, n)):
                covered[j] = True
            start = idx + 1

    # Short words (3 chars) — only count if they're not already covered
    for word in SHORT_WORDS:
        start = 0
        while True:
            idx = up.find(word, start)
            if idx < 0:
                break
            # Only add if at least 1 char is not yet covered
            if not all(covered[idx:idx+3]):
                hits.append((word, idx))
                for j in range(idx, min(idx + 3, n)):
                    covered[j] = True
            start = idx + 1

    coverage = sum(covered) / n
    long_hits = sum(1 for w, _ in hits if len(w) >= 6)

    result = {
        'word_coverage': coverage,
        'long_word_count': long_hits,
    }
    if return_hits:
        result['word_hits'] = sorted(hits, key=lambda x: x[1])
    return result


if __name__ == "__main__":
    # Self-test with Cipher 2 known plaintext
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
    from corpus.canonical import CanonicalCorpus
    from constraints.overlap_engine import load_cipher
    from extractors import get_extractor

    corpus = CanonicalCorpus.load('corpus/CANON_DOI.json')

    # Cipher 2 (known correct)
    cipher2 = load_cipher(2)
    ext = get_extractor('first_letter')
    c2 = corpus.decode_with_extractor(cipher2, ext)
    r2 = score_word_patterns(c2, return_hits=True)
    print(f"Cipher 2 (correct):  coverage={r2['word_coverage']:.3f}, "
          f"long_words={r2['long_word_count']}, total_hits={len(r2['word_hits'])}")
    print(f"  Sample hits: {[(w,p) for w,p in r2['word_hits'][:15]]}")

    # Cipher 1 first_letter
    cipher1 = load_cipher(1)
    c1 = corpus.decode_with_extractor(cipher1, ext)
    r1 = score_word_patterns(c1, return_hits=True)
    print(f"Cipher 1 (first_letter): coverage={r1['word_coverage']:.3f}, "
          f"long_words={r1['long_word_count']}, total_hits={len(r1['word_hits'])}")

    # Cipher 1 best unconstrained
    ext2 = get_extractor('cmod_a1_b0_c1_m5')
    c1b = corpus.decode_with_extractor(cipher1, ext2)
    r1b = score_word_patterns(c1b, return_hits=True)
    print(f"Cipher 1 (cmod best): coverage={r1b['word_coverage']:.3f}, "
          f"long_words={r1b['long_word_count']}, total_hits={len(r1b['word_hits'])}")

    # Null (random)
    import random
    random.seed(42)
    null = ''.join(
        corpus.get_word(cn)[random.randint(0, len(corpus.get_word(cn))-1)].upper()
        if corpus.get_word(cn) else '?'
        for cn in cipher1
    )
    rn = score_word_patterns(null, return_hits=True)
    print(f"Null baseline:       coverage={rn['word_coverage']:.3f}, "
          f"long_words={rn['long_word_count']}, total_hits={len(rn['word_hits'])}")
