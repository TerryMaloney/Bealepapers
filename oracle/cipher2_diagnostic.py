"""
Cipher 2 Differential Diagnostic Engine

Performs comprehensive analysis of the 26.5% oracle mismatch to determine
if the issue is formatting, structural, or edition-based.

Key capabilities:
- Positional heatmap of mismatches
- Drift detection (linear/quadratic patterns)
- Cluster analysis (dense mismatch regions)
- Structural correlation (DOI document features)
- Formatting variant testing
- Extraction rule variant testing
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from collections import Counter
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import Cipher2Oracle, load_cipher2, load_cipher2_known_plaintext, OracleResult
from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry


class Cipher2DiagnosticEngine:
    """Main diagnostic engine for analyzing Cipher 2 oracle mismatches."""
    
    def __init__(self, known_plaintext: str):
        self.oracle = Cipher2Oracle(known_plaintext)
        self.known_plaintext = known_plaintext
    
    def analyze_mismatch_distribution(self, oracle_result: OracleResult) -> Dict:
        """
        Analyze spatial distribution of mismatches.
        
        Returns detailed analysis of WHERE mismatches occur.
        """
        mismatch_positions = oracle_result.mismatch_positions
        total_length = oracle_result.total_chars
        
        if not mismatch_positions:
            return {
                'total_mismatches': 0,
                'mismatch_rate': 0.0,
                'distribution': 'no mismatches',
                'clusters': []
            }
        
        # Compute mismatch rate
        mismatch_rate = len(mismatch_positions) / total_length if total_length > 0 else 0.0
        
        # Detect clusters (dense regions of mismatches)
        clusters = self._detect_clusters(mismatch_positions, total_length)
        
        # Characterize distribution
        distribution = self._characterize_distribution(mismatch_positions, total_length)
        
        return {
            'total_mismatches': len(mismatch_positions),
            'mismatch_rate': mismatch_rate,
            'distribution': distribution,
            'clusters': clusters,
            'match_by_region': oracle_result.match_by_region,
            'drift_coefficient': oracle_result.drift_coefficient
        }
    
    def _detect_clusters(self, mismatch_positions: List[int], total_length: int,
                        window_size: int = 50, density_threshold: float = 0.6) -> List[Tuple[int, int]]:
        """
        Detect dense clusters of mismatches.
        
        Uses sliding window to identify regions where mismatch density
        exceeds threshold.
        """
        if not mismatch_positions or total_length == 0:
            return []
        
        clusters = []
        current_cluster_start = None
        
        for pos in range(0, total_length, window_size // 2):
            window_end = min(pos + window_size, total_length)
            
            # Count mismatches in window
            mismatches_in_window = sum(1 for m in mismatch_positions 
                                      if pos <= m < window_end)
            
            window_density = mismatches_in_window / window_size
            
            if window_density >= density_threshold:
                if current_cluster_start is None:
                    current_cluster_start = pos
            else:
                if current_cluster_start is not None:
                    clusters.append((current_cluster_start, pos))
                    current_cluster_start = None
        
        # Close final cluster if open
        if current_cluster_start is not None:
            clusters.append((current_cluster_start, total_length))
        
        return clusters
    
    def _characterize_distribution(self, mismatch_positions: List[int], 
                                   total_length: int) -> str:
        """
        Characterize overall distribution pattern of mismatches.
        
        Returns: 'uniform', 'early_heavy', 'late_heavy', 'clustered', 'bimodal'
        """
        if not mismatch_positions:
            return 'none'
        
        # Compute quartile distribution
        quartile_size = total_length // 4
        quartile_counts = [0, 0, 0, 0]
        
        for pos in mismatch_positions:
            quartile = min(pos // quartile_size, 3)
            quartile_counts[quartile] += 1
        
        # Normalize
        total_mismatches = len(mismatch_positions)
        quartile_rates = [c / total_mismatches for c in quartile_counts]
        
        # Characterize based on quartile distribution
        if quartile_rates[0] > 0.4:
            return 'early_heavy'
        elif quartile_rates[3] > 0.4:
            return 'late_heavy'
        elif max(quartile_rates) - min(quartile_rates) < 0.15:
            return 'uniform'
        elif sum(1 for r in quartile_rates if r > 0.35) >= 2:
            return 'bimodal'
        else:
            return 'clustered'
    
    def correlate_with_doi_structure(self, oracle_result: OracleResult,
                                     doi_tokens: List[str]) -> Dict:
        """
        Correlate mismatches with DOI document structural features.
        
        Identifies if mismatches correlate with:
        - Word length
        - Punctuation
        - Capitalization
        - Specific DOI sections
        """
        mismatch_details = oracle_result.mismatch_details
        
        if not mismatch_details:
            return {'correlations': {}}
        
        # Analyze word features at mismatch positions
        word_lengths = []
        has_punctuation = []
        is_capitalized = []
        
        for detail in mismatch_details:
            if detail['word']:
                word = detail['word']
                word_lengths.append(len(word))
                has_punctuation.append(any(c in word for c in ',-;:.!?'))
                is_capitalized.append(word[0].isupper() if word else False)
        
        # Compute averages
        avg_mismatch_word_len = sum(word_lengths) / len(word_lengths) if word_lengths else 0
        punc_rate = sum(has_punctuation) / len(has_punctuation) if has_punctuation else 0
        cap_rate = sum(is_capitalized) / len(is_capitalized) if is_capitalized else 0
        
        # Compute corpus-wide averages for comparison
        all_word_lengths = [len(w) for w in doi_tokens if w]
        avg_corpus_word_len = sum(all_word_lengths) / len(all_word_lengths) if all_word_lengths else 0
        
        return {
            'avg_mismatch_word_length': avg_mismatch_word_len,
            'avg_corpus_word_length': avg_corpus_word_len,
            'punctuation_rate': punc_rate,
            'capitalization_rate': cap_rate,
            'word_length_correlation': 'longer_words' if avg_mismatch_word_len > avg_corpus_word_len * 1.1 else 'normal'
        }
    
    def detect_drift_pattern(self, oracle_result: OracleResult) -> Dict:
        """
        Analyze drift pattern in detail.
        
        Returns:
            - drift_type: 'linear', 'quadratic', 'uniform', 'clustered'
            - drift_coefficient: magnitude of drift
            - interpretation: what this means
        """
        drift_coef = oracle_result.drift_coefficient
        match_by_region = oracle_result.match_by_region
        
        # Determine drift type based on regional match rates
        early = match_by_region.get('early', 0)
        middle = match_by_region.get('middle', 0)
        late = match_by_region.get('late', 0)
        
        # Check for linear decline
        if early > middle > late and (early - late) > 20:
            drift_type = 'linear_decline'
            interpretation = 'Progressive numbering offset accumulates through document'
        elif late > middle > early and (late - early) > 20:
            drift_type = 'linear_increase'
            interpretation = 'Early section has structural mismatch that stabilizes later'
        elif abs(early - middle) < 5 and abs(middle - late) < 5:
            drift_type = 'uniform'
            interpretation = 'Mismatches distributed evenly across document'
        else:
            drift_type = 'irregular'
            interpretation = 'Mismatches cluster in specific sections (not progressive drift)'
        
        return {
            'drift_type': drift_type,
            'drift_coefficient': drift_coef,
            'match_early': early,
            'match_middle': middle,
            'match_late': late,
            'interpretation': interpretation
        }


def run_baseline_diagnostic(edition_id: str = 'beale_embedded',
                           tokenizer_name: str = 'hyphen_keep') -> Dict:
    """
    Run baseline diagnostic on specified edition and tokenizer.
    
    This is Step 1 of the comprehensive diagnostic.
    """
    print("=" * 80)
    print("CIPHER 2 BASELINE DIAGNOSTIC")
    print("=" * 80)
    
    # Load data
    print(f"\n[Step 1] Loading Cipher 2 and known plaintext...")
    cipher2_numbers = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    print(f"Cipher 2: {len(cipher2_numbers)} numbers")
    print(f"Known plaintext: {len(known_plaintext)} characters")
    
    # Load DOI
    print(f"\n[Step 2] Loading DOI edition: {edition_id}...")
    loader = DOICorpusLoader()
    edition = loader.load_edition(edition_id)
    
    # Tokenize
    print(f"\n[Step 3] Tokenizing with: {tokenizer_name}...")
    tokenizer = TokenizerRegistry.get_tokenizer(tokenizer_name)
    tokens = tokenizer.tokenize(edition.source_text)
    
    print(f"DOI tokens: {len(tokens)} words")
    
    # Evaluate with oracle
    print(f"\n[Step 4] Running oracle evaluation...")
    oracle = Cipher2Oracle(known_plaintext)
    oracle_result = oracle.evaluate(tokens, cipher2_numbers)
    
    print(f"\n[Step 5] Analyzing mismatch distribution...")
    diagnostic_engine = Cipher2DiagnosticEngine(known_plaintext)
    
    # Mismatch distribution analysis
    mismatch_analysis = diagnostic_engine.analyze_mismatch_distribution(oracle_result)
    
    # Drift pattern analysis
    drift_analysis = diagnostic_engine.detect_drift_pattern(oracle_result)
    
    # Structural correlation
    structural_analysis = diagnostic_engine.correlate_with_doi_structure(oracle_result, tokens)
    
    # Compile results
    results = {
        'edition': edition_id,
        'tokenizer': tokenizer_name,
        'oracle_score': oracle_result.char_match_pct,
        'word_count': len(tokens),
        'total_mismatches': len(oracle_result.mismatch_positions),
        'first_mismatch': oracle_result.first_mismatch,
        'mismatch_analysis': mismatch_analysis,
        'drift_analysis': drift_analysis,
        'structural_analysis': structural_analysis,
        'oracle_result': oracle_result  # Store for later use
    }
    
    return results


def save_baseline_diagnostic(results: Dict, output_dir: str):
    """Save baseline diagnostic results."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON (without oracle_result object)
    json_data = {k: v for k, v in results.items() if k != 'oracle_result'}
    json_file = output_path / f"baseline_diagnostic_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
    
    # Save detailed text report
    txt_file = output_path / f"baseline_diagnostic_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CIPHER 2 BASELINE DIAGNOSTIC REPORT\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Edition: {results['edition']}\n")
        f.write(f"Tokenizer: {results['tokenizer']}\n")
        f.write(f"Word count: {results['word_count']}\n\n")
        
        f.write("ORACLE RESULTS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Character match: {results['oracle_score']:.2f}%\n")
        f.write(f"Total mismatches: {results['total_mismatches']}\n")
        f.write(f"First mismatch at position: {results['first_mismatch']}\n\n")
        
        f.write("REGIONAL MATCH RATES\n")
        f.write("-" * 80 + "\n")
        match_by_region = results['mismatch_analysis']['match_by_region']
        f.write(f"Early (0-33%): {match_by_region.get('early', 0):.2f}%\n")
        f.write(f"Middle (33-66%): {match_by_region.get('middle', 0):.2f}%\n")
        f.write(f"Late (66-100%): {match_by_region.get('late', 0):.2f}%\n\n")
        
        f.write("DRIFT ANALYSIS\n")
        f.write("-" * 80 + "\n")
        drift = results['drift_analysis']
        f.write(f"Drift type: {drift['drift_type']}\n")
        f.write(f"Drift coefficient: {drift['drift_coefficient']:.4f}\n")
        f.write(f"Interpretation: {drift['interpretation']}\n\n")
        
        f.write("MISMATCH DISTRIBUTION\n")
        f.write("-" * 80 + "\n")
        mismatch = results['mismatch_analysis']
        f.write(f"Pattern: {mismatch['distribution']}\n")
        f.write(f"Mismatch rate: {mismatch['mismatch_rate']:.2%}\n")
        f.write(f"Detected clusters: {len(mismatch['clusters'])}\n")
        if mismatch['clusters']:
            f.write("\nCluster regions:\n")
            for i, (start, end) in enumerate(mismatch['clusters'], 1):
                f.write(f"  {i}. Positions {start}-{end} (length: {end-start})\n")
        f.write("\n")
        
        f.write("STRUCTURAL CORRELATION\n")
        f.write("-" * 80 + "\n")
        struct = results['structural_analysis']
        f.write(f"Avg mismatch word length: {struct['avg_mismatch_word_length']:.2f}\n")
        f.write(f"Avg corpus word length: {struct['avg_corpus_word_length']:.2f}\n")
        f.write(f"Correlation: {struct['word_length_correlation']}\n")
        f.write(f"Punctuation rate at mismatches: {struct['punctuation_rate']:.2%}\n")
        f.write(f"Capitalization rate at mismatches: {struct['capitalization_rate']:.2%}\n\n")
    
    print(f"\nBaseline diagnostic saved:")
    print(f"  JSON: {json_file}")
    print(f"  Report: {txt_file}")
    
    return json_file, txt_file


