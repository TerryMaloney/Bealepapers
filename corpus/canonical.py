"""
Canonical Corpus Manager - Lock validated DOI edition with full provenance.

After oracle passes (alignment >= 89.5% or strict >= 90%), this locks the
corpus as immutable ground truth.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass, asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry


@dataclass
class CanonicalCorpusMetadata:
    """Metadata for locked canonical corpus."""
    edition_id: str
    tokenizer_name: str
    word_count: int
    oracle_score: float
    drift_model: Optional[str]
    locked_date: str
    hash: str
    version: str = "1.0"
    notes: str = ""
    oracle_alignment_pct: float = 0.0
    cipher2_validated: bool = False


class CanonicalCorpus:
    """Locked, immutable corpus post-oracle validation."""
    
    def __init__(self, edition_id: str, tokenizer_name: str, 
                 drift_model=None, oracle_score: float = 0.0):
        """
        Initialize canonical corpus from validated edition + tokenizer.
        
        Args:
            edition_id: DOI edition identifier
            tokenizer_name: Tokenizer preset name
            drift_model: Optional drift model instance
            oracle_score: Cipher 2 oracle match percentage
        """
        # Load edition
        loader = DOICorpusLoader()
        self.edition = loader.load_edition(edition_id)
        
        # Load tokenizer
        self.tokenizer = TokenizerRegistry.get_tokenizer(tokenizer_name)
        
        # Tokenize
        self.tokens = self.tokenizer.tokenize(self.edition.source_text)
        
        # Apply drift model if provided
        if drift_model:
            self.tokens = drift_model.apply(self.tokens)
        
        # Create metadata
        self.metadata = CanonicalCorpusMetadata(
            edition_id=edition_id,
            tokenizer_name=tokenizer_name,
            word_count=len(self.tokens),
            oracle_score=oracle_score,
            drift_model=drift_model.__class__.__name__ if drift_model else None,
            locked_date=datetime.now().isoformat(),
            hash=self._hash_corpus(self.tokens)
        )
    
    def _hash_corpus(self, tokens: List[str]) -> str:
        """Generate SHA256 hash of token list."""
        content = '|'.join(tokens).encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    def get_word(self, cipher_number: int) -> Optional[str]:
        """
        Get word by cipher number (1-indexed).
        
        Args:
            cipher_number: Cipher number (1-indexed)
        
        Returns:
            Word string or None if out of range
        """
        idx = cipher_number - 1
        if 0 <= idx < len(self.tokens):
            return self.tokens[idx]
        return None
    
    def get_word_safe(self, cipher_number: int, default: str = '?') -> str:
        """Get word with default fallback for out-of-range numbers."""
        word = self.get_word(cipher_number)
        return word if word is not None else default
    
    def decode_with_extractor(self, cipher_numbers: List[int], extractor) -> str:
        """
        Decode cipher numbers using provided extractor.
        
        Args:
            cipher_numbers: List of cipher numbers
            extractor: Extractor instance with extract(word, word_idx, cipher_pos, doc_source) method
        
        Returns:
            Decoded string
        """
        decoded = []
        for cipher_pos, cipher_num in enumerate(cipher_numbers):
            word = self.get_word(cipher_num)
            if word:
                try:
                    letter = extractor.extract(word, cipher_num - 1, cipher_pos, 'DOI')
                    decoded.append(letter if letter else '?')
                except Exception as e:
                    decoded.append('?')
            else:
                decoded.append('?')
        
        return ''.join(decoded)
    
    def save(self, path: str = 'corpus/CANON_DOI.json'):
        """
        Save locked corpus with full metadata.
        
        Args:
            path: Output path for JSON file
        """
        output = {
            'metadata': asdict(self.metadata),
            'tokens': self.tokens
        }
        
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
        
        print(f"Canonical corpus saved: {output_path}")
        print(f"  Edition: {self.metadata.edition_id}")
        print(f"  Tokenizer: {self.metadata.tokenizer_name}")
        print(f"  Words: {self.metadata.word_count}")
        print(f"  Oracle strict: {self.metadata.oracle_score:.2f}%")
        print(f"  Oracle alignment: {self.metadata.oracle_alignment_pct:.2f}%")
        print(f"  Cipher 2 validated: {self.metadata.cipher2_validated}")
        print(f"  Hash: {self.metadata.hash[:16]}...")
    
    @classmethod
    def load(cls, path: str = 'corpus/CANON_DOI.json') -> 'CanonicalCorpus':
        """
        Load locked corpus from JSON file.
        
        Args:
            path: Path to locked corpus JSON
        
        Returns:
            CanonicalCorpus instance
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create instance (without loading from source again)
        instance = cls.__new__(cls)
        instance.tokens = data['tokens']
        
        # Reconstruct metadata (backwards-compatible with older locks)
        metadata_dict = data['metadata']
        metadata_dict.setdefault('oracle_alignment_pct', 0.0)
        metadata_dict.setdefault('cipher2_validated', False)
        instance.metadata = CanonicalCorpusMetadata(**metadata_dict)
        
        # Verify hash
        computed_hash = instance._hash_corpus(instance.tokens)
        if computed_hash != instance.metadata.hash:
            print(f"WARNING: Hash mismatch!")
            print(f"  Stored: {instance.metadata.hash}")
            print(f"  Computed: {computed_hash}")
        
        return instance
    
    def __repr__(self):
        return (f"CanonicalCorpus(edition='{self.metadata.edition_id}', "
                f"tokenizer='{self.metadata.tokenizer_name}', "
                f"words={self.metadata.word_count}, "
                f"oracle={self.metadata.oracle_score:.2f}%)")


