"""
SUBSTITUTION MODULE (Phase 5)
Post-extraction substitution layers: Caesar, Vigenere, simple substitution.
All methods are deterministic and reproducible with seeds.
"""

import random
import signal_score
from typing import Dict, Tuple


# ============================================================================
# CAESAR SHIFT
# ============================================================================

class CaesarShift:
    """Caesar shift by N positions"""
    def __init__(self, shift: int):
        self.shift = shift % 26
        self.name = f"caesar_{self.shift}"
    
    def apply(self, stream: str) -> str:
        result = []
        for char in stream:
            if char.isalpha():
                shifted = chr((ord(char) - ord('A') + self.shift) % 26 + ord('A'))
                result.append(shifted)
            else:
                result.append(char)
        return ''.join(result)


def generate_all_caesar():
    """Generate all 26 Caesar shifts"""
    return [CaesarShift(i) for i in range(26)]


# ============================================================================
# VIGENERE CIPHER
# ============================================================================

class VigenereCipher:
    """Vigenere cipher with keyword"""
    def __init__(self, key: str):
        self.key = key.upper()
        self.name = f"vigenere_{key.lower()}"
    
    def apply(self, stream: str) -> str:
        result = []
        key_idx = 0
        for char in stream:
            if char.isalpha():
                shift = ord(self.key[key_idx % len(self.key)]) - ord('A')
                shifted = chr((ord(char) - ord('A') + shift) % 26 + ord('A'))
                result.append(shifted)
                key_idx += 1
            else:
                result.append(char)
        return ''.join(result)


def search_vigenere_key(stream: str, key_length: int, seed: int, 
                        max_iters: int = 1000) -> Tuple[str, float]:
    """
    Hillclimb search for best Vigenere key of given length.
    
    Args:
        stream: Character stream to decode
        key_length: Length of key to search for
        seed: Random seed for reproducibility
        max_iters: Maximum iterations
    
    Returns:
        Tuple of (best_key, best_score)
    """
    random.seed(seed)
    
    # Initialize with random key
    current_key = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') 
                         for _ in range(key_length))
    
    # Score current
    current_cipher = VigenereCipher(current_key)
    current_decoded = current_cipher.apply(stream)
    current_score = signal_score.score_stream(current_decoded, use_phase3_metrics=False)['total_score']
    
    best_key = current_key
    best_score = current_score
    
    # Hillclimb with random restarts
    for iteration in range(max_iters):
        # Try modifying one position in key
        test_key = list(current_key)
        pos = random.randint(0, key_length - 1)
        test_key[pos] = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        test_key_str = ''.join(test_key)
        
        # Score it
        test_cipher = VigenereCipher(test_key_str)
        test_decoded = test_cipher.apply(stream)
        test_score = signal_score.score_stream(test_decoded, use_phase3_metrics=False)['total_score']
        
        # Accept if better
        if test_score > current_score:
            current_key = test_key_str
            current_score = test_score
            
            if test_score > best_score:
                best_key = current_key
                best_score = test_score
        
        # Random restart every 100 iterations
        if iteration % 100 == 99 and iteration < max_iters - 1:
            current_key = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') 
                                 for _ in range(key_length))
            current_cipher = VigenereCipher(current_key)
            current_decoded = current_cipher.apply(stream)
            current_score = signal_score.score_stream(current_decoded, use_phase3_metrics=False)['total_score']
    
    return best_key, best_score


# ============================================================================
# SIMPLE SUBSTITUTION (MONOALPHABETIC)
# ============================================================================

class MonoalphabeticSubstitution:
    """General 26-letter substitution mapping"""
    def __init__(self, mapping: Dict[str, str]):
        self.mapping = mapping
        mapping_str = ''.join(mapping[chr(i)] for i in range(ord('A'), ord('Z')+1))
        self.name = f"monoalpha_{hash(mapping_str) % 10000}"
        self.mapping_str = mapping_str
    
    def apply(self, stream: str) -> str:
        return ''.join(self.mapping.get(c, c) for c in stream)


