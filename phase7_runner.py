"""
PHASE 7 G6: UNIFIED RUNNER
Orchestrate full Phase 7 search with all improvements:
- DOI variant calibration (G1)
- OOR analysis (G2)  
- Feature extractors (G3)
- Two-stage transposition (G4)
- Cross-cipher constraints (G5)
"""

import csv
import re
from datetime import datetime
from typing import List, Dict, Tuple
import extractors
import transposition
import signal_score


def load_doi_from_beale():
    """Load DOI"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    doi_line = lines[54]
    pattern = r'(\w+)\((\d+)\)'
    matches = re.findall(pattern, doi_line)
    max_num = max(int(num) for word, num in matches)
    words = [''] * (max_num + 1)
    for word, num in matches:
        words[int(num)] = word.lower()
    
    return words[1:]


def load_cipher1():
    """Load Cipher 1 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]


def evaluate_strategy(extractor, trans, cipher_numbers, doi_words, subset=None):
    """Evaluate a single strategy"""
    if subset is not None:
        cipher_numbers = cipher_numbers[subset]
    
    # Extract
    stream = []
    for position, cipher_num in enumerate(cipher_numbers):
        word_idx = cipher_num - 1
        if 0 <= word_idx < len(doi_words):
            word = doi_words[word_idx]
            char = extractor.extract(word, word_idx, position, 'DOI')
            stream.append(char)
        else:
            stream.append('?')
    
    raw = ''.join(stream)
    final = trans.apply(raw)
    scores = signal_score.score_stream(final, use_phase3_metrics=True)
    
    return {
        'extractor': extractor.name,
        'transposition': trans.name,
        'total_score': scores['total_score'],
        'quadgram': scores.get('quadgram_score', 0),
        'entropy': scores.get('entropy_score', 0),
        'vowel_ratio': scores.get('vowel_ratio_score', 0),
        'coverage': len([c for c in raw if c != '?']) / len(raw) * 100 if raw else 0,
        'stream': final
    }


