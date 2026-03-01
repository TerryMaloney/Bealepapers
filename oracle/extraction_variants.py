"""
Extraction Rule Variant Testing for Cipher 2 Oracle

Tests if Cipher 2 uses non-first-letter extraction rules.

If formatting variants don't explain the 26.5% mismatch, this tests
whether the extraction rule itself (not just the corpus) is wrong.

Extraction variants tested:
- first_letter (baseline)
- second_letter
- last_letter
- middle_letter
- position_dependent (modulo word length)
- cipher_num_dependent
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Callable, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import Cipher2Oracle, load_cipher2, load_cipher2_known_plaintext
from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry


# Define extraction rule variants
EXTRACTION_RULES = {
    'first_letter': lambda word, num, pos: word[0].upper() if word else '?',
    'second_letter': lambda word, num, pos: word[1].upper() if len(word) > 1 else (word[0].upper() if word else '?'),
    'last_letter': lambda word, num, pos: word[-1].upper() if word else '?',
    'middle_letter': lambda word, num, pos: word[len(word)//2].upper() if word else '?',
    'position_mod_length': lambda word, num, pos: word[pos % len(word)].upper() if word and len(word) > 0 else '?',
    'cipher_num_mod_length': lambda word, num, pos: word[num % len(word)].upper() if word and len(word) > 0 else '?',
    'alternating_first_last': lambda word, num, pos: (word[0].upper() if pos % 2 == 0 else word[-1].upper()) if word else '?',
}


def test_extraction_variant(extraction_name: str, extraction_rule: Callable,
                            doi_tokens: List[str], cipher2_numbers: List[int],
                            known_plaintext: str) -> Tuple[float, Dict]:
    """
    Test a single extraction rule variant.
    
    Args:
        extraction_name: Name of extraction rule
        extraction_rule: Function(word, cipher_num, position) -> letter
        doi_tokens: DOI word list
        cipher2_numbers: Cipher 2 number sequence
        known_plaintext: Known Cipher 2 plaintext
    
    Returns:
        (oracle_score, detailed_results)
    """
    oracle = Cipher2Oracle(known_plaintext)
    
    # Decode using custom extraction rule
    decoded = []
    for pos, cipher_num in enumerate(cipher2_numbers):
        word_idx = cipher_num - 1
        
        if 0 <= word_idx < len(doi_tokens):
            word = doi_tokens[word_idx]
            if word:
                try:
                    letter = extraction_rule(word, cipher_num, pos)
                    decoded.append(letter if letter else '?')
                except:
                    decoded.append('?')
            else:
                decoded.append('?')
        else:
            decoded.append('?')
    
    decoded_str = ''.join(decoded)
    
    # Compare to known plaintext
    known_clean = ''.join(c.upper() for c in known_plaintext if c.isalpha())
    
    # Compute match
    char_matches = sum(1 for d, k in zip(decoded_str, known_clean) if d == k)
    total_chars = min(len(decoded_str), len(known_clean))
    char_match_pct = (char_matches / total_chars * 100) if total_chars > 0 else 0.0
    
    # Find first mismatch
    first_mismatch = -1
    for i, (d, k) in enumerate(zip(decoded_str, known_clean)):
        if d != k:
            first_mismatch = i
            break
    
    return char_match_pct, {
        'extraction_rule': extraction_name,
        'char_match_pct': char_match_pct,
        'char_matches': char_matches,
        'total_chars': total_chars,
        'first_mismatch': first_mismatch,
        'decoded_sample': decoded_str[:200]
    }


def run_extraction_sweep(edition_id: str = 'beale_embedded',
                        tokenizer_name: str = 'hyphen_keep',
                        output_dir: str = 'output/oracle_diagnostic') -> Dict:
    """
    Test all extraction rule variants.
    
    This is Step 3 of the comprehensive diagnostic (only run if formatting
    variants don't explain the mismatch).
    """
    print("=" * 80)
    print("EXTRACTION RULE VARIANT SWEEP")
    print("=" * 80)
    
    # Load DOI
    print(f"\n[Step 1] Loading DOI edition: {edition_id}...")
    loader = DOICorpusLoader()
    edition = loader.load_edition(edition_id)
    
    # Tokenize
    print(f"\n[Step 2] Tokenizing with: {tokenizer_name}...")
    tokenizer = TokenizerRegistry.get_tokenizer(tokenizer_name)
    tokens = tokenizer.tokenize(edition.source_text)
    print(f"DOI tokens: {len(tokens)} words")
    
    # Load Cipher 2 and known plaintext
    print(f"\n[Step 3] Loading Cipher 2 and known plaintext...")
    cipher2_numbers = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    # Test each extraction rule
    print(f"\n[Step 4] Testing {len(EXTRACTION_RULES)} extraction rules...")
    results = []
    
    for extraction_name, extraction_rule in EXTRACTION_RULES.items():
        print(f"  {extraction_name:25s}...", end=' ')
        
        try:
            oracle_score, details = test_extraction_variant(
                extraction_name, extraction_rule, tokens,
                cipher2_numbers, known_plaintext
            )
            print(f"{oracle_score:.2f}%")
            
            results.append({
                'extraction_rule': extraction_name,
                'oracle_score': oracle_score,
                **details
            })
        except Exception as e:
            print(f"ERROR: {e}")
    
    # Sort by oracle score (best first)
    results.sort(key=lambda x: x['oracle_score'], reverse=True)
    
    print(f"\n[Step 5] Analysis complete: {len(results)} extraction rules tested")
    
    # Save results
    save_extraction_sweep_results(results, output_dir)
    
    return {
        'total_rules': len(results),
        'best_score': results[0]['oracle_score'] if results else 0.0,
        'best_rule': results[0]['extraction_rule'] if results else '',
        'results': results
    }


def save_extraction_sweep_results(results: List[Dict], output_dir: str):
    """Save extraction sweep results."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save CSV
    csv_file = output_path / f"extraction_sweep_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['rank', 'extraction_rule', 'oracle_score', 'char_matches', 
                     'total_chars', 'first_mismatch']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, result in enumerate(results, 1):
            row = {
                'rank': i,
                'extraction_rule': result['extraction_rule'],
                'oracle_score': result['oracle_score'],
                'char_matches': result['char_matches'],
                'total_chars': result['total_chars'],
                'first_mismatch': result['first_mismatch']
            }
            writer.writerow(row)
    
    # Save JSON
    json_file = output_path / f"extraction_sweep_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'generated': datetime.now().isoformat(),
            'total_rules': len(results),
            'results': results
        }, f, indent=2)
    
    # Save text report
    txt_file = output_path / f"extraction_sweep_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("EXTRACTION RULE VARIANT SWEEP RESULTS\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Extraction rules tested: {len(results)}\n\n")
        
        f.write("RESULTS (sorted by oracle score)\n")
        f.write("-" * 80 + "\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"{i}. {result['extraction_rule']:25s}: {result['oracle_score']:6.2f}%\n")
            f.write(f"   Matches: {result['char_matches']}/{result['total_chars']}\n")
            f.write(f"   First mismatch: position {result['first_mismatch']}\n\n")
    
    print(f"\nExtraction sweep saved:")
    print(f"  CSV: {csv_file}")
    print(f"  JSON: {json_file}")
    print(f"  Report: {txt_file}")


def main():
    """Main entry point for extraction variant sweep."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run extraction variant sweep")
    parser.add_argument('--edition', default='beale_embedded',
                       help='DOI edition to test')
    parser.add_argument('--tokenizer', default='hyphen_keep',
                       help='Tokenizer to use')
    parser.add_argument('--output-dir', default='output/oracle_diagnostic',
                       help='Output directory')
    
    args = parser.parse_args()
    
    # Run sweep
    results = run_extraction_sweep(args.edition, args.tokenizer, args.output_dir)
    
    # Print summary
    print("\n" + "=" * 80)
    print("EXTRACTION RULE VARIANT SWEEP SUMMARY")
    print("=" * 80)
    print(f"\nExtraction rules tested: {results['total_rules']}")
    print(f"Best oracle score: {results['best_score']:.2f}%")
    print(f"Best extraction rule: {results['best_rule']}")
    
    # Interpretation
    baseline_rule = 'first_letter'
    baseline_result = next((r for r in results['results'] if r['extraction_rule'] == baseline_rule), None)
    
    if baseline_result:
        baseline_score = baseline_result['oracle_score']
        improvement = results['best_score'] - baseline_score
        
        print(f"\nBaseline (first_letter): {baseline_score:.2f}%")
        print(f"Improvement: +{improvement:.2f}%")
        
        if results['best_score'] >= 90.0:
            print("\n[BREAKTHROUGH] Non-first-letter extraction achieves ≥90%!")
            print("[RECOMMENDATION] Cipher 2 uses different extraction rule")
        elif improvement > 10:
            print("\n[SIGNIFICANT] Alternative extraction improves oracle")
            print("[RECOMMENDATION] Investigate extraction rule variants further")
        else:
            print("\n[CONFIRMED] First-letter extraction is optimal")
            print("[RECOMMENDATION] Extraction rule is not the issue")
    
    return results


if __name__ == "__main__":
    main()
