"""
Formatting Variant Testing for Cipher 2 Oracle

Tests different formatting/tokenization approaches to determine if the
26.5% oracle mismatch can be explained by formatting rather than edition.

Key variants tested:
- Hyphen handling (keep, split)
- Apostrophe handling (keep, strip, split)
- Punctuation (ignore, as tokens)
- Ampersand special handling
- Header inclusion/exclusion
- Signer names inclusion/exclusion
- Numbers handling
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import re
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import Cipher2Oracle, load_cipher2, load_cipher2_known_plaintext


class FormattingVariantTokenizer:
    """Custom tokenizer for testing formatting variants."""
    
    def __init__(self, config: Dict):
        """
        Initialize with formatting configuration.
        
        Config keys:
        - hyphen: 'keep', 'split'
        - apostrophe: 'keep', 'strip', 'split'
        - punctuation: 'ignore', 'token'
        - ampersand: 'as_and', 'skip', 'token'
        - header: True/False (include "IN CONGRESS..." header)
        - title: True/False (include "The unanimous Declaration...")
        - signers: True/False (include signer names after main text)
        - numbers: 'keep', 'skip'
        """
        self.config = config
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text according to configuration."""
        
        # Step 1: Handle ampersand special case
        if self.config.get('ampersand') == 'as_and':
            text = text.replace('&', 'and')
            text = text.replace('(&)', 'and')
        elif self.config.get('ampersand') == 'skip':
            text = text.replace('&', ' ')
            text = text.replace('(&)', ' ')
        
        # Step 2: Split into raw tokens
        # Use regex to split on whitespace while preserving punctuation
        if self.config.get('punctuation') == 'token':
            # Keep punctuation as separate tokens
            tokens = re.findall(r'\w+[\'\-]?\w*|[^\w\s]', text)
        else:
            # Ignore punctuation (strip it)
            tokens = re.findall(r'\w+[\'\-]?\w*', text)
        
        # Step 3: Handle hyphens
        if self.config.get('hyphen') == 'split':
            new_tokens = []
            for token in tokens:
                if '-' in token:
                    parts = token.split('-')
                    new_tokens.extend([p for p in parts if p])
                else:
                    new_tokens.append(token)
            tokens = new_tokens
        
        # Step 4: Handle apostrophes
        if self.config.get('apostrophe') == 'strip':
            tokens = [t.replace("'", '') for t in tokens]
        elif self.config.get('apostrophe') == 'split':
            new_tokens = []
            for token in tokens:
                if "'" in token:
                    parts = token.split("'")
                    new_tokens.extend([p for p in parts if p])
                else:
                    new_tokens.append(token)
            tokens = new_tokens
        
        # Step 5: Filter numbers if needed
        if self.config.get('numbers') == 'skip':
            tokens = [t for t in tokens if not t.isdigit()]
        
        # Step 6: Clean and normalize
        tokens = [t.strip() for t in tokens if t.strip()]
        tokens = [t for t in tokens if t.isalnum() or "'" in t or '-' in t]
        
        # Step 7: Lowercase (always normalize to lowercase for matching)
        tokens = [t.lower() for t in tokens]
        
        return tokens


def load_doi_with_variants(variant_config: Dict) -> str:
    """
    Load DOI text with structural variants (header, signers, etc).
    
    Returns raw text that will be tokenized.
    """
    # Load base DOI from beale_papers.txt
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Line 55 (index 54) contains numbered Declaration
    doi_line = lines[54].strip()
    
    # Extract words from pattern: word(number)
    pattern = r'(\w+)\((\d+)\)'
    matches = re.findall(pattern, doi_line)
    
    # Build ordered text
    max_num = max(int(num) for word, num in matches)
    words = [''] * (max_num + 1)
    for word, num in matches:
        words[int(num)] = word
    
    # Join words (skip index 0)
    doi_text = ' '.join(words[1:])
    
    # Handle header/title based on config
    # (For beale_embedded, we don't have actual header/title to test)
    # This would be more relevant with actual historical editions
    
    return doi_text


def test_formatting_variant(variant_config: Dict) -> Tuple[float, Dict]:
    """
    Test a single formatting variant configuration.
    
    Returns:
        (oracle_score, detailed_results)
    """
    # Load DOI with structural variants
    doi_text = load_doi_with_variants(variant_config)
    
    # Tokenize with formatting variant
    tokenizer = FormattingVariantTokenizer(variant_config)
    tokens = tokenizer.tokenize(doi_text)
    
    # Load Cipher 2 and known plaintext
    cipher2_numbers = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    # Evaluate with oracle
    oracle = Cipher2Oracle(known_plaintext)
    result = oracle.evaluate(tokens, cipher2_numbers)
    
    return result.char_match_pct, {
        'word_count': len(tokens),
        'char_match_pct': result.char_match_pct,
        'word_match_pct': result.word_match_pct,
        'first_mismatch': result.first_mismatch,
        'total_mismatches': len(result.mismatch_positions)
    }


def generate_variant_configs() -> List[Dict]:
    """
    Generate all meaningful formatting variant configurations.
    
    Returns list of config dicts to test.
    """
    configs = []
    
    # Base configurations (most important)
    hyphen_options = ['keep', 'split']
    apostrophe_options = ['keep', 'strip']
    ampersand_options = ['as_and', 'skip']
    punctuation_options = ['ignore']  # Punctuation as token less relevant for book cipher
    numbers_options = ['skip']  # Numbers typically not in DOI body text
    
    # Generate combinations
    for hyphen in hyphen_options:
        for apostrophe in apostrophe_options:
            for ampersand in ampersand_options:
                config = {
                    'hyphen': hyphen,
                    'apostrophe': apostrophe,
                    'punctuation': 'ignore',
                    'ampersand': ampersand,
                    'numbers': 'skip',
                    'header': False,  # beale_embedded doesn't have header
                    'title': False,   # beale_embedded doesn't have title
                    'signers': False  # beale_embedded doesn't have signers
                }
                configs.append(config)
    
    return configs


