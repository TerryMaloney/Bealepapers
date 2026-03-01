"""
Fragment Consensus Analysis

Identifies fragments (>=4 chars) that appear in multiple independent strategies.

If genuine cipher:
- Fragments should consensus across strategies
- Fragments should concentrate in specific cipher regions

If hoax or noise:
- No consensus (random fragments per strategy)
"""

import json
from collections import Counter
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import re
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors import ALL_EXTRACTORS
from transposition import ALL_TRANSPOSITIONS
from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry


def load_cipher(cipher_num: int) -> List[int]:
    """Load cipher numbers from beale_papers.txt."""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    line_map = {1: 2, 2: 58, 3: 6}
    cipher_line = lines[line_map[cipher_num]].strip()
    return [int(n.strip()) for n in cipher_line.split(",") if n.strip()]


def load_corpus() -> List[str]:
    """Load DOI corpus."""
    loader = DOICorpusLoader()
    edition = loader.load_edition('beale_embedded')
    tokenizer = TokenizerRegistry.get_tokenizer('hyphen_keep')
    return tokenizer.tokenize(edition.source_text)


def decode_cipher(cipher: List[int], corpus: List[str], extractor, transposition) -> str:
    """Decode cipher with strategy."""
    decoded = []
    for cipher_pos, cipher_num in enumerate(cipher):
        word_idx = cipher_num - 1
        if 0 <= word_idx < len(corpus):
            word = corpus[word_idx]
            try:
                letter = extractor.extract(word, word_idx, cipher_pos, 'DOI')
                decoded.append(letter if letter else '?')
            except:
                decoded.append('?')
        else:
            decoded.append('?')
    
    decoded_stream = ''.join(decoded)
    return transposition.apply(decoded_stream)


def is_english_like(fragment: str) -> bool:
    """Check if fragment looks English-like."""
    if len(fragment) < 4:
        return False
    
    # Must be mostly letters
    if sum(c.isalpha() for c in fragment) < len(fragment) * 0.8:
        return False
    
    # Check for reasonable vowel ratio (20-60%)
    vowels = sum(1 for c in fragment.upper() if c in 'AEIOU')
    vowel_ratio = vowels / len(fragment)
    if vowel_ratio < 0.2 or vowel_ratio > 0.6:
        return False
    
    # Check for consonant runs (<4)
    consonant_run = 0
    for c in fragment.upper():
        if c.isalpha() and c not in 'AEIOU':
            consonant_run += 1
            if consonant_run >= 4:
                return False
        else:
            consonant_run = 0
    
    return True


def extract_fragments(stream: str, min_length: int = 4, max_length: int = 8) -> List[str]:
    """Extract all fragments of given length range."""
    fragments = []
    
    for length in range(min_length, max_length + 1):
        for i in range(len(stream) - length + 1):
            fragment = stream[i:i+length]
            if is_english_like(fragment):
                fragments.append(fragment.lower())
    
    return fragments


def find_consensus_fragments(cipher_num: int = 1, topk: int = 20, min_consensus: int = 3):
    """
    Find fragments appearing in multiple independent strategies.
    
    Args:
        cipher_num: Which cipher to analyze (1, 2, or 3)
        topk: Number of top strategies to test
        min_consensus: Minimum number of strategies that must agree
    
    Returns:
        Dict with consensus fragments and their frequencies
    """
    print("=" * 80)
    print(f"FRAGMENT CONSENSUS ANALYSIS - CIPHER {cipher_num}")
    print("=" * 80)
    
    # Load cipher and corpus
    print(f"\n[Step 1] Loading Cipher {cipher_num}...")
    cipher = load_cipher(cipher_num)
    print(f"Cipher {cipher_num}: {len(cipher)} numbers")
    
    print("\n[Step 2] Loading corpus...")
    corpus = load_corpus()
    print(f"Corpus: {len(corpus)} words")
    
    # Get top strategies (use best from Phase 7)
    print(f"\n[Step 3] Testing {topk} strategies...")
    
    best_extractors = [
        'position_times_2',
        'cycle_every_5',
        'nth_letter_by_position',
        'reverse_position',
        'first_letter'
    ]
    
    best_transpositions = [
        'none',
        'rect_w26_spiral_ccw',
        'every_3th',
        'chunk_reverse_3'
    ]
    
    extractors = [e for e in ALL_EXTRACTORS if e.name in best_extractors]
    transpositions = [t for t in ALL_TRANSPOSITIONS if t.name in best_transpositions]
    
    # Decode with each strategy
    fragment_counts = Counter()
    fragment_sources = {}  # Track which strategies produced each fragment
    
    strategy_count = 0
    for extractor in extractors:
        for transposition in transpositions:
            strategy_count += 1
            if strategy_count > topk:
                break
            
            decoded = decode_cipher(cipher, corpus, extractor, transposition)
            fragments = extract_fragments(decoded)
            
            for frag in set(fragments):  # Unique fragments per strategy
                fragment_counts[frag] += 1
                if frag not in fragment_sources:
                    fragment_sources[frag] = []
                fragment_sources[frag].append(f"{extractor.name}+{transposition.name}")
        
        if strategy_count > topk:
            break
    
    print(f"  Strategies tested: {strategy_count}")
    print(f"  Unique fragments found: {len(fragment_counts)}")
    
    # Find consensus fragments
    consensus_fragments = {
        frag: count 
        for frag, count in fragment_counts.items() 
        if count >= min_consensus
    }
    
    print(f"  Consensus fragments (>={min_consensus} strategies): {len(consensus_fragments)}")
    
    # Sort by frequency
    sorted_fragments = sorted(consensus_fragments.items(), key=lambda x: x[1], reverse=True)
    
    return {
        'cipher': cipher_num,
        'strategies_tested': strategy_count,
        'min_consensus': min_consensus,
        'total_fragments': len(fragment_counts),
        'consensus_fragments': len(consensus_fragments),
        'top_fragments': sorted_fragments[:50],
        'fragment_sources': {frag: fragment_sources[frag] for frag, _ in sorted_fragments[:50]}
    }


