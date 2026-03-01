"""
Phase 13 Step C: Edition Clustering via Alignment

Performs pairwise alignment between editions to cluster similar texts.
Selects cluster representatives (medoids) for oracle testing.

Uses:
- difflib.SequenceMatcher (cheap, built-in)
- Optional: python-Levenshtein for faster edit distance
- scipy for hierarchical clustering

Outputs:
- edition_distance_matrix.npy
- edition_clusters.json
- cluster_representatives.txt
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import difflib
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import Levenshtein
    HAS_LEVENSHTEIN = True
except ImportError:
    HAS_LEVENSHTEIN = False
    print("[INFO] python-Levenshtein not available, using difflib (slower)")


def load_edition_tokens(edition_id: str, tokenizer_name: str, corpus_dir: Path) -> List[str]:
    """Load tokens for an edition/tokenizer pair."""
    tokens_file = corpus_dir / "locked_candidates" / edition_id / tokenizer_name / "tokens.json"
    
    if not tokens_file.exists():
        return None
    
    with open(tokens_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("tokens", [])


def compute_token_similarity(tokens1: List[str], tokens2: List[str], method: str = "difflib") -> float:
    """
    Compute similarity between two token sequences.
    
    Returns: similarity in [0, 1], where 1 = identical
    
    Methods:
    - difflib: SequenceMatcher ratio (default)
    - levenshtein: normalized Levenshtein distance (if available)
    """
    if method == "levenshtein" and HAS_LEVENSHTEIN:
        # Convert to strings
        str1 = ' '.join(tokens1)
        str2 = ' '.join(tokens2)
        
        # Levenshtein distance
        dist = Levenshtein.distance(str1, str2)
        max_len = max(len(str1), len(str2))
        
        if max_len == 0:
            return 1.0
        
        # Convert to similarity
        similarity = 1.0 - (dist / max_len)
        return similarity
    
    else:
        # difflib SequenceMatcher
        matcher = difflib.SequenceMatcher(None, tokens1, tokens2)
        return matcher.ratio()


def compute_pairwise_distances(editions: List[str], tokenizer_name: str, 
                               corpus_dir: Path, method: str = "difflib") -> np.ndarray:
    """
    Compute N×N pairwise distance matrix for editions.
    
    Distance = 1 - similarity
    
    Returns: N×N symmetric matrix
    """
    n = len(editions)
    distances = np.zeros((n, n))
    
    print(f"  Computing pairwise distances for {n} editions...")
    print(f"  Method: {method}")
    
    # Load all tokens
    all_tokens = {}
    for i, edition_id in enumerate(editions):
        tokens = load_edition_tokens(edition_id, tokenizer_name, corpus_dir)
        if tokens is None:
            print(f"  [WARNING] No tokens for {edition_id}, using empty")
            tokens = []
        all_tokens[edition_id] = tokens
    
    # Compute pairwise
    comparisons = (n * (n - 1)) // 2
    done = 0
    
    for i in range(n):
        for j in range(i + 1, n):
            tokens1 = all_tokens[editions[i]]
            tokens2 = all_tokens[editions[j]]
            
            similarity = compute_token_similarity(tokens1, tokens2, method)
            distance = 1.0 - similarity
            
            distances[i, j] = distance
            distances[j, i] = distance
            
            done += 1
            if done % 10 == 0:
                print(f"    {done}/{comparisons} comparisons...")
    
    return distances


def cluster_editions(distance_matrix: np.ndarray, method: str = "average", 
                    max_clusters: int = 10) -> np.ndarray:
    """
    Cluster editions using hierarchical clustering.
    
    Args:
        distance_matrix: N×N symmetric distance matrix
        method: linkage method ('single', 'complete', 'average', 'ward')
        max_clusters: maximum number of clusters (will use distance threshold)
    
    Returns:
        Array of cluster labels (one per edition)
    """
    # Convert to condensed form for linkage
    condensed = squareform(distance_matrix)
    
    # Perform hierarchical clustering
    Z = linkage(condensed, method=method)
    
    # Form flat clusters
    # Use criterion='maxclust' to get at most max_clusters
    labels = fcluster(Z, max_clusters, criterion='maxclust')
    
    return labels


def find_medoids(editions: List[str], distance_matrix: np.ndarray, 
                cluster_labels: np.ndarray) -> List[str]:
    """
    Find medoid (representative) for each cluster.
    
    Medoid = edition with minimum total distance to all members of its cluster.
    
    Returns: List of edition IDs (medoids)
    """
    medoids = []
    unique_clusters = np.unique(cluster_labels)
    
    for cluster_id in unique_clusters:
        # Get indices of editions in this cluster
        indices = np.where(cluster_labels == cluster_id)[0]
        
        if len(indices) == 0:
            continue
        
        # Compute total distance for each member to all other members
        min_total_dist = float('inf')
        medoid_idx = indices[0]
        
        for idx in indices:
            # Sum distances to all other members
            total_dist = sum(distance_matrix[idx, other_idx] for other_idx in indices if other_idx != idx)
            
            if total_dist < min_total_dist:
                min_total_dist = total_dist
                medoid_idx = idx
        
        medoids.append(editions[medoid_idx])
    
    return medoids


def run_edition_clustering(editions: List[str], tokenizer_name: str = "hyphen_keep",
                           corpus_dir: Path = None, output_dir: Path = None,
                           method: str = "difflib", max_clusters: int = 10):
    """
    Main entry point for Step C.
    
    Args:
        editions: List of edition IDs to cluster
        tokenizer_name: Tokenizer to use for comparison
        corpus_dir: Corpus directory containing locked_candidates
        output_dir: Output directory for results
        method: Similarity method ('difflib' or 'levenshtein')
        max_clusters: Maximum number of clusters
    """
    if corpus_dir is None:
        corpus_dir = Path("corpus")
    if output_dir is None:
        output_dir = Path("output/phase13")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("PHASE 13 STEP C: EDITION CLUSTERING VIA ALIGNMENT")
    print("=" * 80)
    print(f"\nEditions to cluster: {len(editions)}")
    print(f"Tokenizer: {tokenizer_name}")
    print(f"Similarity method: {method}")
    print(f"Max clusters: {max_clusters}")
    print()
    
    # Step 1: Compute pairwise distances
    print("[Step 1] Computing pairwise distance matrix...")
    distance_matrix = compute_pairwise_distances(editions, tokenizer_name, corpus_dir, method)
    
    # Save distance matrix
    matrix_file = output_dir / "edition_distance_matrix.npy"
    np.save(matrix_file, distance_matrix)
    print(f"  Saved: {matrix_file}")
    print()
    
    # Step 2: Cluster editions
    print("[Step 2] Clustering editions...")
    cluster_labels = cluster_editions(distance_matrix, method='average', max_clusters=max_clusters)
    
    # Build cluster dict
    clusters = {}
    for i, (edition_id, label) in enumerate(zip(editions, cluster_labels)):
        cluster_id = int(label)
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(edition_id)
    
    print(f"  Found {len(clusters)} clusters")
    for cluster_id, members in sorted(clusters.items()):
        print(f"    Cluster {cluster_id}: {len(members)} editions")
    
    # Save clusters
    clusters_file = output_dir / "edition_clusters.json"
    with open(clusters_file, 'w', encoding='utf-8') as f:
        json.dump({
            "generated": datetime.now().isoformat(),
            "tokenizer": tokenizer_name,
            "num_clusters": len(clusters),
            "clusters": {str(k): v for k, v in clusters.items()}
        }, f, indent=2)
    print(f"  Saved: {clusters_file}")
    print()
    
    # Step 3: Find medoids
    print("[Step 3] Finding cluster representatives (medoids)...")
    medoids = find_medoids(editions, distance_matrix, cluster_labels)
    
    print(f"  Representatives: {len(medoids)}")
    for medoid in medoids:
        print(f"    - {medoid}")
    
    # Save representatives
    reps_file = output_dir / "cluster_representatives.txt"
    with open(reps_file, 'w', encoding='utf-8') as f:
        for medoid in medoids:
            f.write(f"{medoid}\n")
    print(f"  Saved: {reps_file}")
    print()
    
    print("=" * 80)
    print("CLUSTERING SUMMARY")
    print("=" * 80)
    print(f"Editions analyzed: {len(editions)}")
    print(f"Clusters found: {len(clusters)}")
    print(f"Representatives selected: {len(medoids)}")
    print()
    print("Next step: Run phase13_hmm_oracle on representatives")
    print("=" * 80)
    
    return {
        "distance_matrix": distance_matrix,
        "clusters": clusters,
        "medoids": medoids
    }


def list_available_editions(corpus_dir: Path) -> List[str]:
    """List all editions that have been tokenized."""
    candidates_dir = corpus_dir / "locked_candidates"
    
    if not candidates_dir.exists():
        return []
    
    editions = []
    for edition_dir in candidates_dir.iterdir():
        if edition_dir.is_dir():
            editions.append(edition_dir.name)
    
    return sorted(editions)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 13 Step C: Edition Clustering")
    parser.add_argument('--corpus-dir', default='corpus', help='Corpus directory')
    parser.add_argument('--output-dir', default='output/phase13', help='Output directory')
    parser.add_argument('--tokenizer', default='hyphen_keep', help='Tokenizer to use')
    parser.add_argument('--method', default='difflib', choices=['difflib', 'levenshtein'],
                       help='Similarity method')
    parser.add_argument('--max-clusters', type=int, default=10, help='Maximum clusters')
    parser.add_argument('--editions', nargs='+', help='Specific editions to cluster (default: all)')
    
    args = parser.parse_args()
    
    corpus_dir = Path(args.corpus_dir)
    output_dir = Path(args.output_dir)
    
    # Get editions
    if args.editions:
        editions = args.editions
    else:
        editions = list_available_editions(corpus_dir)
        if not editions:
            print("[ERROR] No tokenized editions found. Run phase13_tokenize first.")
            sys.exit(1)
    
    run_edition_clustering(editions, args.tokenizer, corpus_dir, output_dir, 
                          args.method, args.max_clusters)