def phase7_staged_search():
    """
    Main Phase 7 search pipeline:
    1. Coarse beam search on 200-position subset
    2. Full 520 evaluation on top 50
    3. Two-stage transposition on top 10
    """
    print("=" * 80)
    print("PHASE 7 G6: UNIFIED SEARCH RUNNER")
    print("=" * 80)
    
    # Load data
    cipher1 = load_cipher1()
    doi_words = load_doi_from_beale()
    
    print(f"\nCipher 1: {len(cipher1)} numbers")
    print(f"DOI: {len(doi_words)} words")
    
    # Build search space
    print("\n[Step 1] Building search space...")
    
    # Top extractors from Phase 6
    top_extractors = [
        extractors.get_extractor('position_times_2'),
        extractors.get_extractor('reverse_position'),
        extractors.get_extractor('cycle_every_5'),
        extractors.get_extractor('nth_letter_by_position'),
        extractors.get_extractor('cycle_every_7')
    ]
    
    # Add Phase 7 feature extractors
    phase7_extractors = [
        extractors.LastVowelExtractor(),
        extractors.LastConsonantExtractor(),
        extractors.VowelPositionExtractor(),
        extractors.ConsonantPositionExtractor(),
        extractors.WordShapeExtractor()
    ]
    
    extractors_to_test = top_extractors + phase7_extractors
    
    # Top single-stage transpositions from Phase 5-6
    top_transpositions = [
        transposition.get_transposition('rect_w26_spiral_ccw'),
        transposition.get_transposition('every_3th'),
        transposition.get_transposition('rect_w13_spiral_ccw'),
        transposition.get_transposition('rect_w40_diagonal'),
        transposition.get_transposition('chunk_reverse_3')
    ]
    
    print(f"  Extractors: {len(extractors_to_test)}")
    print(f"  Single-stage transpositions: {len(top_transpositions)}")
    
    # Stage 1: Coarse beam search (200 positions)
    print("\n[Step 2] Stage 1: Coarse beam search (positions 0-199)...")
    
    coarse_results = []
    total_tests = len(extractors_to_test) * len(top_transpositions)
    
    for i, ext in enumerate(extractors_to_test):
        for trans in top_transpositions:
            result = evaluate_strategy(ext, trans, cipher1, doi_words, subset=slice(0, 200))
            coarse_results.append(result)
        
        if (i + 1) % 2 == 0:
            print(f"  Tested {(i+1) * len(top_transpositions)}/{total_tests} strategies...")
    
    print(f"  Tested {total_tests}/{total_tests} strategies.")
    
    # Sort and take top 50
    coarse_results.sort(key=lambda x: x['total_score'], reverse=True)
    top_50 = coarse_results[:50]
    
    print(f"\n  Top coarse score: {top_50[0]['total_score']:.2f}/100")
    print(f"  Extractor: {top_50[0]['extractor']}")
    print(f"  Transposition: {top_50[0]['transposition']}")
    
    # Stage 2: Full 520 evaluation
    print("\n[Step 3] Stage 2: Full 520 evaluation (top 50 from Stage 1)...")
    
    full_results = []
    
    for i, result in enumerate(top_50):
        ext = extractors.get_extractor(result['extractor'])
        trans = transposition.get_transposition(result['transposition'])
        
        full_result = evaluate_strategy(ext, trans, cipher1, doi_words)
        full_results.append(full_result)
        
        if (i + 1) % 10 == 0:
            print(f"  Evaluated {i+1}/50...")
    
    print(f"  Evaluated 50/50.")
    
    # Sort full results
    full_results.sort(key=lambda x: x['total_score'], reverse=True)
    
    print(f"\n  Top full score: {full_results[0]['total_score']:.2f}/100")
    print(f"  Extractor: {full_results[0]['extractor']}")
    print(f"  Transposition: {full_results[0]['transposition']}")
    
    # Stage 3: Two-stage transposition on top 10
    print("\n[Step 4] Stage 3: Two-stage transposition (top 10)...")
    
    # Get two-stage transpositions
    all_trans = transposition.ALL_TRANSPOSITIONS
    two_stage_trans = [t for t in all_trans if t.name.startswith('two_')]
    
    print(f"  Testing {len(two_stage_trans)} two-stage transpositions...")
    
    two_stage_results = []
    
    for i, result in enumerate(full_results[:10]):
        ext = extractors.get_extractor(result['extractor'])
        
        for trans in two_stage_trans[:5]:  # Test top 5 two-stage variants
            two_stage_result = evaluate_strategy(ext, trans, cipher1, doi_words)
            two_stage_results.append(two_stage_result)
    
    print(f"  Tested {len(two_stage_results)} two-stage combinations.")
    
    # Combine all results
    all_results = full_results + two_stage_results
    all_results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save CSV
    csv_file = f"output/phase7/phase7_ranked_results_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['rank', 'extractor', 'transposition', 'total_score', 'quadgram', 
                     'entropy', 'vowel_ratio', 'coverage']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, result in enumerate(all_results, 1):
            row = {
                'rank': i,
                'extractor': result['extractor'],
                'transposition': result['transposition'],
                'total_score': result['total_score'],
                'quadgram': result['quadgram'],
                'entropy': result['entropy'],
                'vowel_ratio': result['vowel_ratio'],
                'coverage': result['coverage']
            }
            writer.writerow(row)
    
    # Save top 20 readable
    txt_file = f"output/phase7/phase7_top20_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 7: TOP 20 STRATEGIES\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(all_results[:20], 1):
            f.write(f"RANK #{i}  Score: {result['total_score']:.2f}/100\n")
            f.write("-" * 80 + "\n")
            f.write(f"Extractor: {result['extractor']}\n")
            f.write(f"Transposition: {result['transposition']}\n")
            f.write(f"Coverage: {result['coverage']:.1f}%\n")
            f.write(f"Quadgram: {result['quadgram']:.2f}  Entropy: {result['entropy']:.2f}  Vowel: {result['vowel_ratio']:.2f}\n")
            f.write(f"\nFirst 200 chars:\n{result['stream'][:200]}\n")
            f.write("\n" + "=" * 80 + "\n\n")
    
    # Save best stream
    best_file = f"output/phase7/phase7_best_stream_{timestamp}.txt"
    with open(best_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 7: BEST DECODED STREAM\n")
        f.write(f"Score: {all_results[0]['total_score']:.2f}/100\n")
        f.write(f"Extractor: {all_results[0]['extractor']}\n")
        f.write(f"Transposition: {all_results[0]['transposition']}\n")
        f.write("=" * 80 + "\n\n")
        f.write(all_results[0]['stream'])
    
    print(f"\nResults saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Top 20: {txt_file}")
    print(f"  Best stream: {best_file}")
    
    return all_results


if __name__ == "__main__":
    results = phase7_staged_search()
    
    print("\n" + "=" * 80)
    print("PHASE 7 SEARCH COMPLETE")
    print("=" * 80)
    
    best = results[0]
    print(f"\nBest score: {best['total_score']:.2f}/100")
    print(f"Extractor: {best['extractor']}")
    print(f"Transposition: {best['transposition']}")
    print(f"\nPhase 6 baseline: 37.88/100")
    print(f"Improvement: {best['total_score'] - 37.88:+.2f} points")
    
    if best['total_score'] > 40.0:
        print("\n*** BREAKTHROUGH: Score >40/100 ***")
    elif best['total_score'] > 37.88:
        print("\nProgress made, but plateau persists.")
    else:
        print("\nNo improvement over Phase 6.")
