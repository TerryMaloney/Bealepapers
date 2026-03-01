"""
Cipher 3 Domain-Specific Scorer

Implements deterministic heuristics for scoring Cipher 3 "Names and Residences" domain.

This is NOT claiming plaintext - it's a ranking heuristic to prioritize strategies
that produce domain-plausible output for Cipher 3.

Bonuses for:
- Location tokens (county, virginia, north, south, etc.)
- Geographic features (river, creek, mountain, ridge)
- Name-like patterns (capitalization, common surnames)

Penalties for:
- Excessive consonant runs (>4 consecutive)
- Improbable letter sequences
- Random-looking output
"""

import re
from typing import Dict, Tuple, List
from collections import Counter


class Cipher3DomainScorer:
    """Domain-specific scorer for Cipher 3 (Names and Residences)."""
    
    def __init__(self):
        # Location-specific tokens with weights
        self.location_tokens = {
            # Primary Virginia locations (Beale context)
            'bedford': 15, 'campbell': 10, 'lynchburg': 12,
            'buford': 12, 'bufords': 12,
            
            # Administrative
            'county': 10, 'co': 8, 'virginia': 15, 'va': 12,
            
            # Directions
            'north': 8, 'south': 8, 'east': 8, 'west': 8,
            'northeast': 7, 'northwest': 7, 'southeast': 7, 'southwest': 7,
            
            # Geographic features
            'river': 7, 'creek': 7, 'mountain': 7, 'ridge': 7,
            'road': 6, 'hollow': 6, 'fork': 6, 'branch': 6,
            'valley': 6, 'hill': 6, 'spring': 6,
            
            # Distances
            'mile': 5, 'miles': 5, 'distance': 5,
            'near': 5, 'from': 4, 'about': 4,
            
            # Residential
            'residence': 8, 'resides': 7, 'lives': 6,
            'dwelling': 6, 'house': 5, 'home': 5
        }
        
        # Common 19th century Virginia surnames
        self.common_surnames = [
            'smith', 'johnson', 'brown', 'davis', 'miller', 'wilson',
            'moore', 'taylor', 'anderson', 'thomas', 'jackson', 'white',
            'harris', 'martin', 'thompson', 'garcia', 'martinez', 'robinson',
            'clark', 'rodriguez', 'lewis', 'lee', 'walker', 'hall',
            'allen', 'young', 'hernandez', 'king', 'wright', 'lopez',
            'hill', 'scott', 'green', 'adams', 'baker', 'gonzalez',
            'nelson', 'carter', 'mitchell', 'perez', 'roberts', 'turner',
            'phillips', 'campbell', 'parker', 'evans', 'edwards', 'collins'
        ]
        
        # Common 19th century given names
        self.common_given_names = [
            'john', 'william', 'james', 'george', 'charles', 'robert',
            'joseph', 'thomas', 'henry', 'edward', 'samuel', 'david',
            'benjamin', 'daniel', 'peter', 'andrew', 'jacob', 'francis',
            'mary', 'elizabeth', 'sarah', 'ann', 'martha', 'jane',
            'margaret', 'nancy', 'catherine', 'rebecca', 'rachel'
        ]
    
    def score(self, stream: str) -> Tuple[float, Dict]:
        """
        Score Cipher 3 decoded stream for domain likelihood.
        
        Args:
            stream: Decoded character stream
        
        Returns:
            (total_score 0-100, component_scores dict)
        """
        if not stream:
            return 0.0, {}
        
        stream_lower = stream.lower()
        
        scores = {
            'location_tokens': self._score_location_presence(stream_lower),
            'name_patterns': self._score_name_patterns(stream_lower),
            'consonant_runs': -self._penalize_consonant_runs(stream),
            'letter_bigrams': self._score_english_bigrams(stream),
            'vowel_ratio': self._score_vowel_ratio(stream)
        }
        
        # Weighted combination
        total = (
            0.35 * scores['location_tokens'] +
            0.25 * scores['name_patterns'] +
            0.20 * scores['letter_bigrams'] +
            0.10 * scores['vowel_ratio'] +
            0.10 * scores['consonant_runs']
        )
        
        return total, scores
    
    def _score_location_presence(self, stream_lower: str) -> float:
        """Score based on presence of location-related tokens."""
        total_weight = 0.0
        max_possible = sum(self.location_tokens.values())
        
        for token, weight in self.location_tokens.items():
            if token in stream_lower:
                total_weight += weight
        
        return (total_weight / max_possible) * 100 if max_possible > 0 else 0.0
    
    def _score_name_patterns(self, stream_lower: str) -> float:
        """Score based on presence of name-like patterns."""
        score = 0.0
        
        # Check for common surnames
        surname_count = sum(1 for name in self.common_surnames if name in stream_lower)
        score += min(surname_count * 10, 40)  # Cap at 40
        
        # Check for common given names
        given_name_count = sum(1 for name in self.common_given_names if name in stream_lower)
        score += min(given_name_count * 8, 30)  # Cap at 30
        
        # Check for capitalization patterns (if preserved)
        # Name-like: Capitalized word followed by lowercase
        # This is a weak signal but helps
        words = stream_lower.split()
        if len(words) > 10:
            # Bonus for reasonable word-like structure
            score += 10
        
        return min(score, 100)
    
    def _penalize_consonant_runs(self, stream: str) -> float:
        """Penalize excessive consonant runs (artifact of bad extraction)."""
        if not stream:
            return 0.0
        
        vowels = set('AEIOUaeiou')
        max_run = 0
        current_run = 0
        
        for char in stream:
            if char.isalpha():
                if char not in vowels:
                    current_run += 1
                    max_run = max(max_run, current_run)
                else:
                    current_run = 0
        
        # Penalize runs > 4 consonants
        if max_run > 4:
            penalty = (max_run - 4) * 10
            return min(penalty, 50)
        
        return 0.0
    
    def _score_english_bigrams(self, stream: str) -> float:
        """
        Score based on English bigram probabilities.
        
        Uses simple heuristic: common bigrams vs rare bigrams.
        """
        if len(stream) < 2:
            return 0.0
        
        # Common English bigrams (high frequency)
        common_bigrams = {
            'th', 'he', 'in', 'er', 'an', 're', 'on', 'at', 'en', 'nd',
            'ti', 'es', 'or', 'te', 'of', 'ed', 'is', 'it', 'al', 'ar',
            'st', 'to', 'nt', 'ng', 'se', 'ha', 'as', 'ou', 'io', 'le'
        }
        
        # Rare/improbable bigrams
        rare_bigrams = {
            'zx', 'qx', 'jx', 'vx', 'xj', 'xz', 'xq', 'qz', 'qj',
            'zq', 'jq', 'vq', 'fq', 'gq', 'kq', 'pq', 'tq', 'wq'
        }
        
        stream_lower = stream.lower()
        bigrams = [stream_lower[i:i+2] for i in range(len(stream_lower)-1)
                  if stream_lower[i].isalpha() and stream_lower[i+1].isalpha()]
        
        if not bigrams:
            return 0.0
        
        common_count = sum(1 for bg in bigrams if bg in common_bigrams)
        rare_count = sum(1 for bg in bigrams if bg in rare_bigrams)
        
        common_ratio = common_count / len(bigrams)
        rare_ratio = rare_count / len(bigrams)
        
        # Score: high common, low rare
        score = (common_ratio * 100) - (rare_ratio * 50)
        
        return max(0, min(score, 100))
    
    def _score_vowel_ratio(self, stream: str) -> float:
        """Score vowel ratio (English ~38-42%)."""
        if not stream:
            return 0.0
        
        vowels = sum(1 for c in stream if c.upper() in 'AEIOU')
        letters = sum(1 for c in stream if c.isalpha())
        
        if letters == 0:
            return 0.0
        
        ratio = vowels / letters
        
        # Target: 0.40 (40%)
        target = 0.40
        deviation = abs(ratio - target)
        
        score = max(0, 100 - (deviation * 200))
        return score


