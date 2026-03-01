"""
PHASE 5 SANITY CHECK
Verify invariants before proceeding with Phase 5 search.
"""

import re
from datetime import datetime
import extractors
import transposition
import signal_score


def load_doi_from_beale():
    """Load DOI exactly as used in Cipher 2 decoding"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Line 55 (index 54) contains numbered Declaration
    doi_line = lines[54]
    
    # Extract numbered words
    pattern = r'(\w+)\((\d+)\)'
    matches = re.findall(pattern, doi_line)
    max_num = max(int(num) for word, num in matches)
    words = [''] * (max_num + 1)
    for word, num in matches:
        words[int(num)] = word.lower()
    
    return words[1:]  # Skip index 0, return 1-indexed words


def load_cipher1():
    """Load Cipher 1 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]


def extract_doi_only(cipher_numbers, doi_words, extractor, count=520):
    """Extract using DOI-only corpus, NO OFFSET"""
    stream = []
    
    for position, cipher_num in enumerate(cipher_numbers[:count]):
        word_idx = cipher_num - 1
        
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            char = extractor.extract(word, word_idx, position, 'DOI')
            stream.append(char)
        else:
            stream.append('?')
    
    return ''.join(stream)


def run_sanity_check():
    """Run all sanity checks"""
    print("=" * 80)
    print("PHASE 5 SANITY CHECK")
    print("=" * 80)
    
    results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'doi_word_count': 0,
        'cipher1_count': 0,
        'out_of_range': [],
        'cipher2_regression': 'UNKNOWN',
        'phase4_baseline': 'UNKNOWN',
        'all_pass': False
    }
    
    # Test 1: DOI tokenization
    print("\n1. DOI TOKENIZATION CHECK")
    print("-" * 80)
    doi_words = load_doi_from_beale()
    results['doi_word_count'] = len(doi_words)
    
    print(f"DOI word count: {len(doi_words)}")
    
    if len(doi_words) == 1322:
        print("[PASS] Word count = 1322")
        doi_check = True
    else:
        print(f"[FAIL] Expected 1322, got {len(doi_words)}")
        doi_check = False
    
    # Check known Cipher 2 position (word 807 should start with 'i')
    word_807 = doi_words[806] if len(doi_words) > 806 else ""
    print(f"Word 807: '{word_807}'")
    
    if word_807 and word_807[0].lower() == 'i':
        print("[PASS] Word 807 starts with 'i' (Cipher 2 regression)")
        cipher2_check = True
        results['cipher2_regression'] = 'PASS'
    else:
        print(f"[FAIL] Word 807 should start with 'i', got '{word_807}'")
        cipher2_check = False
        results['cipher2_regression'] = 'FAIL'
    
    # Test 2: Cipher 1 parsing
    print("\n2. CIPHER 1 PARSING CHECK")
    print("-" * 80)
    cipher1 = load_cipher1()
    results['cipher1_count'] = len(cipher1)
    
    print(f"Cipher 1 count: {len(cipher1)}")
    
    if len(cipher1) == 520:
        print("[PASS] Cipher 1 has 520 numbers")
        cipher1_check = True
    else:
        print(f"[FAIL] Expected 520, got {len(cipher1)}")
        cipher1_check = False
    
    # Identify out-of-range numbers
    expected_out_of_range = [1431, 1496, 1629, 1701, 1706, 1780, 1817, 2018, 2160, 2906]
    actual_out_of_range = sorted([n for n in cipher1 if n > len(doi_words)])
    results['out_of_range'] = actual_out_of_range
    
    print(f"Out-of-range numbers: {actual_out_of_range}")
    
    if actual_out_of_range == expected_out_of_range:
        print(f"[PASS] Out-of-range matches expected: {expected_out_of_range}")
        out_of_range_check = True
    else:
        print(f"[FAIL] Expected: {expected_out_of_range}")
        print(f"       Got:      {actual_out_of_range}")
        out_of_range_check = False
    
    # Test 3: Phase 4 baseline reproduction
    print("\n3. PHASE 4 BASELINE REPRODUCTION")
    print("-" * 80)
    print("Testing: position_times_2 + every_3th on full 520 numbers")
    
    ext = extractors.get_extractor('position_times_2')
    trans_obj = transposition.get_transposition('every_3th')
    
    if not ext:
        print("[FAIL] position_times_2 extractor not found")
        baseline_check = False
        results['phase4_baseline'] = 'FAIL (extractor missing)'
    elif not trans_obj:
        print("[FAIL] every_3th transposition not found")
        baseline_check = False
        results['phase4_baseline'] = 'FAIL (transposition missing)'
    else:
        # Run extraction
        raw = extract_doi_only(cipher1, doi_words, ext, count=520)
        transformed = trans_obj.apply(raw)
        
        # Score
        scores = signal_score.score_stream(transformed, use_phase3_metrics=True)
        score = scores['total_score']
        
        print(f"Score: {score:.2f}/100")
        print(f"Expected: 34.38/100 (±0.5 tolerance)")
        
        if abs(score - 34.38) <= 0.5:
            print(f"[PASS] Score within tolerance")
            baseline_check = True
            results['phase4_baseline'] = f'PASS ({score:.2f})'
        else:
            print(f"[FAIL] Score outside tolerance: {score:.2f} vs 34.38")
            baseline_check = False
            results['phase4_baseline'] = f'FAIL ({score:.2f})'
    
    # Overall result
    print("\n" + "=" * 80)
    print("SANITY CHECK SUMMARY")
    print("=" * 80)
    
    all_checks = [doi_check, cipher2_check, cipher1_check, out_of_range_check, baseline_check]
    results['all_pass'] = all(all_checks)
    
    print(f"DOI tokenization:       {'PASS' if doi_check else 'FAIL'}")
    print(f"Cipher 2 regression:    {'PASS' if cipher2_check else 'FAIL'}")
    print(f"Cipher 1 parsing:       {'PASS' if cipher1_check else 'FAIL'}")
    print(f"Out-of-range check:     {'PASS' if out_of_range_check else 'FAIL'}")
    print(f"Phase 4 baseline:       {'PASS' if baseline_check else 'FAIL'}")
    print("-" * 80)
    print(f"OVERALL:                {'PASS - Ready for Phase 5' if results['all_pass'] else 'FAIL - Fix issues before proceeding'}")
    
    return results


