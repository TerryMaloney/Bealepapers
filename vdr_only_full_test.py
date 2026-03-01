"""
VDR-ONLY FULL TEST (Phase 3)
Test hypothesis that Cipher 1 primarily uses VDR as key book.
Compare VDR-only decoding vs full-stack on complete 520-number cipher.
"""

from pathlib import Path
import re
from strategy_runner import load_cipher1
import extractors
import transposition
import signal_score
from datetime import datetime


def normalize(text):
    """Normalize text to lowercase words only"""
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]


def load_texts():
    """Load individual text files"""
    vdr = normalize(Path("texts/vdr.txt").read_text(encoding="utf-8"))
    doi = normalize(Path("texts/doi_from_beale.txt").read_text(encoding="utf-8"))
    signers = normalize(Path("texts/signers.txt").read_text(encoding="utf-8"))
    articles = normalize(Path("texts/articles.txt").read_text(encoding="utf-8"))
    
    return {
        'vdr': vdr,
        'doi': doi,
        'signers': signers,
        'articles': articles,
        'full_stack': vdr + doi + signers + articles
    }


def extract_with_corpus(cipher_numbers, word_list, offset, extractor, trans, count=520):
    """
    Extract stream using specified corpus configuration.
    
    Args:
        cipher_numbers: List of cipher numbers
        word_list: List of words to use
        offset: Offset value
        extractor: Extractor object
        trans: Transposition object
        count: Number of cipher numbers to process
    
    Returns:
        Tuple of (raw_stream, transformed_stream)
    """
    raw_stream = []
    
    for i, cipher_num in enumerate(cipher_numbers[:count]):
        # Simple indexing (cipher_num - offset)
        idx = cipher_num - offset - 1  # 1-indexed to 0-indexed
        
        if 0 <= idx < len(word_list):
            word = word_list[idx]
            char = extractor.extract(word, idx, i, 'corpus')
            raw_stream.append(char)
        else:
            raw_stream.append("?")
    
    raw_str = ''.join(raw_stream)
    transformed = trans.apply(raw_str)
    
    return raw_str, transformed


def run_vdr_comparison():
    """
    Compare VDR-only vs full-stack decoding on full 520-number cipher.
    """
    print("=" * 80)
    print("VDR-ONLY FULL TEST - Phase 3")
    print("Testing VDR primary key hypothesis on complete cipher")
    print("=" * 80)
    
    # Load texts
    texts = load_texts()
    cipher1 = load_cipher1()
    
    print(f"\nCorpus sizes:")
    print(f"  VDR:        {len(texts['vdr'])} words")
    print(f"  DOI:        {len(texts['doi'])} words")
    print(f"  Signers:    {len(texts['signers'])} words")
    print(f"  Articles:   {len(texts['articles'])} words")
    print(f"  Full stack: {len(texts['full_stack'])} words")
    print(f"\nCipher 1: {len(cipher1)} numbers")
    
    # Best extractor and transposition from Phase 2
    ext = extractors.get_extractor('nth_letter_by_position')
    trans_obj = transposition.get_transposition('every_2th')
    
    print(f"\nUsing: {ext.name} + {trans_obj.name}")
    
    # Test configurations
    configs = [
        {'corpus': texts['vdr'], 'offset': 0, 'label': 'VDR-only (no offset)'},
        {'corpus': texts['vdr'], 'offset': 335, 'label': 'VDR-only (offset 335)'},
        {'corpus': texts['vdr'], 'offset': 860, 'label': 'VDR-only (at VDR boundary)'},
        {'corpus': texts['doi'], 'offset': 0, 'label': 'DOI-only (no offset)'},
        {'corpus': texts['doi'], 'offset': 860, 'label': 'DOI-only (offset 860)'},
        {'corpus': texts['full_stack'], 'offset': 335, 'label': 'Full stack (offset 335)'},
        {'corpus': texts['full_stack'], 'offset': 338, 'label': 'Full stack (offset 338)'},
    ]
    
    print("\nTesting configurations on full 520 numbers...")
    print("-" * 80)
    
    results = []
    
    for config in configs:
        raw, transformed = extract_with_corpus(
            cipher1, 
            config['corpus'], 
            config['offset'], 
            ext, 
            trans_obj, 
            count=520
        )
        
        # Score with Phase 3 metrics
        scores = signal_score.score_stream(transformed, use_phase3_metrics=True)
        
        # Count valid mappings (non-'?' characters)
        valid_chars = sum(1 for c in raw if c != '?')
        coverage = (valid_chars / len(raw)) * 100
        
        print(f"\n{config['label']}:")
        print(f"  Corpus size: {len(config['corpus'])} words")
        print(f"  Offset: {config['offset']}")
        print(f"  Coverage: {coverage:.1f}% ({valid_chars}/520 numbers mapped)")
        print(f"  Score: {scores['total_score']:.2f}/100")
        
        # Detect fragments
        fragments = signal_score.detect_word_fragments(transformed)
        print(f"  Fragments: {len(fragments)}")
        
        results.append({
            'config': config,
            'raw_stream': raw,
            'transformed_stream': transformed,
            'scores': scores,
            'coverage': coverage,
            'fragments': fragments
        })
    
    return results


