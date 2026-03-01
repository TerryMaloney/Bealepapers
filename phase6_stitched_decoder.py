"""
PHASE 6 STITCHED DECODER
Test segment-specific extraction rules to break through the 37/100 plateau.
"""

import re
import csv
from datetime import datetime
from pathlib import Path
import extractors
import transposition
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


class StitchedStrategy:
    """
    Decoder that applies different extractors to different cipher segments.
    This tests the hypothesis that the encoding method varies across the cipher.
    """
    def __init__(self, segment_extractors, trans, segments=None):
        """
        Args:
            segment_extractors: dict mapping segment_id -> extractor
            trans: transposition to apply to stitched stream
            segments: list of (start, end, seg_id) tuples, defaults to 5 equal segments
        """
        self.segment_extractors = segment_extractors
        self.transposition = trans
        
        if segments is None:
            self.segments = [
                (0, 100, 1),
                (100, 200, 2),
                (200, 300, 3),
                (300, 400, 4),
                (400, 520, 5)
            ]
        else:
            self.segments = segments
    
    def get_name(self):
        """Generate name showing segment configuration"""
        seg_names = []
        for start, end, seg_id in self.segments:
            ext_name = self.segment_extractors[seg_id].name
            seg_names.append(f"seg{seg_id}:{ext_name}")
        
        config = "+".join(seg_names)
        return f"stitched[{config}]+{self.transposition.name}"
    
    def apply(self, cipher_numbers, doi_words):
        """
        Apply segment-specific extraction followed by transposition.
        
        Returns:
            (raw_stream, final_stream)
        """
        stitched_stream = []
        
        for start, end, seg_id in self.segments:
            extractor = self.segment_extractors[seg_id]
            
            for position in range(start, min(end, len(cipher_numbers))):
                cipher_num = cipher_numbers[position]
                word_idx = cipher_num - 1
                
                if 0 <= word_idx < len(doi_words):
                    word = doi_words[word_idx]
                    char = extractor.extract(word, word_idx, position, 'DOI')
                    stitched_stream.append(char)
                else:
                    stitched_stream.append('?')
        
        raw = ''.join(stitched_stream)
        final = self.transposition.apply(raw)
        
        return raw, final


def evaluate_stitched_strategy(strategy, cipher_numbers, doi_words):
    """Evaluate a stitched strategy and return results"""
    raw, final = strategy.apply(cipher_numbers, doi_words)
    
    # Score final stream
    scores = signal_score.score_stream(final, use_phase3_metrics=True)
    
    # Count valid mappings
    valid = sum(1 for c in raw if c != '?')
    coverage = (valid / len(raw)) * 100
    
    # Detect fragments
    fragments = signal_score.detect_word_fragments(final)
    
    # Build extractor description
    ext_desc = []
    for start, end, seg_id in strategy.segments:
        ext = strategy.segment_extractors[seg_id]
        ext_desc.append(f"seg{seg_id}:{ext.name}")
    
    return {
        'strategy_name': strategy.get_name(),
        'extractor_config': " | ".join(ext_desc),
        'transposition': strategy.transposition.name,
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
        'final_stream': final
    }


def save_results_csv(results, filename):
    """Save results to CSV"""
    if not results:
        return
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['rank', 'total_score', 'extractor_config', 'transposition',
                     'bigram_score', 'trigram_score', 'quadgram_score',
                     'vowel_score', 'dict_score', 'letter_freq_score', 'entropy_score',
                     'fragment_score', 'coverage', 'valid_mappings', 'fragment_count']
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, result in enumerate(results, 1):
            row = {k: result[k] for k in fieldnames if k in result}
            row['rank'] = i
            row['fragment_count'] = len(result['fragments'])
            writer.writerow(row)


def save_top20_readable(results, filename, baseline_score=37.28):
    """Save top 20 results in human-readable format"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 6 TOP 20 STITCHED STRATEGIES\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Baseline (Phase 5 best): {baseline_score:.2f}/100\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results[:20], 1):
            improvement = result['total_score'] - baseline_score
            f.write(f"RANK #{i}  Score: {result['total_score']:.2f}/100  ")
            f.write(f"(Baseline: {improvement:+.2f})\n")
            f.write("-" * 80 + "\n")
            f.write(f"Extractor Config:\n  {result['extractor_config']}\n")
            f.write(f"Transposition: {result['transposition']}\n")
            f.write(f"Coverage: {result['coverage']:.1f}% ({result['valid_mappings']}/520)\n\n")
            
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


if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 6 STITCHED DECODER")
    print("=" * 80)
    print("\nThis module provides infrastructure for segment-specific extraction.")
    print("Use specific test scripts:")
    print("  - phase6_optimal_test.py for Task B (optimal configuration)")
    print("  - phase6_beam_search.py for Task C (beam search)")
    print("  - phase6_boundary_test.py for Task D (boundary variations)")