def generate_report(results):
    """Generate sanity check report"""
    filename = "output/phase5/phase5_sanity.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 5 SANITY CHECK REPORT\n")
        f.write(f"Generated: {results['timestamp']}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("INVARIANT CHECKS\n")
        f.write("-" * 80 + "\n")
        f.write(f"DOI word count: {results['doi_word_count']}\n")
        f.write(f"Cipher 1 count: {results['cipher1_count']}\n")
        f.write(f"Out-of-range: {results['out_of_range']}\n")
        f.write(f"Cipher 2 regression: {results['cipher2_regression']}\n")
        f.write(f"Phase 4 baseline: {results['phase4_baseline']}\n\n")
        
        f.write("VERDICT\n")
        f.write("-" * 80 + "\n")
        if results['all_pass']:
            f.write("ALL CHECKS PASSED\n")
            f.write("System is ready for Phase 5 execution.\n")
        else:
            f.write("SOME CHECKS FAILED\n")
            f.write("Fix issues before proceeding with Phase 5.\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"\nReport saved to: {filename}")


if __name__ == "__main__":
    results = run_sanity_check()
    generate_report(results)
    
    if not results['all_pass']:
        print("\n[!] Sanity check failed. Phase 5 should not proceed.")
        exit(1)
    else:
        print("\n[OK] All checks passed. Phase 5 ready to execute.")
        exit(0)
