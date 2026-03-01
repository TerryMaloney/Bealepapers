"""
PHASE 7 G1: CIPHER 2 ORACLE SWEEP
Test all DOI variants against Cipher 2's known plaintext to find correct tokenization.
This is CRITICAL - book ciphers fail completely if tokenization is wrong.
"""

import csv
from datetime import datetime
from doi_variants import DOIVariantGenerator, load_doi_raw


def load_cipher2():
    """Load Cipher 2 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Line 59 (index 58) contains Cipher 2
    return [int(n.strip()) for n in lines[58].strip().split(",") if n.strip()]


def get_cipher2_known_plaintext():
    """Get Cipher 2 known plaintext from beale_papers.txt"""
    # Line 63 contains the decoded plaintext
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    plaintext = lines[62].strip()
    return plaintext


def cipher2_oracle_sweep(variants, cipher2_numbers, known_plaintext):
    """
    Test each DOI variant against Cipher 2 known plaintext.
    Cipher 2 rule: first letter of word at cipher_number position.
    """
    results = []
    
    print("=" * 80)
    print("CIPHER 2 ORACLE SWEEP")
    print("=" * 80)
    print(f"\nCipher 2: {len(cipher2_numbers)} numbers")
    print(f"Known plaintext: {len(known_plaintext)} characters")
    print(f"Testing {len(variants)} DOI variants...")
    print("-" * 80)
    
    for i, variant in enumerate(variants, 1):
        word_list = variant['word_list']
        
        # Decode Cipher 2 using this variant (first-letter rule)
        decoded = []
        out_of_range = 0
        
        for cipher_num in cipher2_numbers:
            word_idx = cipher_num - 1
            if 0 <= word_idx < len(word_list):
                word = word_list[word_idx]
                if word:
                    decoded.append(word[0].upper())
                else:
                    decoded.append('?')
            else:
                decoded.append('?')
                out_of_range += 1
        
        decoded_str = ''.join(decoded)
        
        # Compare to known plaintext (case-insensitive)
        match_count = 0
        total_compared = min(len(decoded_str), len(known_plaintext))
        
        for d, k in zip(decoded_str, known_plaintext):
            if d.upper() == k.upper():
                match_count += 1
        
        match_pct = (match_count / total_compared) * 100 if total_compared > 0 else 0
        
        # Find first mismatch
        first_mismatch = -1
        mismatch_context = ""
        for idx, (d, k) in enumerate(zip(decoded_str, known_plaintext)):
            if d.upper() != k.upper():
                first_mismatch = idx
                # Get context around mismatch
                start = max(0, idx - 10)
                end = min(len(decoded_str), idx + 11)
                mismatch_context = f"...{decoded_str[start:end]}..."
                break
        
        results.append({
            'variant_id': variant['id'],
            'word_count': variant['word_count'],
            'match_pct': match_pct,
            'match_count': match_count,
            'out_of_range': out_of_range,
            'first_mismatch': first_mismatch,
            'mismatch_context': mismatch_context,
            'decoded_sample': decoded_str[:100],
            'rules': variant['rules']
        })
        
        if i % 4 == 0:
            print(f"  Tested {i}/{len(variants)} variants...")
    
    print(f"  Tested {len(variants)}/{len(variants)} variants.")
    
    # Sort by match percentage
    results.sort(key=lambda x: x['match_pct'], reverse=True)
    
    return results


def save_oracle_results(results, known_plaintext):
    """Save oracle sweep results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save CSV
    csv_file = f"output/phase7/cipher2_oracle_sweep_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['rank', 'variant_id', 'word_count', 'match_pct', 'match_count', 
                     'out_of_range', 'first_mismatch', 'mismatch_context']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, result in enumerate(results, 1):
            row = {k: result[k] for k in fieldnames if k in result}
            row['rank'] = i
            writer.writerow(row)
    
    # Save detailed text report
    txt_file = f"output/phase7/cipher2_oracle_sweep_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 7 G1: CIPHER 2 ORACLE SWEEP RESULTS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE:\n")
        f.write("Identify correct DOI tokenization by testing against Cipher 2 known plaintext.\n")
        f.write("Cipher 2 uses: first letter of word[cipher_number].\n\n")
        
        f.write(f"Known plaintext length: {len(known_plaintext)} characters\n")
        f.write(f"Variants tested: {len(results)}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("TOP 10 VARIANTS\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results[:10], 1):
            f.write(f"RANK #{i}  Match: {result['match_pct']:.2f}%\n")
            f.write("-" * 80 + "\n")
            f.write(f"Variant ID: {result['variant_id']}\n")
            f.write(f"Word count: {result['word_count']}\n")
            f.write(f"Matches: {result['match_count']}/{len(known_plaintext)}\n")
            f.write(f"Out-of-range numbers: {result['out_of_range']}\n")
            
            f.write("\nRules:\n")
            for key, value in result['rules'].items():
                f.write(f"  {key}: {value}\n")
            
            if result['first_mismatch'] >= 0:
                f.write(f"\nFirst mismatch at position: {result['first_mismatch']}\n")
                f.write(f"Context: {result['mismatch_context']}\n")
            else:
                f.write("\nPERFECT MATCH!\n")
            
            f.write(f"\nDecoded sample (first 100 chars):\n")
            f.write(f"  {result['decoded_sample']}\n")
            f.write("\n" + "=" * 80 + "\n\n")
        
        f.write("\nALL VARIANTS RANKED:\n")
        f.write("-" * 80 + "\n")
        for i, result in enumerate(results, 1):
            f.write(f"{i:2d}. {result['variant_id']:8s} | {result['match_pct']:6.2f}% | Words: {result['word_count']:4d} | OOR: {result['out_of_range']:2d}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("INTERPRETATION\n")
        f.write("=" * 80 + "\n\n")
        
        best = results[0]
        if best['match_pct'] >= 98.0:
            f.write("EXCELLENT: Best variant matches >98% of known plaintext.\n")
            f.write("This variant is almost certainly the correct tokenization.\n")
            f.write(f"Recommended for Cipher 1 testing: {best['variant_id']}\n")
        elif best['match_pct'] >= 95.0:
            f.write("GOOD: Best variant matches >95% of known plaintext.\n")
            f.write("Minor discrepancies may be due to historical text variations.\n")
            f.write(f"Recommended for Cipher 1 testing: {best['variant_id']}\n")
        elif best['match_pct'] >= 90.0:
            f.write("MODERATE: Best variant matches >90% of known plaintext.\n")
            f.write("Significant differences exist. May need additional DOI sources.\n")
        else:
            f.write("POOR: Best variant matches <90% of known plaintext.\n")
            f.write("WARNING: Our DOI text may fundamentally differ from encoder's version.\n")
            f.write("Consider testing historical DOI editions (1776 Dunlap, 1823 facsimile).\n")
    
    print(f"\nResults saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Report: {txt_file}")
    
    return csv_file, txt_file


def run_oracle_sweep():
    """Main oracle sweep execution"""
    # Load DOI and generate variants
    print("\n[Step 1] Loading DOI and generating variants...")
    raw_doi = load_doi_raw()
    generator = DOIVariantGenerator(raw_doi)
    variants = generator.generate_variants()
    print(f"Generated {len(variants)} variants")
    
    # Load Cipher 2
    print("\n[Step 2] Loading Cipher 2...")
    cipher2 = load_cipher2()
    known_plaintext = get_cipher2_known_plaintext()
    print(f"Cipher 2: {len(cipher2)} numbers")
    print(f"Known plaintext: {len(known_plaintext)} chars")
    print(f"First 50 chars: {known_plaintext[:50]}")
    
    # Run oracle sweep
    print("\n[Step 3] Running oracle sweep...")
    results = cipher2_oracle_sweep(variants, cipher2, known_plaintext)
    
    # Save results
    print("\n[Step 4] Saving results...")
    save_oracle_results(results, known_plaintext)
    
    # Print summary
    print("\n" + "=" * 80)
    print("ORACLE SWEEP COMPLETE")
    print("=" * 80)
    
    print(f"\nTop 5 variants by match percentage:")
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result['variant_id']:8s} | {result['match_pct']:6.2f}% | Words: {result['word_count']}")
    
    best = results[0]
    print(f"\nBest variant: {best['variant_id']}")
    print(f"Match: {best['match_pct']:.2f}% ({best['match_count']}/{len(known_plaintext)} chars)")
    
    if best['match_pct'] >= 98:
        print("\nVERDICT: EXCELLENT match. Use this variant for Cipher 1.")
    elif best['match_pct'] >= 95:
        print("\nVERDICT: GOOD match. Proceed with this variant.")
    else:
        print("\nVERDICT: Suboptimal match. May need different DOI source.")
    
    return results


if __name__ == "__main__":
    results = run_oracle_sweep()