def hillclimb_substitution(stream: str, seed: int, max_iters: int = 10000,
                           temp_start: float = 100.0, temp_end: float = 0.1) -> Tuple[Dict[str, str], float]:
    """
    Simulated annealing to find best simple substitution mapping.
    
    Args:
        stream: Character stream to decode
        seed: Random seed for reproducibility
        max_iters: Maximum iterations
        temp_start: Starting temperature
        temp_end: Ending temperature
    
    Returns:
        Tuple of (best_mapping, best_score)
    """
    random.seed(seed)
    
    # Initialize with identity mapping
    letters = [chr(i) for i in range(ord('A'), ord('Z')+1)]
    current_mapping = {c: c for c in letters}
    
    # Score current
    current_decoded = ''.join(current_mapping.get(c, c) for c in stream)
    current_score = signal_score.score_stream(current_decoded, use_phase3_metrics=False)['total_score']
    
    best_mapping = current_mapping.copy()
    best_score = current_score
    
    # Temperature schedule
    def temperature(iteration):
        return temp_start * ((temp_end / temp_start) ** (iteration / max_iters))
    
    # Simulated annealing
    for iteration in range(max_iters):
        # Generate neighbor by swapping two letters
        test_mapping = current_mapping.copy()
        letter1, letter2 = random.sample(letters, 2)
        test_mapping[letter1], test_mapping[letter2] = test_mapping[letter2], test_mapping[letter1]
        
        # Score it
        test_decoded = ''.join(test_mapping.get(c, c) for c in stream)
        test_score = signal_score.score_stream(test_decoded, use_phase3_metrics=False)['total_score']
        
        # Accept if better, or probabilistically if worse
        delta = test_score - current_score
        temp = temperature(iteration)
        
        if delta > 0 or (temp > 0 and random.random() < (2 ** (delta / temp) if delta / temp > -10 else 0)):
            current_mapping = test_mapping
            current_score = test_score
            
            if test_score > best_score:
                best_mapping = current_mapping.copy()
                best_score = test_score
    
    return best_mapping, best_score


def run_substitution_trials(stream: str, num_seeds: int = 20, max_iters: int = 10000) -> Dict:
    """
    Run multiple seeded trials of substitution hillclimb.
    
    Args:
        stream: Character stream to decode
        num_seeds: Number of independent seeds to try
        max_iters: Iterations per seed
    
    Returns:
        Dictionary with best mapping, scores, and statistics
    """
    print(f"Running {num_seeds} seeded trials of substitution hillclimb...")
    print(f"Max iterations per seed: {max_iters}")
    
    trials = []
    
    for seed in range(num_seeds):
        print(f"  Seed {seed+1}/{num_seeds}...", end="")
        
        mapping, score = hillclimb_substitution(stream, seed, max_iters)
        
        trials.append({
            'seed': seed,
            'score': score,
            'mapping': mapping
        })
        
        print(f" score: {score:.2f}/100")
    
    # Statistics
    scores = [t['score'] for t in trials]
    best_trial = max(trials, key=lambda x: x['score'])
    
    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std_dev = variance ** 0.5
    
    return {
        'trials': trials,
        'best': best_trial,
        'mean': mean_score,
        'std_dev': std_dev,
        'min': min(scores),
        'max': max(scores)
    }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SUBSTITUTION MODULE TEST")
    print("=" * 70)
    
    # Test Caesar
    print("\nCaesar Shift Test:")
    test_text = "HELLO"
    for shift in [0, 1, 13, 25]:
        caesar = CaesarShift(shift)
        result = caesar.apply(test_text)
        print(f"  Shift {shift:2d}: {test_text} -> {result}")
    
    # Test Vigenere
    print("\nVigenere Test:")
    vig = VigenereCipher("KEY")
    result = vig.apply("HELLO")
    print(f"  Key 'KEY': HELLO -> {result}")
    
    # Test substitution (small sample)
    print("\nSubstitution hillclimb test (100 iters, seed=42):")
    test_stream = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG"
    mapping, score = hillclimb_substitution(test_stream, seed=42, max_iters=100)
    decoded = ''.join(mapping.get(c, c) for c in test_stream)
    print(f"  Score: {score:.2f}/100")
    print(f"  Decoded: {decoded[:40]}")
    
    print("\n" + "=" * 70)
    print("SUBSTITUTION MODULE READY")
    print("=" * 70)
