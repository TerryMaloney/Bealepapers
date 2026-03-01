"""
Phase D: Multi-Objective Scoring

Enhanced scoring to avoid false plateaus:
- 19th-century lexicon weighting
- Function word density
- Letter doubling penalty
- Entropy bounds
- Fragment detection
"""

import math
from typing import Dict, List, Tuple
from collections import Counter
import re


class MultiObjectiveScorer:
    """Enhanced scoring to avoid false plateaus and detect authentic plaintext."""
    
    def __init__(self):
        # Load n-gram models (using existing signal_score data)
        self.bigram_freq = self._load_bigrams()
        self.trigram_freq = self._load_trigrams()
        
        # 19th-century and Beale-relevant words
        self.period_lexicon = self._build_period_lexicon()
        
        # Common English function words
        self.function_words = [
            'the', 'of', 'and', 'to', 'in', 'a', 'is', 'that', 'it', 'for',
            'as', 'with', 'was', 'his', 'by', 'on', 'at', 'from', 'this',
            'be', 'are', 'or', 'an', 'were', 'which', 'have', 'had', 'their'
        ]
        
        # Beale-specific cribs
        self.beale_cribs = [
            'bedford', 'county', 'virginia', 'vault', 'feet', 'north', 'south',
            'ridge', 'creek', 'mile', 'degrees', 'chestnut', 'oak', 'rock',
            'buford', 'tavern', 'iron', 'pot', 'stone', 'buried', 'deposit'
        ]
    
    def _load_bigrams(self) -> Dict[str, float]:
        """Load bigram frequencies (simplified - use existing if available)."""
        # Use existing bigram data from signal_score if available
        try:
            from signal_score import load_bigrams
            return load_bigrams()
        except:
            # Fallback: return empty dict
            return {}
    
    def _load_trigrams(self) -> Dict[str, float]:
        """Load trigram frequencies."""
        try:
            from signal_score import load_trigrams
            return load_trigrams()
        except:
            return {}
    
    def _build_period_lexicon(self) -> Dict[str, float]:
        """Build 19th-century weighted lexicon."""
        # Period-specific and Beale-relevant terms with weights
        lexicon = {
            # Location words (high weight)
            'bedford': 10.0, 'virginia': 10.0, 'county': 8.0, 'tavern': 8.0,
            'buford': 10.0, 'lynchburg': 10.0,
            
            # Treasure/deposit words
            'vault': 8.0, 'deposit': 8.0, 'buried': 8.0, 'treasure': 8.0,
            'iron': 6.0, 'pot': 6.0, 'stone': 6.0, 'feet': 6.0,
            
            # Direction/measurement
            'north': 6.0, 'south': 6.0, 'east': 6.0, 'west': 6.0,
            'mile': 6.0, 'miles': 6.0, 'degrees': 6.0,
            
            # Natural features
            'ridge': 6.0, 'creek': 6.0, 'mountain': 6.0, 'rock': 6.0,
            'chestnut': 6.0, 'oak': 6.0, 'tree': 6.0,
            
            # Common 19th-century words
            'situated': 4.0, 'excavation': 4.0, 'described': 4.0,
            'following': 4.0, 'containing': 4.0, 'obtained': 4.0
        }
        
        return lexicon
    
    def score(self, stream: str) -> Tuple[float, Dict[str, float]]:
        """
        Score decoded stream with multiple objectives.
        
        Returns:
            (total_score, component_scores)
        """
        if not stream:
            return 0.0, {}
        
        stream = stream.upper()
        
        scores = {
            'bigram': self._score_bigrams(stream),
            'trigram': self._score_trigrams(stream),
            'period_words': self._score_period_vocabulary(stream),
            'function_density': self._score_function_words(stream),
            'letter_doubling': -self._penalize_doubling(stream),
            'entropy': self._score_entropy(stream),
            'vowel_ratio': self._score_vowel_ratio(stream),
            'beale_cribs': self._score_beale_cribs(stream)
        }
        
        # Weighted combination
        total = (
            0.25 * scores['bigram'] +
            0.20 * scores['trigram'] +
            0.15 * scores['period_words'] +
            0.10 * scores['function_density'] +
            0.10 * scores['letter_doubling'] +
            0.05 * scores['entropy'] +
            0.05 * scores['vowel_ratio'] +
            0.10 * scores['beale_cribs']
        )
        
        return total, scores
    
    def _score_bigrams(self, stream: str) -> float:
        """Score bigram frequencies."""
        if len(stream) < 2 or not self.bigram_freq:
            return 0.0
        
        score = 0.0
        count = 0
        
        for i in range(len(stream) - 1):
            bigram = stream[i:i+2]
            if bigram in self.bigram_freq:
                score += math.log10(self.bigram_freq[bigram] + 1e-10)
                count += 1
        
        return (score / count) * 10 if count > 0 else 0.0
    
    def _score_trigrams(self, stream: str) -> float:
        """Score trigram frequencies."""
        if len(stream) < 3 or not self.trigram_freq:
            return 0.0
        
        score = 0.0
        count = 0
        
        for i in range(len(stream) - 2):
            trigram = stream[i:i+3]
            if trigram in self.trigram_freq:
                score += math.log10(self.trigram_freq[trigram] + 1e-10)
                count += 1
        
        return (score / count) * 10 if count > 0 else 0.0
    
    def _score_period_vocabulary(self, stream: str) -> float:
        """Score based on 19th-century lexicon presence."""
        stream_lower = stream.lower()
        
        total_weight = 0.0
        max_possible = sum(self.period_lexicon.values())
        
        for word, weight in self.period_lexicon.items():
            if word in stream_lower:
                total_weight += weight
        
        return (total_weight / max_possible) * 100 if max_possible > 0 else 0.0
    
    def _score_function_words(self, stream: str) -> float:
        """Score function word density."""
        stream_lower = stream.lower()
        
        count = sum(1 for word in self.function_words if word in stream_lower)
        
        # Normalize by number of function words
        return (count / len(self.function_words)) * 100
    
    def _penalize_doubling(self, stream: str) -> float:
        """Penalize excessive letter doubling (artifact of bad extraction)."""
        if len(stream) < 2:
            return 0.0
        
        doubles = sum(1 for i in range(len(stream) - 1)
                     if stream[i] == stream[i+1])
        
        # Normalize by length
        doubling_rate = doubles / len(stream)
        
        # English has ~6-8% natural doubling
        expected = 0.07
        penalty = max(0, (doubling_rate - expected) * 100)
        
        return penalty
    
    def _score_entropy(self, stream: str) -> float:
        """Score Shannon entropy (should be moderate for English)."""
        if not stream:
            return 0.0
        
        counter = Counter(stream)
        total = len(stream)
        
        entropy = -sum((count / total) * math.log2(count / total)
                      for count in counter.values())
        
        # English entropy ~4.0-4.5 bits per character
        # Penalize too low (repetitive) or too high (random)
        target = 4.2
        deviation = abs(entropy - target)
        
        score = max(0, 100 - (deviation * 30))
        return score
    
    def _score_vowel_ratio(self, stream: str) -> float:
        """Score vowel ratio (English ~38-42%)."""
        if not stream:
            return 0.0
        
        vowels = sum(1 for c in stream if c in 'AEIOU')
        ratio = vowels / len(stream)
        
        # Target: 0.40 (40%)
        target = 0.40
        deviation = abs(ratio - target)
        
        score = max(0, 100 - (deviation * 200))
        return score
    
    def _score_beale_cribs(self, stream: str) -> float:
        """Score presence of Beale-specific cribs."""
        stream_lower = stream.lower()
        
        found = sum(1 for crib in self.beale_cribs if crib in stream_lower)
        
        return (found / len(self.beale_cribs)) * 100


def test_multi_objective_scorer():
    """Test multi-objective scorer."""
    print("=" * 80)
    print("MULTI-OBJECTIVE SCORER TEST")
    print("=" * 80)
    
    scorer = MultiObjectiveScorer()
    
    # Test with good English
    print("\n[1] Testing with good English text...")
    good_text = "IHAVEDEPOSITEDINTHEBEALESVAULT"
    total, scores = scorer.score(good_text)
    
    print(f"Text: {good_text}")
    print(f"Total score: {total:.2f}/100")
    print(f"Component scores:")
    for key, value in scores.items():
        print(f"  {key:20s}: {value:6.2f}")
    
    # Test with random
    print("\n[2] Testing with random text...")
    random_text = "XQZMKVPWBYLRNCJDSFGTHAOEIUX"
    total, scores = scorer.score(random_text)
    
    print(f"Text: {random_text}")
    print(f"Total score: {total:.2f}/100")
    print(f"Component scores:")
    for key, value in scores.items():
        print(f"  {key:20s}: {value:6.2f}")
    
    print("\n" + "=" * 80)
    print("MULTI-OBJECTIVE SCORER TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_multi_objective_scorer()
