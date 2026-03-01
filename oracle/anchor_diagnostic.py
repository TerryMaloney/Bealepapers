"""
Phase 12A: Hard Anchor Testing

Inspects raw alignment of the first 20 Cipher 2 positions to identify
where the initial misalignment occurs and by how many words.

Critical insight: "First mismatch at position 3" indicates initial anchor
misalignment, not progressive drift. This script provides the raw evidence.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from oracle.cipher2_evaluator import load_cipher2, load_cipher2_known_plaintext
from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry


def load_doi_tokens(edition_id: str = "beale_embedded", tokenizer_name: str = "hyphen_keep") -> List[str]:
    """Load DOI tokens for the specified edition and tokenizer."""
    loader = DOICorpusLoader()
    edition = loader.load_edition(edition_id)
    
    if not edition:
        raise ValueError(f"Edition '{edition_id}' not found")
    
    tokenizer = TokenizerRegistry.get_tokenizer(tokenizer_name)
    tokens = tokenizer.tokenize(edition.source_text)
    
    return tokens


def analyze_anchor_alignment(num_positions: int = 20) -> Dict:
    """
    Analyze raw alignment for the first N positions.
    
    Returns detailed comparison showing exactly where misalignment occurs.
    """
    # Load data
    cipher2_numbers = load_cipher2()
    known_plaintext = load_cipher2_known_plaintext()
    doi_tokens = load_doi_tokens()
    
    # Clean known plaintext to letters only
    known_clean = ''.join(c.upper() for c in known_plaintext if c.isalpha())
    
    # Analyze first N positions
    positions = []
    
    for i in range(min(num_positions, len(cipher2_numbers), len(known_clean))):
        cipher_num = cipher2_numbers[i]
        expected_letter = known_clean[i]
        
        # Get word from DOI
        word_idx = cipher_num - 1  # 1-indexed to 0-indexed
        
        if 0 <= word_idx < len(doi_tokens):
            word = doi_tokens[word_idx]
            extracted_letter = word[0].upper() if word else '?'
        else:
            word = f"[OUT_OF_RANGE:{cipher_num}]"
            extracted_letter = '?'
        
        match = (extracted_letter == expected_letter)
        
        positions.append({
            'position': i,
            'cipher_num': cipher_num,
            'word': word,
            'extracted': extracted_letter,
            'expected': expected_letter,
            'match': match
        })
    
    # Compute statistics
    matches = sum(1 for p in positions if p['match'])
    match_rate = (matches / len(positions) * 100) if positions else 0.0
    
    # Find first mismatch
    first_mismatch = -1
    first_mismatch_detail = None
    for p in positions:
        if not p['match']:
            first_mismatch = p['position']
            first_mismatch_detail = p
            break
    
    return {
        'positions': positions,
        'total_analyzed': len(positions),
        'matches': matches,
        'match_rate': match_rate,
        'first_mismatch': first_mismatch,
        'first_mismatch_detail': first_mismatch_detail,
        'doi_token_count': len(doi_tokens)
    }


def interpret_anchor_offset(results: Dict) -> str:
    """
    Interpret the anchor offset based on the first mismatch.
    
    Attempts to identify what word SHOULD be at the mismatch position
    and infer the offset.
    """
    if results['first_mismatch'] == -1:
        return "No mismatches found in analyzed positions. Anchor appears correct."
    
    detail = results['first_mismatch_detail']
    pos = detail['position']
    cipher_num = detail['cipher_num']
    word = detail['word']
    extracted = detail['extracted']
    expected = detail['expected']
    
    interpretation = []
    interpretation.append(f"\nFIRST MISMATCH ANALYSIS:")
    interpretation.append(f"  Position: {pos}")
    interpretation.append(f"  Cipher number: {cipher_num}")
    interpretation.append(f"  Word at index {cipher_num}: '{word}'")
    interpretation.append(f"  Extracted letter: '{extracted}'")
    interpretation.append(f"  Expected letter: '{expected}'")
    interpretation.append("")
    interpretation.append("INTERPRETATION:")
    
    # Try to find a word starting with the expected letter nearby
    doi_tokens = load_doi_tokens()
    
    # Search window: ±50 words around cipher_num
    search_start = max(0, cipher_num - 50)
    search_end = min(len(doi_tokens), cipher_num + 50)
    
    candidates = []
    for idx in range(search_start, search_end):
        if idx < len(doi_tokens):
            candidate_word = doi_tokens[idx]
            if candidate_word and candidate_word[0].upper() == expected:
                offset = (idx + 1) - cipher_num  # Convert to 1-indexed
                candidates.append({
                    'word_num': idx + 1,
                    'word': candidate_word,
                    'offset': offset
                })
    
    if candidates:
        interpretation.append(f"  Found {len(candidates)} words starting with '{expected}' within ±50 words:")
        for c in candidates[:10]:  # Show first 10
            interpretation.append(f"    Word {c['word_num']}: '{c['word']}' (offset: {c['offset']:+d})")
        
        if len(candidates) > 10:
            interpretation.append(f"    ... and {len(candidates) - 10} more")
        
        # Suggest most likely offset (closest to zero)
        closest = min(candidates, key=lambda x: abs(x['offset']))
        interpretation.append("")
        interpretation.append(f"  MOST LIKELY CORRECTION:")
        interpretation.append(f"    Word {closest['word_num']} '{closest['word']}' would require offset: {closest['offset']:+d}")
        
        if abs(closest['offset']) <= 5:
            interpretation.append(f"    This is a SMALL constant offset — testable in Phase 12C")
        elif abs(closest['offset']) <= 20:
            interpretation.append(f"    This is a MODERATE offset — suggests structural miscount")
        else:
            interpretation.append(f"    This is a LARGE offset — suggests wrong edition or major structural difference")
    else:
        interpretation.append(f"  No words starting with '{expected}' found within ±50 words of position {cipher_num}")
        interpretation.append(f"  This suggests either:")
        interpretation.append(f"    1. Wrong edition of DOI")
        interpretation.append(f"    2. Different tokenization convention")
        interpretation.append(f"    3. Incorrect known plaintext")
    
    return '\n'.join(interpretation)


def save_anchor_report(results: Dict, output_path: Path):
    """Save anchor diagnostic report to file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 12A: HARD ANCHOR TESTING\n")
        f.write("Raw Alignment Analysis - First 20 Positions\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"DOI Edition: beale_embedded\n")
        f.write(f"DOI Token Count: {results['doi_token_count']}\n")
        f.write("\n")
        
        f.write("SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Positions analyzed: {results['total_analyzed']}\n")
        f.write(f"Matches: {results['matches']}\n")
        f.write(f"Match rate: {results['match_rate']:.2f}%\n")
        f.write(f"First mismatch: position {results['first_mismatch']}\n")
        f.write("\n")
        
        f.write("POSITION-BY-POSITION ALIGNMENT\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Pos':<5} {'Cipher#':<8} {'Word':<20} {'Ext':<5} {'Exp':<5} {'Match':<6}\n")
        f.write("-" * 80 + "\n")
        
        for p in results['positions']:
            match_str = 'Y' if p['match'] else 'N'
            marker = ' <-- FIRST MISMATCH' if p['position'] == results['first_mismatch'] else ''
            f.write(f"{p['position']:<5} {p['cipher_num']:<8} {p['word']:<20} "
                   f"{p['extracted']:<5} {p['expected']:<5} {match_str:<6}{marker}\n")
        
        f.write("\n")
        f.write("-" * 80 + "\n")
        
        # Interpretation
        interpretation = interpret_anchor_offset(results)
        f.write(interpretation)
        f.write("\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("NEXT STEPS\n")
        f.write("=" * 80 + "\n")
        f.write("1. If first mismatch offset is ≤5: Run Phase 12C (offset sweep -5 to +5)\n")
        f.write("2. If first mismatch offset is >5: Run Phase 12B (convention tests)\n")
        f.write("3. If no nearby candidates found: Consider acquiring Stone 1823 edition\n")
        f.write("\n")


def run_anchor_diagnostic(num_positions: int = 20) -> Dict:
    """
    Run the full anchor diagnostic analysis.
    
    Args:
        num_positions: Number of positions to analyze (default: 20)
    
    Returns:
        Dictionary with analysis results
    """
    print("\nPhase 12A: Hard Anchor Testing")
    print("=" * 80)
    print(f"Analyzing first {num_positions} positions...")
    print()
    
    results = analyze_anchor_alignment(num_positions)
    
    print(f"Positions analyzed: {results['total_analyzed']}")
    print(f"Matches: {results['matches']}/{results['total_analyzed']} ({results['match_rate']:.2f}%)")
    print(f"First mismatch: position {results['first_mismatch']}")
    print()
    
    # Save report
    output_dir = Path("output/oracle_diagnostic")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"anchor_report_{timestamp}.txt"
    
    save_anchor_report(results, output_path)
    
    print(f"Report saved: {output_path}")
    print()
    
    # Print interpretation to console
    interpretation = interpret_anchor_offset(results)
    print(interpretation)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 12A: Hard Anchor Testing")
    parser.add_argument('--positions', type=int, default=20,
                       help='Number of positions to analyze (default: 20)')
    
    args = parser.parse_args()
    
    run_anchor_diagnostic(args.positions)