def test_cipher3_scorer():
    """Test Cipher 3 domain scorer."""
    print("=" * 80)
    print("CIPHER 3 DOMAIN SCORER TEST")
    print("=" * 80)
    
    scorer = Cipher3DomainScorer()
    
    # Test 1: Good domain text
    print("\n[Test 1] Domain-appropriate text...")
    good_text = "JOHNSMITHBEDFORDCOUNTYVIRGINIANEARBUFORDSRIDGE"
    total, scores = scorer.score(good_text)
    
    print(f"Text: {good_text}")
    print(f"Total score: {total:.2f}/100")
    print(f"Component scores:")
    for key, value in scores.items():
        print(f"  {key:20s}: {value:6.2f}")
    
    # Test 2: Random text
    print("\n[Test 2] Random text...")
    random_text = "XQZMKVPWBYLRNCJDSFGTHAOEIUX"
    total, scores = scorer.score(random_text)
    
    print(f"Text: {random_text}")
    print(f"Total score: {total:.2f}/100")
    print(f"Component scores:")
    for key, value in scores.items():
        print(f"  {key:20s}: {value:6.2f}")
    
    # Test 3: Mixed text
    print("\n[Test 3] Mixed text with some domain tokens...")
    mixed_text = "RESIDESINCAMPBELLCOUNTYNEARTHERIVER"
    total, scores = scorer.score(mixed_text)
    
    print(f"Text: {mixed_text}")
    print(f"Total score: {total:.2f}/100")
    print(f"Component scores:")
    for key, value in scores.items():
        print(f"  {key:20s}: {value:6.2f}")
    
    print("\n" + "=" * 80)
    print("CIPHER 3 DOMAIN SCORER TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_cipher3_scorer()