def main():
    """Main entry point for baseline diagnostic."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Cipher 2 baseline diagnostic")
    parser.add_argument('--edition', default='beale_embedded',
                       help='DOI edition to test')
    parser.add_argument('--tokenizer', default='hyphen_keep',
                       help='Tokenizer to use')
    parser.add_argument('--output-dir', default='output/oracle_diagnostic',
                       help='Output directory')
    
    args = parser.parse_args()
    
    # Run diagnostic
    results = run_baseline_diagnostic(args.edition, args.tokenizer)
    
    # Save results
    save_baseline_diagnostic(results, args.output_dir)
    
    # Print summary
    print("\n" + "=" * 80)
    print("BASELINE DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"\nOracle score: {results['oracle_score']:.2f}%")
    print(f"Drift type: {results['drift_analysis']['drift_type']}")
    print(f"Distribution: {results['mismatch_analysis']['distribution']}")
    print(f"Clusters: {len(results['mismatch_analysis']['clusters'])}")
    
    drift = results['drift_analysis']
    print(f"\nRegional match rates:")
    print(f"  Early:  {drift['match_early']:.2f}%")
    print(f"  Middle: {drift['match_middle']:.2f}%")
    print(f"  Late:   {drift['match_late']:.2f}%")
    
    print(f"\nInterpretation: {drift['interpretation']}")
    
    return results


if __name__ == "__main__":
    main()
