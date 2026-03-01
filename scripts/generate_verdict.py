"""
Final Verdict Report Generator

Synthesizes all Phase 8+9 results into a comprehensive analysis report:
- Oracle sweep results (matrix, best edition)
- Concurrent search results (top strategies, composite scores)
- Stability check results (pass/fail for top strategies)
- Cross-cipher overlap analysis
- Final GO/NO-GO decision
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse


def load_oracle_results(oracle_file: str) -> Dict:
    """Load oracle sweep results."""
    if not Path(oracle_file).exists():
        print(f"[WARNING] Oracle results not found: {oracle_file}")
        return {}
    
    # Load CSV
    results = []
    with open(oracle_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    
    return {
        'file': oracle_file,
        'results': results,
        'best': results[0] if results else None,
        'count': len(results)
    }


def load_search_results(search_file: str) -> Dict:
    """Load concurrent search results."""
    if not Path(search_file).exists():
        print(f"[WARNING] Search results not found: {search_file}")
        return {}
    
    results = []
    with open(search_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    
    return {
        'file': search_file,
        'results': results,
        'best': results[0] if results else None,
        'count': len(results)
    }


def load_stability_results(stability_file: str) -> Dict:
    """Load stability check results."""
    if not Path(stability_file).exists():
        print(f"[WARNING] Stability results not found: {stability_file}")
        return {}
    
    # Assume text format summary
    with open(stability_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return {
        'file': stability_file,
        'content': content,
        'summary': content[:500]  # First 500 chars
    }


def load_overlap_results(overlap_file: str) -> Dict:
    """Load overlap analysis results."""
    if not Path(overlap_file).exists():
        print(f"[WARNING] Overlap results not found: {overlap_file}")
        return {}
    
    with open(overlap_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_verdict_report(oracle_file: str, search_file: Optional[str] = None,
                           stability_file: Optional[str] = None,
                           overlap_file: Optional[str] = None,
                           output_file: str = "output/phase89/FINAL_VERDICT.txt"):
    """Generate comprehensive final verdict report."""
    
    print("=" * 80)
    print("PHASE 8+9: FINAL VERDICT REPORT GENERATION")
    print("=" * 80)
    
    # Load results
    print("\n[Step 1] Loading results...")
    oracle_data = load_oracle_results(oracle_file)
    search_data = load_search_results(search_file) if search_file else {}
    stability_data = load_stability_results(stability_file) if stability_file else {}
    overlap_data = load_overlap_results(overlap_file) if overlap_file else {}
    
    print(f"  Oracle results: {'Loaded' if oracle_data else 'Missing'}")
    print(f"  Search results: {'Loaded' if search_data else 'Missing'}")
    print(f"  Stability results: {'Loaded' if stability_data else 'Missing'}")
    print(f"  Overlap results: {'Loaded' if overlap_data else 'Missing'}")
    
    # Generate report
    print("\n[Step 2] Generating report...")
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("PHASE 8+9: FULL NUCLEAR EDITION ACQUISITION + CROSS-CIPHER ATTACK\n")
        f.write("FINAL VERDICT REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"\nGenerated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        # Executive Summary
        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 80 + "\n\n")
        
        oracle_score = 0.0
        oracle_edition = "unknown"
        oracle_tokenizer = "unknown"
        
        if oracle_data and oracle_data.get('best'):
            best_oracle = oracle_data['best']
            oracle_score = float(best_oracle.get('char_match_pct', 0))
            oracle_edition = best_oracle.get('edition', 'unknown')
            oracle_tokenizer = best_oracle.get('tokenizer', 'unknown')
        
        f.write(f"Oracle Status:\n")
        f.write(f"  Best Match: {oracle_score:.2f}%\n")
        f.write(f"  Edition: {oracle_edition}\n")
        f.write(f"  Tokenizer: {oracle_tokenizer}\n")
        f.write(f"  Threshold: 90.0% (required for GO)\n\n")
        
        if oracle_score >= 90.0:
            verdict = "GO"
            verdict_desc = "Oracle passed - corpus validated"
        elif oracle_score >= 80.0:
            verdict = "CONDITIONAL"
            verdict_desc = "Oracle close - consider drift models or acquire more editions"
        else:
            verdict = "NO-GO"
            verdict_desc = "Oracle failed - must acquire historical DOI editions"
        
        f.write(f"VERDICT: {verdict}\n")
        f.write(f"  {verdict_desc}\n\n")
        
        # Oracle Sweep Section
        f.write("=" * 80 + "\n")
        f.write("1. ORACLE SWEEP RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        if oracle_data and oracle_data.get('results'):
            f.write(f"Combinations Tested: {oracle_data['count']}\n\n")
            
            f.write("Top 10 Results:\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Rank':<6s} {'Edition':<25s} {'Tokenizer':<25s} {'Match %':<10s}\n")
            f.write("-" * 80 + "\n")
            
            for i, result in enumerate(oracle_data['results'][:10], 1):
                f.write(f"{i:<6d} {result.get('edition', ''):<25s} "
                       f"{result.get('tokenizer', ''):<25s} "
                       f"{result.get('char_match_pct', '0'):<10s}\n")
            
            f.write("\n")
            
            if oracle_score >= 90.0:
                f.write("DECISION: PASS - Corpus is validated\n")
                f.write(f"  Lock corpus: python run_pipeline.py lock_corpus "
                       f"--edition {oracle_edition} --tokenizer {oracle_tokenizer}\n\n")
            else:
                f.write("DECISION: FAIL - Corpus not validated\n")
                f.write("  Next steps:\n")
                f.write("  1. Acquire more historical DOI editions\n")
                f.write("  2. Visit LOC, NARA, Yale Avalon for authoritative transcripts\n")
                f.write("  3. Test additional tokenization variants\n")
                f.write("  4. Consider drift models if close to threshold\n\n")
        else:
            f.write("NO RESULTS AVAILABLE\n\n")
        
        # Overlap Analysis Section
        f.write("=" * 80 + "\n")
        f.write("2. CROSS-CIPHER OVERLAP ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        
        if overlap_data:
            counts = overlap_data.get('overlaps', {}).get('counts', {})
            f.write(f"Cipher 1 AND 2 overlaps: {counts.get('overlap_12', 0)} numbers\n")
            f.write(f"Cipher 1 AND 3 overlaps: {counts.get('overlap_13', 0)} numbers\n")
            f.write(f"Cipher 2 AND 3 overlaps: {counts.get('overlap_23', 0)} numbers\n")
            f.write(f"All three ciphers: {counts.get('overlap_all', 0)} numbers\n\n")
            
            high_freq = overlap_data.get('high_frequency_overlaps', [])
            f.write(f"High-frequency overlaps (>=10 occurrences): {len(high_freq)}\n\n")
            
            if high_freq:
                f.write("Top 10 high-frequency overlap numbers:\n")
                f.write(f"{'Number':<10s} {'C1':<6s} {'C2':<6s} {'C3':<6s} {'Total':<6s}\n")
                f.write("-" * 40 + "\n")
                for item in high_freq[:10]:
                    f.write(f"{item['number']:<10d} {item['freq_c1']:<6d} "
                           f"{item['freq_c2']:<6d} {item['freq_c3']:<6d} "
                           f"{item['total_freq']:<6d}\n")
                f.write("\n")
            
            f.write("IMPLICATIONS:\n")
            f.write(f"- {counts.get('overlap_12', 0)} Cipher 1-2 overlaps can be used as hard constraints\n")
            f.write("  once oracle passes (>=90%)\n")
            f.write(f"- {len(high_freq)} high-frequency numbers suggest homophonic behavior\n")
            f.write("  or common words (the, of, and, etc.)\n\n")
        else:
            f.write("NO RESULTS AVAILABLE\n")
            f.write("Run: python analysis/overlap_frequency_analysis.py\n\n")
        
        # Concurrent Search Section
        f.write("=" * 80 + "\n")
        f.write("3. CONCURRENT CIPHER 1+3 SEARCH RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        if search_data and search_data.get('results'):
            f.write(f"Strategies Evaluated: {search_data['count']}\n\n")
            
            f.write("Top 10 Strategies:\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Rank':<6s} {'Extractor':<25s} {'Transposition':<25s} {'Composite':<10s}\n")
            f.write("-" * 80 + "\n")
            
            for i, result in enumerate(search_data['results'][:10], 1):
                f.write(f"{i:<6d} {result.get('extractor', ''):<25s} "
                       f"{result.get('transposition', ''):<25s} "
                       f"{result.get('composite_score', '0'):<10s}\n")
            
            f.write("\n")
            
            if oracle_score >= 90.0:
                f.write("NOTE: Search results are meaningful (corpus validated)\n\n")
            else:
                f.write("WARNING: Search results may not be meaningful (corpus not validated)\n")
                f.write("Recommend waiting until oracle passes before interpreting results\n\n")
        else:
            if oracle_score >= 90.0:
                f.write("NO RESULTS AVAILABLE\n")
                f.write("Run: python run_pipeline.py search_concurrent --topk 2000\n\n")
            else:
                f.write("SKIPPED - Oracle has not passed yet\n")
                f.write("Complete oracle sweep and lock corpus before running search\n\n")
        
        # Stability Checks Section
        f.write("=" * 80 + "\n")
        f.write("4. STABILITY CHECKS\n")
        f.write("=" * 80 + "\n\n")
        
        if stability_data:
            f.write("Summary:\n")
            f.write(stability_data.get('summary', 'See detailed report for full results'))
            f.write("\n\n")
        else:
            if oracle_score >= 90.0 and search_data:
                f.write("NO RESULTS AVAILABLE\n")
                f.write("Run stability checks on top strategies:\n")
                f.write("  python run_pipeline.py stability_checks --strategy-file <config.json>\n\n")
            else:
                f.write("SKIPPED - Prerequisites not met\n\n")
        
        # Recommendations Section
        f.write("=" * 80 + "\n")
        f.write("5. RECOMMENDATIONS\n")
        f.write("=" * 80 + "\n\n")
        
        if verdict == "GO":
            f.write("ORACLE PASSED - PROCEED WITH FULL ANALYSIS\n\n")
            f.write("Immediate next steps:\n")
            f.write(f"1. Lock corpus: python run_pipeline.py lock_corpus "
                   f"--edition {oracle_edition} --tokenizer {oracle_tokenizer}\n")
            f.write("2. Run concurrent search: python run_pipeline.py search_concurrent --topk 2000\n")
            f.write("3. Run stability checks on top 20 strategies\n")
            f.write("4. Analyze fragment consensus across strategies\n")
            f.write("5. Validate with Beale-specific cribs (bedford, county, virginia)\n\n")
        
        elif verdict == "CONDITIONAL":
            f.write("ORACLE CLOSE BUT NOT PASSED\n\n")
            f.write("Options:\n")
            f.write("A. Acquire more historical DOI editions:\n")
            f.write("   - Search for 1820s Virginia political handbooks\n")
            f.write("   - Check alternative Stone engraving transcripts\n")
            f.write("   - Verify Beale pamphlet's embedded DOI text\n\n")
            f.write("B. Implement drift models (corpus/drift_models.py):\n")
            f.write("   - Progressive numbering offset\n")
            f.write("   - Periodic heading inserts\n")
            f.write("   - Line-wrap simulation\n\n")
            f.write("C. Test additional tokenization edge cases:\n")
            f.write("   - Header line inclusion/exclusion\n")
            f.write("   - Signer names inclusion/exclusion\n")
            f.write("   - Hyphenation variants\n\n")
        
        else:  # NO-GO
            f.write("ORACLE FAILED - CORPUS ACQUISITION REQUIRED\n\n")
            f.write("Critical action items:\n")
            f.write("1. Acquire authoritative historical DOI editions:\n")
            f.write("   a. Dunlap Broadside 1776 (LOC Digital Collection)\n")
            f.write("   b. Stone Engraving 1823 (NARA, closest to Beale era)\n")
            f.write("   c. Goddard Printing 1777 (Baltimore, official version)\n")
            f.write("   d. 1820s Virginia reprints (period-appropriate)\n\n")
            f.write("2. Save editions to: corpus/editions/<edition_id>.txt\n\n")
            f.write("3. Register editions:\n")
            f.write("   python scripts/acquire_doi_editions.py register <edition_id>\n\n")
            f.write("4. Re-run oracle sweep:\n")
            f.write("   python run_pipeline.py oracle_sweep_enhanced\n\n")
            f.write("DO NOT proceed with search until oracle passes (>=90%)\n\n")
        
        # Footer
        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")
    
    print(f"\n[SUCCESS] Verdict report saved: {output_path}")
    
    # Print summary to console
    print("\n" + "=" * 80)
    print("VERDICT SUMMARY")
    print("=" * 80)
    print(f"\nOracle Score: {oracle_score:.2f}% (threshold: 90.0%)")
    print(f"Verdict: {verdict}")
    print(f"Description: {verdict_desc}")
    
    if verdict == "GO":
        print("\n[SUCCESS] Ready for full analysis")
    elif verdict == "CONDITIONAL":
        print("\n[WARNING] Close but not passing - acquire more editions or use drift models")
    else:
        print("\n[BLOCKED] Must acquire historical DOI editions before proceeding")
    
    return verdict


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive Phase 8+9 verdict report",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--oracle-results', required=True,
                       help='Path to oracle sweep matrix CSV')
    parser.add_argument('--search-results', default=None,
                       help='Path to concurrent search results CSV')
    parser.add_argument('--stability-results', default=None,
                       help='Path to stability summary file')
    parser.add_argument('--overlap-results', default=None,
                       help='Path to overlap analysis JSON')
    parser.add_argument('--output', default='output/phase89/FINAL_VERDICT.txt',
                       help='Output path for verdict report')
    
    args = parser.parse_args()
    
    verdict = generate_verdict_report(
        oracle_file=args.oracle_results,
        search_file=args.search_results,
        stability_file=args.stability_results,
        overlap_file=args.overlap_results,
        output_file=args.output
    )
    
    return verdict


if __name__ == "__main__":
    main()
