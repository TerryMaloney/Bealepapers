"""
Phase 13 Step E: Changepoint Detection

Detects breakpoints in:
1. Match series (0/1 observations from HMM)
2. Offset path series (from HMM Viterbi solution)

Uses ruptures library for changepoint detection.
Labels breakpoints as "structural boundaries" when offset jumps align with match drops.

Outputs changepoints/<edition>_<tokenizer>.txt
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import ruptures as rpt
    HAS_RUPTURES = True
except ImportError:
    HAS_RUPTURES = False
    print("[ERROR] ruptures not installed. Run: pip install ruptures")


def load_hmm_plot_data(edition_id: str, tokenizer_name: str, hmm_dir: Path) -> Tuple[List[int], List[int]]:
    """
    Load match series and offset path from HMM plot CSV.
    
    Returns:
        (match_series, offset_series)
    """
    import csv
    
    csv_file = hmm_dir / f"{edition_id}_{tokenizer_name}_plot.csv"
    
    if not csv_file.exists():
        raise FileNotFoundError(f"HMM plot not found: {csv_file}")
    
    match_series = []
    offset_series = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            match_series.append(int(row['match']))
            offset_series.append(int(row['offset']))
    
    return match_series, offset_series


def detect_changepoints_pelt(signal: np.ndarray, model: str = "l2", pen: float = 10.0) -> List[int]:
    """
    Detect changepoints using PELT (Pruned Exact Linear Time).
    
    Args:
        signal: 1D signal (match series or offset series)
        model: Cost model ('l2', 'l1', 'rbf', 'linear', 'normal', 'ar')
        pen: Penalty value (higher = fewer changepoints)
    
    Returns:
        List of changepoint indices (breakpoints)
    """
    if not HAS_RUPTURES:
        return []
    
    # Reshape for ruptures (expects 2D)
    signal_2d = signal.reshape(-1, 1)
    
    # PELT algorithm
    algo = rpt.Pelt(model=model).fit(signal_2d)
    changepoints = algo.predict(pen=pen)
    
    # Remove last breakpoint (always at end)
    if changepoints and changepoints[-1] == len(signal):
        changepoints = changepoints[:-1]
    
    return changepoints


def detect_changepoints_binseg(signal: np.ndarray, model: str = "l2", n_bkps: int = 5) -> List[int]:
    """
    Detect changepoints using Binary Segmentation.
    
    Args:
        signal: 1D signal
        model: Cost model
        n_bkps: Number of breakpoints to find
    
    Returns:
        List of changepoint indices
    """
    if not HAS_RUPTURES:
        return []
    
    signal_2d = signal.reshape(-1, 1)
    
    algo = rpt.Binseg(model=model).fit(signal_2d)
    changepoints = algo.predict(n_bkps=n_bkps)
    
    # Remove last breakpoint
    if changepoints and changepoints[-1] == len(signal):
        changepoints = changepoints[:-1]
    
    return changepoints


def label_breakpoints(match_bkps: List[int], offset_bkps: List[int], 
                     match_series: List[int], offset_series: List[int],
                     window: int = 10) -> List[Dict]:
    """
    Label breakpoints based on match drops and offset jumps.
    
    A breakpoint is labeled "structural boundary" if:
    - It appears in both match and offset changepoints (or very close)
    - Match rate drops significantly before/after
    - Offset has a large jump nearby
    
    Args:
        match_bkps: Changepoints in match series
        offset_bkps: Changepoints in offset series
        match_series: Full match series (0/1)
        offset_series: Full offset series
        window: Window size for checking alignment
    
    Returns:
        List of labeled breakpoints with metadata
    """
    labeled = []
    
    # Check match breakpoints
    for bkp in match_bkps:
        # Find nearby offset breakpoint
        nearby_offset_bkp = None
        min_dist = float('inf')
        
        for offset_bkp in offset_bkps:
            dist = abs(bkp - offset_bkp)
            if dist < min_dist and dist <= window:
                min_dist = dist
                nearby_offset_bkp = offset_bkp
        
        # Compute match rate before/after
        before_start = max(0, bkp - window)
        before_end = bkp
        after_start = bkp
        after_end = min(len(match_series), bkp + window)
        
        if before_end > before_start and after_end > after_start:
            match_before = sum(match_series[before_start:before_end]) / (before_end - before_start)
            match_after = sum(match_series[after_start:after_end]) / (after_end - after_start)
            match_drop = match_before - match_after
        else:
            match_drop = 0.0
        
        # Check offset jump
        if 0 < bkp < len(offset_series):
            offset_jump = abs(offset_series[bkp] - offset_series[bkp-1])
        else:
            offset_jump = 0
        
        # Label
        is_structural = (nearby_offset_bkp is not None and match_drop > 0.2 and offset_jump > 5)
        
        labeled.append({
            "position": bkp,
            "type": "match_changepoint",
            "match_drop": match_drop,
            "offset_jump": offset_jump,
            "nearby_offset_bkp": nearby_offset_bkp,
            "is_structural_boundary": is_structural
        })
    
    # Check offset breakpoints not already near match breakpoints
    for bkp in offset_bkps:
        # Check if already covered
        already_covered = any(abs(bkp - lb["position"]) <= window for lb in labeled)
        
        if not already_covered:
            # Check offset jump
            if 0 < bkp < len(offset_series):
                offset_jump = abs(offset_series[bkp] - offset_series[bkp-1])
            else:
                offset_jump = 0
            
            labeled.append({
                "position": bkp,
                "type": "offset_changepoint",
                "match_drop": 0.0,
                "offset_jump": offset_jump,
                "nearby_offset_bkp": None,
                "is_structural_boundary": (offset_jump > 10)
            })
    
    # Sort by position
    labeled.sort(key=lambda x: x["position"])
    
    return labeled


def run_changepoint_detection(edition_id: str, tokenizer_name: str,
                              hmm_dir: Path, output_dir: Path,
                              penalty: float = 10.0, n_bkps: int = 5):
    """
    Run changepoint detection for a single edition/tokenizer.
    
    Args:
        edition_id: Edition ID
        tokenizer_name: Tokenizer name
        hmm_dir: Directory with HMM results
        output_dir: Output directory for changepoint results
        penalty: PELT penalty (higher = fewer breakpoints)
        n_bkps: BinSeg number of breakpoints
    """
    if not HAS_RUPTURES:
        print("[ERROR] ruptures not available")
        return None
    
    print(f"\n[Edition: {edition_id}, Tokenizer: {tokenizer_name}]")
    
    # Load HMM data
    try:
        match_series, offset_series = load_hmm_plot_data(edition_id, tokenizer_name, hmm_dir)
    except FileNotFoundError as e:
        print(f"  [SKIP] {e}")
        return None
    
    print(f"  Loaded {len(match_series)} observations")
    
    # Convert to numpy
    match_array = np.array(match_series, dtype=float)
    offset_array = np.array(offset_series, dtype=float)
    
    # Detect changepoints in match series
    print(f"  Detecting match changepoints (PELT, pen={penalty})...")
    match_bkps = detect_changepoints_pelt(match_array, model='l2', pen=penalty)
    print(f"    Found {len(match_bkps)} breakpoints")
    
    # Detect changepoints in offset series
    print(f"  Detecting offset changepoints (BinSeg, n={n_bkps})...")
    offset_bkps = detect_changepoints_binseg(offset_array, model='l2', n_bkps=n_bkps)
    print(f"    Found {len(offset_bkps)} breakpoints")
    
    # Label breakpoints
    print(f"  Labeling breakpoints...")
    labeled = label_breakpoints(match_bkps, offset_bkps, match_series, offset_series)
    
    structural = [lb for lb in labeled if lb["is_structural_boundary"]]
    print(f"    Structural boundaries: {len(structural)}")
    
    # Save results
    changepoints_dir = output_dir / "changepoints"
    changepoints_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = changepoints_dir / f"{edition_id}_{tokenizer_name}.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"CHANGEPOINT DETECTION: {edition_id} + {tokenizer_name}\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Observations: {len(match_series)}\n")
        f.write(f"PELT penalty: {penalty}\n")
        f.write(f"BinSeg n_bkps: {n_bkps}\n")
        f.write("\n")
        
        f.write("DETECTED BREAKPOINTS\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Position':<10} {'Type':<20} {'Match Drop':<12} {'Offset Jump':<12} {'Structural?':<12}\n")
        f.write("-" * 80 + "\n")
        
        for lb in labeled:
            structural_mark = "YES" if lb["is_structural_boundary"] else ""
            f.write(f"{lb['position']:<10} {lb['type']:<20} {lb['match_drop']:<12.2f} "
                   f"{lb['offset_jump']:<12} {structural_mark:<12}\n")
        
        f.write("\n")
        f.write("STRUCTURAL BOUNDARIES\n")
        f.write("-" * 80 + "\n")
        
        if structural:
            for lb in structural:
                f.write(f"Position {lb['position']}: match_drop={lb['match_drop']:.2f}, "
                       f"offset_jump={lb['offset_jump']}\n")
        else:
            f.write("No strong structural boundaries detected.\n")
        
        f.write("\n")
    
    print(f"  Saved: {output_file}")
    
    return {
        "edition_id": edition_id,
        "tokenizer_name": tokenizer_name,
        "match_bkps": match_bkps,
        "offset_bkps": offset_bkps,
        "labeled": labeled,
        "n_structural": len(structural)
    }


def run_changepoint_sweep(edition_ids: List[str], tokenizer_names: List[str],
                         output_dir: Path = None, penalty: float = 10.0, n_bkps: int = 5):
    """
    Run changepoint detection for multiple edition/tokenizer pairs.
    """
    if output_dir is None:
        output_dir = Path("output/phase13")
    
    hmm_dir = output_dir / "oracle_hmm"
    
    if not hmm_dir.exists():
        print(f"[ERROR] HMM directory not found: {hmm_dir}")
        print("Run phase13_hmm_oracle first.")
        return []
    
    print("=" * 80)
    print("PHASE 13 STEP E: CHANGEPOINT DETECTION")
    print("=" * 80)
    print(f"\nEditions: {len(edition_ids)}")
    print(f"Tokenizers: {len(tokenizer_names)}")
    print(f"PELT penalty: {penalty}")
    print(f"BinSeg n_bkps: {n_bkps}")
    print()
    
    results = []
    
    for edition_id in edition_ids:
        for tokenizer_name in tokenizer_names:
            result = run_changepoint_detection(edition_id, tokenizer_name, 
                                              hmm_dir, output_dir, penalty, n_bkps)
            if result:
                results.append(result)
    
    print("\n" + "=" * 80)
    print("CHANGEPOINT SUMMARY")
    print("=" * 80)
    print(f"Analyzed: {len(results)} combinations")
    
    if results:
        total_structural = sum(r["n_structural"] for r in results)
        print(f"Total structural boundaries: {total_structural}")
        
        avg_structural = total_structural / len(results)
        print(f"Average per combination: {avg_structural:.1f}")
    
    print("\nNext step: Run phase13_rank for acceptance gates")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 13 Step E: Changepoint Detection")
    parser.add_argument('--output-dir', default='output/phase13', help='Output directory')
    parser.add_argument('--editions', nargs='+', required=True, help='Edition IDs')
    parser.add_argument('--tokenizers', nargs='+', default=['hyphen_keep'], 
                       help='Tokenizer names')
    parser.add_argument('--penalty', type=float, default=10.0, help='PELT penalty')
    parser.add_argument('--n-bkps', type=int, default=5, help='BinSeg number of breakpoints')
    
    args = parser.parse_args()
    
    run_changepoint_sweep(args.editions, args.tokenizers, 
                         Path(args.output_dir), args.penalty, args.n_bkps)
