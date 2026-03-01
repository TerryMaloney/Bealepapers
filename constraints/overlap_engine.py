"""
Phase C: Cross-Cipher Constraint Engine

Derives hard constraints from overlapping cipher numbers across Cipher 1, 2, 3.
Uses Cipher 2 oracle (known plaintext) to filter strategies for Cipher 1 and 3.
"""

from typing import List, Dict, Set, Tuple
from pathlib import Path
import sys
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.canonical import CanonicalCorpus


def load_cipher(cipher_num: int) -> List[int]:
    """Load cipher numbers from canonical file (if available) or beale_papers.txt."""
    canonical_path = Path(f"corpus/cipher{cipher_num}_numbers_canonical.txt")
    if canonical_path.exists():
        with open(canonical_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                return [int(n.strip()) for n in line.split(",")
                        if n.strip().replace(".", "").isdigit()]
    # Fallback
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    line_map = {1: 2, 2: 58, 3: 6}
    cipher_line = lines[line_map[cipher_num]].strip()
    return [int(n.strip()) for n in cipher_line.split(",") if n.strip()]


def load_cipher2_known_plaintext() -> str:
    """Load Cipher 2 known plaintext."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    plaintext_parts = []
    for line_idx in [62, 64, 66]:
        if line_idx < len(lines):
            plaintext_parts.append(lines[line_idx].strip())
    
    return ' '.join(plaintext_parts)


class CrossCipherConstraints:
    """Derives and applies cross-cipher constraints."""
    
    def __init__(self, corpus: CanonicalCorpus):
        self.corpus = corpus
        self.cipher1 = load_cipher(1)
        self.cipher2 = load_cipher(2)
        self.cipher3 = load_cipher(3)
        
        # Compute overlap sets
        self.overlaps_12 = set(self.cipher1) & set(self.cipher2)
        self.overlaps_13 = set(self.cipher1) & set(self.cipher3)
        self.overlaps_23 = set(self.cipher2) & set(self.cipher3)
        self.overlaps_all = self.overlaps_12 & set(self.cipher3)
        
        print(f"Cross-cipher overlaps:")
        print(f"  Cipher 1 & 2: {len(self.overlaps_12)} numbers")
        print(f"  Cipher 1 & 3: {len(self.overlaps_13)} numbers")
        print(f"  Cipher 2 & 3: {len(self.overlaps_23)} numbers")
        print(f"  All three:    {len(self.overlaps_all)} numbers")
    
    def derive_cipher2_oracle_constraints(self) -> Dict[int, Dict]:
        """
        Derive constraints from Cipher 2 validated extraction rule.
        
        For each cipher number in overlap_12 (appears in both Cipher 1 and 2):
        - The validated extraction for Cipher 2 is first-letter of DOI word.
        - The oracle letter is therefore word[0].upper() — derived directly
          from the corpus, NOT from strict-positional known_clean indexing
          (which suffers from stream drift).
        - Constraint: any extractor applied to Cipher 1 must also produce
          this letter for the same cipher number.
        
        Returns:
            Dict mapping cipher_number -> constraint info
        """
        constraints = {}
        
        for cipher_num in self.overlaps_12:
            word = self.corpus.get_word(cipher_num)
            if not word:
                continue
            
            # Oracle letter: first letter of DOI word (validated extraction rule)
            oracle_letter = word[0].upper()
            
            # Find positions in Cipher 1 and Cipher 2 (for diagnostics)
            c1_positions = [i for i, n in enumerate(self.cipher1) if n == cipher_num]
            c2_positions = [i for i, n in enumerate(self.cipher2) if n == cipher_num]
            
            constraints[cipher_num] = {
                'word': word,
                'oracle_letters': [oracle_letter],
                'c1_positions': c1_positions,
                'c2_positions': c2_positions
            }
        
        return constraints
    
    def validate_strategy(self, extractor, transposition, constraints: Dict) -> Tuple[bool, float]:
        """
        Check if strategy violates oracle constraints.
        
        Args:
            extractor: Extractor instance
            transposition: Transposition instance (not used for pre-transposition check)
            constraints: Constraints dict from derive_cipher2_oracle_constraints
        
        Returns:
            (passes, violation_rate) - passes=True if violation_rate < threshold
        """
        violations = 0
        total_checks = 0
        
        for cipher_num, info in constraints.items():
            word = info['word']
            oracle_letters = info['oracle_letters']
            c1_positions = info['c1_positions']
            
            if not word or not oracle_letters:
                continue
            
            # Extract letter at each Cipher 1 position
            for pos in c1_positions:
                try:
                    extracted = extractor.extract(word, cipher_num - 1, pos, 'DOI')
                    if extracted:
                        # Check if matches ANY oracle letter
                        if extracted.upper() not in oracle_letters:
                            violations += 1
                        total_checks += 1
                except:
                    pass
        
        violation_rate = violations / total_checks if total_checks > 0 else 0.0
        passes = violation_rate < 0.5  # Allow some tolerance
        
        return passes, violation_rate
    
    def save_constraints(self, output_path: str = "output/cross_cipher_constraints/constraints.json"):
        """Save constraints to file."""
        constraints = self.derive_cipher2_oracle_constraints()
        
        # Convert to serializable format
        output_data = {
            'metadata': {
                'generated': datetime.now().isoformat(),
                'corpus': str(self.corpus),
                'overlaps': {
                    'cipher_1_2': len(self.overlaps_12),
                    'cipher_1_3': len(self.overlaps_13),
                    'cipher_2_3': len(self.overlaps_23),
                    'all_three': len(self.overlaps_all)
                }
            },
            'constraints': constraints
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"\nConstraints saved: {output_path}")
        print(f"  Total constraints: {len(constraints)}")


def generate_cross_cipher_constraints():
    """Main function to generate cross-cipher constraints."""
    print("=" * 80)
    print("PHASE C: CROSS-CIPHER CONSTRAINTS")
    print("=" * 80)
    
    # Load corpus
    print("\n[Step 1] Loading CANON_DOI...")
    try:
        corpus = CanonicalCorpus.load('corpus/CANON_DOI.json')
        print(f"Loaded: {corpus}")
    except FileNotFoundError:
        print("[ERROR] CANON_DOI.json not found")
        print("ACTION: Run 'python run_pipeline.py lock_corpus' first")
        return None
    
    # Create constraints
    print("\n[Step 2] Computing cross-cipher overlaps...")
    constraints_engine = CrossCipherConstraints(corpus)
    
    # Derive oracle constraints
    print("\n[Step 3] Deriving Cipher 2 oracle constraints...")
    constraints = constraints_engine.derive_cipher2_oracle_constraints()
    print(f"Derived {len(constraints)} constraints from Cipher 1-2 overlaps")
    
    # Save
    print("\n[Step 4] Saving constraints...")
    constraints_engine.save_constraints()
    
    print("\n" + "=" * 80)
    print("CROSS-CIPHER CONSTRAINTS COMPLETE")
    print("=" * 80)
    
    print(f"\nSummary:")
    print(f"  Cipher 1-2 overlap: {len(constraints_engine.overlaps_12)} numbers")
    print(f"  Constraints derived: {len(constraints)}")
    print(f"  Use these to filter Cipher 1 strategies in Phase D")
    
    return constraints_engine


if __name__ == "__main__":
    generate_cross_cipher_constraints()
