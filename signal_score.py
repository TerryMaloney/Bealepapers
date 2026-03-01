"""
SIGNAL SCORING ENGINE
Quantify "English-likeness" of decoded character streams.

Scores text on multiple metrics to identify streams that look like English.
"""

from collections import Counter
from typing import Dict

# ============================================================================
# ENGLISH LANGUAGE REFERENCE DATA
# ============================================================================

# Top 20 English bigrams by frequency
TOP_BIGRAMS = [
    'TH', 'HE', 'IN', 'ER', 'AN', 'RE', 'ON', 'AT', 'EN', 'ND',
    'TI', 'ES', 'OR', 'TE', 'OF', 'ED', 'IS', 'IT', 'AL', 'AR'
]

# Top 15 English trigrams by frequency
TOP_TRIGRAMS = [
    'THE', 'AND', 'ING', 'HER', 'HAT', 'HIS', 'THA', 'ERE',
    'FOR', 'ENT', 'ION', 'TER', 'WAS', 'YOU', 'ITH'
]

# Common English words to look for
COMMON_WORDS = [
    'THE', 'AND', 'OF', 'TO', 'IN', 'FOR', 'IS', 'ON', 'THAT', 'WITH',
    'AS', 'WAS', 'ARE', 'HAD', 'FROM', 'OR', 'BY', 'AT', 'BE', 'THIS'
]

# Additional context words relevant to Beale Ciphers
BEALE_CONTEXT_WORDS = [
    'BEDFORD', 'COUNTY', 'VIRGINIA', 'TREASURE', 'GOLD', 'SILVER',
    'DEPOSIT', 'VAULT', 'BURIED', 'LOCATION', 'NORTH', 'SOUTH',
    'EAST', 'WEST', 'MILES', 'FEET', 'BUFORD'
]


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def score_bigrams(text: str) -> float:
    """
    Score text based on common English bigram frequency.
    Returns score 0-100 based on % of bigrams that are common.
    """
    if len(text) < 2:
        return 0.0
    
    # Extract all bigrams
    bigrams = [text[i:i+2] for i in range(len(text)-1)]
    if not bigrams:
        return 0.0
    
    # Count matches with common bigrams
    matches = sum(1 for bg in bigrams if bg in TOP_BIGRAMS)
    score = (matches / len(bigrams)) * 100
    
    return min(score, 100.0)


def score_trigrams(text: str) -> float:
    """
    Score text based on common English trigram frequency.
    Returns score 0-100 based on % of trigrams that are common.
    """
    if len(text) < 3:
        return 0.0
    
    # Extract all trigrams
    trigrams = [text[i:i+3] for i in range(len(text)-2)]
    if not trigrams:
        return 0.0
    
    # Count matches with common trigrams
    matches = sum(1 for tg in trigrams if tg in TOP_TRIGRAMS)
    score = (matches / len(trigrams)) * 100
    
    return min(score, 100.0)


def score_vowel_ratio(text: str) -> float:
    """
    Score text based on vowel/consonant ratio.
    English is typically ~40% vowels. Returns score 0-100.
    """
    if not text:
        return 0.0
    
    # Count vowels and consonants
    vowels = sum(1 for c in text.upper() if c in 'AEIOU')
    consonants = sum(1 for c in text.upper() if c.isalpha() and c not in 'AEIOU')
    
    total_letters = vowels + consonants
    if total_letters == 0:
        return 0.0
    
    vowel_ratio = vowels / total_letters
    
    # English is ~38-42% vowels, score based on distance from 40%
    ideal_ratio = 0.40
    distance = abs(vowel_ratio - ideal_ratio)
    
    # Convert distance to score (0 distance = 100, >0.3 distance = 0)
    score = max(0, 100 * (1 - distance / 0.3))
    
    return min(score, 100.0)


def count_dictionary_words(text: str) -> int:
    """
    Count occurrences of common English words in the text.
    Returns raw count.
    """
    count = 0
    text_upper = text.upper()
    
    # Check for common words
    for word in COMMON_WORDS:
        count += text_upper.count(word)
    
    # Check for Beale-specific context words (bonus points)
    for word in BEALE_CONTEXT_WORDS:
        if word in text_upper:
            count += 5  # Bonus for context-relevant words
    
    return count


