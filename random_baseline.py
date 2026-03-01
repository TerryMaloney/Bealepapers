"""
RANDOM BASELINE (Phase 4)
Generate random letter streams and compare to DOI-only results.
Tests if current scores are statistically significant vs random noise.
"""

import random
import signal_score
from datetime import datetime


def generate_random_stream(length=520):
    """Generate random uppercase letter stream"""
    return ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') 
                   for _ in range(length))


def run_random_baseline(trials=100, stream_length=520):
    """
    Generate multiple random trials and compute score distribution.
    
    Args:
        trials: Number of random streams to test
        stream_length: Length of each random stream
    
    Returns:
        Dictionary with statistics
    """
    print("=" * 80)
    print("RANDOM BASELINE COMPARISON - Phase 4")
    print(f"Generating {trials} random trials")
    print("=" * 80)
    
    random_scores = []
    
    for i in range(trials):
        # Generate random stream
        random_stream = generate_random_stream(stream_length)
        
        # Score it
        scores = signal_score.score_stream(random_stream, use_phase3_metrics=True)
        random_scores.append(scores['total_score'])
        
        if (i + 1) % 20 == 0:
            print(f"Progress: {i + 1}/{trials} trials...")
    
    # Calculate statistics
    avg_random = sum(random_scores) / len(random_scores)
    max_random = max(random_scores)
    min_random = min(random_scores)
    
    # Standard deviation
    variance = sum((x - avg_random) ** 2 for x in random_scores) / len(random_scores)
    std_dev = variance ** 0.5
    
    print(f"\nRandom baseline statistics ({trials} trials):")
    print(f"  Average: {avg_random:.2f}/100")
    print(f"  Std Dev: {std_dev:.2f}")
    print(f"  Min:     {min_random:.2f}/100")
    print(f"  Max:     {max_random:.2f}/100")
    
    return {
        'trials': trials,
        'average': avg_random,
        'std_dev': std_dev,
        'min': min_random,
        'max': max_random,
        'scores': random_scores
    }


def compare_to_doi_result(baseline_stats, doi_score):
    """
    Compare DOI-only result to random baseline.
    Determine statistical significance.
    """
    print("\n" + "=" * 80)
    print("STATISTICAL COMPARISON")
    print("=" * 80)
    
    avg_random = baseline_stats['average']
    max_random = baseline_stats['max']
    std_dev = baseline_stats['std_dev']
    
    difference_from_avg = doi_score - avg_random
    difference_from_max = doi_score - max_random
    sigma_above = difference_from_avg / std_dev if std_dev > 0 else 0
    
    print(f"\nDOI-only best score:    {doi_score:.2f}/100")
    print(f"Random average:         {avg_random:.2f}/100")
    print(f"Random max (100 trials):{max_random:.2f}/100")
    print(f"\nDifference from avg:    {difference_from_avg:+.2f} points")
    print(f"Difference from max:    {difference_from_max:+.2f} points")
    print(f"Sigma above mean:       {sigma_above:.2f} std devs")
    
    # Verdict
    print("\n" + "-" * 80)
    print("STATISTICAL VERDICT")
    print("-" * 80)
    
    if doi_score > max_random + 10:
        verdict = "HIGHLY SIGNIFICANT"
        interpretation = "DOI-only score is far above random. Signal is REAL."
        confidence = "Very high confidence that method extracts non-random information."
    elif doi_score > max_random + 5:
        verdict = "SIGNIFICANT"
        interpretation = "DOI-only score exceeds all random trials. Signal is likely real."
        confidence = "High confidence that method detects structure."
    elif doi_score > avg_random + 2 * std_dev:
        verdict = "MODERATELY SIGNIFICANT"
        interpretation = "DOI-only score is above random by 2+ standard deviations."
        confidence = "Moderate confidence. Signal present but weak."
    elif doi_score > avg_random + std_dev:
        verdict = "MARGINALLY SIGNIFICANT"
        interpretation = "DOI-only score slightly above random average."
        confidence = "Low confidence. Could be statistical artifact."
    else:
        verdict = "NOT SIGNIFICANT"
        interpretation = "DOI-only score within random range."
        confidence = "No evidence of non-random signal. Method ineffective."
    
    print(f"Verdict: {verdict}")
    print(f"\n{interpretation}")
    print(f"{confidence}")
    
    return {
        'verdict': verdict,
        'difference_from_avg': difference_from_avg,
        'difference_from_max': difference_from_max,
        'sigma': sigma_above,
        'interpretation': interpretation
    }