def save_consensus_results(results: Dict, timestamp: str):
    """Save consensus analysis results."""
    output_dir = Path("output/phase10")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = output_dir / f"fragment_consensus_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    txt_file = output_dir / f"fragment_consensus_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"FRAGMENT CONSENSUS ANALYSIS - CIPHER {results['cipher']}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE:\n")
        f.write("Find fragments (>=4 chars) appearing in multiple independent strategies.\n")
        f.write("Consensus validates genuine cipher (vs noise fitting).\n\n")
        
        f.write(f"Strategies tested: {results['strategies_tested']}\n")
        f.write(f"Minimum consensus: {results['min_consensus']} strategies\n")
        f.write(f"Total unique fragments: {results['total_fragments']}\n")
        f.write(f"Consensus fragments: {results['consensus_fragments']}\n\n")
        
        if results['consensus_fragments'] > 0:
            f.write("=" * 80 + "\n")
            f.write("TOP 20 CONSENSUS FRAGMENTS\n")
            f.write("=" * 80 + "\n\n")
            
            for i, (frag, count) in enumerate(results['top_fragments'][:20], 1):
                f.write(f"{i:2d}. \"{frag}\" - appears in {count} strategies\n")
                sources = results['fragment_sources'].get(frag, [])
                f.write(f"    Found in: {', '.join(sources[:3])}")
                if len(sources) > 3:
                    f.write(f" ... and {len(sources)-3} more")
                f.write("\n\n")
        else:
            f.write("NO CONSENSUS FRAGMENTS FOUND\n")
            f.write("This suggests either:\n")
            f.write("1. Strategies are fitting noise (not genuine signal)\n")
            f.write("2. Wrong corpus prevents fragment emergence\n")
            f.write("3. Need more diverse strategies or lower consensus threshold\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("INTERPRETATION\n")
        f.write("=" * 80 + "\n\n")
        
        if results['consensus_fragments'] >= 10:
            f.write("STRONG CONSENSUS: Multiple fragments appear across strategies.\n")
            f.write("This supports genuine cipher structure.\n")
        elif results['consensus_fragments'] >= 3:
            f.write("WEAK CONSENSUS: Few fragments show agreement.\n")
            f.write("Partial signal, but not definitive.\n")
        else:
            f.write("NO CONSENSUS: Fragments are strategy-specific.\n")
            f.write("Suggests noise fitting or wrong corpus.\n")
    
    print(f"\nResults saved:")
    print(f"  JSON: {json_file}")
    print(f"  Report: {txt_file}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Find consensus fragments across strategies"
    )
    parser.add_argument('--cipher', type=int, default=1, choices=[1,2,3],
                       help='Cipher number to analyze')
    parser.add_argument('--topk', type=int, default=20,
                       help='Number of strategies to test')
    parser.add_argument('--min-consensus', type=int, default=3,
                       help='Minimum strategies that must agree')
    
    args = parser.parse_args()
    
    results = find_consensus_fragments(
        cipher_num=args.cipher,
        topk=args.topk,
        min_consensus=args.min_consensus
    )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_consensus_results(results, timestamp)
    
    print("\n" + "=" * 80)
    print("FRAGMENT CONSENSUS ANALYSIS COMPLETE")
    print("=" * 80)
    
    if results['consensus_fragments'] > 0:
        print(f"\nFound {results['consensus_fragments']} consensus fragments")
        print("\nTop 5 fragments:")
        for i, (frag, count) in enumerate(results['top_fragments'][:5], 1):
            print(f"  {i}. \"{frag}\" - {count} strategies")
    else:
        print("\nNo consensus fragments found.")
        print("This suggests either noise fitting or wrong corpus preventing signal.")
    
    return results


if __name__ == "__main__":
    main()
