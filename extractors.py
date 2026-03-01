"""
UNIVERSAL EXTRACTION ENGINE
Modular extraction framework for testing different cipher decode methods.

Each extractor is a pure function that takes word properties and returns
a single character or number that can be used in the decoded stream.
"""

from typing import Optional

class Extractor:
    """Base class for all extractors"""
    
    def __init__(self, name: str):
        self.name = name
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, 
                doc_source: str) -> str:
        """
        Extract a character from the word based on the extraction method.
        
        Args:
            word: The word from the corpus
            word_idx: Index of word in corpus (0-indexed)
            cipher_pos: Position in cipher sequence (0-indexed)
            doc_source: Document source ('VDR', 'DOI', 'SIGNERS', 'ARTICLES')
        
        Returns:
            Single character (or digit as string for numeric methods)
        """
        raise NotImplementedError
    
    def __repr__(self):
        return f"Extractor({self.name})"


# ============================================================================
# LETTER-BASED EXTRACTORS
# ============================================================================

class FirstLetter(Extractor):
    """Extract first letter of word"""
    def __init__(self):
        super().__init__("first_letter")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        return word[0].upper() if word else "?"


class SecondLetter(Extractor):
    """Extract second letter of word"""
    def __init__(self):
        super().__init__("second_letter")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        return word[1].upper() if len(word) >= 2 else "_"


class ThirdLetter(Extractor):
    """Extract third letter of word"""
    def __init__(self):
        super().__init__("third_letter")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        return word[2].upper() if len(word) >= 3 else "_"


class LastLetter(Extractor):
    """Extract last letter of word"""
    def __init__(self):
        super().__init__("last_letter")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        return word[-1].upper() if word else "?"


class MiddleLetter(Extractor):
    """Extract middle letter of word"""
    def __init__(self):
        super().__init__("middle_letter")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        mid_idx = len(word) // 2
        return word[mid_idx].upper()


class NthLetterByPosition(Extractor):
    """Extract Nth letter where N = cipher position mod word length"""
    def __init__(self):
        super().__init__("nth_letter_by_position")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        idx = cipher_pos % len(word)
        return word[idx].upper()


# ============================================================================
# STRUCTURE-BASED EXTRACTORS
# ============================================================================

class WordLength(Extractor):
    """Extract word length as single digit (or X for 10+)"""
    def __init__(self):
        super().__init__("word_length")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        length = len(word)
        return str(length) if length < 10 else "X"


class VowelCount(Extractor):
    """Extract vowel count as single digit (or X for 10+)"""
    def __init__(self):
        super().__init__("vowel_count")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        vowels = sum(1 for c in word.lower() if c in 'aeiou')
        return str(vowels) if vowels < 10 else "X"


class ConsonantCount(Extractor):
    """Extract consonant count as single digit (or X for 10+)"""
    def __init__(self):
        super().__init__("consonant_count")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        consonants = sum(1 for c in word.lower() if c.isalpha() and c not in 'aeiou')
        return str(consonants) if consonants < 10 else "X"


class FirstConsonant(Extractor):
    """Extract first consonant in word"""
    def __init__(self):
        super().__init__("first_consonant")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        for c in word.lower():
            if c.isalpha() and c not in 'aeiou':
                return c.upper()
        return "_"


class FirstVowel(Extractor):
    """Extract first vowel in word"""
    def __init__(self):
        super().__init__("first_vowel")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        for c in word.lower():
            if c in 'aeiou':
                return c.upper()
        return "_"


# ============================================================================
# POSITION-BASED EXTRACTORS
# ============================================================================

class LetterAtCipherMod(Extractor):
    """Extract letter at position = (cipher_number mod word_length)"""
    def __init__(self):
        super().__init__("letter_at_cipher_mod")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        # Use word_idx as proxy for cipher number (actual cipher number not passed here)
        idx = word_idx % len(word)
        return word[idx].upper()


class LetterAtIndexMod(Extractor):
    """Extract letter at position = (word_index mod word_length)"""
    def __init__(self):
        super().__init__("letter_at_index_mod")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        idx = word_idx % len(word)
        return word[idx].upper()


# ============================================================================
# ADVANCED POSITION-BASED EXTRACTORS (Phase 3)
# ============================================================================

class PositionPlusOffset(Extractor):
    """Extract at: (position + offset) mod word_length"""
    def __init__(self, offset_val: int = 335):
        super().__init__(f"position_plus_offset_{offset_val}")
        self.offset_val = offset_val
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        idx = (cipher_pos + self.offset_val) % len(word)
        return word[idx].upper()


