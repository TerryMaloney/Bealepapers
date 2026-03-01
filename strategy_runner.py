"""
AUTOMATED STRATEGY RUNNER
Run comprehensive test matrix across all extraction and transposition methods.

Tests: 11 offsets × 15 extractors × 23 transpositions = 3,795 combinations
"""

import re
from pathlib import Path
from datetime import datetime
import time

# Import our modules
import extractors
import transposition
import signal_score


def normalize(text):
    """Normalize text to lowercase words only"""
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]


def load_corpus():
    """Load all text files and return word lists"""
    vdr = normalize(Path("texts/vdr.txt").read_text(encoding="utf-8"))
    doi = normalize(Path("texts/doi_from_beale.txt").read_text(encoding="utf-8"))
    signers = normalize(Path("texts/signers.txt").read_text(encoding="utf-8"))
    articles = normalize(Path("texts/articles.txt").read_text(encoding="utf-8"))
    
    return {
        'vdr': vdr,
        'doi': doi,
        'signers': signers,
        'articles': articles,
        'master': vdr + doi + signers + articles
    }


def load_cipher1():
    """Load Cipher 1 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]


def get_doc_source(idx: int, vdr_len: int, doi_len: int, signers_len: int) -> str:
    """Determine which document a word index comes from"""
    if idx < vdr_len:
        return 'VDR'
    elif idx < vdr_len + doi_len:
        return 'DOI'
    elif idx < vdr_len + doi_len + signers_len:
        return 'SIGNERS'
    else:
        return 'ARTICLES'


def extract_stream(cipher_numbers, corpus, extractor, offset, count=200):
    """
    Extract a character stream using specified extractor and offset.
    
    Args:
        cipher_numbers: List of cipher numbers
        corpus: Dictionary with word lists
        extractor: Extractor object
        offset: Offset value (e.g., 335)
        count: Number of cipher numbers to process
    
    Returns:
        String of extracted characters
    """
    vdr_len = len(corpus['vdr'])
    doi_len = len(corpus['doi'])
    signers_len = len(corpus['signers'])
    master = corpus['master']
    
    stream = []
    
    for i, cipher_num in enumerate(cipher_numbers[:count]):
        # Apply offset logic
        if cipher_num <= offset:
            idx = cipher_num - 1
        else:
            idx = (cipher_num - offset) + vdr_len - 1
        
        # Get word and document source
        if 0 <= idx < len(master):
            word = master[idx]
            doc_source = get_doc_source(idx, vdr_len, doi_len, signers_len)
            
            # Extract character using extractor
            char = extractor.extract(word, idx, i, doc_source)
            stream.append(char)
        else:
            stream.append("?")
    
    return ''.join(stream)


def run_strategy(cipher_numbers, corpus, extractor, trans, offset, count=200):
    """
    Run a single strategy: extract stream, apply transposition, score.
    
    Returns:
        Dictionary with strategy details and score
    """
    # Extract stream
    raw_stream = extract_stream(cipher_numbers, corpus, extractor, offset, count)
    
    # Apply transposition
    transformed_stream = trans.apply(raw_stream)
    
    # Score the result
    scores = signal_score.score_stream(transformed_stream)
    
    return {
        'offset': offset,
        'extractor': extractor.name,
        'transposition': trans.name,
        'total_score': scores['total_score'],
        'bigram_score': scores['bigram_score'],
        'trigram_score': scores['trigram_score'],
        'vowel_score': scores['vowel_ratio_score'],
        'dict_score': scores['dictionary_score'],
        'stream_preview': transformed_stream[:100],  # First 100 chars
        'raw_stream_preview': raw_stream[:100]
    }


def run_comprehensive_test(sample_size=200):
    """
    Run comprehensive test matrix across all combinations.
    
    Args:
        sample_size: Number of cipher numbers to test (default 200)
    """
    print("=" * 70)
    print("STRATEGY RUNNER - COMPREHENSIVE TEST MATRIX")
    print("=" * 70)
    
    start_time = time.time()
    
    # Load data
    print("\n[1/4] Loading corpus and cipher...")
    corpus = load_corpus()
    cipher1 = load_cipher1()
    
    print(f"  Corpus: {len(corpus['master'])} words")
    print(f"  Cipher 1: {len(cipher1)} numbers")
    print(f"  Testing first {sample_size} numbers")
    
    # Get all extractors and transpositions
    print("\n[2/4] Initializing test matrix...")
    all_extractors = extractors.ALL_EXTRACTORS
    all_transpositions = transposition.ALL_TRANSPOSITIONS
    offsets = list(range(330, 341))  # 330-340
    
    total_tests = len(offsets) * len(all_extractors) * len(all_transpositions)
    print(f"  Offsets: {len(offsets)}")
    print(f"  Extractors: {len(all_extractors)}")
    print(f"  Transpositions: {len(all_transpositions)}")
    print(f"  Total combinations: {total_tests:,}")
    
    # Run all combinations
    print("\n[3/4] Running strategy tests...")
    print("  (This may take 2-5 minutes)")
    
    results = []
    tested = 0
    last_report = 0
    
    for offset in offsets:
        for ext in all_extractors:
            for trans in all_transpositions:
                result = run_strategy(cipher1, corpus, ext, trans, offset, sample_size)
                results.append(result)
                tested += 1
                
                # Progress report every 10%
                progress = (tested / total_tests) * 100
                if progress - last_report >= 10:
                    elapsed = time.time() - start_time
                    print(f"    Progress: {progress:.0f}% ({tested}/{total_tests}) - {elapsed:.1f}s elapsed")
                    last_report = progress
    
    elapsed = time.time() - start_time
    print(f"\n  Completed {tested:,} tests in {elapsed:.1f} seconds")
    print(f"  Average: {elapsed/tested*1000:.2f}ms per test")
    
    # Sort results by score
    print("\n[4/4] Analyzing results...")
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    report_file = output_dir / f"strategy_results_{timestamp}.txt"
    
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 2 CRYPTANALYSIS - COMPREHENSIVE STRATEGY TEST RESULTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Strategies Tested: {len(results):,}\n")
        f.write(f"Sample Size: {sample_size} cipher numbers\n")
        f.write(f"Execution Time: {elapsed:.1f} seconds\n\n")
        
        # Top 50 results
        f.write("=" * 80 + "\n")
        f.write("TOP 50 SCORING STRATEGIES\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"{'Rank':>4} | {'Score':>5} | {'Offset':>6} | {'Extractor':<22} | {'Transposition':<20}\n")
        f.write("-" * 80 + "\n")
        
        for i, result in enumerate(results[:50], 1):
            f.write(f"{i:4d} | {result['total_score']:5.1f} | {result['offset']:6d} | "
                   f"{result['extractor']:<22s} | {result['transposition']:<20s}\n")
        
        # Detailed top 10
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED ANALYSIS - TOP 10 STRATEGIES\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results[:10], 1):
            f.write(f"--- RANK {i} ---\n")
            f.write(f"Total Score:    {result['total_score']:.2f}/100\n")
            f.write(f"Offset:         {result['offset']}\n")
            f.write(f"Extractor:      {result['extractor']}\n")
            f.write(f"Transposition:  {result['transposition']}\n")
            f.write(f"Bigram Score:   {result['bigram_score']:.2f}/100\n")
            f.write(f"Trigram Score:  {result['trigram_score']:.2f}/100\n")
            f.write(f"Vowel Score:    {result['vowel_score']:.2f}/100\n")
            f.write(f"Dict Score:     {result['dict_score']:.2f}/100\n")
            f.write(f"\nTransformed Stream (first 100 chars):\n")
            f.write(f"{result['stream_preview']}\n\n")
            f.write(f"Raw Stream (first 100 chars):\n")
            f.write(f"{result['raw_stream_preview']}\n\n")
        
        # Score distribution
        f.write("=" * 80 + "\n")
        f.write("SCORE DISTRIBUTION\n")
        f.write("=" * 80 + "\n\n")
        
        score_ranges = [
            (60, 100, "60-100 (Strong English signal)"),
            (40, 60, "40-60 (Moderate signal)"),
            (30, 40, "30-40 (Weak signal)"),
            (20, 30, "20-30 (Very weak signal)"),
            (0, 20, "0-20 (Noise)")
        ]
        
        for low, high, label in score_ranges:
            count = sum(1 for r in results if low <= r['total_score'] < high)
            pct = (count / len(results)) * 100
            f.write(f"{label:35s}: {count:4d} ({pct:5.1f}%)\n")
        
        # Statistics
        f.write("\n" + "=" * 80 + "\n")
        f.write("STATISTICS\n")
        f.write("=" * 80 + "\n\n")
        
        scores = [r['total_score'] for r in results]
        f.write(f"Highest Score:  {max(scores):.2f}\n")
        f.write(f"Lowest Score:   {min(scores):.2f}\n")
        f.write(f"Average Score:  {sum(scores)/len(scores):.2f}\n")
        f.write(f"Median Score:   {sorted(scores)[len(scores)//2]:.2f}\n")
        
        # Best performing combinations
        f.write("\n" + "=" * 80 + "\n")
        f.write("BEST PERFORMING EXTRACTORS (Average Score)\n")
        f.write("=" * 80 + "\n\n")
        
        extractor_scores = {}
        for result in results:
            ext = result['extractor']
            if ext not in extractor_scores:
                extractor_scores[ext] = []
            extractor_scores[ext].append(result['total_score'])
        
        ext_avg = [(ext, sum(scores)/len(scores)) for ext, scores in extractor_scores.items()]
        ext_avg.sort(key=lambda x: x[1], reverse=True)
        
        for ext, avg_score in ext_avg[:10]:
            f.write(f"{ext:<25s}: {avg_score:5.2f}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("BEST PERFORMING TRANSPOSITIONS (Average Score)\n")
        f.write("=" * 80 + "\n\n")
        
        trans_scores = {}
        for result in results:
            trans = result['transposition']
            if trans not in trans_scores:
                trans_scores[trans] = []
            trans_scores[trans].append(result['total_score'])
        
        trans_avg = [(trans, sum(scores)/len(scores)) for trans, scores in trans_scores.items()]
        trans_avg.sort(key=lambda x: x[1], reverse=True)
        
        for trans, avg_score in trans_avg[:10]:
            f.write(f"{trans:<25s}: {avg_score:5.2f}\n")
    
    # Also create a symlink/copy to latest
    latest_file = output_dir / "strategy_results.txt"
    with open(latest_file, "w", encoding="utf-8") as f:
        with open(report_file, "r", encoding="utf-8") as src:
            f.write(src.read())
    
    print(f"\n  Report saved to: {report_file}")
    print(f"  Latest copy: {latest_file}")
    
    # Print summary to console
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"\nTop 5 Strategies:")
    for i, result in enumerate(results[:5], 1):
        print(f"  {i}. Score {result['total_score']:.1f} | Offset {result['offset']} | "
              f"{result['extractor']} + {result['transposition']}")
    
    print(f"\nHighest Score: {max(scores):.2f}")
    print(f"Average Score: {sum(scores)/len(scores):.2f}")
    
    if max(scores) > 50:
        print("\n[!] STRONG SIGNAL DETECTED (score > 50)")
        print("    Review top strategies for English-like patterns")
    elif max(scores) > 35:
        print("\n[~] MODERATE SIGNAL DETECTED (score > 35)")
        print("    Further investigation recommended")
    else:
        print("\n[*] WEAK SIGNAL (all scores < 35)")
        print("    May indicate wrong corpus or unsolvable cipher")
    
    return results


if __name__ == "__main__":
    run_comprehensive_test(sample_size=200)