def score_dictionary_hits(text: str) -> float:
    """
    Score text based on dictionary word hits.
    Returns score 0-100 based on word density.
    """
    if len(text) < 10:
        return 0.0
    
    hits = count_dictionary_words(text)
    
    # Score based on hits per 100 characters
    density = (hits / len(text)) * 100
    
    # Scale: 10+ hits per 100 chars = max score
    score = min(density * 10, 100.0)
    
    return score


def score_letter_frequency(text: str) -> float:
    """
    Score text based on English letter frequency distribution.
    Returns score 0-100 based on how well it matches expected frequencies.
    """
    if len(text) < 20:
        return 0.0
    
    # Expected English letter frequencies (%)
    expected_freq = {
        'E': 12.70, 'T': 9.06, 'A': 8.17, 'O': 7.51, 'I': 6.97,
        'N': 6.75, 'S': 6.33, 'H': 6.09, 'R': 5.99, 'D': 4.25,
        'L': 4.03, 'C': 2.78, 'U': 2.76, 'M': 2.41, 'W': 2.36,
        'F': 2.23, 'G': 2.02, 'Y': 1.97, 'P': 1.93, 'B': 1.29
    }
    
    # Count actual frequencies
    text_upper = text.upper()
    letter_counts = Counter(c for c in text_upper if c.isalpha())
    total_letters = sum(letter_counts.values())
    
    if total_letters == 0:
        return 0.0
    
    # Calculate chi-squared-like distance
    distance = 0.0
    for letter in 'ETAOINSHR':  # Focus on most common letters
        actual_pct = (letter_counts.get(letter, 0) / total_letters) * 100
        expected_pct = expected_freq.get(letter, 0)
        distance += abs(actual_pct - expected_pct)
    
    # Convert distance to score (lower distance = higher score)
    # Distance of 0 = perfect match (100), distance of 50 = 0
    score = max(0, 100 * (1 - distance / 50))
    
    return min(score, 100.0)


# ============================================================================
# ADVANCED METRICS (Phase 3)
# ============================================================================

# Top 30 English quadgrams by frequency
TOP_QUADGRAMS = [
    'TION', 'ATIO', 'THAT', 'THER', 'WITH', 'MENT', 'IONS', 'THIS',
    'HERE', 'FROM', 'OULD', 'TING', 'HICH', 'WHIC', 'CTIO', 'INTH',
    'OULD', 'INGR', 'EDTH', 'ENTI', 'SAND', 'STHE', 'ANDT', 'WARE',
    'OUSE', 'ATED', 'THEI', 'THES', 'THEC', 'ESTI'
]

def score_quadgrams(text: str) -> float:
    """
    Score text based on common English quadgram frequency.
    More selective than trigrams - returns score 0-100.
    """
    if len(text) < 4:
        return 0.0
    
    # Extract all quadgrams
    quadgrams = [text[i:i+4] for i in range(len(text)-3)]
    if not quadgrams:
        return 0.0
    
    # Count matches with common quadgrams
    matches = sum(1 for qg in quadgrams if qg in TOP_QUADGRAMS)
    score = (matches / len(quadgrams)) * 100
    
    # Quadgrams are rare, so scale up: 5% match = full score
    scaled_score = min(score * 20, 100.0)
    
    return scaled_score