def generate_baseline_report(baseline_stats, comparison, doi_score):
    """Generate baseline comparison report"""
    filename = "output/phase4_random_baseline.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("PHASE 4 RANDOM BASELINE COMPARISON\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("METHODOLOGY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Generated {baseline_stats['trials']} random letter streams (520 chars each)\n")
        f.write("Scored each using Phase 3 metrics (bigram, trigram, quadgram, etc.)\n")
        f.write("Compared distribution to DOI-only best result\n\n")
        
        f.write("RANDOM BASELINE STATISTICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Trials: {baseline_stats['trials']}\n")
        f.write(f"Average score: {baseline_stats['average']:.2f}/100\n")
        f.write(f"Std deviation: {baseline_stats['std_dev']:.2f}\n")
        f.write(f"Min score: {baseline_stats['min']:.2f}/100\n")
        f.write(f"Max score: {baseline_stats['max']:.2f}/100\n")
        f.write(f"Range: {baseline_stats['max'] - baseline_stats['min']:.2f} points\n\n")
        
        f.write("DOI-ONLY COMPARISON\n")
        f.write("-" * 80 + "\n")
        f.write(f"DOI-only best score: {doi_score:.2f}/100\n")
        f.write(f"Random average: {baseline_stats['average']:.2f}/100\n")
        f.write(f"Difference: {comparison['difference_from_avg']:+.2f} points\n\n")
        
        f.write(f"DOI score vs random max: {comparison['difference_from_max']:+.2f} points\n")
        f.write(f"Sigma above mean: {comparison['sigma']:.2f} std devs\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("STATISTICAL VERDICT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"{comparison['verdict']}\n\n")
        f.write(f"{comparison['interpretation']}\n\n")
        
        f.write("INTERPRETATION GUIDE\n")
        f.write("-" * 80 + "\n")
        f.write(">10 points above random max: Highly significant (real signal)\n")
        f.write(">5 points above random max: Significant (likely real signal)\n")
        f.write(">2 std devs above mean: Moderately significant (weak signal)\n")
        f.write(">1 std dev above mean: Marginally significant (uncertain)\n")
        f.write("Within 1 std dev: Not significant (random noise)\n\n")
        
        f.write("=" * 80 + "\n")
    
    print(f"\nBaseline report saved to: {filename}")


if __name__ == "__main__":
    # Run random baseline
    baseline_stats = run_random_baseline(trials=100, stream_length=520)
    
    # Get DOI-only best score from previous run
    # User must provide this or we read from the output file
    print("\n" + "=" * 80)
    print("Enter DOI-only best score (from doi_only_runner.py):")
    print("Or press Enter to read from output/phase4_doi_only_results.txt")
    print("=" * 80)
    
    user_input = input("DOI-only score: ").strip()
    
    if user_input:
        doi_score = float(user_input)
    else:
        # Try to extract from output file
        try:
            with open("output/phase4_doi_only_results.txt", 'r', encoding='utf-8') as f:
                content = f.read()
                # Look for "RANK #1  Score: XX.XX/100"
                import re
                match = re.search(r'RANK #1\s+Score:\s+(\d+\.\d+)/100', content)
                if match:
                    doi_score = float(match.group(1))
                    print(f"\nExtracted DOI-only score: {doi_score:.2f}/100")
                else:
                    print("\nCould not extract score. Using placeholder.")
                    doi_score = 0.0
        except:
            print("\nCould not read output file. Using placeholder.")
            doi_score = 0.0
    
    # Compare
    comparison = compare_to_doi_result(baseline_stats, doi_score)
    
    # Generate report
    generate_baseline_report(baseline_stats, comparison, doi_score)
    
    print("\n" + "=" * 80)
    print("RANDOM BASELINE COMPLETE")
    print("=" * 80)
    print(f"\nVerdict: {comparison['verdict']}")
    print(f"DOI-only: {doi_score:.2f}/100")
    print(f"Random avg: {baseline_stats['average']:.2f}/100")
    print(f"Difference: {comparison['difference_from_avg']:+.2f} points")
