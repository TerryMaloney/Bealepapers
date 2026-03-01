"""
PHASE 7 G1: DOI VARIANT GENERATOR
Generate multiple tokenization/normalization variants of the Declaration of Independence.
Book ciphers are fragile - small differences in tokenization can preserve signal while blocking readability.
"""

import re
import hashlib
from typing import List, Dict


def load_doi_raw():
    """Load raw DOI text from beale_papers.txt (line 55, without numbering)"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Line 55 contains numbered DOI
    doi_line = lines[54]
    
    # Extract text without numbers
    pattern = r'(\w+)\((\d+)\)'
    matches = re.findall(pattern, doi_line)
    
    # Reconstruct raw text in order
    words = []
    for word, num in matches:
        words.append(word)
    
    raw_text = ' '.join(words)
    return raw_text


class DOIVariantGenerator:
    """Generate DOI tokenization variants"""
    
    def __init__(self, source_text: str):
        self.source_text = source_text
    
    def _apply_rules(self, hyphen, apostrophe, punct, case, header):
        """Apply transformation rules to source text"""
        text = self.source_text
        
        # Case handling (do first)
        if case == 'lower':
            text = text.lower()
        # else: preserve case
        
        # Apostrophe handling
        if apostrophe == 'strip':
            # Remove apostrophes: "nature's" -> "natures"
            text = text.replace("'", "")
        # else: keep apostrophes
        
        # Hyphen handling (affects tokenization)
        if hyphen == 'split':
            # Replace hyphens with spaces: "self-evident" -> "self evident"
            text = text.replace("-", " ")
        # else: keep hyphens as part of words
        
        # Punctuation handling
        if punct == 'strict':
            # Remove all punctuation
            text = re.sub(r'[^\w\s-]', '', text)
        else:  # light
            # Keep some structure (periods, commas removed but preserve ampersand, etc.)
            text = re.sub(r'[.,;:!?"\(\)]', '', text)
        
        return text
    
    def _tokenize(self, text):
        """Tokenize text into word list"""
        # Split on whitespace and filter empty
        words = text.split()
        words = [w for w in words if w]  # Remove empty strings
        return words
    
    def _hash_variant(self, word_list):
        """Generate stable hash of word list"""
        combined = '|'.join(word_list)
        return hashlib.md5(combined.encode()).hexdigest()[:8]
    
    def generate_variants(self):
        """Generate all plausible DOI tokenization variants"""
        variants = []
        
        # Variant axes (keeping header fixed at 'exclude' since raw text doesn't have it)
        for hyphen in ['keep', 'split']:
            for apostrophe in ['keep', 'strip']:
                for punct in ['strict', 'light']:
                    for case in ['lower', 'preserve']:
                        # Apply rules
                        transformed_text = self._apply_rules(
                            hyphen, apostrophe, punct, case, 'exclude'
                        )
                        
                        # Tokenize
                        word_list = self._tokenize(transformed_text)
                        word_count = len(word_list)
                        
                        # Generate variant ID
                        variant_id = f"h{hyphen[0]}a{apostrophe[0]}p{punct[0]}c{case[0]}"
                        
                        variants.append({
                            'id': variant_id,
                            'rules': {
                                'hyphen': hyphen,
                                'apostrophe': apostrophe,
                                'punctuation': punct,
                                'case': case,
                                'header': 'exclude'
                            },
                            'word_list': word_list,
                            'word_count': word_count,
                            'hash': self._hash_variant(word_list)
                        })
        
        return variants


def test_variants():
    """Test DOI variant generation"""
    print("=" * 80)
    print("DOI VARIANT GENERATOR TEST")
    print("=" * 80)
    
    # Load raw DOI
    raw_doi = load_doi_raw()
    print(f"\nRaw DOI loaded: {len(raw_doi)} characters")
    print(f"First 100 chars: {raw_doi[:100]}")
    
    # Generate variants
    generator = DOIVariantGenerator(raw_doi)
    variants = generator.generate_variants()
    
    print(f"\nGenerated {len(variants)} variants")
    print("\nVariant details:")
    print("-" * 80)
    
    for i, variant in enumerate(variants, 1):
        print(f"{i:2d}. {variant['id']:8s} | Words: {variant['word_count']:4d} | Hash: {variant['hash']}")
        
        # Show sample words for first few
        if i <= 3:
            sample = ' '.join(variant['word_list'][:20])
            print(f"    Sample: {sample}...")
    
    # Compare word counts
    counts = [v['word_count'] for v in variants]
    print(f"\nWord count range: {min(counts)} - {max(counts)}")
    print(f"Unique counts: {len(set(counts))}")
    
    # Show variants with different word counts
    print("\nWord count distribution:")
    count_dist = {}
    for v in variants:
        count = v['word_count']
        if count not in count_dist:
            count_dist[count] = []
        count_dist[count].append(v['id'])
    
    for count in sorted(count_dist.keys()):
        ids = count_dist[count]
        print(f"  {count:4d} words: {', '.join(ids)}")
    
    return variants


if __name__ == "__main__":
    variants = test_variants()
    
    print("\n" + "=" * 80)
    print("DOI VARIANT GENERATOR READY")
    print("=" * 80)
    print(f"\nGenerated {len(variants)} variants for Cipher 2 oracle testing.")
