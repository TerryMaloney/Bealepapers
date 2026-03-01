"""
PHASE 5 UNIFIED RUNNER
Main orchestration script for comprehensive search across extraction, transposition, and substitution layers.
"""

import re
import csv
from datetime import datetime
from pathlib import Path
import extractors
import transposition
import substitution
import signal_score


def load_doi_from_beale():
    """Load DOI exactly as used in Cipher 2 decoding"""
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


class Strategy:
    """Complete decoding strategy with optional substitution layer"""
    def __init__(self, extractor, trans, sub=None):
        self.extractor = extractor
        self.transposition = trans
        self.substitution = sub
    
    def get_name(self):
        """Get full strategy name"""
        name = f"{self.extractor.name}+{self.transposition.name}"
        if self.substitution:
            name += f"+{self.substitution.name}"
        return name
    
    def apply(self, cipher_numbers, doi_words, count=520):
        """Apply complete strategy pipeline"""
        # 1. Extract
        raw_stream = []
        for position, cipher_num in enumerate(cipher_numbers[:count]):
            word_idx = cipher_num - 1
            
            if 0 <= word_idx < len(doi_words):
                word = doi_words[word_idx]
                char = self.extractor.extract(word, word_idx, position, 'DOI')
                raw_stream.append(char)
            else:
                raw_stream.append('?')
        
        raw_str = ''.join(raw_stream)
        
        # 2. Transpose
        transposed = self.transposition.apply(raw_str)
        
        # 3. Substitute (optional)
        if self.substitution:
            final_stream = self.substitution.apply(transposed)
        else:
            final_stream = transposed
        
        return raw_str, transposed, final_stream


def evaluate_strategy(strategy, cipher_numbers, doi_words):
    """Evaluate a complete strategy and return results"""
    raw, transposed, final = strategy.apply(cipher_numbers, doi_words)
    
    # Score final stream
    scores = signal_score.score_stream(final, use_phase3_metrics=True)
    
    # Count valid mappings
    valid = sum(1 for c in raw if c != '?')
    coverage = (valid / len(raw)) * 100
    
    # Detect fragments
    fragments = signal_score.detect_word_fragments(final)
    
    return {
        'strategy_name': strategy.get_name(),
        'extractor': strategy.extractor.name,
        'transposition': strategy.transposition.name,
        'substitution': strategy.substitution.name if strategy.substitution else 'none',
        'total_score': scores['total_score'],
        'bigram_score': scores['bigram_score'],
        'trigram_score': scores['trigram_score'],
        'quadgram_score': scores['quadgram_score'],
        'vowel_score': scores['vowel_ratio_score'],
        'dict_score': scores['dictionary_score'],
        'letter_freq_score': scores['letter_freq_score'],
        'entropy_score': scores['entropy_score'],
        'fragment_score': scores['fragment_score'],
        'coverage': coverage,
        'valid_mappings': valid,
        'fragments': fragments,
        'raw_stream': raw,
        'transposed_stream': transposed,
        'final_stream': final
    }


def save_results_csv(results, filename):
    """Save results to CSV"""
    if not results:
        return
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['rank', 'strategy_name', 'extractor', 'transposition', 'substitution',
                     'total_score', 'bigram_score', 'trigram_score', 'quadgram_score',
                     'vowel_score', 'dict_score', 'letter_freq_score', 'entropy_score',
                     'fragment_score', 'coverage', 'valid_mappings', 'fragment_count']
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, result in enumerate(results, 1):
            row = {k: result[k] for k in fieldnames if k in result}
            row['rank'] = i
            row['fragment_count'] = len(result['fragments'])
            writer.writerow(row)


def save_top20_readable(results, filename):
    """Save top 20 results in human-readable format"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 5 TOP 20 STRATEGIES\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results[:20], 1):
            f.write(f"RANK #{i}  Score: {result['total_score']:.2f}/100\n")
            f.write("-" * 80 + "\n")
            f.write(f"Extractor:     {result['extractor']}\n")
            f.write(f"Transposition: {result['transposition']}\n")
            f.write(f"Substitution:  {result['substitution']}\n")
            f.write(f"Coverage:      {result['coverage']:.1f}% ({result['valid_mappings']}/520)\n\n")
            
            f.write("Detailed scores:\n")
            f.write(f"  Bigram:      {result['bigram_score']:6.2f}/100\n")
            f.write(f"  Trigram:     {result['trigram_score']:6.2f}/100\n")
            f.write(f"  Quadgram:    {result['quadgram_score']:6.2f}/100\n")
            f.write(f"  Vowel ratio: {result['vowel_score']:6.2f}/100\n")
            f.write(f"  Dictionary:  {result['dict_score']:6.2f}/100\n")
            f.write(f"  Letter freq: {result['letter_freq_score']:6.2f}/100\n")
            f.write(f"  Entropy:     {result['entropy_score']:6.2f}/100\n")
            f.write(f"  Fragments:   {result['fragment_score']:6.2f}/100\n\n")
            
            stream = result['final_stream']
            f.write(f"Output (first 200 chars):\n")
            f.write(f"  {stream[:200]}\n\n")
            
            if result['fragments']:
                frags = sorted(result['fragments'].items(), key=lambda x: x[1], reverse=True)
                frag_str = ', '.join([f"{w}({c}x)" for w, c in frags[:10]])
                f.write(f"Fragments: {frag_str}\n")
            
            f.write("\n" + "=" * 80 + "\n\n")


# ============================================================================
# MAIN EXECUTION FUNCTIONS
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 5 UNIFIED RUNNER")
    print("=" * 80)
    print("\nThis module provides infrastructure for Phase 5 search.")
    print("Use specific search scripts:")
    print("  - phase5_grid_search.py for Stage 2")
    print("  - phase5_caesar_sweep.py for Stage 3")
    print("  - phase5_vigenere_search.py for Stage 4")
    print("  - phase5_substitution_search.py for Stage 5")
