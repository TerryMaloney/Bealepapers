"""
Phase A2: Drift Models - Systematic numbering shift models for printing artifacts.

Models printing layout effects that could cause numbering drift in 19th century texts.
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import Cipher2Oracle, load_cipher2, load_cipher2_known_plaintext


@dataclass
class DriftModelResult:
    """Result of drift model application."""
    model_name: str
    parameters: Dict
    adjusted_tokens: List[str]
    oracle_score: float
    word_count: int


class ProgressiveDriftModel:
    """Model progressive offset that increases linearly through text."""
    
    def __init__(self, drift_rate: float = 0.001):
        """
        Args:
            drift_rate: Offset accumulation rate per word position
        """
        self.drift_rate = drift_rate
        self.name = f"progressive_drift_rate_{drift_rate:.4f}"
    
    def apply(self, tokens: List[str]) -> List[str]:
        """
        Apply progressive drift to token list.
        Creates shifted indexing: position i maps to token at i + floor(i * drift_rate)
        """
        adjusted = []
        for i in range(len(tokens)):
            offset = int(i * self.drift_rate)
            adjusted_idx = i + offset
            if adjusted_idx < len(tokens):
                adjusted.append(tokens[adjusted_idx])
            else:
                adjusted.append(tokens[i % len(tokens)])  # Wrap around
        
        return adjusted


class PeriodicHeadingModel:
    """Model periodic heading insertion (some words counted, some skipped)."""
    
    def __init__(self, period: int = 100, heading_words: int = 2):
        """
        Args:
            period: Insert heading every N words
            heading_words: Number of heading words to skip
        """
        self.period = period
        self.heading_words = heading_words
        self.name = f"periodic_heading_p{period}_h{heading_words}"
    
    def apply(self, tokens: List[str]) -> List[str]:
        """
        Apply periodic heading skip to token list.
        Every 'period' words, skip 'heading_words' in cipher number mapping.
        """
        adjusted = []
        token_idx = 0
        
        for cipher_idx in range(len(tokens)):
            # Check if we're at a heading boundary
            if cipher_idx > 0 and cipher_idx % self.period == 0:
                token_idx += self.heading_words  # Skip heading words
            
            if token_idx < len(tokens):
                adjusted.append(tokens[token_idx])
                token_idx += 1
            else:
                # Ran out of tokens
                adjusted.append('?')
        
        return adjusted


class LineWrapModel:
    """Model line-wrap artifact where first word of each line is counted twice."""
    
    def __init__(self, words_per_line: int = 12):
        """
        Args:
            words_per_line: Average words per printed line
        """
        self.words_per_line = words_per_line
        self.name = f"linewrap_wpl{words_per_line}"
    
    def apply(self, tokens: List[str]) -> List[str]:
        """
        Apply line-wrap double-counting.
        First word of each line gets counted twice in numbering.
        """
        adjusted = []
        token_idx = 0
        
        for cipher_idx in range(len(tokens)):
            # Check if we're at line start
            if cipher_idx > 0 and cipher_idx % self.words_per_line == 0:
                # Repeat previous word (line-start double count)
                if adjusted:
                    adjusted.append(adjusted[-1])
                    continue
            
            if token_idx < len(tokens):
                adjusted.append(tokens[token_idx])
                token_idx += 1
            else:
                adjusted.append('?')
        
        return adjusted


class ColumnNumberingModel:
    """Model column-based numbering (number down columns, not across rows)."""
    
    def __init__(self, words_per_column: int = 50, columns: int = 2):
        """
        Args:
            words_per_column: Words per column
            columns: Number of columns
        """
        self.words_per_column = words_per_column
        self.columns = columns
        self.name = f"column_wpc{words_per_column}_c{columns}"
    
    def apply(self, tokens: List[str]) -> List[str]:
        """
        Apply column-based renumbering.
        Original: numbered across rows (1,2,3,4...)
        Column model: numbered down columns (1...50, then 51...100)
        """
        if not tokens:
            return tokens
        
        # Simulate column layout
        total_words = len(tokens)
        rows = (total_words + self.columns - 1) // self.columns
        
        # Build column-ordered index
        adjusted = []
        for row in range(rows):
            for col in range(self.columns):
                idx = col * rows + row
                if idx < len(tokens):
                    adjusted.append(tokens[idx])
                else:
                    adjusted.append('?')
        
        return adjusted


def fit_drift_model_to_oracle(tokens: List[str], cipher2_numbers: List[int],
                               known_plaintext: str) -> Tuple[Optional[DriftModelResult], List[DriftModelResult]]:
    """
    Test multiple drift models and find best fit for Cipher 2 oracle.
    
    Returns:
        best_result: Best drift model result
        all_results: All results sorted by oracle score
    """
    print("=" * 80)
    print("PHASE A2: DRIFT MODEL FITTING")
    print("=" * 80)
    
    oracle = Cipher2Oracle(known_plaintext)
    all_results = []
    
    # Test baseline (no drift)
    print("\n[Baseline] No drift model...")
    baseline_result = oracle.evaluate(tokens, cipher2_numbers)
    baseline_score = baseline_result.char_match_pct
    print(f"  Baseline: {baseline_score:.2f}%")
    
    # Test progressive drift models
    print("\n[1] Testing Progressive Drift models...")
    for drift_rate in [0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01]:
        model = ProgressiveDriftModel(drift_rate)
        adjusted = model.apply(tokens)
        result = oracle.evaluate(adjusted, cipher2_numbers)
        
        all_results.append(DriftModelResult(
            model_name=model.name,
            parameters={'drift_rate': drift_rate},
            adjusted_tokens=adjusted,
            oracle_score=result.char_match_pct,
            word_count=len(adjusted)
        ))
        
        print(f"  drift_rate={drift_rate:.4f}: {result.char_match_pct:6.2f}% (improvement: {result.char_match_pct - baseline_score:+.2f})")
    
    # Test periodic heading models
    print("\n[2] Testing Periodic Heading models...")
    for period in [50, 100, 150, 200]:
        for heading_words in [1, 2, 3]:
            model = PeriodicHeadingModel(period, heading_words)
            adjusted = model.apply(tokens)
            result = oracle.evaluate(adjusted, cipher2_numbers)
            
            all_results.append(DriftModelResult(
                model_name=model.name,
                parameters={'period': period, 'heading_words': heading_words},
                adjusted_tokens=adjusted,
                oracle_score=result.char_match_pct,
                word_count=len(adjusted)
            ))
            
            improvement = result.char_match_pct - baseline_score
            if abs(improvement) > 0.5:  # Only show significant changes
                print(f"  period={period}, heading={heading_words}: {result.char_match_pct:6.2f}% ({improvement:+.2f})")
    
    # Test line-wrap models
    print("\n[3] Testing Line-Wrap models...")
    for wpl in [8, 10, 12, 15, 20]:
        model = LineWrapModel(wpl)
        adjusted = model.apply(tokens)
        result = oracle.evaluate(adjusted, cipher2_numbers)
        
        all_results.append(DriftModelResult(
            model_name=model.name,
            parameters={'words_per_line': wpl},
            adjusted_tokens=adjusted,
            oracle_score=result.char_match_pct,
            word_count=len(adjusted)
        ))
        
        improvement = result.char_match_pct - baseline_score
        if abs(improvement) > 0.5:
            print(f"  words_per_line={wpl}: {result.char_match_pct:6.2f}% ({improvement:+.2f})")
    
    # Test column numbering models
    print("\n[4] Testing Column Numbering models...")
    for wpc in [40, 50, 60, 70]:
        for cols in [2, 3]:
            model = ColumnNumberingModel(wpc, cols)
            adjusted = model.apply(tokens)
            result = oracle.evaluate(adjusted, cipher2_numbers)
            
            all_results.append(DriftModelResult(
                model_name=model.name,
                parameters={'words_per_column': wpc, 'columns': cols},
                adjusted_tokens=adjusted,
                oracle_score=result.char_match_pct,
                word_count=len(adjusted)
            ))
            
            improvement = result.char_match_pct - baseline_score
            if abs(improvement) > 0.5:
                print(f"  wpc={wpc}, cols={cols}: {result.char_match_pct:6.2f}% ({improvement:+.2f})")
    
    # Sort by oracle score
    all_results.sort(key=lambda x: x.oracle_score, reverse=True)
    
    best_result = all_results[0] if all_results else None
    
    print("\n" + "=" * 80)
    print("DRIFT MODEL RESULTS")
    print("=" * 80)
    
    print(f"\nBaseline (no drift): {baseline_score:.2f}%")
    
    if best_result:
        print(f"\nBest drift model: {best_result.model_name}")
        print(f"  Oracle score: {best_result.oracle_score:.2f}%")
        print(f"  Improvement: {best_result.oracle_score - baseline_score:+.2f} points")
        print(f"  Parameters: {best_result.parameters}")
        
        if best_result.oracle_score >= 90.0:
            print(f"\n*** SUCCESS *** Drift model achieves >=90% oracle match!")
            print("ACTION: Lock this drift model as CANON_INDEXING")
        elif best_result.oracle_score > baseline_score + 5.0:
            print(f"\n*** IMPROVEMENT *** Drift model helps (+{best_result.oracle_score - baseline_score:.2f} points)")
            print("ACTION: Use this drift model, may need further tuning")
        else:
            print(f"\n*** INSUFFICIENT *** Best drift model only +{best_result.oracle_score - baseline_score:.2f} points")
            print("ACTION: Drift models do not solve the DOI mismatch")
            print("RECOMMENDATION: Acquire historical DOI editions (Dunlap 1776, Stone 1823)")
    
    return best_result, all_results


def save_drift_model_results(results: List[DriftModelResult], baseline_score: float, timestamp: str):
    """Save drift model fitting results."""
    output_file = f"output/oracle_sweep/drift_models_{timestamp}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE A2: DRIFT MODEL FITTING RESULTS\n")
        f.write(f"Generated: {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE:\n")
        f.write("Model printing artifacts that cause systematic numbering drift.\n")
        f.write("Target: Improve Cipher 2 oracle match from 26.5% to >=90%\n\n")
        
        f.write(f"Baseline (no drift): {baseline_score:.2f}%\n")
        f.write(f"Models tested: {len(results)}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("TOP 10 DRIFT MODELS\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results[:10], 1):
            improvement = result.oracle_score - baseline_score
            f.write(f"{i:2d}. {result.model_name}\n")
            f.write(f"    Score: {result.oracle_score:6.2f}% ({improvement:+.2f})\n")
            f.write(f"    Parameters: {result.parameters}\n")
            f.write(f"    Word count: {result.word_count}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("VERDICT\n")
        f.write("=" * 80 + "\n\n")
        
        best = results[0]
        improvement = best.oracle_score - baseline_score
        
        if best.oracle_score >= 90.0:
            f.write(f"SUCCESS: {best.model_name} achieves >=90% oracle match\n")
            f.write(f"Score: {best.oracle_score:.2f}%\n")
            f.write(f"Lock this model as CANON_INDEXING and proceed to Phase B.\n")
        elif improvement > 5.0:
            f.write(f"IMPROVEMENT: {best.model_name} helps but insufficient\n")
            f.write(f"Score: {best.oracle_score:.2f}% (+{improvement:.2f})\n")
            f.write(f"Further tuning may help, or consider combined models.\n")
        else:
            f.write(f"INSUFFICIENT: Best model only improves by {improvement:.2f} points\n")
            f.write(f"Score: {best.oracle_score:.2f}%\n")
            f.write(f"\nConclusion: Drift models do NOT solve the DOI mismatch.\n")
            f.write(f"\nRecommendation: Acquire historical DOI editions:\n")
            f.write(f"  1. Dunlap broadside 1776 (Library of Congress)\n")
            f.write(f"  2. Stone engraving 1823 (facsimile)\n")
            f.write(f"  3. Goddard 1777 (Baltimore)\n")
    
    print(f"\nDrift model results saved: {output_file}")
    return output_file


def run_drift_model_test():
    """Main drift model test execution."""
    print("=" * 80)
    print("PHASE A2: DRIFT MODEL TEST")
    print("=" * 80)
    print("\nTRIGGER: Phase A oracle failed (26.5% < 50%)")
    print("OBJECTIVE: Test if printing artifacts explain numbering mismatch")
    print("=" * 80)
    
    # Load data
    print("\n[Step 1] Loading DOI and Cipher 2...")
    from corpus.doi_editions import DOICorpusLoader
    from corpus.tokenizers import TokenizerRegistry
    
    loader = DOICorpusLoader()
    doi_edition = loader.load_edition("beale_embedded")
    
    # Use best tokenizer from Phase A (they all scored same)
    tokenizer = TokenizerRegistry.get_tokenizer("hyphen_keep")
    tokens = tokenizer.tokenize(doi_edition.source_text)
    
    cipher2_numbers = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    print(f"DOI tokens: {len(tokens)}")
    print(f"Cipher 2: {len(cipher2_numbers)} numbers")
    print(f"Known plaintext: {len(known_plaintext)} chars")
    
    # Fit drift models
    print("\n[Step 2] Fitting drift models to oracle...")
    best_result, all_results = fit_drift_model_to_oracle(tokens, cipher2_numbers, known_plaintext)
    
    # Save results
    print("\n[Step 3] Saving results...")
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    baseline_oracle = Cipher2Oracle(known_plaintext)
    baseline_result = baseline_oracle.evaluate(tokens, cipher2_numbers)
    baseline_score = baseline_result.char_match_pct
    
    save_drift_model_results(all_results, baseline_score, timestamp)
    
    # Final verdict
    print("\n" + "=" * 80)
    print("PHASE A2 VERDICT")
    print("=" * 80)
    
    if best_result:
        improvement = best_result.oracle_score - baseline_score
        
        if best_result.oracle_score >= 90.0:
            print(f"\n*** GO *** Drift model passes oracle (>=90%)")
            print(f"  Model: {best_result.model_name}")
            print(f"  Score: {best_result.oracle_score:.2f}%")
            print("\nNext: Lock corpus with this drift model and proceed to Phase B")
        elif improvement > 5.0:
            print(f"\n*** PARTIAL *** Drift model improves oracle by {improvement:.2f} points")
            print(f"  Model: {best_result.model_name}")
            print(f"  Score: {best_result.oracle_score:.2f}%")
            print("\nNext: Try combined models or acquire historical editions")
        else:
            print(f"\n*** NO-GO *** Drift models insufficient")
            print(f"  Best improvement: {improvement:.2f} points")
            print(f"  Best score: {best_result.oracle_score:.2f}%")
            print("\nConclusion: Drift artifacts do NOT explain the 26.5% mismatch")
            print("\nRECOMMENDATION: Acquire historical DOI editions")
            print("  Priority: Dunlap broadside 1776 (original printing)")
    
    return best_result, all_results


if __name__ == "__main__":
    best, all_results = run_drift_model_test()
