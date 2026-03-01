"""
Cipher 2 Oracle Evaluator - Validates DOI editions against known plaintext.

Uses Cipher 2's known plaintext as ground truth to test DOI editions.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Callable, Tuple, Dict, Optional, Union


@dataclass
class OracleResult:
    """Result of oracle evaluation with detailed per-position tracking."""
    char_match_pct: float
    word_match_pct: float
    char_matches: int
    total_chars: int
    first_mismatch: int
    diff_report: str
    decoded_sample: str
    # Per-position tracking for diagnostic analysis
    mismatch_positions: List[int] = field(default_factory=list)
    mismatch_details: List[Dict] = field(default_factory=list)
    match_by_region: Dict[str, float] = field(default_factory=dict)
    drift_coefficient: float = 0.0
    # Alignment-based score (tolerates insertions/deletions; robust to length shifts)
    alignment_pct: float = 0.0

    def __repr__(self):
        return f"OracleResult(char={self.char_match_pct:.2f}%, align={self.alignment_pct:.2f}%, mismatch@{self.first_mismatch})"


class Cipher2Oracle:
    """Evaluates DOI token lists against Cipher 2 known plaintext."""
    
    def __init__(self, known_plaintext: str):
        self.known_plaintext = known_plaintext
        self.known_clean = self._clean_plaintext(known_plaintext)
    
    def _clean_plaintext(self, text: str) -> str:
        """Clean plaintext to letters only (uppercase). Used for oracle comparison."""
        return ''.join(c.upper() for c in text if c.isalpha())
    
    # Beale pamphlet letter overrides (cipher_num 1-indexed -> letter)
    # Word 95: unalienable/inalienable -> u
    BEALE_LETTER_OVERRIDES = {95: 'u', 811: 'y', 1005: 'x'}

    def evaluate(self, doi_tokens: List[str], cipher2_numbers: List[int],
                 extraction_rule: Callable = None,
                 letter_overrides: Optional[Dict[int, str]] = None) -> OracleResult:
        """
        Evaluate a DOI token list against Cipher 2.
        
        Args:
            doi_tokens: List of DOI words (1-indexed via cipher numbers)
            cipher2_numbers: Cipher 2 number sequence
            extraction_rule: Function(word, cipher_num) -> letter
                            Default: first letter of word
            letter_overrides: Optional dict mapping cipher_num -> letter
                            (e.g. Beale 811->y, 1005->x). Checked before extraction_rule.
        
        Returns:
            OracleResult with match statistics
        """
        
        if extraction_rule is None:
            extraction_rule = lambda word, n: word[0].upper() if word else '?'
        
        if letter_overrides:
            _base = extraction_rule
            def _with_overrides(word: str, cipher_num: int):
                if cipher_num in letter_overrides:
                    return letter_overrides[cipher_num]
                return _base(word, cipher_num)
            extraction_rule = _with_overrides
        
        # Decode Cipher 2 using DOI tokens.
        # extraction_rule should return single letters (A-Z) or '?'; decoded_str is
        # compared position-by-position to known_clean (letters only, uppercase).
        decoded = []
        for cipher_num in cipher2_numbers:
            word_idx = cipher_num - 1
            
            if 0 <= word_idx < len(doi_tokens):
                word = doi_tokens[word_idx]
                if word:
                    try:
                        letter = extraction_rule(word, cipher_num)
                        decoded.append(letter if letter else '?')
                    except:
                        decoded.append('?')
                else:
                    decoded.append('?')
            else:
                decoded.append('?')
        
        decoded_str = ''.join(decoded)
        
        # Character-by-character match
        char_matches = 0
        total_chars = min(len(decoded_str), len(self.known_clean))
        
        # NEW: Track ALL mismatches for diagnostic analysis
        mismatch_positions = []
        mismatch_details = []
        first_mismatch = -1
        
        for i, (d, k) in enumerate(zip(decoded_str, self.known_clean)):
            if d == k:
                char_matches += 1
            else:
                mismatch_positions.append(i)
                
                # Record detailed mismatch info
                cipher_num = cipher2_numbers[i] if i < len(cipher2_numbers) else None
                word = None
                if cipher_num and 0 <= cipher_num - 1 < len(doi_tokens):
                    word = doi_tokens[cipher_num - 1]
                
                mismatch_details.append({
                    'position': i,
                    'decoded': d,
                    'expected': k,
                    'cipher_num': cipher_num,
                    'word': word
                })
                
                # Track first mismatch
                if first_mismatch == -1:
                    first_mismatch = i
        
        char_match_pct = (char_matches / total_chars * 100) if total_chars > 0 else 0.0

        # Alignment-based score (LCS; tolerates insertions/deletions)
        alignment_pct = self._compute_alignment_pct(decoded_str, self.known_clean)
        
        # Word-level match
        word_match_pct = self._compute_word_match(decoded_str, self.known_clean)
        
        # NEW: Compute regional match rates
        match_by_region = self._compute_regional_matches(decoded_str, self.known_clean)
        
        # NEW: Detect drift pattern
        drift_coefficient = self._compute_drift(mismatch_positions, len(decoded_str))
        
        # Generate diff report
        diff_report = self._generate_diff(decoded_str, self.known_clean, first_mismatch)
        
        return OracleResult(
            char_match_pct=char_match_pct,
            word_match_pct=word_match_pct,
            char_matches=char_matches,
            alignment_pct=alignment_pct,
            total_chars=total_chars,
            first_mismatch=first_mismatch,
            diff_report=diff_report,
            decoded_sample=decoded_str[:200],
            mismatch_positions=mismatch_positions,
            mismatch_details=mismatch_details,
            match_by_region=match_by_region,
            drift_coefficient=drift_coefficient
        )
    
    def _compute_alignment_pct(self, decoded: str, known: str) -> float:
        """
        Compute alignment-based match percentage using LCS.
        Tolerates insertions/deletions; robust to single length-shift errors.
        """
        if not decoded or not known:
            return 0.0
        m, n = len(decoded), len(known)
        # LCS via DP
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if decoded[i - 1] == known[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        lcs_len = dp[m][n]
        # Normalize by reference length (known)
        return (lcs_len / n * 100) if n > 0 else 0.0

    def _compute_word_match(self, decoded: str, known: str) -> float:
        """Compute word-level match percentage."""
        # Split known plaintext into words (by extracting from original)
        words_in_known = []
        current_word = ""
        for c in self.known_plaintext:
            if c.isalpha():
                current_word += c.upper()
            elif current_word:
                words_in_known.append(current_word)
                current_word = ""
        if current_word:
            words_in_known.append(current_word)
        
        # Search for each known word in decoded
        matches = 0
        for word in words_in_known:
            if word in decoded:
                matches += 1
        
        return (matches / len(words_in_known) * 100) if words_in_known else 0.0
    
    def _generate_diff(self, decoded: str, known: str, first_mismatch: int) -> str:
        """Generate diff report around first mismatch."""
        if first_mismatch < 0:
            return "PERFECT MATCH"
        
        # Show context around mismatch
        start = max(0, first_mismatch - 20)
        end = min(len(decoded), first_mismatch + 21)
        
        decoded_context = decoded[start:end]
        known_context = known[start:end]
        
        # Build visual diff
        diff_lines = []
        diff_lines.append(f"Position {first_mismatch}:")
        diff_lines.append(f"  Decoded: ...{decoded_context}...")
        diff_lines.append(f"  Known:   ...{known_context}...")
        diff_lines.append(f"            {' ' * (first_mismatch - start + 3)}^")
        
        return '\n'.join(diff_lines)
    
    def _compute_regional_matches(self, decoded: str, known: str) -> Dict[str, float]:
        """
        Compute match percentage by document region.
        
        Divides document into early/middle/late thirds to detect
        if mismatch rate changes across the document.
        """
        total_len = min(len(decoded), len(known))
        if total_len == 0:
            return {'early': 0.0, 'middle': 0.0, 'late': 0.0}
        
        third = total_len // 3
        
        regions = {
            'early': (0, third),
            'middle': (third, 2 * third),
            'late': (2 * third, total_len)
        }
        
        match_by_region = {}
        
        for region_name, (start, end) in regions.items():
            if start >= end:
                match_by_region[region_name] = 0.0
                continue
            
            matches = sum(1 for i in range(start, end) 
                         if i < len(decoded) and i < len(known) and decoded[i] == known[i])
            region_len = end - start
            match_by_region[region_name] = (matches / region_len * 100) if region_len > 0 else 0.0
        
        return match_by_region
    
    def _compute_drift(self, mismatch_positions: List[int], total_length: int) -> float:
        """
        Compute drift coefficient (linear fit of mismatch rate vs position).
        
        Returns:
            Positive coefficient indicates error rate increases with position.
            Negative coefficient indicates error rate decreases.
            Near-zero indicates random/uniform distribution.
        """
        if len(mismatch_positions) < 2 or total_length == 0:
            return 0.0
        
        # Normalize positions to [0, 1]
        normalized_positions = [pos / total_length for pos in mismatch_positions]
        
        # Simple linear regression: y = mx + b
        # where y = 1 (constant, all positions are mismatches)
        # and x = normalized position
        n = len(normalized_positions)
        sum_x = sum(normalized_positions)
        sum_x2 = sum(x * x for x in normalized_positions)
        
        # Compute expected position if uniform
        expected_mean = 0.5
        actual_mean = sum_x / n if n > 0 else 0.5
        
        # Drift coefficient: difference from expected
        # Positive = mismatches concentrate later in document
        # Negative = mismatches concentrate earlier
        drift_coefficient = (actual_mean - expected_mean) * 2.0  # Scale to [-1, 1]
        
        return drift_coefficient


def _parse_cipher2_line(text: str) -> List[int]:
    """Parse a comma-separated line of cipher numbers."""
    return [int(n.strip()) for n in text.split(",") if n.strip()]


def load_cipher2(path: Optional[Union[str, Path]] = None) -> List[int]:
    """
    Load Cipher 2 numbers. Uses canonical file when available.

    Args:
        path: If None, loads from corpus/cipher2_numbers_canonical.txt when it exists,
              else falls back to beale_papers.txt line 59. If provided, loads from that file.

    Returns:
        List of cipher numbers (integers).
    """
    if path is not None:
        filepath = Path(path)
    else:
        canonical = Path("corpus/cipher2_numbers_canonical.txt")
        if canonical.exists():
            filepath = canonical
        else:
            filepath = Path("beale_papers.txt")

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if filepath.name == "cipher2_numbers_canonical.txt":
        # Canonical file: skip comment lines, parse first data line
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                return _parse_cipher2_line(line)
        return []

    if "beale_papers" in str(filepath):
        # beale_papers.txt: line 59 (index 58) contains Cipher 2
        cipher2_line = lines[58].strip()
        return _parse_cipher2_line(cipher2_line)

    # Generic: concatenate non-comment lines and parse
    data = "".join(
        line for line in lines if line.strip() and not line.strip().startswith("#")
    )
    return _parse_cipher2_line(data) if data else []


def load_cipher2_known_plaintext():
    """Load Cipher 2 known plaintext from beale_papers.txt."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Lines 63, 65, 67 (indices 62, 64, 66) contain the known plaintext paragraphs
    plaintext_parts = []
    for line_idx in [62, 64, 66]:
        if line_idx < len(lines):
            plaintext_parts.append(lines[line_idx].strip())
    
    return ' '.join(plaintext_parts)