class PositionTimes2(Extractor):
    """Extract at: (position * 2) mod word_length"""
    def __init__(self):
        super().__init__("position_times_2")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        idx = (cipher_pos * 2) % len(word)
        return word[idx].upper()


class PositionTimes3(Extractor):
    """Extract at: (position * 3) mod word_length"""
    def __init__(self):
        super().__init__("position_times_3")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        idx = (cipher_pos * 3) % len(word)
        return word[idx].upper()


class AlternatingRule(Extractor):
    """Even positions: first_letter, Odd positions: last_letter"""
    def __init__(self):
        super().__init__("alternating_first_last")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        if cipher_pos % 2 == 0:
            return word[0].upper()
        else:
            return word[-1].upper()


class CycleEvery5(Extractor):
    """Cycle through [1st, 2nd, 3rd, last, middle] every 5 positions"""
    def __init__(self):
        super().__init__("cycle_every_5")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        cycle_pos = cipher_pos % 5
        if cycle_pos == 0:
            return word[0].upper()
        elif cycle_pos == 1:
            return word[1].upper() if len(word) >= 2 else word[0].upper()
        elif cycle_pos == 2:
            return word[2].upper() if len(word) >= 3 else word[0].upper()
        elif cycle_pos == 3:
            return word[-1].upper()
        else:  # cycle_pos == 4
            mid = len(word) // 2
            return word[mid].upper()


