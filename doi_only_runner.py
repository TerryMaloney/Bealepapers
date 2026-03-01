"""
DOI-ONLY RUNNER (Phase 4)
Test DOI-only hypothesis with limited extraction methods.
Binary question: Does Cipher 1 derive from DOI only (no offset)?
"""

import re
from pathlib import Path
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
    """
    Extract using DOI-only corpus, NO OFFSET.
    
    Mapping: cipher_number -> doi_words[cipher_number - 1]
    
    Out-of-range numbers marked as '?'
    """
    stream = []
    
    for position, cipher_num in enumerate(cipher_numbers[:count]):
        # Direct mapping (1-indexed to 0-indexed)
        word_idx = cipher_num - 1
        
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            char = extractor.extract(word, word_idx, position, 'DOI')
            stream.append(char)
        else:
            stream.append('?')  # Out of DOI range
    
    return ''.join(stream)


def run_doi_only_test():
    """Test DOI-only hypothesis with limited extraction methods"""
    print("=" * 80)
    print("DOI-ONLY RUNNER - Phase 4")
    print("Testing: Cipher 1 derives from DOI only (no offset)")
    print("=" * 80)
    
    # Load data
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    
    print(f"\nDOI corpus: {len(doi_words)} words")
    print(f"Cipher 1: {len(cipher1)} numbers")
    
    # Coverage analysis
    in_range = sum(1 for n in cipher1 if n <= len(doi_words))
    coverage = (in_range / len(cipher1)) * 100
    print(f"Coverage: {coverage:.1f}% ({in_range}/520 numbers in DOI range)")
    
    # Limited test matrix (Phase 4 constraint)
    EXTRACTORS_TO_TEST = [
        'nth_letter_by_position',      # Phase 2 best
        'position_times_2',             # Mathematical variant
        'reverse_position',             # Reverse indexing
        'alternating_first_last'        # Dual-rule test
    ]
    
    TRANSPOSITIONS_TO_TEST = [
        'none',           # Baseline
        'every_2th',      # Phase 2 best
        'every_3th',      # Alternative stride
        'railfence_2',    # 1820s classic
        'railfence_3'     # 1820s variant
    ]
    
    print(f"\nTest matrix:")
    print(f"  Extractors: {len(EXTRACTORS_TO_TEST)}")
    print(f"  Transpositions: {len(TRANSPOSITIONS_TO_TEST)}")
    print(f"  Total combinations: {len(EXTRACTORS_TO_TEST) * len(TRANSPOSITIONS_TO_TEST)}")
    print("-" * 80)
    
    results = []
    test_count = 0
    
    for ext_name in EXTRACTORS_TO_TEST:
        ext = extractors.get_extractor(ext_name)
        if not ext:
            print(f"Warning: Extractor '{ext_name}' not found, skipping")
            continue
        
        for trans_name in TRANSPOSITIONS_TO_TEST:
            trans_obj = transposition.get_transposition(trans_name)
            test_count += 1
            
            # Extract + transform
            raw = extract_doi_only(cipher1, doi_words, ext, count=520)
            transformed = trans_obj.apply(raw)
            
            # Score with Phase 3 metrics
            scores = signal_score.score_stream(transformed, use_phase3_metrics=True)
            
            # Count valid mappings (non-'?' characters)
            valid = sum(1 for c in raw if c != '?')
            
            # Detect fragments
            fragments = signal_score.detect_word_fragments(transformed)
            
            result = {
                'extractor': ext_name,
                'transposition': trans_name,
                'score': scores['total_score'],
                'valid_mappings': valid,
                'scores': scores,
                'stream': transformed,
                'fragments': fragments
            }
            
            results.append(result)
            
            if test_count % 5 == 0:
                print(f"Progress: {test_count}/{len(EXTRACTORS_TO_TEST) * len(TRANSPOSITIONS_TO_TEST)} tests...")
    
    print(f"All {test_count} tests completed!")
    
    # Sort by score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results


