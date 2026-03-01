"""
Phase 12B: Word-Counting Convention Tests

Tests systematic structural variants that could cause constant offsets.
Each convention creates a shift in word indexing.

Conventions tested:
- Header inclusion (prepend "IN CONGRESS..." heading)
- Hyphen handling ("self-evident" as 1 vs 2 words)
- Other structural features as applicable
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import csv
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import Cipher2Oracle, load_cipher2, load_cipher2_known_plaintext
from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry


def load_base_doi_text() -> str:
    """Load the base beale_embedded DOI text."""
    loader = DOICorpusLoader()
    edition = loader.load_edition("beale_embedded")
    return edition.source_text


def create_header_variant(base_text: str, header_text: str) -> str:
    """Prepend header to DOI text."""
    return header_text + " " + base_text


def create_hyphen_merged_variant(base_text: str) -> str:
    """
    Merge hyphenated words.
    
    In beale_embedded, "self(78) evident(79)" are two words.
    This variant makes "selfevident(78)" one word and renumbers.
    """
    # The beale_embedded format has numbered words like word(num)
    # We need to work with the raw format from beale_papers.txt
    # But since we're working with tokenized text, we'll apply merging to the tokenized output
    
    # For the tokenized text, we merge words like "self evident" -> "selfevident"
    # This is effectively what hyphen_split vs hyphen_keep does, but we need to
    # account for the case where beale_embedded has them as separate numbered words
    
    # Simple approach: replace "self evident" with "selfevident"
    text = base_text.replace("self evident", "selfevident")
    return text


def create_convention_variant(variant_name: str, base_text: str) -> Tuple[str, str]:
    """
    Create a DOI text variant based on the convention.
    
    Returns:
        (variant_text, description)
    """
    if variant_name == "header_congress":
        header = "in congress july 4 1776"
        return create_header_variant(base_text, header), "Prepend 'IN CONGRESS, July 4, 1776'"
    
    elif variant_name == "header_unanimous":
        header = "the unanimous declaration of the thirteen united states of america"
        return create_header_variant(base_text, header), "Prepend 'The unanimous Declaration...'"
    
    elif variant_name == "header_full":
        header = "in congress july 4 1776 the unanimous declaration of the thirteen united states of america"
        return create_header_variant(base_text, header), "Prepend full heading"
    
    elif variant_name == "hyphen_merged":
        return create_hyphen_merged_variant(base_text), "Merge 'self evident' -> 'selfevident'"
    
    elif variant_name == "baseline":
        return base_text, "Baseline (beale_embedded as-is)"
    
    else:
        raise ValueError(f"Unknown variant: {variant_name}")


def evaluate_convention(variant_name: str, variant_text: str, tokenizer_name: str = "hyphen_keep") -> Dict:
    """
    Evaluate a DOI variant against Cipher 2 oracle.
    
    Returns:
        Dictionary with variant performance metrics
    """
    # Tokenize variant
    tokenizer = TokenizerRegistry.get_tokenizer(tokenizer_name)
    tokens = tokenizer.tokenize(variant_text)
    
    # Load Cipher 2 and known plaintext
    cipher2_numbers = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    # Evaluate
    oracle = Cipher2Oracle(known_plaintext)
    result = oracle.evaluate(tokens, cipher2_numbers)
    
    # Compute early-region match (first 100 positions)
    decoded = []
    for i, cipher_num in enumerate(cipher2_numbers[:100]):
        word_idx = cipher_num - 1
        if 0 <= word_idx < len(tokens) and tokens[word_idx]:
            decoded.append(tokens[word_idx][0].upper())
        else:
            decoded.append('?')
    
    known_clean = ''.join(c.upper() for c in known_plaintext if c.isalpha())
    early_matches = sum(1 for i, (d, k) in enumerate(zip(decoded, known_clean[:100])) if d == k)
    early_100_match_pct = (early_matches / 100.0 * 100) if len(decoded) >= 100 else 0.0
    
    return {
        'variant': variant_name,
        'char_match_pct': result.char_match_pct,
        'word_match_pct': result.word_match_pct,
        'first_mismatch': result.first_mismatch,
        'early_100_match_pct': early_100_match_pct,
        'token_count': len(tokens)
    }


def run_convention_sweep() -> List[Dict]:
    """
    Run full sweep of word-counting convention variants.
    
    Returns:
        List of results for each variant
    """
    print("\nPhase 12B: Word-Counting Convention Tests")
    print("=" * 80)
    print("Testing structural variants that could cause constant offsets...")
    print()
    
    base_text = load_base_doi_text()
    
    # Define variants to test
    variants_to_test = [
        "baseline",
        "header_congress",
        "header_unanimous",
        "header_full",
        "hyphen_merged"
    ]
    
    results = []
    
    for variant_name in variants_to_test:
        print(f"Testing: {variant_name}...")
        
        variant_text, description = create_convention_variant(variant_name, base_text)
        result = evaluate_convention(variant_name, variant_text)
        result['description'] = description
        
        results.append(result)
        
        print(f"  Char match: {result['char_match_pct']:.2f}%")
        print(f"  Early 100: {result['early_100_match_pct']:.2f}%")
        print(f"  First mismatch: position {result['first_mismatch']}")
        print()
    
    return results


def save_convention_results(results: List[Dict], output_dir: Path):
    """Save convention test results to CSV and text report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV output
    csv_path = output_dir / f"convention_sweep_{timestamp}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['variant', 'description', 'char_match_pct', 'early_100_match_pct',
                     'word_match_pct', 'first_mismatch', 'token_count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"CSV saved: {csv_path}")
    
    # Text report
    txt_path = output_dir / f"convention_sweep_{timestamp}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 12B: WORD-COUNTING CONVENTION TESTS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("\n")
        
        f.write("RESULTS SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Variant':<20} {'Description':<40} {'Char%':<8} {'Early100%':<10} {'1stMis':<8}\n")
        f.write("-" * 80 + "\n")
        
        for r in results:
            f.write(f"{r['variant']:<20} {r['description']:<40} "
                   f"{r['char_match_pct']:<8.2f} {r['early_100_match_pct']:<10.2f} {r['first_mismatch']:<8}\n")
        
        f.write("\n")
        
        # Find best variant
        best = max(results, key=lambda x: x['early_100_match_pct'])
        baseline = next(r for r in results if r['variant'] == 'baseline')
        
        f.write("ANALYSIS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Baseline (beale_embedded): {baseline['early_100_match_pct']:.2f}% early-100\n")
        f.write(f"Best variant: {best['variant']}: {best['early_100_match_pct']:.2f}% early-100\n")
        f.write(f"Improvement: {best['early_100_match_pct'] - baseline['early_100_match_pct']:+.2f} percentage points\n")
        f.write("\n")
        
        if best['early_100_match_pct'] >= 85.0:
            f.write("VERDICT: [SUCCESS] Convention variant achieves >=85% early-100 match\n")
            f.write(f"RECOMMENDATION: Lock convention '{best['variant']}' and proceed to Phase 12C\n")
        elif best['early_100_match_pct'] > baseline['early_100_match_pct'] + 10.0:
            f.write("VERDICT: [WARNING] Convention variant shows material improvement\n")
            f.write("RECOMMENDATION: Investigate this variant further; may need more refined conventions\n")
        else:
            f.write("VERDICT: [INFO] No convention variant materially improves alignment\n")
            f.write("RECOMMENDATION: Proceed to Phase 12C (constant offset sweep)\n")
        
        f.write("\n")
    
    print(f"Report saved: {txt_path}")