def test_cipher2_oracle():
    """Test Cipher 2 oracle evaluator."""
    print("=" * 80)
    print("CIPHER 2 ORACLE EVALUATOR TEST")
    print("=" * 80)
    
    # Load data
    print("\n[Step 1] Loading Cipher 2 and known plaintext...")
    cipher2 = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    print(f"Cipher 2: {len(cipher2)} numbers")
    print(f"Known plaintext: {len(known_plaintext)} chars")
    print(f"Sample: {known_plaintext[:100]}...")
    
    # Load test DOI
    print("\n[Step 2] Loading beale_embedded DOI...")
    import sys
    sys.path.insert(0, '..')
    from corpus.doi_editions import DOICorpusLoader
    from corpus.tokenizers import TokenizerRegistry
    
    loader = DOICorpusLoader()
    doi_edition = loader.load_edition("beale_embedded")
    
    # Test with different tokenizers
    print("\n[Step 3] Testing oracle with different tokenizers...")
    print("-" * 80)
    
    oracle = Cipher2Oracle(known_plaintext)
    tokenizers = TokenizerRegistry.get_all_tokenizers()
    
    results = []
    for tokenizer in tokenizers:
        tokens = tokenizer.tokenize(doi_edition.source_text)
        result = oracle.evaluate(tokens, cipher2)
        results.append((tokenizer.name, result))
        
        print(f"{tokenizer.name:20s} | {result.char_match_pct:6.2f}% | Words: {len(tokens):4d}")
    
    # Show best result details
    print("\n" + "=" * 80)
    print("BEST RESULT DETAILS")
    print("=" * 80)
    
    best_name, best_result = max(results, key=lambda x: x[1].char_match_pct)
    print(f"\nBest tokenizer: {best_name}")
    print(f"Character match: {best_result.char_match_pct:.2f}% ({best_result.char_matches}/{best_result.total_chars})")
    print(f"Word match: {best_result.word_match_pct:.2f}%")
    print(f"\n{best_result.diff_report}")
    print(f"\nDecoded sample (first 200 chars):")
    print(f"  {best_result.decoded_sample}")
    
    print("\n" + "=" * 80)
    print("ORACLE EVALUATOR TEST COMPLETE")
    print("=" * 80)
    
    if best_result.char_match_pct >= 90.0:
        print("\nGO: Oracle passed with ≥90% match!")
    elif best_result.char_match_pct >= 50.0:
        print("\nCAUTION: Moderate match. Consider historical editions.")
    else:
        print("\nNO-GO: Poor match. Historical editions or drift models needed.")
    
    return results


if __name__ == "__main__":
    test_cipher2_oracle()