class CycleEvery7(Extractor):
    """Cycle through 7 different extraction rules"""
    def __init__(self):
        super().__init__("cycle_every_7")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        cycle_pos = cipher_pos % 7
        # Safely handle different word lengths
        if cycle_pos == 0:
            return word[0].upper()
        elif cycle_pos == 1:
            return word[1].upper() if len(word) >= 2 else word[0].upper()
        elif cycle_pos == 2:
            return word[2].upper() if len(word) >= 3 else word[0].upper()
        elif cycle_pos == 3:
            return word[-1].upper()
        elif cycle_pos == 4:
            return word[len(word)//2].upper()
        elif cycle_pos == 5:
            return word[-2].upper() if len(word) >= 2 else word[0].upper()
        else:  # cycle_pos == 6
            return word[1].upper() if len(word) >= 2 else word[0].upper()


class ReversePosition(Extractor):
    """Extract at: word_length - (position mod word_length) - 1"""
    def __init__(self):
        super().__init__("reverse_position")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        forward_idx = cipher_pos % len(word)
        reverse_idx = len(word) - forward_idx - 1
        return word[reverse_idx].upper()


class PositionModOffset(Extractor):
    """Extract at: (position mod 335) mod word_length"""
    def __init__(self, offset_val: int = 335):
        super().__init__(f"position_mod_offset_{offset_val}")
        self.offset_val = offset_val
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        idx = (cipher_pos % self.offset_val) % len(word)
        return word[idx].upper()


# ============================================================================
# DOCUMENT-AWARE EXTRACTORS
# ============================================================================

class DocumentID(Extractor):
    """Extract document ID: V=VDR, D=DOI, S=Signers, A=Articles"""
    def __init__(self):
        super().__init__("document_id")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        return doc_source[0].upper()  # First letter of source


class DocumentFirstLetter(Extractor):
    """Extract first letter of document name"""
    def __init__(self):
        super().__init__("document_first_letter")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        # Map document sources to their full names
        doc_names = {
            'VDR': 'VIRGINIA',
            'DOI': 'DECLARATION',
            'SIGNERS': 'SIGNERS',
            'ARTICLES': 'ARTICLES'
        }
        name = doc_names.get(doc_source, 'UNKNOWN')
        return name[0]


# ============================================================================
# PHASE 5 ADVANCED EXTRACTORS
# ============================================================================

class GeneralizedPosition(Extractor):
    """Extract at position: (a*i + b) mod L"""
    def __init__(self, a: int, b: int):
        super().__init__(f"gen_pos_a{a}_b{b}")
        self.a = a
        self.b = b
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return "?"
        idx = (self.a * cipher_pos + self.b) % len(word)
        return word[idx].upper()


class CipherModulatedPosition(Extractor):
    """Extract at: (a*i + b + c*(cipher_number mod m)) mod L"""
    def __init__(self, a: int, b: int, c: int, m: int):
        super().__init__(f"cmod_a{a}_b{b}_c{c}_m{m}")
        self.a = a
        self.b = b
        self.c = c
        self.m = m
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        # word_idx is cipher_number - 1 in DOI context
        cipher_num = word_idx + 1
        if not word:
            return "?"
        idx = (self.a * cipher_pos + self.b + self.c * (cipher_num % self.m)) % len(word)
        return word[idx].upper()


class XORPosition(Extractor):
    """Position determined by: (i XOR cipher_number) mod L"""
    def __init__(self):
        super().__init__("xor_position")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        cipher_num = word_idx + 1
        if not word:
            return "?"
        idx = (cipher_pos ^ cipher_num) % len(word)
        return word[idx].upper()


class PopcountPosition(Extractor):
    """Position: (i + popcount(cipher_number)) mod L"""
    def __init__(self):
        super().__init__("popcount_position")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        cipher_num = word_idx + 1
        if not word:
            return "?"
        popcount = bin(cipher_num).count('1')
        idx = (cipher_pos + popcount) % len(word)
        return word[idx].upper()


class DigitSumPosition(Extractor):
    """Position: (i + digit_sum(cipher_number)) mod L"""
    def __init__(self):
        super().__init__("digitsum_position")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        cipher_num = word_idx + 1
        if not word:
            return "?"
        digit_sum = sum(int(d) for d in str(cipher_num))
        idx = (cipher_pos + digit_sum) % len(word)
        return word[idx].upper()


# ============================================================================
# PHASE 7 FEATURE-BASED EXTRACTORS
# ============================================================================

class LastVowelExtractor(Extractor):
    """Extract last vowel from word"""
    def __init__(self):
        super().__init__("last_vowel")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        vowels_found = []
        for c in word.lower():
            if c in 'aeiou':
                vowels_found.append(c)
        return vowels_found[-1].upper() if vowels_found else '?'


class LastConsonantExtractor(Extractor):
    """Extract last consonant from word"""
    def __init__(self):
        super().__init__("last_consonant")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        consonants = []
        for c in word.lower():
            if c.isalpha() and c not in 'aeiou':
                consonants.append(c)
        return consonants[-1].upper() if consonants else '?'


class DigraphIndexExtractor(Extractor):
    """Extract bigram at position-dependent index, return first char"""
    def __init__(self):
        super().__init__("digraph_index")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if len(word) < 2:
            return word[0].upper() if word else '?'
        idx = cipher_pos % (len(word) - 1)
        return word[idx].upper()


class LetterClassIndexExtractor(Extractor):
    """Map word to V/C pattern, then index into that"""
    def __init__(self):
        super().__init__("letter_class_index")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        # Build vowel/consonant pattern
        pattern_positions = []
        for i, c in enumerate(word):
            if c.isalpha():
                pattern_positions.append(i)
        
        if not pattern_positions:
            return '?'
        
        idx = cipher_pos % len(pattern_positions)
        actual_pos = pattern_positions[idx]
        return word[actual_pos].upper()


class VowelPositionExtractor(Extractor):
    """Extract vowel at position (cipher_pos mod vowel_count)"""
    def __init__(self):
        super().__init__("vowel_position")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        vowels = [c for c in word.lower() if c in 'aeiou']
        if not vowels:
            return '?'
        idx = cipher_pos % len(vowels)
        return vowels[idx].upper()


class ConsonantPositionExtractor(Extractor):
    """Extract consonant at position (cipher_pos mod consonant_count)"""
    def __init__(self):
        super().__init__("consonant_position")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        consonants = [c for c in word.lower() if c.isalpha() and c not in 'aeiou']
        if not consonants:
            return '?'
        idx = cipher_pos % len(consonants)
        return consonants[idx].upper()


class WordShapeExtractor(Extractor):
    """Extract based on word shape pattern"""
    def __init__(self):
        super().__init__("word_shape")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return '?'
        
        # Classify word shape: long/short, vowel-heavy/consonant-heavy
        vowels = sum(1 for c in word.lower() if c in 'aeiou')
        consonants = sum(1 for c in word.lower() if c.isalpha() and c not in 'aeiou')
        
        # Use shape to choose index
        if len(word) <= 3:  # Short word
            idx = 0
        elif vowels > consonants:  # Vowel-heavy
            idx = cipher_pos % len(word)
        else:  # Consonant-heavy
            idx = (cipher_pos * 2) % len(word)
        
        return word[idx].upper()


class AlternateVowelConsonant(Extractor):
    """Alternate between vowel and consonant extraction"""
    def __init__(self):
        super().__init__("alternate_vowel_consonant")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return '?'
        
        if cipher_pos % 2 == 0:
            # Extract vowel
            for c in word.lower():
                if c in 'aeiou':
                    return c.upper()
            return word[0].upper()
        else:
            # Extract consonant
            for c in word.lower():
                if c.isalpha() and c not in 'aeiou':
                    return c.upper()
            return word[0].upper()


class CipherProductMod(Extractor):
    """Use (cipher_num * position) to determine index"""
    def __init__(self):
        super().__init__("cipher_product_mod")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        cipher_num = word_idx + 1
        if not word:
            return '?'
        idx = (cipher_num * cipher_pos) % len(word)
        return word[idx].upper()


class WordLengthModulated(Extractor):
    """Position modulated by word length: (pos * word_len) mod word_len"""
    def __init__(self):
        super().__init__("wordlen_modulated")
    
    def extract(self, word: str, word_idx: int, cipher_pos: int, doc_source: str) -> str:
        if not word:
            return '?'
        wlen = len(word)
        idx = (cipher_pos * wlen) % wlen if wlen > 0 else 0
        return word[idx].upper()


# ============================================================================
# EXTRACTOR REGISTRY
# ============================================================================

# Generate Phase 5 extractor variants
def _generate_phase5_extractors():
    """Generate Phase 5 extractor family variants"""
    variants = []
    
    # Generalized position: a in {1,2,3,5,7}, b in {0,1,2,3,5}
    for a in [1, 2, 3, 5, 7]:
        for b in [0, 1, 2, 3, 5]:
            variants.append(GeneralizedPosition(a, b))
    
    # Cipher-modulated: a=1, b=0, c in {1,2}, m in {5,7}
    for c in [1, 2]:
        for m in [5, 7]:
            variants.append(CipherModulatedPosition(1, 0, c, m))
    
    # Mixed features
    variants.extend([
        XORPosition(),
        PopcountPosition(),
        DigitSumPosition()
    ])
    
    return variants


ALL_EXTRACTORS = [
    # Phase 1-2: Basic extractors
    FirstLetter(),
    SecondLetter(),
    ThirdLetter(),
    LastLetter(),
    MiddleLetter(),
    NthLetterByPosition(),
    WordLength(),
    VowelCount(),
    ConsonantCount(),
    FirstConsonant(),
    FirstVowel(),
    LetterAtCipherMod(),
    LetterAtIndexMod(),
    DocumentID(),
    DocumentFirstLetter(),
    # Phase 3: Advanced position-based variants
    PositionPlusOffset(335),
    PositionTimes2(),
    PositionTimes3(),
    AlternatingRule(),
    CycleEvery5(),
    CycleEvery7(),
    ReversePosition(),
    PositionModOffset(335),
] + _generate_phase5_extractors() + [  # Phase 5: 32 variants + Phase 7: 10 feature-based
    # Phase 7: Feature-based extractors
    LastVowelExtractor(),
    LastConsonantExtractor(),
    DigraphIndexExtractor(),
    LetterClassIndexExtractor(),
    VowelPositionExtractor(),
    ConsonantPositionExtractor(),
    WordShapeExtractor(),
    AlternateVowelConsonant(),
    CipherProductMod(),
    WordLengthModulated()
]


def get_extractor(name: str) -> Optional[Extractor]:
    """Get extractor by name"""
    for ext in ALL_EXTRACTORS:
        if ext.name == name:
            return ext
    return None


def list_extractors():
    """Print all available extractors"""
    print(f"Available extractors ({len(ALL_EXTRACTORS)} total):")
    print("\nLetter-based:")
    for ext in ALL_EXTRACTORS[:6]:
        print(f"  - {ext.name}")
    print("\nStructure-based:")
    for ext in ALL_EXTRACTORS[6:11]:
        print(f"  - {ext.name}")
    print("\nPosition-based (Phase 2):")
    for ext in ALL_EXTRACTORS[11:13]:
        print(f"  - {ext.name}")
    print("\nDocument-aware:")
    for ext in ALL_EXTRACTORS[13:15]:
        print(f"  - {ext.name}")
    print("\nAdvanced Position-based (Phase 3):")
    for ext in ALL_EXTRACTORS[15:23]:
        print(f"  - {ext.name}")
    print(f"\nPhase 5 Extractors ({len(ALL_EXTRACTORS[23:])} variants):")
    phase5_count = len(ALL_EXTRACTORS[23:])
    if phase5_count <= 10:
        for ext in ALL_EXTRACTORS[23:]:
            print(f"  - {ext.name}")
    else:
        for ext in ALL_EXTRACTORS[23:28]:
            print(f"  - {ext.name}")
        print(f"  ... and {phase5_count - 5} more")


if __name__ == "__main__":
    # Test the extractors
    print("=" * 70)
    print("EXTRACTOR MODULE TEST")
    print("=" * 70)
    
    list_extractors()
    
    # Test with sample word
    print("\n" + "=" * 70)
    print("Sample extractions from word 'CRYPTANALYSIS':")
    print("=" * 70)
    
    test_word = "cryptanalysis"
    for ext in ALL_EXTRACTORS:
        result = ext.extract(test_word, 42, 10, 'DOI')
        print(f"{ext.name:25s} -> {result}")
