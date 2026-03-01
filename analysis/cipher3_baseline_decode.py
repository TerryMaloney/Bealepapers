"""
Cipher 3 Baseline Decoding and Semantic Analysis

Decode Cipher 3 with current corpus using top strategies from Phase 7.
Focus on name/location pattern extraction using domain-specific scoring.

Key advantage: Cipher 3 domain (Names & Residences) has stronger semantic
anchors than Cipher 1. Patterns emerge EVEN with wrong corpus.
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
import re
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors import ALL_EXTRACTORS
from transposition import ALL_TRANSPOSITIONS
from scoring.cipher3_domain_scorer import Cipher3DomainScorer
from signal_score import score_stream


def load_cipher(cipher_num: int) -> List[int]:
    """Load cipher numbers from canonical file (if available) or beale_papers.txt."""
    from pathlib import Path
    canonical_path = Path(f"corpus/cipher{cipher_num}_numbers_canonical.txt")
    if canonical_path.exists():
        with open(canonical_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                return [int(n.strip()) for n in line.split(",") if n.strip().replace(".", "").isdigit()]
    # Fallback to beale_papers.txt
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    line_map = {1: 2, 2: 58, 3: 6}
    cipher_line = lines[line_map[cipher_num]].strip()
    return [int(n.strip()) for n in cipher_line.split(",") if n.strip()]


def load_current_corpus() -> List[str]:
    """Load current DOI corpus (beale_adjusted_doi preferred, falls back to beale_embedded)."""
    from corpus.doi_editions import DOICorpusLoader
    
    loader = DOICorpusLoader()
    try:
        edition = loader.load_edition('beale_adjusted_doi')
    except Exception:
        edition = loader.load_edition('beale_embedded')
    
    # Use hyphen_keep tokenizer (same as Phase 7)
    from corpus.tokenizers import TokenizerRegistry
    tokenizer = TokenizerRegistry.get_tokenizer('hyphen_keep')
    
    # Tokenize the source text
    tokens = tokenizer.tokenize(edition.source_text)
    return tokens


def decode_cipher3_with_strategy(cipher3: List[int], corpus: List[str],
                                 extractor, transposition) -> str:
    """Decode Cipher 3 using extractor + transposition."""
    
    # Extract
    decoded = []
    for cipher_pos, cipher_num in enumerate(cipher3):
        word_idx = cipher_num - 1  # Convert to 0-indexed
        
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
    
    # Apply transposition
    transposed = transposition.apply(decoded_stream)
    
    return transposed


def extract_name_like_sequences(stream: str, min_length: int = 4) -> List[str]:
    """
    Extract sequences that look like names.
    
    Heuristics:
    - Capitalized words (or all caps)
    - 2-token sequences (first name + surname)
    - Length >= min_length
    """
    # Split into word-like tokens
    words = re.findall(r'[A-Z][a-z]+|[A-Z]{2,}', stream)
    
    name_patterns = []
    
    # Single capitalized words >= min_length
    for word in words:
        if len(word) >= min_length:
            name_patterns.append(word)
    
    # 2-token sequences
    for i in range(len(words) - 1):
        two_token = f"{words[i]} {words[i+1]}"
        name_patterns.append(two_token)
    
    return name_patterns


def extract_location_tokens(stream: str, location_keywords: List[str]) -> List[Tuple[str, int]]:
    """Extract location-related tokens from stream."""
    stream_lower = stream.lower()
    
    found = []
    for keyword in location_keywords:
        count = stream_lower.count(keyword)
        if count > 0:
            found.append((keyword, count))
    
    return sorted(found, key=lambda x: x[1], reverse=True)


def run_cipher3_baseline_analysis(topk: int = 20):
    """
    Run Cipher 3 baseline analysis with top strategies.
    
    Args:
        topk: Number of top strategies to test
    """
    print("=" * 80)
    print("CIPHER 3 BASELINE DECODING & SEMANTIC ANALYSIS")
    print("=" * 80)
    
    # Load Cipher 3
    print("\n[Step 1] Loading Cipher 3...")
    cipher3 = load_cipher(3)
    print(f"Cipher 3: {len(cipher3)} numbers")
    
    # Load current corpus
    print("\n[Step 2] Loading current corpus...")
    corpus = load_current_corpus()
    print(f"Corpus: {len(corpus)} words")
    
    # Initialize scorers
    print("\n[Step 3] Initializing scorers...")
    c3_scorer = Cipher3DomainScorer()
    
    # Define location keywords from Cipher3DomainScorer
    location_keywords = list(c3_scorer.location_tokens.keys())
    
    # Get top strategies from Phase 7
    print(f"\n[Step 4] Testing top {topk} strategies...")
    
    # Best extractors from Phase 7
    best_extractor_names = [
        'position_times_2',
        'cycle_every_5',
        'nth_letter_by_position',
        'reverse_position',
        'first_letter'
    ]
    
    # Best transpositions from Phase 7
    best_transposition_names = [
        'none',
        'rect_w26_spiral_ccw',
        'every_3th',
        'rect_w13_spiral_ccw',
        'chunk_reverse_3'
    ]
    
    extractors = [e for e in ALL_EXTRACTORS if e.name in best_extractor_names]
    transpositions = [t for t in ALL_TRANSPOSITIONS if t.name in best_transposition_names]
    
    print(f"  Extractors: {len(extractors)}")
    print(f"  Transpositions: {len(transpositions)}")
    print(f"  Total combinations: {len(extractors) * len(transpositions)}")
    
    results = []
    
    for extractor in extractors:
        for transposition in transpositions:
            # Decode Cipher 3
            decoded = decode_cipher3_with_strategy(cipher3, corpus, extractor, transposition)
            
            # Score with domain scorer
            domain_score, domain_components = c3_scorer.score(decoded)
            
            # Also get general English score for comparison
            english_result = score_stream(decoded)
            english_score = english_result.get('total_score', 0.0)
            
            # Extract patterns
            name_patterns = extract_name_like_sequences(decoded)
            location_tokens = extract_location_tokens(decoded, location_keywords)
            
            results.append({
                'extractor': extractor.name,
                'transposition': transposition.name,
                'domain_score': domain_score,
                'english_score': english_score,
                'location_token_count': len(location_tokens),
                'name_pattern_count': len(name_patterns),
                'decoded_sample': decoded[:200],
                'domain_components': domain_components,
                'name_patterns_top5': name_patterns[:5],
                'location_tokens_top5': location_tokens[:5]
            })
    
    # Sort by domain score
    results.sort(key=lambda x: x['domain_score'], reverse=True)
    
    print(f"\n[Step 5] Analysis complete: {len(results)} strategies tested")
    
    return results


def save_cipher3_baseline_results(results: List[Dict], timestamp: str):
    """Save Cipher 3 baseline results."""
    output_dir = Path("output/phase10")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save CSV
    csv_file = output_dir / f"cipher3_baseline_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['rank', 'extractor', 'transposition', 'domain_score',
                     'english_score', 'location_token_count', 'name_pattern_count']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, result in enumerate(results, 1):
            row = {k: result.get(k, '') for k in fieldnames if k != 'rank'}
            row['rank'] = i
            writer.writerow(row)
    
    # Save detailed text report
    txt_file = output_dir / f"cipher3_baseline_{timestamp}.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CIPHER 3 BASELINE DECODING RESULTS\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("OBJECTIVE:\n")
        f.write("Extract name/location patterns from Cipher 3 using domain-specific scoring.\n")
        f.write("This analysis works EVEN with wrong corpus due to semantic anchors.\n\n")
        
        f.write(f"Strategies tested: {len(results)}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("TOP 10 STRATEGIES BY DOMAIN SCORE\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results[:10], 1):
            f.write(f"RANK {i}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Extractor: {result['extractor']}\n")
            f.write(f"Transposition: {result['transposition']}\n")
            f.write(f"\nScores:\n")
            f.write(f"  Domain (Names & Residences): {result['domain_score']:.2f}/100\n")
            f.write(f"  English likelihood: {result['english_score']:.2f}/100\n")
            f.write(f"  Location tokens found: {result['location_token_count']}\n")
            f.write(f"  Name patterns found: {result['name_pattern_count']}\n")
            
            f.write(f"\nDomain Score Components:\n")
            for key, value in result['domain_components'].items():
                f.write(f"  {key:20s}: {value:6.2f}\n")
            
            if result['name_patterns_top5']:
                f.write(f"\nTop Name Patterns:\n")
                for pattern in result['name_patterns_top5']:
                    f.write(f"  - {pattern}\n")
            
            if result['location_tokens_top5']:
                f.write(f"\nTop Location Tokens:\n")
                for token, count in result['location_tokens_top5']:
                    f.write(f"  - {token}: {count} occurrences\n")
            
            f.write(f"\nDecoded Sample (first 200 chars):\n")
            f.write(f"{result['decoded_sample']}\n\n")
            f.write("=" * 80 + "\n\n")
    
    # Save JSON for programmatic access
    json_file = output_dir / f"cipher3_baseline_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'generated': datetime.now().isoformat(),
            'strategies_tested': len(results),
            'results': results[:20]  # Save top 20 to JSON
        }, f, indent=2)
    
    print(f"\nResults saved:")
    print(f"  CSV: {csv_file}")
    print(f"  Report: {txt_file}")
    print(f"  JSON: {json_file}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run Cipher 3 baseline decoding and semantic analysis"
    )
    parser.add_argument('--topk', type=int, default=20,
                       help='Number of top strategies to test (default: 20)')
    
    args = parser.parse_args()
    
    # Run analysis
    results = run_cipher3_baseline_analysis(topk=args.topk)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_cipher3_baseline_results(results, timestamp)
    
    # Print summary
    print("\n" + "=" * 80)
    print("CIPHER 3 BASELINE ANALYSIS COMPLETE")
    print("=" * 80)
    
    if results:
        best = results[0]
        print(f"\nBest strategy (by domain score):")
        print(f"  {best['extractor']} + {best['transposition']}")
        print(f"  Domain score: {best['domain_score']:.2f}/100")
        print(f"  English score: {best['english_score']:.2f}/100")
        print(f"  Location tokens: {best['location_token_count']}")
        print(f"  Name patterns: {best['name_pattern_count']}")
        
        print(f"\nTop 5 strategies:")
        for i, result in enumerate(results[:5], 1):
            print(f"{i}. {result['extractor']:25s} + {result['transposition']:25s}")
            print(f"   Domain: {result['domain_score']:5.2f} | "
                  f"English: {result['english_score']:5.2f} | "
                  f"Locations: {result['location_token_count']:2d} | "
                  f"Names: {result['name_pattern_count']:2d}")
    
    return results


if __name__ == "__main__":
    main()
