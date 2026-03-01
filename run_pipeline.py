"""
Unified CLI Pipeline for Beale Cipher Analysis

Commands:
  - oracle_sweep: Run Phase A oracle sweep
  - lock_corpus: Lock validated corpus
  - decode_cipher: Decode cipher with CANON_DOI
  - cross_constraints: Generate cross-cipher constraints
  - search: Run constrained search
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def cmd_oracle_sweep(args):
    """Run Phase A oracle sweep."""
    from oracle.sweep_runner import run_oracle_sweep
    
    print("\nRunning Phase A: DOI Oracle Sweep")
    print("=" * 80)
    
    results = run_oracle_sweep()
    
    if results:
        best = results[0]
        print(f"\nBest result: {best['edition']} + {best['tokenizer']}")
        print(f"Match: {best['char_match_pct']:.2f}%")
        
        if best['char_match_pct'] >= 90.0:
            print("\n[RECOMMENDATION] Lock this corpus:")
            print(f"  python run_pipeline.py lock_corpus --edition {best['edition']} --tokenizer {best['tokenizer']}")
        elif best['char_match_pct'] >= 50.0:
            print("\n[RECOMMENDATION] Try drift models:")
            print("  python corpus/drift_models.py")
        else:
            print("\n[RECOMMENDATION] Acquire historical DOI editions")
    else:
        print("\n[ERROR] No valid editions to test (all placeholders)")
        print("[ACTION] Acquire historical DOI texts and save to corpus/editions/")


# Key post-patch anchors (must hold after net -12 edits)
_POST_PATCH_ANCHORS = {811: "fundamentally", 1005: "have"}


def _print_post_patch_anchor_check(base_tokens: list, patched_tokens: list):
    """Print post-patch anchor verification and len check."""
    print("\n" + "=" * 60)
    print("POST-PATCH ANCHOR CHECK")
    print("=" * 60)
    expected_len = len(base_tokens) - 12
    len_ok = len(patched_tokens) == expected_len
    print(f"  len(patched)={len(patched_tokens)} vs len(base)-12={expected_len} [{('PASS' if len_ok else 'FAIL')}]")
    for idx, expected in _POST_PATCH_ANCHORS.items():
        actual = patched_tokens[idx - 1] if idx <= len(patched_tokens) else "(out of range)"
        match = "OK" if actual == expected else "MISMATCH"
        print(f"  {idx:4}: \"{actual}\" (expected: {expected}) [{match}]")
    print("=" * 60)


# Anchor indices (1-indexed) and expected words for Beale DOI numbering verification
_BEALE_ANCHOR_EXPECTATIONS = {
    115: "instituted",
    154: "institute",
    157: "laying",
    240: "invariably",
    246: "design",
    466: "houses",
    495: "be",
    630: "eat",
    654: "to",
    677: "foreign",
    811: "fundamentally",
    819: "valuable",
    1005: "have",
}


def cmd_beale_patch_validate(args):
    """Run Beale DOI structural patch search and validate Cipher 2 oracle."""
    from corpus.beale_patch_tokenizer import load_nara_base_tokens
    from corpus.beale_structural_patch import run_structural_patch_search
    from oracle.cipher2_evaluator import (
        Cipher2Oracle,
        load_cipher2,
        load_cipher2_known_plaintext,
    )
    from pathlib import Path

    print("=" * 80)
    print("BEALE DOI PATCH VALIDATION")
    print("=" * 80)

    print("\n[Step 1] Loading nara_transcript and applying tokenization quirks...")
    base_tokens = load_nara_base_tokens()
    print(f"  Base tokens: {len(base_tokens)}")

    if getattr(args, 'anchors_only', False):
        print("\nANCHOR CHECK (1-indexed)")
        for idx in sorted(_BEALE_ANCHOR_EXPECTATIONS.keys()):
            expected = _BEALE_ANCHOR_EXPECTATIONS[idx]
            actual = base_tokens[idx - 1] if idx <= len(base_tokens) else "(out of range)"
            match = "OK" if actual == expected else "MISMATCH"
            print(f"  {idx:4}: \"{actual}\" (expected: {expected}) [{match}]")
        return

    # Control-patch mode: use deterministic content-based edits
    use_control_patch = getattr(args, 'control_patch', False)
    if use_control_patch:
        from corpus.beale_control_patch import run_control_patch
        print("\n[Step 2] Running deterministic control patch (Wikipedia-suggested edits)...")
        patched_tokens, score = run_control_patch(base_tokens)
        config = {}
    else:
        print("\n[Step 2] Running structural patch search (5 edits, sequential greedy)...")
        patched_tokens, score, config = run_structural_patch_search(base_tokens, verbose=True)

    # Post-patch anchor check (diagnostic)
    if getattr(args, 'post_patch_anchors', False):
        _print_post_patch_anchor_check(base_tokens, patched_tokens)
        return

    print("\n[Step 3] Saving patched edition...")
    editions_dir = Path("corpus/editions")
    editions_dir.mkdir(parents=True, exist_ok=True)
    patched_file = editions_dir / "nara_beale_patched.txt"
    with open(patched_file, 'w', encoding='utf-8') as f:
        f.write(' '.join(patched_tokens))
    print(f"  Saved: {patched_file}")
    print(f"  Patched tokens: {len(patched_tokens)}")

    print("\n[Step 4] Full Cipher 2 oracle evaluation (with 811->y, 1005->x overrides)...")
    cipher2 = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    oracle = Cipher2Oracle(known_plaintext)
    result = oracle.evaluate(patched_tokens, cipher2, letter_overrides={95: 'u', 811: 'y', 1005: 'x'})

    print("\n" + "=" * 80)
    print("BEALE PATCH VALIDATION RESULT")
    print("=" * 80)
    print(f"Total match: {result.char_match_pct:.2f}%")
    print(f"Regional: Early={result.match_by_region.get('early', 0):.1f}%, "
          f"Middle={result.match_by_region.get('middle', 0):.1f}%, "
          f"Late={result.match_by_region.get('late', 0):.1f}%")
    print(f"First mismatch: position {result.first_mismatch}")

    if result.char_match_pct >= 90.0:
        print("\n[SUCCESS] Cipher 2 oracle PASSED (>=90%)")
        print("ACTION: Lock corpus and rerun search:")
        print("  python run_pipeline.py lock_corpus --edition nara_beale_patched --tokenizer beale_patch_hyphen_split --oracle-score", f"{result.char_match_pct:.2f}")
        print("  python run_pipeline.py search_concurrent --topk 2000")
    else:
        print(f"\n[INFO] Oracle at {result.char_match_pct:.2f}% (target >=90%)")
        print("Check for residual transcription issues or adjust patch windows.")
    print("=" * 80)


def cmd_beale_pamphlet_validate(args):
    """Validate DOI from Beale pamphlet (PDF or beale_papers.txt) using marker anchors."""
    from corpus.beale_pamphlet_pdf import load_and_tokenize, load_pamphlet_raw
    from corpus.beale_doi_adjusted import get_adjusted_tokens
    from oracle.cipher2_evaluator import (
        Cipher2Oracle,
        load_cipher2,
        load_cipher2_known_plaintext,
    )
    from pathlib import Path

    print("=" * 80)
    print("BEALE PAMPHLET VALIDATION (marker-based)")
    print("=" * 80)

    pdf_path = getattr(args, "pdf_path", None)
    use_adjusted = not getattr(args, "no_adjusted", False)
    print("\n[Step 1] Loading pamphlet raw text...")
    raw = load_pamphlet_raw(pdf_path)
    if not raw:
        print("  [ERROR] No pamphlet text found. Check PDF path or beale_papers.txt.")
        return
    print(f"  Raw length: {len(raw)} chars")

    print("\n[Step 2] Extracting marker anchors and tokenizing...")
    tokens, anchors = load_and_tokenize(pdf_path)
    print(f"  Tokens: {len(tokens)}")
    print(f"  Markers extracted: {len(anchors)}")

    if getattr(args, "markers_only", False):
        print("\nMARKER ANCHOR TABLE (sample)")
        for idx in sorted(anchors.keys())[:30]:
            expected = anchors[idx]
            actual = tokens[idx - 1] if idx <= len(tokens) else "(OOR)"
            ok = "OK" if (idx <= len(tokens) and tokens[idx - 1].lower() == expected.lower()) else "MISMATCH"
            print(f"  {idx:4}: expected=\"{expected}\" actual=\"{actual}\" [{ok}]")
        if len(anchors) > 30:
            print(f"  ... and {len(anchors) - 30} more")
        return

    print("\n[Step 3] Marker validation...")
    passed = 0
    for idx, expected in anchors.items():
        actual = tokens[idx - 1].lower() if idx <= len(tokens) else ""
        if actual == expected.lower():
            passed += 1
    print(f"  Pass rate: {passed}/{len(anchors)} markers")

    oracle_tokens = get_adjusted_tokens() if use_adjusted else tokens
    if use_adjusted:
        print(f"\n[Step 4] Cipher 2 oracle (using beale_adjusted_doi, {len(oracle_tokens)} tokens)...")
    else:
        print("\n[Step 4] Cipher 2 oracle evaluation (using pamphlet tokens)...")
    cipher2_source = getattr(args, "cipher2_source", "canonical")
    if cipher2_source == "beale_papers":
        cipher2 = load_cipher2(path="beale_papers.txt")
        print("  (using beale_papers.txt for Cipher 2 numbers)")
    else:
        cipher2 = load_cipher2()  # uses canonical by default
        print("  (using canonical Cipher 2 numbers)")
    known_plaintext = load_cipher2_known_plaintext()
    oracle = Cipher2Oracle(known_plaintext)
    result = oracle.evaluate(oracle_tokens, cipher2, letter_overrides={95: "U", 811: "Y", 1005: "X"})

    print("\n" + "=" * 80)
    print("BEALE PAMPHLET VALIDATION RESULT")
    print("=" * 80)
    print(f"Marker pass rate: {passed}/{len(anchors)}")
    print(f"Cipher 2 oracle (strict): {result.char_match_pct:.2f}%")
    align = getattr(result, "alignment_pct", 0.0)
    if align > 0:
        print(f"Cipher 2 oracle (alignment): {align:.2f}%")
    print(f"First mismatch: position {result.first_mismatch}")
    align = getattr(result, "alignment_pct", 0.0)
    if align >= 89.5 or result.char_match_pct >= 90.0:
        print("\n[SUCCESS] Pamphlet DOI validated (alignment >= 89.5% or strict >= 90%)")
    else:
        print(f"\n[INFO] Strict: {result.char_match_pct:.2f}%, Alignment: {align:.2f}% (target: alignment >= 89.5%)")
    print("=" * 80)


def cmd_lock_corpus(args):
    """Lock corpus after oracle passes."""
    from corpus.canonical import lock_corpus_from_oracle_result
    
    if not args.edition or not args.tokenizer:
        print("[ERROR] Must specify --edition and --tokenizer")
        return
    
    # Get oracle score from user
    if args.oracle_score is None:
        print(f"\n[INFO] Locking corpus without oracle validation")
        print("       Use --oracle-score to record validation result")
        oracle_score = 0.0
    else:
        oracle_score = args.oracle_score
    
    corpus = lock_corpus_from_oracle_result(
        edition_id=args.edition,
        tokenizer_name=args.tokenizer,
        oracle_score=oracle_score,
        drift_model=None  # TODO: Support drift models
    )
    
    print(f"\n[SUCCESS] Corpus locked: corpus/CANON_DOI.json")


def cmd_decode_cipher(args):
    """Decode cipher with CANON_DOI."""
    if not args.cipher:
        print("[ERROR] Must specify --cipher {1,2,3}")
        return
    
    print(f"\n[TODO] Decode Cipher {args.cipher} with CANON_DOI")
    print("  This feature requires rebase/baseline_runner.py to be implemented")
    print("  See: docs/HYPOTHESIS_TREE.md for status")


def cmd_cross_constraints(args):
    """Generate cross-cipher constraints."""
    print("\n[TODO] Generate cross-cipher constraints")
    print("  This feature requires constraints/overlap_engine.py to be implemented")
    print("  See: docs/HYPOTHESIS_TREE.md for status")


def cmd_search(args):
    """Run constrained search."""
    print(f"\n[TODO] Run constrained search (budget: {args.budget})")
    print("  This feature requires constraints/filter_search.py to be implemented")
    print("  See: docs/HYPOTHESIS_TREE.md for status")


def cmd_acquire_editions(args):
    """Acquire historical DOI editions."""
    from scripts.acquire_doi_editions import manual_acquisition_guide, list_editions
    
    print("\nAcquiring DOI editions...")
    
    if args.editions == ['all']:
        manual_acquisition_guide()
        print("\n")
        list_editions()
    else:
        print(f"Editions requested: {args.editions}")
        print("\nUse 'python scripts/acquire_doi_editions.py' for detailed workflow")


def cmd_oracle_sweep_enhanced(args):
    """Run enhanced oracle sweep with matrix output."""
    from oracle.sweep_runner import run_oracle_sweep
    
    print("\nRunning Enhanced Oracle Sweep (Phase 8+9)")
    print("=" * 80)
    
    # Run standard sweep (already has matrix output after our modifications)
    results = run_oracle_sweep()
    
    if results:
        print("\n[SUCCESS] Oracle sweep complete with matrix output")
        print("Check: output/oracle_sweep/matrix_*.txt for visual comparison")


def cmd_search_concurrent(args):
    """Run concurrent Cipher 1+3 search."""
    from search.concurrent_search import run_concurrent_search_pipeline
    
    # Parse time budget
    time_budget_minutes = 30
    if args.time_budget.endswith('m'):
        time_budget_minutes = int(args.time_budget[:-1])
    elif args.time_budget.endswith('h'):
        time_budget_minutes = int(args.time_budget[:-1]) * 60
    
    run_concurrent_search_pipeline(args.topk, time_budget_minutes)


def cmd_stability_checks(args):
    """Run stability checks on strategy."""
    from validation.stability_checks import run_stability_batch
    
    run_stability_batch(args.strategy_file, args.cipher)


def cmd_cipher3_baseline(args):
    """Run Cipher 3 baseline analysis."""
    from analysis.cipher3_baseline_decode import run_cipher3_baseline_analysis, save_cipher3_baseline_results
    from datetime import datetime
    
    print("\nRunning Cipher 3 Baseline Analysis...")
    results = run_cipher3_baseline_analysis(topk=args.topk)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_cipher3_baseline_results(results, timestamp)
    
    print(f"\n[SUCCESS] Cipher 3 baseline analysis complete")


def cmd_hoax_test(args):
    """Run hoax hypothesis statistical tests."""
    from analysis.hoax_hypothesis_test import run_hoax_hypothesis_tests, save_hoax_test_results
    from datetime import datetime
    
    print("\nRunning Hoax Hypothesis Tests...")
    results = run_hoax_hypothesis_tests()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_hoax_test_results(results, timestamp)
    
    print(f"\n[SUCCESS] Hoax hypothesis tests complete")


def cmd_fragment_consensus(args):
    """Run fragment consensus analysis."""
    from analysis.fragment_consensus import find_consensus_fragments, save_consensus_results
    from datetime import datetime
    
    print(f"\nRunning Fragment Consensus Analysis (Cipher {args.cipher})...")
    results = find_consensus_fragments(
        cipher_num=args.cipher,
        topk=args.topk,
        min_consensus=args.min_consensus
    )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_consensus_results(results, timestamp)
    
    print(f"\n[SUCCESS] Fragment consensus analysis complete")


def cmd_anchor_diagnostic(args):
    """Run Phase 12A: Hard Anchor Testing."""
    from oracle.anchor_diagnostic import run_anchor_diagnostic
    
    run_anchor_diagnostic(args.positions)


def cmd_convention_tests(args):
    """Run Phase 12B: Word-Counting Convention Tests."""
    from oracle.convention_tests import run_convention_tests
    
    run_convention_tests(args.output_dir)


def cmd_offset_sweep(args):
    """Run Phase 12C/12D: Offset Sweep."""
    from oracle.offset_sweep import run_offset_sweep_pipeline
    
    run_offset_sweep_pipeline(
        mode=args.mode,
        output_dir=args.output_dir,
        offset_range=(args.offset_min, args.offset_max),
        segment_size=args.segment_size,
        k_range=(args.k_min, args.k_max, args.k_step)
    )


def cmd_phase13_discover(args):
    """Run Phase 13 Step A: Discover DOI Editions."""
    from scripts.discover_doi_sources import run_discovery
    from pathlib import Path
    
    run_discovery(Path(args.output_dir), Path(args.corpus_dir))


def cmd_phase13_tokenize(args):
    """Run Phase 13 Step B: Tokenize All Editions."""
    from scripts.phase13_tokenize import run_tokenization
    from pathlib import Path
    
    run_tokenization(Path(args.corpus_dir))


def cmd_phase13_cluster(args):
    """Run Phase 13 Step C: Edition Clustering."""
    from analysis.edition_alignment import run_edition_clustering, list_available_editions
    from pathlib import Path
    
    corpus_dir = Path(args.corpus_dir)
    output_dir = Path(args.output_dir)
    
    # Get editions
    if args.editions:
        editions = args.editions
    else:
        editions = list_available_editions(corpus_dir)
        if not editions:
            print("[ERROR] No editions found. Run phase13_tokenize first.")
            return
    
    run_edition_clustering(editions, args.tokenizer, corpus_dir, output_dir,
                          args.method, args.max_clusters)


def cmd_phase13_hmm_oracle(args):
    """Run Phase 13 Step D: HMM/Viterbi Offset Solver."""
    from oracle.hmm_offset_solver import run_hmm_oracle_sweep
    from pathlib import Path
    
    run_hmm_oracle_sweep(args.editions, args.tokenizers,
                        Path(args.corpus_dir), Path(args.output_dir), args.K)


def cmd_phase13_changepoints(args):
    """Run Phase 13 Step E: Changepoint Detection."""
    from analysis.changepoints import run_changepoint_sweep
    from pathlib import Path
    
    run_changepoint_sweep(args.editions, args.tokenizers,
                         Path(args.output_dir), args.penalty, args.n_bkps)


def cmd_phase13_rank(args):
    """Run Phase 13 Step F: Ranking + Acceptance Gates."""
    from oracle.phase13_ranker import run_ranking_and_gates
    from pathlib import Path
    
    run_ranking_and_gates(args.editions, args.tokenizers, Path(args.output_dir))


def cmd_phase13_lock_rerun(args):
    """Run Phase 13 Step G: Lock Corpus and Rerun Cipher 1+3."""
    from scripts.phase13_lock_rerun import run_lock_and_rerun
    from pathlib import Path
    
    run_lock_and_rerun(Path(args.corpus_dir), Path(args.output_dir))


def cmd_cipher2_diagnostic(args):
    """Run comprehensive Cipher 2 differential diagnostic."""
    from oracle.cipher2_diagnostic import run_baseline_diagnostic, save_baseline_diagnostic
    from oracle.formatting_variants import run_formatting_sweep
    from oracle.extraction_variants import run_extraction_sweep
    from datetime import datetime
    
    print("\n" + "=" * 80)
    print("PHASE 11: CIPHER 2 DIFFERENTIAL DIAGNOSTIC")
    print("=" * 80)
    print("\nMISSION: Diagnose 26.5% oracle mismatch BEFORE acquiring new editions")
    print("Tests: Positional heatmap, drift detection, formatting variants, extraction variants")
    print("=" * 80)
    
    output_dir = args.output_dir
    
    # Step 1: Baseline diagnostic
    print("\n[PHASE 11.1] Running baseline diagnostic...")
    baseline_results = run_baseline_diagnostic(args.edition, args.tokenizer)
    save_baseline_diagnostic(baseline_results, output_dir)
    
    baseline_score = baseline_results['oracle_score']
    
    # Step 2: Formatting variant sweep (unless skipped)
    formatting_results = None
    if not args.skip_formatting:
        print("\n[PHASE 11.2] Running formatting variant sweep...")
        formatting_results = run_formatting_sweep(output_dir)
    else:
        print("\n[PHASE 11.2] Formatting sweep SKIPPED by user")
        formatting_results = {'best_score': baseline_score, 'best_config_name': 'skipped'}
    
    # Step 3: Extraction variant sweep (unless skipped or formatting succeeded)
    extraction_results = None
    if not args.skip_extraction and formatting_results['best_score'] < 50.0:
        print("\n[PHASE 11.3] Running extraction variant sweep...")
        extraction_results = run_extraction_sweep(args.edition, args.tokenizer, output_dir)
    elif args.skip_extraction:
        print("\n[PHASE 11.3] Extraction sweep SKIPPED by user")
    else:
        print("\n[PHASE 11.3] Extraction sweep SKIPPED (formatting improved oracle >50%)")
    
    # Generate comprehensive verdict
    print("\n[PHASE 11.4] Generating diagnostic verdict...")
    
    best_score = baseline_score
    best_method = f"{args.edition} + {args.tokenizer} (baseline)"
    
    if formatting_results and formatting_results['best_score'] > best_score:
        best_score = formatting_results['best_score']
        best_method = f"formatting: {formatting_results['best_config_name']}"
    
    if extraction_results and extraction_results['best_score'] > best_score:
        best_score = extraction_results['best_score']
        best_method = f"extraction: {extraction_results['best_rule']}"
    
    # Print summary
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"\nBaseline oracle: {baseline_score:.2f}%")
    
    if formatting_results and not args.skip_formatting:
        print(f"Best formatting variant: {formatting_results['best_score']:.2f}%")
        print(f"Improvement: +{formatting_results['best_score'] - baseline_score:.2f}%")
    
    if extraction_results:
        print(f"Best extraction rule: {extraction_results['best_score']:.2f}%")
    
    print(f"\nOverall best: {best_score:.2f}%")
    print(f"Method: {best_method}")
    
    # Drift analysis
    drift = baseline_results['drift_analysis']
    print(f"\nDrift detected: {drift['drift_type']}")
    print(f"Drift coefficient: {drift['drift_coefficient']:.4f}")
    print(f"Regional matches: Early={drift['match_early']:.1f}%, "
          f"Middle={drift['match_middle']:.1f}%, Late={drift['match_late']:.1f}%")
    
    # Mismatch distribution
    mismatch = baseline_results['mismatch_analysis']
    print(f"\nMismatch distribution: {mismatch['distribution']}")
    print(f"Detected clusters: {len(mismatch['clusters'])}")
    
    # Decision logic
    print("\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)
    
    improvement = best_score - baseline_score
    
    if best_score >= 90.0:
        print("\n[BREAKTHROUGH] Formatting/extraction variant achieves ≥90% oracle!")
        print(f"Best config: {best_method}")
        print("[RECOMMENDATION] Lock this configuration and skip edition acquisition")
        verdict = "BREAKTHROUGH"
    elif improvement > 10:
        print("\n[SIGNIFICANT] Formatting/extraction improves oracle by >10%")
        print(f"Best config: {best_method}")
        print("[RECOMMENDATION] Further optimize formatting before acquiring editions")
        verdict = "PARTIAL_SUCCESS"
    elif improvement > 5:
        print("\n[MODERATE] Some improvement from formatting/extraction")
        print("[RECOMMENDATION] Formatting matters, but edition likely also matters")
        print("                 Acquire Stone 1823 with attention to formatting")
        verdict = "FORMATTING_RELEVANT"
    else:
        print("\n[CONFIRMED] Formatting/extraction variants do not explain 26.5%")
        print("[RECOMMENDATION] Proceed with Stone 1823 acquisition")
        print("                 Edition mismatch confirmed as root cause")
        verdict = "EDITION_MISMATCH"
    
    # Save comprehensive verdict
    verdict_data = {
        'generated': datetime.now().isoformat(),
        'baseline_score': baseline_score,
        'best_score': best_score,
        'improvement': improvement,
        'best_method': best_method,
        'verdict': verdict,
        'drift_analysis': baseline_results['drift_analysis'],
        'mismatch_analysis': baseline_results['mismatch_analysis']
    }
    
    verdict_file = Path(output_dir) / "DIAGNOSTIC_VERDICT.txt"
    with open(verdict_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 11: CIPHER 2 DIFFERENTIAL DIAGNOSTIC - FINAL VERDICT\n")
        f.write(f"Generated: {verdict_data['generated']}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("RESULTS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Baseline oracle: {baseline_score:.2f}%\n")
        f.write(f"Best achievable: {best_score:.2f}%\n")
        f.write(f"Improvement: +{improvement:.2f}%\n")
        f.write(f"Best method: {best_method}\n\n")
        
        f.write("VERDICT\n")
        f.write("-" * 80 + "\n")
        f.write(f"{verdict}\n\n")
        
        f.write("INTERPRETATION\n")
        f.write("-" * 80 + "\n")
        f.write(f"Drift type: {drift['drift_type']}\n")
        f.write(f"{drift['interpretation']}\n\n")
        
        f.write("RECOMMENDATION\n")
        f.write("-" * 80 + "\n")
        
        if verdict == "BREAKTHROUGH":
            f.write("Oracle passed with formatting/extraction optimization!\n")
            f.write("Action: Lock this configuration and proceed to Cipher 1/3 search.\n")
        elif verdict == "EDITION_MISMATCH":
            f.write("Formatting/extraction cannot explain 26.5% mismatch.\n")
            f.write("Action: Acquire Stone Engraving 1823 (temporal proximity to Beale era).\n")
            f.write("Expected: Stone 1823 likely to score 80-95% on oracle.\n")
        else:
            f.write("Formatting provides partial improvement but insufficient.\n")
            f.write("Action: Acquire Stone 1823 AND test formatting variants on it.\n")
    
    print(f"\n[SUCCESS] Comprehensive diagnostic verdict saved: {verdict_file}")
    
    return verdict_data


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Beale Cipher Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run oracle sweep
  python run_pipeline.py oracle_sweep
  
  # Lock corpus after oracle passes
  python run_pipeline.py lock_corpus --edition beale_embedded --tokenizer hyphen_keep --oracle-score 95.5
  
  # Decode cipher with locked corpus
  python run_pipeline.py decode_cipher --cipher 1 --topk 50
  
  # Generate cross-cipher constraints
  python run_pipeline.py cross_constraints
  
  # Run constrained search
  python run_pipeline.py search --budget 1000
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Oracle sweep
    parser_oracle = subparsers.add_parser('oracle_sweep',
                                          help='Run Phase A oracle sweep')
    parser_oracle.set_defaults(func=cmd_oracle_sweep)
    
    # Lock corpus
    parser_lock = subparsers.add_parser('lock_corpus',
                                        help='Lock validated corpus')
    parser_lock.add_argument('--edition', required=True,
                            help='DOI edition ID')
    parser_lock.add_argument('--tokenizer', required=True,
                            help='Tokenizer preset name')
    parser_lock.add_argument('--oracle-score', type=float,
                            help='Oracle match percentage')
    parser_lock.set_defaults(func=cmd_lock_corpus)

    # Beale DOI patch validation
    parser_beale = subparsers.add_parser('beale_patch_validate',
                                        help='Run Beale DOI structural patch search and validate Cipher 2')
    parser_beale.add_argument('--anchors-only', action='store_true',
                             help='Print anchor tokens and expected words, then exit (no patch search)')
    parser_beale.add_argument('--post-patch-anchors', action='store_true',
                             help='Run patch search, then print anchor check on patched tokens')
    parser_beale.add_argument('--control-patch', action='store_true',
                             help='Use deterministic Wikipedia-suggested edits instead of search')
    parser_beale.set_defaults(func=cmd_beale_patch_validate)

    # Beale pamphlet (PDF / beale_papers.txt) validation
    parser_pamphlet = subparsers.add_parser("beale_pamphlet_validate",
                                           help="Validate DOI from Beale pamphlet using marker anchors")
    parser_pamphlet.add_argument("--pdf-path", type=str,
                                help="Path to Beale Papers PDF (default: corpus/raw_sources/beale_pamphlet/beale_papers.pdf)")
    parser_pamphlet.add_argument("--markers-only", action="store_true",
                                help="Print marker table and exit (no oracle)")
    parser_pamphlet.add_argument("--no-adjusted", action="store_true",
                                help="Use raw pamphlet tokens for oracle (default: use beale_adjusted_doi)")
    parser_pamphlet.add_argument("--cipher2-source", choices=["canonical", "beale_papers"],
                                default="canonical",
                                help="Cipher 2 number list source (default: canonical)")
    parser_pamphlet.set_defaults(func=cmd_beale_pamphlet_validate, use_adjusted=True)

    # Decode cipher
    parser_decode = subparsers.add_parser('decode_cipher',
                                         help='Decode cipher with CANON_DOI')
    parser_decode.add_argument('--cipher', type=int, choices=[1,2,3], required=True,
                              help='Cipher number to decode')
    parser_decode.add_argument('--topk', type=int, default=50,
                              help='Number of top strategies to return')
    parser_decode.set_defaults(func=cmd_decode_cipher)
    
    # Cross constraints
    parser_cross = subparsers.add_parser('cross_constraints',
                                         help='Generate cross-cipher constraints')
    parser_cross.set_defaults(func=cmd_cross_constraints)
    
    # Search
    parser_search = subparsers.add_parser('search',
                                         help='Run constrained search')
    parser_search.add_argument('--budget', type=int, default=1000,
                              help='Maximum strategies to evaluate')
    parser_search.set_defaults(func=cmd_search)
    
    # Phase 8+9 commands
    
    # Acquire DOI editions
    parser_acquire = subparsers.add_parser('acquire_editions',
                                          help='Acquire historical DOI editions')
    parser_acquire.add_argument('--editions', nargs='+', default=['all'],
                               help='Edition IDs to acquire')
    parser_acquire.set_defaults(func=cmd_acquire_editions)
    
    # Enhanced oracle sweep
    parser_oracle_enh = subparsers.add_parser('oracle_sweep_enhanced',
                                             help='Enhanced oracle with matrix output')
    parser_oracle_enh.add_argument('--editions', default='all',
                                  help='Edition IDs to test (default: all)')
    parser_oracle_enh.add_argument('--presets', default='all',
                                  help='Tokenizer presets (default: all)')
    parser_oracle_enh.set_defaults(func=cmd_oracle_sweep_enhanced)
    
    # Concurrent search
    parser_concurrent = subparsers.add_parser('search_concurrent',
                                            help='Concurrent Cipher 1+3 search')
    parser_concurrent.add_argument('--topk', type=int, default=2000,
                                  help='Maximum strategies to evaluate')
    parser_concurrent.add_argument('--time-budget', type=str, default='30m',
                                  help='Time budget (e.g., 30m, 1h)')
    parser_concurrent.set_defaults(func=cmd_search_concurrent)
    
    # Stability checks
    parser_stability = subparsers.add_parser('stability_checks',
                                           help='Run stability checks on strategy')
    parser_stability.add_argument('--strategy-file', required=True,
                                 help='Path to strategy config JSON')
    parser_stability.add_argument('--cipher', type=int, default=1, choices=[1,2,3],
                                 help='Cipher number to test')
    parser_stability.set_defaults(func=cmd_stability_checks)
    
    # Phase 10 commands
    
    # Cipher 3 baseline analysis
    parser_c3_baseline = subparsers.add_parser('cipher3_baseline',
                                              help='Run Cipher 3 baseline decoding and semantic analysis')
    parser_c3_baseline.add_argument('--topk', type=int, default=25,
                                   help='Number of strategies to test')
    parser_c3_baseline.set_defaults(func=cmd_cipher3_baseline)
    
    # Hoax hypothesis test
    parser_hoax = subparsers.add_parser('hoax_test',
                                       help='Run statistical hoax hypothesis tests')
    parser_hoax.set_defaults(func=cmd_hoax_test)
    
    # Fragment consensus
    parser_fragments = subparsers.add_parser('fragment_consensus',
                                            help='Find consensus fragments across strategies')
    parser_fragments.add_argument('--cipher', type=int, default=1, choices=[1,2,3],
                                 help='Cipher number to analyze')
    parser_fragments.add_argument('--topk', type=int, default=20,
                                 help='Number of strategies to test')
    parser_fragments.add_argument('--min-consensus', type=int, default=3,
                                 help='Minimum strategies that must agree')
    parser_fragments.set_defaults(func=cmd_fragment_consensus)
    
    # Phase 11 commands
    
    # Cipher 2 differential diagnostic
    parser_c2_diag = subparsers.add_parser('cipher2_diagnostic',
                                          help='Comprehensive Cipher 2 diagnostic (baseline + formatting + extraction)')
    parser_c2_diag.add_argument('--edition', default='beale_embedded',
                               help='DOI edition to test')
    parser_c2_diag.add_argument('--tokenizer', default='hyphen_keep',
                               help='Tokenizer to use for baseline')
    parser_c2_diag.add_argument('--output-dir', default='output/oracle_diagnostic',
                               help='Output directory')
    parser_c2_diag.add_argument('--skip-formatting', action='store_true',
                               help='Skip formatting variant sweep')
    parser_c2_diag.add_argument('--skip-extraction', action='store_true',
                               help='Skip extraction variant sweep')
    parser_c2_diag.set_defaults(func=cmd_cipher2_diagnostic)
    
    # Phase 12 commands
    
    # Phase 12A: Anchor diagnostic
    parser_anchor = subparsers.add_parser('anchor_diagnostic',
                                         help='Phase 12A: Hard anchor testing - inspect first N positions')
    parser_anchor.add_argument('--positions', type=int, default=20,
                              help='Number of positions to analyze (default: 20)')
    parser_anchor.set_defaults(func=cmd_anchor_diagnostic)
    
    # Phase 12B: Convention tests
    parser_convention = subparsers.add_parser('convention_tests',
                                             help='Phase 12B: Word-counting convention tests')
    parser_convention.add_argument('--output-dir', default='output/oracle_diagnostic',
                                  help='Output directory for results')
    parser_convention.set_defaults(func=cmd_convention_tests)
    
    # Phase 12C/12D: Offset sweep
    parser_offset = subparsers.add_parser('offset_sweep',
                                         help='Phase 12C/12D: Constant and progressive offset sweep')
    parser_offset.add_argument('--mode', choices=['constant', 'progressive'], default='constant',
                              help='Offset mode: constant (12C) or progressive (12D)')
    parser_offset.add_argument('--output-dir', default='output/oracle_diagnostic',
                              help='Output directory for results')
    parser_offset.add_argument('--offset-min', type=int, default=-5,
                              help='Minimum offset for constant mode')
    parser_offset.add_argument('--offset-max', type=int, default=5,
                              help='Maximum offset for constant mode')
    parser_offset.add_argument('--segment-size', type=int, default=100,
                              help='Early segment size for constant mode')
    parser_offset.add_argument('--k-min', type=float, default=-0.1,
                              help='Minimum k for progressive mode')
    parser_offset.add_argument('--k-max', type=float, default=0.1,
                              help='Maximum k for progressive mode')
    parser_offset.add_argument('--k-step', type=float, default=0.01,
                              help='Step size for k in progressive mode')
    parser_offset.set_defaults(func=cmd_offset_sweep)
    
    # Phase 13 commands
    
    # Step A: Discover DOI editions
    parser_p13_discover = subparsers.add_parser('phase13_discover',
                                               help='Phase 13 Step A: Discover and acquire DOI editions')
    parser_p13_discover.add_argument('--output-dir', default='.',
                                    help='Project root for output/phase13')
    parser_p13_discover.add_argument('--corpus-dir', default='corpus',
                                    help='Corpus directory for editions and raw_sources')
    parser_p13_discover.set_defaults(func=cmd_phase13_discover)
    
    # Step B: Tokenize editions
    parser_p13_tokenize = subparsers.add_parser('phase13_tokenize',
                                               help='Phase 13 Step B: Tokenize all editions with all tokenizers')
    parser_p13_tokenize.add_argument('--corpus-dir', default='corpus',
                                    help='Corpus directory')
    parser_p13_tokenize.set_defaults(func=cmd_phase13_tokenize)
    
    # Step C: Edition clustering
    parser_p13_cluster = subparsers.add_parser('phase13_cluster',
                                              help='Phase 13 Step C: Cluster editions via alignment')
    parser_p13_cluster.add_argument('--corpus-dir', default='corpus',
                                   help='Corpus directory')
    parser_p13_cluster.add_argument('--output-dir', default='output/phase13',
                                   help='Output directory')
    parser_p13_cluster.add_argument('--tokenizer', default='hyphen_keep',
                                   help='Tokenizer to use for clustering')
    parser_p13_cluster.add_argument('--method', default='difflib', choices=['difflib', 'levenshtein'],
                                   help='Similarity method')
    parser_p13_cluster.add_argument('--max-clusters', type=int, default=10,
                                   help='Maximum number of clusters')
    parser_p13_cluster.add_argument('--editions', nargs='+',
                                   help='Specific editions to cluster')
    parser_p13_cluster.set_defaults(func=cmd_phase13_cluster)
    
    # Step D: HMM oracle
    parser_p13_hmm = subparsers.add_parser('phase13_hmm_oracle',
                                          help='Phase 13 Step D: HMM/Viterbi offset path solver')
    parser_p13_hmm.add_argument('--corpus-dir', default='corpus',
                               help='Corpus directory')
    parser_p13_hmm.add_argument('--output-dir', default='output/phase13',
                               help='Output directory')
    parser_p13_hmm.add_argument('--editions', nargs='+', required=True,
                               help='Edition IDs to solve')
    parser_p13_hmm.add_argument('--tokenizers', nargs='+', default=['hyphen_keep'],
                               help='Tokenizer names')
    parser_p13_hmm.add_argument('--K', type=int, default=50,
                               help='Max offset magnitude')
    parser_p13_hmm.set_defaults(func=cmd_phase13_hmm_oracle)
    
    # Step E: Changepoints
    parser_p13_cp = subparsers.add_parser('phase13_changepoints',
                                         help='Phase 13 Step E: Changepoint detection')
    parser_p13_cp.add_argument('--output-dir', default='output/phase13',
                              help='Output directory')
    parser_p13_cp.add_argument('--editions', nargs='+', required=True,
                              help='Edition IDs')
    parser_p13_cp.add_argument('--tokenizers', nargs='+', default=['hyphen_keep'],
                              help='Tokenizer names')
    parser_p13_cp.add_argument('--penalty', type=float, default=10.0,
                              help='PELT penalty')
    parser_p13_cp.add_argument('--n-bkps', type=int, default=5,
                              help='BinSeg number of breakpoints')
    parser_p13_cp.set_defaults(func=cmd_phase13_changepoints)
    
    # Step F: Ranking
    parser_p13_rank = subparsers.add_parser('phase13_rank',
                                           help='Phase 13 Step F: Ranking and acceptance gates')
    parser_p13_rank.add_argument('--output-dir', default='output/phase13',
                                help='Output directory')
    parser_p13_rank.add_argument('--editions', nargs='+', required=True,
                                help='Edition IDs')
    parser_p13_rank.add_argument('--tokenizers', nargs='+', default=['hyphen_keep'],
                                help='Tokenizer names')
    parser_p13_rank.set_defaults(func=cmd_phase13_rank)
    
    # Step G: Lock and rerun
    parser_p13_lock = subparsers.add_parser('phase13_lock_rerun',
                                           help='Phase 13 Step G: Lock corpus and rerun Cipher 1+3')
    parser_p13_lock.add_argument('--corpus-dir', default='corpus',
                                help='Corpus directory')
    parser_p13_lock.add_argument('--output-dir', default='output/phase13',
                                help='Output directory')
    parser_p13_lock.set_defaults(func=cmd_phase13_lock_rerun)
    
    # Parse args
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    args.func(args)


if __name__ == "__main__":
    main()