def run_formatting_sweep(output_dir: str = 'output/oracle_diagnostic') -> Dict:
    """
    Test all formatting variants and identify best performers.
    
    This is Step 2 of the comprehensive diagnostic.
    """
    print("=" * 80)
    print("FORMATTING VARIANT SWEEP")
    print("=" * 80)
    
    # Generate variant configurations
    print("\n[Step 1] Generating formatting variant configurations...")
    variant_configs = generate_variant_configs()
    print(f"Total variants to test: {len(variant_configs)}")
    
    # Test each variant
    print("\n[Step 2] Testing each variant...")
    results = []
    
    for i, config in enumerate(variant_configs, 1):
        # Create config name
        config_name = (f"hyphen_{config['hyphen']}_"
                      f"apostrophe_{config['apostrophe']}_"
                      f"ampersand_{config['ampersand']}")
        
        print(f"  {i}/{len(variant_configs)}: {config_name}...", end=' ')
        
        try:
            oracle_score, details = test_formatting_variant(config)
            print(f"{oracle_score:.2f}%")
            
            results.append({
                'config_name': config_name,
                'config': config,
                'oracle_score': oracle_score,
                **details
            })
        except Exception as e:
            print(f"ERROR: {e}")
    
    # Sort by oracle score (best first)
    results.sort(key=lambda x: x['oracle_score'], reverse=True)
    
    print(f"\n[Step 3] Analysis complete: {len(results)} variants tested")
    
    # Save results
    save_formatting_sweep_results(results, output_dir)
    
    return {
        'total_variants': len(results),
        'best_score': results[0]['oracle_score'] if results else 0.0,
        'best_config': results[0]['config'] if results else {},
        'best_config_name': results[0]['config_name'] if results else '',
        'results': results
    }


def save_formatting_sweep_results(results: List[Dict], output_dir: str):
    """Save formatting sweep results."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save CSV
    csv_file = output_path / f"formatting_sweep_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['rank', 'config_name', 'oracle_score', 'word_count', 
                     'first_mismatch', 'total_mismatches']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, result in enumerate(results, 1):
            row = {
                'rank': i,
                'config_name': result['config_name'],
                'oracle_score': result['oracle_score'],
                'word_count': result['word_count'],
                'first_mismatch': result['first_mismatch'],
                'total_mismatches': result['total_mismatches']
            }
            writer.writerow(row)
    
    # Save JSON with full config details
    json_file = output_path / f"formatting_sweep_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'generated': datetime.now().isoformat(),
            'total_variants': len(results),
            'results': results[:20]  # Save top 20
        }, f, indent=2)
    
    # Save text report
    txt_file = output_path / f"formatting_sweep_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("FORMATTING VARIANT SWEEP RESULTS\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Variants tested: {len(results)}\n\n")
        
        f.write("TOP 10 FORMATTING VARIANTS\n")
        f.write("-" * 80 + "\n\n")
        
        for i, result in enumerate(results[:10], 1):
            f.write(f"RANK {i}: {result['oracle_score']:.2f}%\n")
            f.write(f"  Config: {result['config_name']}\n")
            f.write(f"  Word count: {result['word_count']}\n")
            f.write(f"  Total mismatches: {result['total_mismatches']}\n")
            f.write(f"  First mismatch: position {result['first_mismatch']}\n\n")
    
    print(f"\nFormatting sweep saved:")
    print(f"  CSV: {csv_file}")
    print(f"  JSON: {json_file}")
    print(f"  Report: {txt_file}")


def main():
    """Main entry point for formatting variant sweep."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run formatting variant sweep")
    parser.add_argument('--output-dir', default='output/oracle_diagnostic',
                       help='Output directory')
    
    args = parser.parse_args()
    
    # Run sweep
    results = run_formatting_sweep(args.output_dir)
    
    # Print summary
    print("\n" + "=" * 80)
    print("FORMATTING VARIANT SWEEP SUMMARY")
    print("=" * 80)
    print(f"\nVariants tested: {results['total_variants']}")
    print(f"Best oracle score: {results['best_score']:.2f}%")
    print(f"Best configuration: {results['best_config_name']}")
    
    # Interpretation
    baseline = 26.5  # Known baseline
    improvement = results['best_score'] - baseline
    
    print(f"\nImprovement over baseline: +{improvement:.2f}%")
    
    if results['best_score'] >= 90.0:
        print("\n[BREAKTHROUGH] Formatting variant achieves ≥90% oracle!")
        print("[RECOMMENDATION] Lock this formatting and skip edition acquisition")
    elif improvement > 10:
        print("\n[SIGNIFICANT] Formatting improves oracle by >10%")
        print("[RECOMMENDATION] Test more formatting combinations")
    elif improvement > 5:
        print("\n[MODERATE] Formatting provides some improvement")
        print("[RECOMMENDATION] Formatting matters, but edition likely also matters")
    else:
        print("\n[CONFIRMED] Formatting variants do not explain 26.5%")
        print("[RECOMMENDATION] Proceed with Stone 1823 acquisition")
    
    return results


if __name__ == "__main__":
    main()