def lock_corpus_from_oracle_result(edition_id: str, tokenizer_name: str,
                                   oracle_score: float, drift_model=None,
                                   oracle_alignment_pct: float = 0.0) -> CanonicalCorpus:
    """
    Helper to lock corpus after oracle passes.
    
    Args:
        edition_id: Validated edition ID
        tokenizer_name: Validated tokenizer name
        oracle_score: Oracle strict match percentage
        drift_model: Optional drift model instance
        oracle_alignment_pct: Alignment-based (LCS) match percentage
    
    Returns:
        CanonicalCorpus instance
    """
    print("=" * 80)
    print("LOCKING CANONICAL CORPUS")
    print("=" * 80)
    
    print(f"\nEdition: {edition_id}")
    print(f"Tokenizer: {tokenizer_name}")
    print(f"Oracle score (strict): {oracle_score:.2f}%")
    print(f"Oracle score (alignment): {oracle_alignment_pct:.2f}%")
    if drift_model:
        print(f"Drift model: {drift_model.__class__.__name__}")
    
    # Determine validation status
    cipher2_validated = oracle_alignment_pct >= 89.5 or oracle_score >= 90.0
    
    corpus = CanonicalCorpus(edition_id, tokenizer_name, drift_model, oracle_score)
    corpus.metadata.oracle_alignment_pct = oracle_alignment_pct
    corpus.metadata.cipher2_validated = cipher2_validated
    
    print(f"\nCorpus locked:")
    print(f"  {len(corpus.tokens)} words")
    print(f"  Hash: {corpus.metadata.hash}")
    print(f"  Cipher 2 validated: {cipher2_validated}")
    
    corpus.save()
    
    print("\n" + "=" * 80)
    print("CORPUS LOCKED SUCCESSFULLY")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. python run_pipeline.py search_concurrent --topk 2000")
    print("  2. python run_pipeline.py decode_cipher --cipher 1 --topk 50")
    print("  3. python run_pipeline.py decode_cipher --cipher 3 --topk 50")
    
    return corpus


def test_canonical_corpus():
    """Test canonical corpus save/load."""
    print("=" * 80)
    print("CANONICAL CORPUS TEST")
    print("=" * 80)
    
    # Create test corpus
    print("\n[1] Creating canonical corpus...")
    corpus = CanonicalCorpus(
        edition_id="beale_embedded",
        tokenizer_name="hyphen_keep",
        drift_model=None,
        oracle_score=26.50
    )
    
    print(f"\nCreated: {corpus}")
    print(f"First 10 words: {corpus.tokens[:10]}")
    
    # Test word retrieval
    print("\n[2] Testing word retrieval...")
    for num in [1, 100, 500, 1000, 1322, 1500]:
        word = corpus.get_word(num)
        print(f"  Word {num:4d}: {word if word else '[OUT OF RANGE]'}")
    
    # Save
    print("\n[3] Saving corpus...")
    test_path = "corpus/TEST_CANON.json"
    corpus.save(test_path)
    
    # Load
    print("\n[4] Loading corpus...")
    loaded = CanonicalCorpus.load(test_path)
    print(f"Loaded: {loaded}")
    
    # Verify
    print("\n[5] Verifying integrity...")
    if loaded.tokens == corpus.tokens:
        print("  [OK] Tokens match")
    else:
        print("  [ERROR] Tokens mismatch!")
    
    if loaded.metadata.hash == corpus.metadata.hash:
        print("  [OK] Hash matches")
    else:
        print("  [ERROR] Hash mismatch!")
    
    print("\n" + "=" * 80)
    print("CANONICAL CORPUS TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_canonical_corpus()