def generate_doi_report(results, doi_word_count, cipher_count):
    """Generate Phase 4 DOI-only verdict report"""
    filename = "output/phase4_doi_only_results.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 4 DOI-ONLY ANALYSIS\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("HYPOTHESIS TESTED\n")
        f.write("-" * 80 + "\n")
        f.write("Cipher 1 derives from Declaration of Independence only (no offset).\n\n")
        
        f.write("CORPUS\n")
        f.write("-" * 80 + "\n")
        f.write(f"DOI from beale_papers.txt (line 55)\n")
        f.write(f"Word count: {doi_word_count}\n")
        f.write(f"Same version that decoded Cipher 2\n\n")
        
        f.write("MAPPING\n")
        f.write("-" * 80 + "\n")
        f.write("Direct mapping (no offset):\n")
        f.write("  cipher_number -> DOI word[cipher_number - 1]\n\n")
        
        best = results[0]
        coverage = (best['valid_mappings'] / cipher_count) * 100
        
        f.write("CIPHER 1 COVERAGE\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total numbers: {cipher_count}\n")
        f.write(f"In DOI range (<={doi_word_count}): {best['valid_mappings']} ({coverage:.1f}%)\n")
        f.write(f"Out of range (>{doi_word_count}): {cipher_count - best['valid_mappings']} ({100-coverage:.1f}%)\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("TOP 5 STRATEGIES\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results[:5], 1):
            f.write(f"RANK #{i}  Score: {result['score']:.2f}/100\n")
            f.write("-" * 80 + "\n")
            f.write(f"Extractor: {result['extractor']}\n")
            f.write(f"Transposition: {result['transposition']}\n")
            f.write(f"Valid mappings: {result['valid_mappings']}/520\n\n")
            
            scores = result['scores']
            f.write("Detailed scores:\n")
            f.write(f"  Bigram:      {scores['bigram_score']:6.2f}/100\n")
            f.write(f"  Trigram:     {scores['trigram_score']:6.2f}/100\n")
            f.write(f"  Quadgram:    {scores['quadgram_score']:6.2f}/100\n")
            f.write(f"  Vowel ratio: {scores['vowel_ratio_score']:6.2f}/100\n")
            f.write(f"  Dictionary:  {scores['dictionary_score']:6.2f}/100\n")
            f.write(f"  Letter freq: {scores['letter_freq_score']:6.2f}/100\n")
            f.write(f"  Entropy:     {scores['entropy_score']:6.2f}/100\n")
            f.write(f"  Fragments:   {scores['fragment_score']:6.2f}/100\n\n")
            
            stream = result['stream']
            f.write(f"Output (first 200 chars):\n")
            f.write(f"  {stream[:200]}\n\n")
            
            if result['fragments']:
                f.write(f"Fragments detected ({len(result['fragments'])}):\n")
                sorted_frags = sorted(result['fragments'].items(), 
                                    key=lambda x: x[1], reverse=True)
                for word, count in sorted_frags[:10]:
                    f.write(f"  {word}: {count}x\n")
            else:
                f.write("No fragments detected.\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
        
        # Store best score for verdict
        best_score = results[0]['score']
        
        f.write("=" * 80 + "\n")
        return best_score
    
    print(f"\nReport saved to: {filename}")
    return best_score


if __name__ == "__main__":
    results = run_doi_only_test()
    
    doi_words = load_doi_from_beale()
    cipher1 = load_cipher1()
    
    best_score = generate_doi_report(results, len(doi_words), len(cipher1))
    
    print("\n" + "=" * 80)
    print("DOI-ONLY TEST COMPLETE")
    print("=" * 80)
    
    print(f"\nTop 5 results:")
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result['extractor']:<30} + {result['transposition']:<15} = {result['score']:.2f}/100")
    
    print(f"\nBest score: {best_score:.2f}/100")
    print(f"Coverage: {results[0]['valid_mappings']}/520 numbers")
    print(f"Fragments: {len(results[0]['fragments'])} unique")
    
    print("\nNext: Run random_baseline.py for statistical comparison")