def run_convention_tests(output_dir: str = "output/oracle_diagnostic"):
    """
    Main entry point for Phase 12B.
    
    Args:
        output_dir: Directory to save results
    """
    output_path = Path(output_dir)
    
    results = run_convention_sweep()
    save_convention_results(results, output_path)
    
    # Print summary
    best = max(results, key=lambda x: x['early_100_match_pct'])
    baseline = next(r for r in results if r['variant'] == 'baseline')
    
    print("\n" + "=" * 80)
    print("CONVENTION TEST SUMMARY")
    print("=" * 80)
    print(f"Baseline: {baseline['early_100_match_pct']:.2f}% early-100")
    print(f"Best: {best['variant']} - {best['early_100_match_pct']:.2f}% early-100")
    print(f"Improvement: {best['early_100_match_pct'] - baseline['early_100_match_pct']:+.2f} pp")
    print()
    
    if best['early_100_match_pct'] >= 85.0:
        print("[SUCCESS] BREAKTHROUGH: Convention variant achieves >=85%!")
        print(f"   Lock '{best['variant']}' and proceed to Phase 12C")
    elif best['early_100_match_pct'] > baseline['early_100_match_pct'] + 10.0:
        print("[WARNING] Material improvement detected")
        print("   Consider refining conventions or combining variants")
    else:
        print("[INFO] No convention materially improves alignment")
        print("   Proceed to Phase 12C: Constant offset sweep")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 12B: Word-Counting Convention Tests")
    parser.add_argument('--output-dir', default='output/oracle_diagnostic',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    run_convention_tests(args.output_dir)