def generate_vdr_report(results):
    """Generate detailed VDR comparison report"""
    filename = "output/vdr_full_test.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 3 VDR-ONLY FULL TEST\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("HYPOTHESIS\n")
        f.write("-" * 80 + "\n")
        f.write("Phase 2 showed VDR-only (offset 335) marginally outscored full-stack.\n")
        f.write("This test validates whether VDR is the primary key book on full cipher.\n\n")
        f.write("If VDR-only scores >45 and beats full-stack by >3 points,\n")
        f.write("VDR is confirmed as primary key.\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("CONFIGURATION RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        # Sort by score
        sorted_results = sorted(results, key=lambda x: x['scores']['total_score'], reverse=True)
        
        for i, result in enumerate(sorted_results, 1):
            config = result['config']
            scores = result['scores']
            
            f.write(f"RANK #{i}: {config['label']}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Corpus: {len(config['corpus'])} words, Offset: {config['offset']}\n")
            f.write(f"Coverage: {result['coverage']:.1f}%\n")
            f.write(f"Total score: {scores['total_score']:.2f}/100\n\n")
            
            f.write("Detailed scores:\n")
            f.write(f"  Bigram:       {scores['bigram_score']:6.2f}/100\n")
            f.write(f"  Trigram:      {scores['trigram_score']:6.2f}/100\n")
            f.write(f"  Quadgram:     {scores['quadgram_score']:6.2f}/100\n")
            f.write(f"  Vowel ratio:  {scores['vowel_ratio_score']:6.2f}/100\n")
            f.write(f"  Dictionary:   {scores['dictionary_score']:6.2f}/100\n")
            f.write(f"  Letter freq:  {scores['letter_freq_score']:6.2f}/100\n")
            f.write(f"  Entropy:      {scores['entropy_score']:6.2f}/100\n")
            f.write(f"  Fragments:    {scores['fragment_score']:6.2f}/100\n\n")
            
            # Output sample
            stream = result['transformed_stream']
            f.write("Output stream (first 200 chars):\n")
            f.write(f"  {stream[:200]}\n\n")
            
            # Fragments
            if result['fragments']:
                f.write(f"Fragments detected ({len(result['fragments'])}):\n")
                sorted_frags = sorted(result['fragments'].items(), 
                                    key=lambda x: x[1], reverse=True)
                for word, count in sorted_frags[:15]:
                    f.write(f"  {word}: {count}x\n")
            else:
                f.write("No fragments detected.\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
        
        # Analysis
        f.write("COMPARATIVE ANALYSIS\n")
        f.write("-" * 80 + "\n\n")
        
        # Find best VDR-only and best full-stack
        vdr_results = [r for r in results if 'VDR-only' in r['config']['label']]
        full_stack_results = [r for r in results if 'Full stack' in r['config']['label']]
        
        best_vdr = max(vdr_results, key=lambda x: x['scores']['total_score'])
        best_full = max(full_stack_results, key=lambda x: x['scores']['total_score'])
        
        vdr_score = best_vdr['scores']['total_score']
        full_score = best_full['scores']['total_score']
        difference = vdr_score - full_score
        
        f.write(f"Best VDR-only:   {best_vdr['config']['label']}\n")
        f.write(f"  Score: {vdr_score:.2f}/100\n")
        f.write(f"  Coverage: {best_vdr['coverage']:.1f}%\n\n")
        
        f.write(f"Best full-stack: {best_full['config']['label']}\n")
        f.write(f"  Score: {full_score:.2f}/100\n")
        f.write(f"  Coverage: {best_full['coverage']:.1f}%\n\n")
        
        f.write(f"Difference: {difference:+.2f} points\n\n")
        
        # Verdict
        if vdr_score > 45 and difference > 3:
            f.write("VERDICT: VDR PRIMARY KEY CONFIRMED\n")
            f.write("VDR-only significantly outperforms full-stack.\n")
            f.write("Recommendation: Focus exclusively on VDR as key text.\n")
        elif difference > 2:
            f.write("VERDICT: VDR PREFERRED\n")
            f.write("VDR-only performs better than full-stack.\n")
            f.write("Recommendation: Prioritize VDR but keep full-stack as fallback.\n")
        elif abs(difference) <= 2:
            f.write("VERDICT: NO CLEAR PREFERENCE\n")
            f.write("VDR-only and full-stack perform similarly.\n")
            f.write("Recommendation: Use full-stack for better coverage.\n")
        else:
            f.write("VERDICT: FULL-STACK PREFERRED\n")
            f.write("Full-stack outperforms VDR-only.\n")
            f.write("Recommendation: Continue with full document stack.\n")
        
        # Coverage analysis
        f.write("\n\nCOVERAGE ANALYSIS\n")
        f.write("-" * 80 + "\n\n")
        
        low_coverage = [r for r in results if r['coverage'] < 80]
        if low_coverage:
            f.write("Configurations with <80% coverage:\n")
            for r in low_coverage:
                f.write(f"  {r['config']['label']}: {r['coverage']:.1f}%\n")
            f.write("\nLow coverage indicates many cipher numbers fall outside corpus range.\n")
            f.write("This suggests offset or corpus mismatch.\n")
        else:
            f.write("All configurations show >80% coverage.\n")
            f.write("Corpus size is adequate for cipher number range.\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"\nVDR comparison report saved to: {filename}")
    return filename


if __name__ == "__main__":
    results = run_vdr_comparison()
    report_file = generate_vdr_report(results)
    
    print("\n" + "=" * 80)
    print("VDR-ONLY FULL TEST COMPLETE")
    print("=" * 80)
    
    # Show comparison
    vdr_results = [r for r in results if 'VDR-only' in r['config']['label']]
    full_stack_results = [r for r in results if 'Full stack' in r['config']['label']]
    
    best_vdr = max(vdr_results, key=lambda x: x['scores']['total_score'])
    best_full = max(full_stack_results, key=lambda x: x['scores']['total_score'])
    
    print(f"\nBest VDR-only:   {best_vdr['scores']['total_score']:.2f}/100 ({best_vdr['config']['label']})")
    print(f"Best full-stack: {best_full['scores']['total_score']:.2f}/100 ({best_full['config']['label']})")
    print(f"Difference:      {best_vdr['scores']['total_score'] - best_full['scores']['total_score']:+.2f} points")
    
    print(f"\nFull report: {report_file}")
    print("\nFinal step: Generate phase3_summary.txt with all results")
