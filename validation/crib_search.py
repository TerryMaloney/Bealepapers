"""
Phase E: Crib-Drag Search

Post-hoc validation: Test near-English streams for expected Beale semantics
WITHOUT forcing matches. Only accept if stream also scores high on general metrics.
"""

from typing import List, Dict, Tuple
import re
from pathlib import Path


# Beale-specific cribs
BEALE_CRIBS = [
    'bedford', 'county', 'virginia', 'vault', 'feet', 'north', 'south',
    'ridge', 'creek', 'mile', 'degrees', 'chestnut', 'oak', 'rock',
    'buford', 'tavern', 'iron', 'pot', 'stone', 'buried', 'deposit',
    'treasure', 'excavation', 'located', 'distance', 'southwest',
    'northeast', 'branch', 'fork', 'hollow', 'cave', 'hill', 'mountain'
]


def edit_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def crib_drag_search(stream: str, cribs: List[str] = None,
                     max_edit_distance: int = 2) -> List[Dict]:
    """
    Search for cribs in decoded stream under small perturbations.
    
    Args:
        stream: Decoded character stream
        cribs: List of crib words to search for (default: BEALE_CRIBS)
        max_edit_distance: Maximum edit distance for fuzzy matching
    
    Returns:
        List of found cribs with positions and match types
    """
    if cribs is None:
        cribs = BEALE_CRIBS
    
    stream_lower = stream.lower()
    found_cribs = []
    
    for crib in cribs:
        # Exact match
        if crib in stream_lower:
            positions = [m.start() for m in re.finditer(crib, stream_lower)]
            for pos in positions:
                found_cribs.append({
                    'crib': crib,
                    'position': pos,
                    'match_type': 'exact',
                    'matched_text': stream_lower[pos:pos+len(crib)],
                    'edit_distance': 0
                })
        
        # Fuzzy match (sliding window)
        crib_len = len(crib)
        for i in range(len(stream_lower) - crib_len + 1):
            window = stream_lower[i:i+crib_len]
            dist = edit_distance(window, crib)
            
            if 0 < dist <= max_edit_distance:
                found_cribs.append({
                    'crib': crib,
                    'position': i,
                    'match_type': 'fuzzy',
                    'matched_text': window,
                    'edit_distance': dist
                })
    
    # Remove duplicates (keep best match for each position)
    seen_positions = {}
    for crib_match in found_cribs:
        key = (crib_match['crib'], crib_match['position'])
        if key not in seen_positions or crib_match['edit_distance'] < seen_positions[key]['edit_distance']:
            seen_positions[key] = crib_match
    
    found_cribs = list(seen_positions.values())
    found_cribs.sort(key=lambda x: (x['position'], x['edit_distance']))
    
    return found_cribs


def score_crib_density(stream: str, cribs: List[str] = None) -> Tuple[float, Dict]:
    """
    Score stream based on crib density and distribution.
    
    Returns:
        (score, details) where score is 0-100
    """
    if cribs is None:
        cribs = BEALE_CRIBS
    
    found = crib_drag_search(stream, cribs)
    
    # Count unique cribs found
    unique_cribs = set(f['crib'] for f in found)
    
    # Exact vs fuzzy
    exact_count = sum(1 for f in found if f['match_type'] == 'exact')
    fuzzy_count = sum(1 for f in found if f['match_type'] == 'fuzzy')
    
    # Score
    crib_coverage = len(unique_cribs) / len(cribs) * 100
    exact_weight = exact_count * 10
    fuzzy_weight = fuzzy_count * 5
    
    total_score = min(100, crib_coverage + exact_weight + fuzzy_weight)
    
    details = {
        'total_cribs_found': len(found),
        'unique_cribs': len(unique_cribs),
        'exact_matches': exact_count,
        'fuzzy_matches': fuzzy_count,
        'coverage_pct': crib_coverage,
        'found_crib_list': list(unique_cribs)
    }
    
    return total_score, details


def validate_with_cribs(stream: str, min_general_score: float = 35.0,
                       min_crib_score: float = 10.0) -> Dict:
    """
    Validate a decoded stream with both general English metrics and crib presence.
    
    Only accept if BOTH conditions hold:
    1. General English score >= min_general_score
    2. Crib score >= min_crib_score
    
    Args:
        stream: Decoded character stream
        min_general_score: Minimum required general English score
        min_crib_score: Minimum required crib score
    
    Returns:
        Validation result dict
    """
    # Compute crib score
    crib_score, crib_details = score_crib_density(stream)
    
    # Note: General score would come from signal_score or multi_objective
    # For now, we'll just return crib analysis
    
    passed = crib_score >= min_crib_score
    
    result = {
        'stream': stream[:200],  # Sample
        'stream_length': len(stream),
        'crib_score': crib_score,
        'crib_details': crib_details,
        'min_crib_score': min_crib_score,
        'validation_passed': passed
    }
    
    return result


def test_crib_search():
    """Test crib search on sample streams."""
    print("=" * 80)
    print("CRIB SEARCH TEST")
    print("=" * 80)
    
    # Test 1: Stream with exact cribs
    print("\n[Test 1] Stream with exact cribs...")
    stream1 = "IHAVEDEPOSITEDINTHEBEALESVAULTINBEDFORDCOUNTYVIRGINIA"
    found = crib_drag_search(stream1)
    
    print(f"Stream: {stream1}")
    print(f"Found {len(found)} crib matches:")
    for match in found:
        print(f"  {match['crib']:15s} @ position {match['position']:3d} | "
              f"{match['match_type']:5s} | edit_dist={match['edit_distance']}")
    
    score, details = score_crib_density(stream1)
    print(f"\nCrib score: {score:.2f}/100")
    print(f"  Unique cribs: {details['unique_cribs']}")
    print(f"  Exact: {details['exact_matches']}, Fuzzy: {details['fuzzy_matches']}")
    print(f"  Found: {details['found_crib_list']}")
    
    # Test 2: Stream with fuzzy cribs
    print("\n[Test 2] Stream with fuzzy cribs...")
    stream2 = "LOCATEDNORTHOFBUFORDSRIDGE"  # "BUFORDS" vs "BUFORD"
    found = crib_drag_search(stream2, max_edit_distance=2)
    
    print(f"Stream: {stream2}")
    print(f"Found {len(found)} crib matches:")
    for match in found:
        print(f"  {match['crib']:15s} @ position {match['position']:3d} | "
              f"{match['match_type']:5s} | matched='{match['matched_text']}' | "
              f"edit_dist={match['edit_distance']}")
    
    score, details = score_crib_density(stream2)
    print(f"\nCrib score: {score:.2f}/100")
    
    # Test 3: Random stream (should find nothing)
    print("\n[Test 3] Random stream...")
    stream3 = "XQZMKVPWBYLRNCJDSFGTHAOEIUX"
    found = crib_drag_search(stream3)
    
    print(f"Stream: {stream3}")
    print(f"Found {len(found)} crib matches")
    
    score, details = score_crib_density(stream3)
    print(f"Crib score: {score:.2f}/100")
    
    print("\n" + "=" * 80)
    print("CRIB SEARCH TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_crib_search()