def calculate_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of text.
    English text typically has entropy ~4.1 bits per character.
    Returns score 0-100 based on proximity to expected English entropy.
    """
    import math
    
    if not text:
        return 0.0
    
    # Count character frequencies
    freq = Counter(text.upper())
    total = sum(freq.values())
    
    if total == 0:
        return 0.0
    
    # Calculate Shannon entropy
    entropy = 0.0
    for count in freq.values():
        probability = count / total
        if probability > 0:
            entropy -= probability * math.log2(probability)
    
    # English text has entropy ~4.0-4.2 bits
    # Random text has entropy ~4.7 bits
    # Cipher text varies widely
    ideal_entropy = 4.1
    distance = abs(entropy - ideal_entropy)
    
    # Convert distance to score (0 distance = 100, >2.0 distance = 0)
    score = max(0, 100 * (1 - distance / 2.0))
    
    return round(score, 2)


def detect_word_fragments(text: str) -> Dict[str, int]:
    """
    Search for 3-8 letter English word fragments.
    Returns dictionary of found fragments with counts.
    """
    fragments = {}
    text_upper = text.upper()
    
    # 3-letter common words
    three_letter = ['THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAD', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'MAN', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WAY', 'WHO', 'BOY', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE']
    
    # 4-letter common words
    four_letter = ['THAT', 'WITH', 'HAVE', 'THIS', 'WILL', 'YOUR', 'FROM', 'THEY', 'BEEN', 'HAVE', 'WERE', 'SAID', 'WHAT', 'WORD', 'BEEN', 'CALL', 'CAME', 'COME', 'EACH', 'FIND', 'GIVE', 'GOOD', 'HAND', 'HIGH', 'JUST', 'KIND', 'KNOW', 'LAST', 'LONG', 'MADE', 'MAKE', 'MANY', 'MORE', 'MOST', 'MUCH', 'NAME', 'NEXT', 'ONLY', 'OVER', 'PART', 'SAME', 'SUCH', 'TAKE', 'THAN', 'THEN', 'THEM', 'THEY', 'TIME', 'VERY', 'WELL', 'WENT', 'WHEN', 'WORK', 'YEAR']
    
    # 5+ letter Beale context words
    context_words = ['BEDFORD', 'COUNTY', 'VIRGINIA', 'TREASURE', 'BURIED', 'VAULT', 'NORTH', 'SOUTH', 'MILES', 'FEET', 'GOLD', 'SILVER', 'DEPOSIT']
    
    # Search for all fragments
    all_words = three_letter + four_letter + context_words
    
    for word in all_words:
        count = text_upper.count(word)
        if count > 0:
            fragments[word] = count
    
    return fragments


def score_fragments(text: str) -> float:
    """
    Score text based on detected word fragments.
    Returns score 0-100 based on fragment density and quality.
    """
    if len(text) < 10:
        return 0.0
    
    fragments = detect_word_fragments(text)
    
    if not fragments:
        return 0.0
    
    # Calculate score based on:
    # - Total fragments found
    # - Density (fragments per 100 chars)
    # - Quality (longer words = better)
    
    total_fragments = sum(fragments.values())
    density = (total_fragments / len(text)) * 100
    
    # Bonus for longer words (Beale context words)
    quality_bonus = sum(5 for word in fragments.keys() if len(word) >= 6)
    
    # Base score from density (5+ per 100 chars = good)
    base_score = min(density * 20, 100.0)
    
    # Add quality bonus (up to 20 points)
    final_score = min(base_score + quality_bonus, 100.0)
    
    return round(final_score, 2)


# ============================================================================
# COMPOSITE SCORING
# ============================================================================

def score_stream(text: str, use_phase3_metrics: bool = True) -> Dict[str, float]:
    """
    Score a text stream on multiple English-likeness metrics.
    
    Args:
        text: The text to score
        use_phase3_metrics: If True, include Phase 3 advanced metrics (quadgrams, entropy, fragments)
    
    Returns:
        Dictionary with individual scores and weighted total_score (0-100)
    """
    if not text or len(text) < 5:
        result = {
            'bigram_score': 0.0,
            'trigram_score': 0.0,
            'vowel_ratio_score': 0.0,
            'dictionary_score': 0.0,
            'letter_freq_score': 0.0,
            'total_score': 0.0,
            'word_count': 0
        }
        if use_phase3_metrics:
            result.update({
                'quadgram_score': 0.0,
                'entropy_score': 0.0,
                'fragment_score': 0.0
            })
        return result
    
    # Calculate Phase 2 scores
    bigram = score_bigrams(text)
    trigram = score_trigrams(text)
    vowel = score_vowel_ratio(text)
    dictionary = score_dictionary_hits(text)
    letter_freq = score_letter_frequency(text)
    word_count = count_dictionary_words(text)
    
    # Calculate Phase 3 scores if requested
    if use_phase3_metrics:
        quadgram = score_quadgrams(text)
        entropy = calculate_entropy(text)
        fragment = score_fragments(text)
        
        # Weighted average with Phase 3 metrics
        weights = {
            'bigram': 0.20,
            'trigram': 0.20,
            'quadgram': 0.15,
            'vowel': 0.10,
            'dictionary': 0.10,
            'letter_freq': 0.10,
            'entropy': 0.05,
            'fragment': 0.10
        }
        
        total = (
            bigram * weights['bigram'] +
            trigram * weights['trigram'] +
            quadgram * weights['quadgram'] +
            vowel * weights['vowel'] +
            dictionary * weights['dictionary'] +
            letter_freq * weights['letter_freq'] +
            entropy * weights['entropy'] +
            fragment * weights['fragment']
        )
        
        return {
            'bigram_score': round(bigram, 2),
            'trigram_score': round(trigram, 2),
            'quadgram_score': round(quadgram, 2),
            'vowel_ratio_score': round(vowel, 2),
            'dictionary_score': round(dictionary, 2),
            'letter_freq_score': round(letter_freq, 2),
            'entropy_score': round(entropy, 2),
            'fragment_score': round(fragment, 2),
            'total_score': round(total, 2),
            'word_count': word_count
        }
    else:
        # Phase 2 weighted average (backward compatible)
        weights = {
            'bigram': 0.30,
            'trigram': 0.30,
            'vowel': 0.15,
            'dictionary': 0.15,
            'letter_freq': 0.10
        }
        
        total = (
            bigram * weights['bigram'] +
            trigram * weights['trigram'] +
            vowel * weights['vowel'] +
            dictionary * weights['dictionary'] +
            letter_freq * weights['letter_freq']
        )
        
        return {
            'bigram_score': round(bigram, 2),
            'trigram_score': round(trigram, 2),
            'vowel_ratio_score': round(vowel, 2),
            'dictionary_score': round(dictionary, 2),
            'letter_freq_score': round(letter_freq, 2),
            'total_score': round(total, 2),
            'word_count': word_count
        }


# ============================================================================
# TESTING AND UTILITIES
# ============================================================================

def print_score_report(text: str, label: str = "Text", use_phase3: bool = True):
    """Print detailed scoring report for a text sample"""
    scores = score_stream(text, use_phase3_metrics=use_phase3)
    
    print(f"\nScoring report for: {label}")
    print("=" * 60)
    print(f"Text: {text[:80]}{'...' if len(text) > 80 else ''}")
    print(f"Length: {len(text)} characters")
    print()
    print(f"Bigram score:       {scores['bigram_score']:6.2f}/100")
    print(f"Trigram score:      {scores['trigram_score']:6.2f}/100")
    if use_phase3 and 'quadgram_score' in scores:
        print(f"Quadgram score:     {scores['quadgram_score']:6.2f}/100")
    print(f"Vowel ratio score:  {scores['vowel_ratio_score']:6.2f}/100")
    print(f"Dictionary score:   {scores['dictionary_score']:6.2f}/100")
    print(f"Letter freq score:  {scores['letter_freq_score']:6.2f}/100")
    if use_phase3 and 'entropy_score' in scores:
        print(f"Entropy score:      {scores['entropy_score']:6.2f}/100")
        print(f"Fragment score:     {scores['fragment_score']:6.2f}/100")
    print("-" * 60)
    print(f"TOTAL SCORE:        {scores['total_score']:6.2f}/100")
    print(f"Dictionary hits:    {scores['word_count']}")
    if use_phase3:
        fragments = detect_word_fragments(text)
        if fragments:
            print(f"Fragments found:    {', '.join(list(fragments.keys())[:10])}")
    print("=" * 60)


if __name__ == "__main__":
    # Test the scoring system
    print("=" * 70)
    print("SIGNAL SCORING ENGINE TEST")
    print("=" * 70)
    
    # Test with actual English
    english_text = "THE TREASURE IS BURIED IN BEDFORD COUNTY VIRGINIA ABOUT FOUR MILES FROM THE TOWN"
    print_score_report(english_text, "Valid English Text")
    
    # Test with random letters
    random_text = "XQZJKPVWMRFYLNTBHGDSCAOEIU"
    print_score_report(random_text, "Random Letters")
    
    # Test with Phase 1 output
    phase1_output = "PMTLITIAFAIIARVFTHTCOVTADWIOGEIAGSOARTPTAODITWFLPPAJCSISPDNOOGIOAI"
    print_score_report(phase1_output, "Phase 1 Cipher 1 Output")
