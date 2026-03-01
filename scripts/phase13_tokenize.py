"""
Phase 13 Step B: Tokenize All Edition Candidates

For each (edition_id, tokenizer_name) pair:
- Load edition text
- Tokenize via TokenizerRegistry
- Compute SHA256 of token sequence
- Save to corpus/locked_candidates/<edition_id>/<tokenizer_id>/tokens.json

Generates token_counts_matrix.csv showing token counts per edition/tokenizer.
"""

import json
import hashlib
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry


def compute_tokens_hash(tokens: List[str]) -> str:
    """Compute SHA256 hash of token sequence."""
    content = '|'.join(tokens).encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def list_all_edition_ids(corpus_dir: Path) -> List[str]:
    """
    List all available edition IDs from corpus/editions/*.txt and beale_embedded.
    
    Returns list of edition IDs.
    """
    editions_dir = corpus_dir / "editions"
    
    edition_ids = ["beale_embedded"]  # Always include embedded
    
    if editions_dir.exists():
        for txt_file in editions_dir.glob("*.txt"):
            edition_id = txt_file.stem
            if edition_id != "beale_embedded":
                edition_ids.append(edition_id)
    
    return edition_ids


def tokenize_edition(edition_id: str, tokenizer_name: str, loader: DOICorpusLoader) -> Dict:
    """
    Tokenize a single edition with a single tokenizer.
    
    Returns dict with tokens, hash, and metadata.
    """
    # Load edition
    try:
        edition = loader.load_edition(edition_id)
    except Exception as e:
        print(f"  [ERROR] Could not load edition '{edition_id}': {e}")
        return None
    
    # Check if placeholder
    if not edition.source_text or edition.source_text.startswith("[PLACEHOLDER"):
        print(f"  [SKIP] Placeholder edition: {edition_id}")
        return None
    
    # Get tokenizer
    try:
        tokenizer = TokenizerRegistry.get_tokenizer(tokenizer_name)
    except Exception as e:
        print(f"  [ERROR] Could not get tokenizer '{tokenizer_name}': {e}")
        return None
    
    # Tokenize
    tokens = tokenizer.tokenize(edition.source_text)
    
    # Compute hash
    tokens_hash = compute_tokens_hash(tokens)
    
    return {
        "edition_id": edition_id,
        "tokenizer_name": tokenizer_name,
        "tokens": tokens,
        "token_count": len(tokens),
        "sha256": tokens_hash,
        "tokenized_at": datetime.now().isoformat()
    }


def save_tokenized_candidate(result: Dict, output_dir: Path):
    """
    Save tokenized candidate to:
    corpus/locked_candidates/<edition_id>/<tokenizer_id>/tokens.json
    """
    candidate_dir = output_dir / "locked_candidates" / result["edition_id"] / result["tokenizer_name"]
    candidate_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = candidate_dir / "tokens.json"
    
    # Save without the full tokens list initially (save separately for space)
    metadata = {
        "edition_id": result["edition_id"],
        "tokenizer_name": result["tokenizer_name"],
        "token_count": result["token_count"],
        "sha256": result["sha256"],
        "tokenized_at": result["tokenized_at"]
    }
    
    full_data = {
        "metadata": metadata,
        "tokens": result["tokens"]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, indent=2)
    
    return output_file


def create_token_counts_matrix(results: List[Dict], output_dir: Path):
    """
    Create CSV matrix: rows=editions, cols=tokenizers, values=token count.
    
    Saves to output/phase13/token_counts_matrix.csv
    """
    phase13_dir = output_dir / "output" / "phase13"
    phase13_dir.mkdir(parents=True, exist_ok=True)
    
    # Get unique editions and tokenizers
    editions = sorted(set(r["edition_id"] for r in results))
    tokenizers = sorted(set(r["tokenizer_name"] for r in results))
    
    # Build matrix
    matrix = {}
    for r in results:
        key = (r["edition_id"], r["tokenizer_name"])
        matrix[key] = r["token_count"]
    
    # Write CSV
    csv_file = phase13_dir / "token_counts_matrix.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(["edition_id"] + tokenizers)
        
        # Rows
        for edition in editions:
            row = [edition]
            for tokenizer in tokenizers:
                count = matrix.get((edition, tokenizer), 0)
                row.append(count)
            writer.writerow(row)
    
    print(f"\nToken counts matrix saved: {csv_file}")
    print(f"  Editions: {len(editions)}")
    print(f"  Tokenizers: {len(tokenizers)}")
    print(f"  Total combinations: {len(results)}")


def run_tokenization(corpus_dir: Path = None):
    """
    Main entry point for Step B.
    
    Tokenizes all editions with all tokenizer presets.
    """
    if corpus_dir is None:
        corpus_dir = Path("corpus")
    
    print("=" * 80)
    print("PHASE 13 STEP B: TOKENIZE ALL EDITION CANDIDATES")
    print("=" * 80)
    
    # Get all editions
    print("\n[Step 1] Discovering editions...")
    edition_ids = list_all_edition_ids(corpus_dir)
    print(f"  Found {len(edition_ids)} editions")
    
    # Get all tokenizers
    print("\n[Step 2] Loading tokenizers...")
    tokenizer_names = TokenizerRegistry.list_presets()
    print(f"  Found {len(tokenizer_names)} tokenizer presets")
    
    total_combinations = len(edition_ids) * len(tokenizer_names)
    print(f"\n[Step 3] Tokenizing {total_combinations} combinations...")
    print("  (edition × tokenizer)")
    print()
    
    loader = DOICorpusLoader()
    results = []
    skipped = 0
    
    for i, edition_id in enumerate(edition_ids, 1):
        print(f"[{i}/{len(edition_ids)}] Edition: {edition_id}")
        
        for tokenizer_name in tokenizer_names:
            result = tokenize_edition(edition_id, tokenizer_name, loader)
            
            if result is None:
                skipped += 1
                continue
            
            # Save candidate
            output_file = save_tokenized_candidate(result, corpus_dir)
            results.append(result)
            
            # Print progress (only for first few tokenizers to avoid spam)
            if len(results) % 10 == 0:
                print(f"  Tokenized: {len(results)} candidates...")
        
        print(f"  Completed {len(tokenizer_names)} tokenizers for {edition_id}")
        print()
    
    print(f"\n[Step 4] Generating token counts matrix...")
    create_token_counts_matrix(results, corpus_dir)
    
    print("\n" + "=" * 80)
    print("TOKENIZATION SUMMARY")
    print("=" * 80)
    print(f"Total combinations: {total_combinations}")
    print(f"  Tokenized: {len(results)}")
    print(f"  Skipped: {skipped}")
    print()
    
    # Statistics
    if results:
        token_counts = [r["token_count"] for r in results]
        print(f"Token count statistics:")
        print(f"  Min: {min(token_counts)}")
        print(f"  Max: {max(token_counts)}")
        print(f"  Mean: {sum(token_counts) / len(token_counts):.1f}")
    
    print("\nNext step: Run phase13_cluster for edition alignment and clustering")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 13 Step B: Tokenize Edition Candidates")
    parser.add_argument('--corpus-dir', default='corpus', help='Corpus directory (default: corpus)')
    
    args = parser.parse_args()
    
    run_tokenization(Path(args.corpus_dir))
