"""
VDR BIAS INVESTIGATION
Test if Cipher 1 primarily uses VDR as key book.

Phase 1 showed 76% of first 100 mappings came from VDR.
This tests VDR-only vs full-stack performance.
"""

import re
from pathlib import Path
import signal_score
import extractors
import transposition


def normalize(text):
    """Normalize text to lowercase words only"""
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return [w for w in text.split() if w]


def load_texts():
    """Load all text files separately"""
    vdr = normalize(Path("texts/vdr.txt").read_text(encoding="utf-8"))
    doi = normalize(Path("texts/doi_from_beale.txt").read_text(encoding="utf-8"))
    signers = normalize(Path("texts/signers.txt").read_text(encoding="utf-8"))
    articles = normalize(Path("texts/articles.txt").read_text(encoding="utf-8"))
    
    return vdr, doi, signers, articles


def load_cipher1():
    """Load Cipher 1 numbers"""
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [int(n.strip()) for n in lines[2].strip().split(",") if n.strip()]


def extract_with_corpus(cipher_numbers, corpus, offset, extractor, count=200):
    """Extract stream using specified corpus and offset"""
    stream = []
    
    for i, cipher_num in enumerate(cipher_numbers[:count]):
        # Apply offset logic
        if cipher_num <= offset:
            idx = cipher_num - 1
        else:
            idx = (cipher_num - offset) - 1
        
        # Get word
        if 0 <= idx < len(corpus):
            word = corpus[idx]
            char = extractor.extract(word, idx, i, 'VDR')
            stream.append(char)
        else:
            stream.append("?")
    
    return ''.join(stream)


def test_vdr_hypotheses():
    """Test VDR-only vs full-stack hypotheses"""
    print("=" * 70)
    print("VDR BIAS INVESTIGATION")
    print("=" * 70)
    
    # Load data
    print("\n[1/4] Loading data...")
    vdr, doi, signers, articles = load_texts()
    cipher1 = load_cipher1()
    
    full_stack = vdr + doi + signers + articles
    
    print(f"  VDR: {len(vdr)} words")
    print(f"  DOI: {len(doi)} words")
    print(f"  Signers: {len(signers)} words")
    print(f"  Articles: {len(articles)} words")
    print(f"  Full stack: {len(full_stack)} words")
    print(f"  Cipher 1: {len(cipher1)} numbers")
    
    # Test configurations
    print("\n[2/4] Testing configurations...")
    
    configs = [
        {
            'name': 'VDR-only (no offset)',
            'corpus': vdr,
            'offset': 0
        },
        {
            'name': 'VDR-only (offset 335)',
            'corpus': vdr,
            'offset': 335
        },
        {
            'name': 'VDR-only (offset 860)',
            'corpus': vdr,
            'offset': 860
        },
        {
            'name': 'Full stack (offset 335)',
            'corpus': full_stack,
            'offset': 335
        },
        {
            'name': 'Full stack (offset 860)',
            'corpus': full_stack,
            'offset': 860
        },
        {
            'name': 'DOI-only (no offset)',
            'corpus': doi,
            'offset': 0
        }
    ]
    
    # Use top-scoring extractor from Phase 2
    top_extractor = extractors.get_extractor("nth_letter_by_position")
    top_trans = transposition.get_transposition("every_2th")
    
    print(f"  Using extractor: {top_extractor.name}")
    print(f"  Using transposition: {top_trans.name}")
    
    # Run tests
    print("\n[3/4] Running tests...")
    results = []
    
    for config in configs:
        # Extract stream
        stream = extract_with_corpus(
            cipher1, 
            config['corpus'], 
            config['offset'],
            top_extractor,
            count=200
        )
        
        # Apply transposition
        transformed = top_trans.apply(stream)
        
        # Score
        scores = signal_score.score_stream(transformed)
        
        # Count coverage (non-? characters)
        coverage = (len(stream) - stream.count('?')) / len(stream) * 100
        
        results.append({
            'name': config['name'],
            'score': scores['total_score'],
            'bigram': scores['bigram_score'],
            'trigram': scores['trigram_score'],
            'vowel': scores['vowel_ratio_score'],
            'dict': scores['dictionary_score'],
            'coverage': coverage,
            'stream_preview': transformed[:80]
        })
    
    # Print results
    print("\n[4/4] Results:")
    print("=" * 70)
    print("\nConfiguration Comparison:")
    print(f"{'Configuration':30s} | {'Score':>5s} | {'Coverage':>8s} | Stream Preview")
    print("-" * 70)
    
    for result in results:
        print(f"{result['name']:30s} | {result['score']:5.1f} | {result['coverage']:7.1f}% | "
              f"{result['stream_preview'][:40]}")
    
    # Find best
    best = max(results, key=lambda x: x['score'])
    
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    
    print(f"\nBest Configuration: {best['name']}")
    print(f"  Score: {best['score']:.2f}/100")
    print(f"  Coverage: {best['coverage']:.1f}%")
    print(f"  Stream Preview: {best['stream_preview']}")
    
    # Compare VDR-only vs Full stack
    vdr_scores = [r['score'] for r in results if 'VDR-only' in r['name']]
    full_scores = [r['score'] for r in results if 'Full stack' in r['name']]
    
    print(f"\nVDR-only average score: {sum(vdr_scores)/len(vdr_scores):.2f}")
    print(f"Full stack average score: {sum(full_scores)/len(full_scores):.2f}")
    
    if sum(vdr_scores) > sum(full_scores):
        print("\nConclusion: VDR-ONLY shows stronger signal")
        print("Recommendation: Cipher 1 may use VDR as primary key")
    else:
        print("\nConclusion: FULL STACK shows stronger signal")
        print("Recommendation: Cipher 1 uses stacked documents as key")
    
    # Save detailed report
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "vdr_bias_analysis.txt", "w", encoding="utf-8") as f:
        f.write("VDR BIAS INVESTIGATION\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("Configuration Comparison:\n\n")
        f.write(f"{'Configuration':30s} | {'Score':>5s} | {'Bigram':>6s} | {'Trigram':>7s} | "
                f"{'Vowel':>6s} | {'Dict':>5s} | {'Coverage':>8s}\n")
        f.write("-" * 110 + "\n")
        
        for result in results:
            f.write(f"{result['name']:30s} | {result['score']:5.1f} | "
                   f"{result['bigram']:6.1f} | {result['trigram']:7.1f} | "
                   f"{result['vowel']:6.1f} | {result['dict']:5.1f} | "
                   f"{result['coverage']:7.1f}%\n")
        
        f.write(f"\n\nBest Configuration: {best['name']}\n")
        f.write(f"Score: {best['score']:.2f}/100\n")
        f.write(f"Coverage: {best['coverage']:.1f}%\n\n")
        
        f.write(f"VDR-only average: {sum(vdr_scores)/len(vdr_scores):.2f}\n")
        f.write(f"Full stack average: {sum(full_scores)/len(full_scores):.2f}\n")
    
    print(f"\nDetailed report saved to: output/vdr_bias_analysis.txt")
    
    return results


if __name__ == "__main__":
    test_vdr_hypotheses()
