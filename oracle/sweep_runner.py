"""
Oracle Sweep Runner - Tests all DOI edition × tokenizer combinations.

This is the CRITICAL PATH for Phase A. Everything depends on finding a DOI
edition that matches Cipher 2's known plaintext with >=90% accuracy.
"""

import csv
import json
from datetime import datetime
from typing import List, Dict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.doi_editions import DOICorpusLoader, DOIEdition
from corpus.tokenizers import TokenizerRegistry, Tokenizer
from oracle.cipher2_evaluator import Cipher2Oracle, load_cipher2, load_cipher2_known_plaintext, OracleResult


def run_oracle_sweep() -> List[Dict]:
    """
    Test all (edition × tokenizer) combinations against Cipher 2 oracle.
    
    Returns list of results sorted by match percentage (best first).
    """
    print("=" * 80)
    print("PHASE A: DOI ORACLE SWEEP")
    print("=" * 80)
    print("\nMISSION: Find DOI edition + tokenization that matches Cipher 2 >=90%")
    print("CURRENT STATE: beale_embedded matches only 26.5%")
    print("=" * 80)
    
    # Load Cipher 2 and known plaintext
    print("\n[Step 1] Loading Cipher 2 oracle data...")
    cipher2_numbers = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    
    print(f"Cipher 2: {len(cipher2_numbers)} numbers")
    print(f"Known plaintext: {len(known_plaintext)} characters")
    print(f"Sample: {known_plaintext[:80]}...")
    
    # Initialize oracle
    oracle = Cipher2Oracle(known_plaintext)
    
    # Load all editions
    print("\n[Step 2] Loading DOI editions...")
    loader = DOICorpusLoader()
    editions = loader.list_available_editions()
    print(f"Editions to test: {editions}")
    
    # Get all tokenizers
    print("\n[Step 3] Loading tokenizers...")
    tokenizers = TokenizerRegistry.get_all_tokenizers()
    print(f"Tokenizers to test: {[t.name for t in tokenizers]}")
    
    # Run sweep
    print("\n[Step 4] Running oracle sweep...")
    print(f"Total combinations: {len(editions)} editions × {len(tokenizers)} tokenizers = {len(editions) * len(tokenizers)}")
    print("-" * 80)
    
    results = []
    test_count = 0
    
    for edition_id in editions:
        print(f"\nTesting edition: {edition_id}")
        
        # Load edition
        edition = loader.load_edition(edition_id)
        
        if not edition.source_text:
            print(f"  SKIPPED: Edition not yet acquired (placeholder only)")
            continue
        
        # Test with each tokenizer
        for tokenizer in tokenizers:
            test_count += 1
            
            # Tokenize
            tokens = tokenizer.tokenize(edition.source_text)
            
            # Evaluate against oracle
            oracle_result = oracle.evaluate(tokens, cipher2_numbers)
            
            # Store result
            results.append({
                'edition': edition_id,
                'tokenizer': tokenizer.name,
                'word_count': len(tokens),
                'char_match_pct': oracle_result.char_match_pct,
                'word_match_pct': oracle_result.word_match_pct,
                'char_matches': oracle_result.char_matches,
                'total_chars': oracle_result.total_chars,
                'first_mismatch': oracle_result.first_mismatch,
                'diff_report': oracle_result.diff_report,
                'decoded_sample': oracle_result.decoded_sample
            })
            
            print(f"  {tokenizer.name:20s}: {oracle_result.char_match_pct:6.2f}% | Words: {len(tokens):4d}")
    
    print(f"\n  Tested {test_count} combinations.")
    
    # Sort by match percentage
    results.sort(key=lambda x: x['char_match_pct'], reverse=True)
    
    # Save results
    print("\n[Step 5] Saving results...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_oracle_sweep_results(results, timestamp)
    
    # Generate GO/NO-GO decision
    print("\n" + "=" * 80)
    print("ORACLE SWEEP RESULTS")
    print("=" * 80)
    
    if not results:
        print("\nNO RESULTS: All editions are placeholders.")
        print("ACTION REQUIRED: Acquire historical DOI editions.")
        print("\nRecommended sources:")
        print("  1. Library of Congress: https://www.loc.gov/")
        print("  2. National Archives: https://www.archives.gov/")
        print("  3. Founders Online: https://founders.archives.gov/")
        return results
    
    # Show top 10
    print("\nTop 10 results:")
    for i, result in enumerate(results[:10], 1):
        print(f"{i:2d}. {result['edition']:20s} + {result['tokenizer']:20s} | "
              f"{result['char_match_pct']:6.2f}% ({result['char_matches']}/{result['total_chars']})")
    
    # Best result
    best = results[0]
    print("\n" + "=" * 80)
    print("GO/NO-GO DECISION")
    print("=" * 80)
    
    print(f"\nBest result:")
    print(f"  Edition: {best['edition']}")
    print(f"  Tokenizer: {best['tokenizer']}")
    print(f"  Match: {best['char_match_pct']:.2f}% ({best['char_matches']}/{best['total_chars']})")
    print(f"  Word count: {best['word_count']}")
    
    if best['char_match_pct'] >= 90.0:
        print(f"\n*** GO *** Oracle passed with {best['char_match_pct']:.1f}% >= 90%")
        print(f"\nACTION: Lock corpus and proceed to Phase B (rebase)")
        print(f"  Edition: {best['edition']}")
        print(f"  Tokenizer: {best['tokenizer']}")
        decision = "GO"
    elif best['char_match_pct'] >= 50.0:
        print(f"\n*** CONDITIONAL *** Oracle at {best['char_match_pct']:.1f}% (50-90%)")
        print(f"\nACTION: Try Phase A2 (drift models) to improve match")
        decision = "CONDITIONAL"
    else:
        print(f"\n*** NO-GO *** Oracle failed with {best['char_match_pct']:.1f}% < 50%")
        print(f"\nACTION: Acquire historical DOI editions or implement drift models")
        print(f"\nCurrent best ({best['edition']}) is insufficient.")
        decision = "NO-GO"
    
    # Save decision
    decision_file = f"output/oracle_sweep/decision_{timestamp}.txt"
    with open(decision_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ORACLE SWEEP GO/NO-GO DECISION\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Decision: {decision}\n\n")
        f.write(f"Best result:\n")
        f.write(f"  Edition: {best['edition']}\n")
        f.write(f"  Tokenizer: {best['tokenizer']}\n")
        f.write(f"  Match: {best['char_match_pct']:.2f}%\n")
        f.write(f"  Word count: {best['word_count']}\n\n")
        
        if decision == "GO":
            f.write("Next steps:\n")
            f.write(f"1. python run_pipeline.py lock_corpus --edition {best['edition']} --tokenizer {best['tokenizer']}\n")
            f.write(f"2. python run_pipeline.py decode_cipher --cipher 1 --topk 50\n")
            f.write(f"3. python run_pipeline.py decode_cipher --cipher 3 --topk 50\n")
        elif decision == "CONDITIONAL":
            f.write("Next steps:\n")
            f.write("1. Implement corpus/drift_models.py (Phase A2)\n")
            f.write("2. Fit drift models to improve oracle match\n")
            f.write("3. Re-run oracle sweep with drift-adjusted corpus\n")
        else:  # NO-GO
            f.write("Next steps:\n")
            f.write("1. Acquire historical DOI editions:\n")
            f.write("   - Dunlap broadside 1776 (Library of Congress)\n")
            f.write("   - Goddard printing 1777 (Baltimore)\n")
            f.write("   - Stone engraving 1823 (facsimile)\n")
            f.write("2. Save texts to corpus/editions/[edition_id].txt\n")
            f.write("3. Re-run: python run_pipeline.py oracle_sweep\n")
    
    print(f"\nDecision saved: {decision_file}")
    
    return results


def save_oracle_matrix(results: List[Dict], timestamp: str):
    """
    Save oracle results as matrix: rows=editions, cols=presets, values=match%.
    
    This format allows quick visual identification of:
    - Which edition is structurally correct (high scores across multiple presets)
    - Which tokenization preset matters most (high variance within edition)
    - Dead ends (consistent low scores)
    """
    from collections import defaultdict
    
    # Build matrix data structure
    matrix = defaultdict(dict)
    editions = set()
    tokenizers = set()
    
    for result in results:
        edition = result['edition']
        tokenizer = result['tokenizer']
        match_pct = result['char_match_pct']
        
        matrix[edition][tokenizer] = match_pct
        editions.add(edition)
        tokenizers.add(tokenizer)
    
    editions = sorted(editions)
    tokenizers = sorted(tokenizers)
    
    # Save as CSV (pivot table)
    csv_file = f"output/oracle_sweep/matrix_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header row
        writer.writerow(['Edition'] + tokenizers)
        
        # Data rows
        for edition in editions:
            row = [edition]
            for tokenizer in tokenizers:
                match_pct = matrix[edition].get(tokenizer, 0.0)
                row.append(f"{match_pct:.2f}")
            writer.writerow(row)
    
    # Save as human-readable text
    txt_file = f"output/oracle_sweep/matrix_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 120 + "\n")
        f.write("ORACLE SWEEP MATRIX (Character Match %)\n")
        f.write("=" * 120 + "\n\n")
        
        # Column headers
        header = f"{'Edition':<25s}"
        for tokenizer in tokenizers:
            header += f" | {tokenizer[:12]:>12s}"
        f.write(header + "\n")
        f.write("-" * 120 + "\n")
        
        # Data rows
        for edition in editions:
            row = f"{edition:<25s}"
            for tokenizer in tokenizers:
                match_pct = matrix[edition].get(tokenizer, 0.0)
                row += f" | {match_pct:12.2f}"
            f.write(row + "\n")
        
        f.write("\n" + "=" * 120 + "\n")
        f.write("INTERPRETATION GUIDE:\n")
        f.write("- Horizontal consistency (within row) = edition is structurally correct\n")
        f.write("- Vertical variance (within column) = tokenization matters\n")
        f.write("- All low scores = edition is wrong\n")
        f.write("- Target: ANY cell >= 90.0%\n")
        f.write("=" * 120 + "\n")
    
    print(f"\nMatrix output saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Text: {txt_file}")


def save_oracle_sweep_results(results: List[Dict], timestamp: str):
    """Save oracle sweep results to output files."""
    
    # Save CSV
    csv_file = f"output/oracle_sweep/sweep_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if results:
            fieldnames = ['rank', 'edition', 'tokenizer', 'word_count', 'char_match_pct', 
                         'word_match_pct', 'char_matches', 'total_chars', 'first_mismatch']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for i, result in enumerate(results, 1):
                row = {k: result[k] for k in fieldnames if k in result}
                row['rank'] = i
                writer.writerow(row)
    
    # Save matrix output
    save_oracle_matrix(results, timestamp)
    
    # Save detailed text report
    txt_file = f"output/oracle_sweep/sweep_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE A: DOI ORACLE SWEEP RESULTS\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE:\n")
        f.write("Find correct DOI edition + tokenization using Cipher 2 as validation.\n")
        f.write("Success threshold: >=90% character match\n\n")
        
        f.write(f"Combinations tested: {len(results)}\n\n")
        
        if results:
            f.write("=" * 80 + "\n")
            f.write("TOP 10 RESULTS\n")
            f.write("=" * 80 + "\n\n")
            
            for i, result in enumerate(results[:10], 1):
                f.write(f"RANK {i}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Edition: {result['edition']}\n")
                f.write(f"Tokenizer: {result['tokenizer']}\n")
                f.write(f"Word count: {result['word_count']}\n")
                f.write(f"Character match: {result['char_match_pct']:.2f}% "
                       f"({result['char_matches']}/{result['total_chars']})\n")
                f.write(f"Word match: {result['word_match_pct']:.2f}%\n")
                f.write(f"First mismatch: position {result['first_mismatch']}\n\n")
                f.write(f"Diff report:\n{result['diff_report']}\n\n")
                f.write(f"Decoded sample:\n{result['decoded_sample']}\n\n")
                f.write("=" * 80 + "\n\n")
            
            # All results summary
            f.write("\nALL RESULTS (ranked):\n")
            f.write("-" * 80 + "\n")
            for i, result in enumerate(results, 1):
                f.write(f"{i:2d}. {result['edition']:20s} + {result['tokenizer']:20s} | "
                       f"{result['char_match_pct']:6.2f}%\n")
        else:
            f.write("NO RESULTS: All editions are placeholders (not yet acquired).\n")
    
    print(f"Results saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Report: {txt_file}")


if __name__ == "__main__":
    results = run_oracle_sweep()
