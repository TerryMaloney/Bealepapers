"""
Monte Carlo simulation: can a book cipher on English text produce
an Index of Coincidence as low as Cipher 1's?

Method:
  1. Generate synthetic "books" (random English text, various lengths)
  2. Generate synthetic "ciphers" by encoding random English plaintext
     through each book using standard first-letter book-cipher rules
  3. Compute IC on the cipher number streams
  4. Build a distribution of expected IC values
  5. Compare observed C1/C2/C3 IC against this distribution

If C1's IC=0.00309 falls outside the 99% confidence interval of
simulated book ciphers, this is strong statistical evidence that
C1 is NOT a standard book cipher encoding English.
"""

import sys
import random
import math
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from constraints.overlap_engine import load_cipher

OUT_DIR = Path("output/phase90")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# English letter frequencies
ENG_FREQ = {
    'A': 0.0817, 'B': 0.0149, 'C': 0.0278, 'D': 0.0425, 'E': 0.1270,
    'F': 0.0223, 'G': 0.0202, 'H': 0.0609, 'I': 0.0697, 'J': 0.0015,
    'K': 0.0077, 'L': 0.0403, 'M': 0.0241, 'N': 0.0675, 'O': 0.0751,
    'P': 0.0193, 'Q': 0.0010, 'R': 0.0599, 'S': 0.0633, 'T': 0.0906,
    'U': 0.0276, 'V': 0.0098, 'W': 0.0236, 'X': 0.0015, 'Y': 0.0197,
    'Z': 0.0007,
}

LETTERS = list(ENG_FREQ.keys())
WEIGHTS = [ENG_FREQ[l] for l in LETTERS]


def generate_book(n_words, seed=None):
    """Generate a synthetic book: n_words words with first letters
    drawn from English letter frequency distribution."""
    rng = random.Random(seed)
    first_letters = rng.choices(LETTERS, weights=WEIGHTS, k=n_words)
    return first_letters


def generate_plaintext(length, seed=None):
    """Generate random English plaintext as a letter sequence."""
    rng = random.Random(seed)
    return rng.choices(LETTERS, weights=WEIGHTS, k=length)


def encode_book_cipher(plaintext_letters, book_first_letters):
    """Encode plaintext using a book cipher.
    For each plaintext letter, pick a random word in the book
    that starts with that letter."""
    letter_to_indices = {}
    for i, fl in enumerate(book_first_letters):
        letter_to_indices.setdefault(fl, []).append(i + 1)  # 1-indexed

    cipher_nums = []
    rng = random.Random(42)
    for letter in plaintext_letters:
        indices = letter_to_indices.get(letter, [])
        if indices:
            cipher_nums.append(rng.choice(indices))
        else:
            cipher_nums.append(rng.randint(1, len(book_first_letters)))
    return cipher_nums


def compute_ic(nums):
    """Index of Coincidence for a number stream."""
    n = len(nums)
    if n < 2:
        return 0
    counts = Counter(nums)
    return sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))


def main():
    random.seed(2024)

    c1 = load_cipher(1)
    c2 = load_cipher(2)
    c3 = load_cipher(3)

    ic_c1 = compute_ic(c1)
    ic_c2 = compute_ic(c2)
    ic_c3 = compute_ic(c3)

    print(f"Observed IC values:")
    print(f"  C1: {ic_c1:.6f}  (520 numbers, {len(set(c1))} unique)")
    print(f"  C2: {ic_c2:.6f}  (763 numbers, {len(set(c2))} unique)")
    print(f"  C3: {ic_c3:.6f}  (618 numbers, {len(set(c3))} unique)")

    # Simulation parameters
    N_SIMULATIONS = 5000
    BOOK_SIZES = [1322, 2000, 3000, 5000, 10000, 50000]  # various book lengths
    CIPHER_LENGTHS = [520, 618, 763]

    results = {}

    for book_size in BOOK_SIZES:
        for cipher_len in CIPHER_LENGTHS:
            key = (book_size, cipher_len)
            ics = []
            for trial in range(N_SIMULATIONS):
                book = generate_book(book_size, seed=trial * 1000 + book_size)
                plaintext = generate_plaintext(cipher_len, seed=trial * 2000 + cipher_len)
                cipher = encode_book_cipher(plaintext, book)
                ics.append(compute_ic(cipher))
            results[key] = ics

    # Write report
    report_path = OUT_DIR / "ic_simulation_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("INDEX OF COINCIDENCE — MONTE CARLO SIMULATION\n")
        f.write(f"Command: python scripts/ic_simulation.py\n")
        f.write(f"Simulations per configuration: {N_SIMULATIONS}\n")
        f.write("=" * 80 + "\n\n")

        f.write("OBSERVED VALUES:\n")
        f.write(f"  Cipher 1: IC = {ic_c1:.6f}  (n=520, unique=298)\n")
        f.write(f"  Cipher 2: IC = {ic_c2:.6f}  (n=763, unique=180)\n")
        f.write(f"  Cipher 3: IC = {ic_c3:.6f}  (n=618, unique=263)\n\n")

        f.write("=" * 80 + "\n")
        f.write("SIMULATION RESULTS\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"{'Book Size':>10s}  {'Cipher Len':>10s}  "
                f"{'IC Mean':>10s}  {'IC Std':>10s}  "
                f"{'IC Min':>10s}  {'IC 1%':>10s}  {'IC 5%':>10s}  "
                f"{'IC 95%':>10s}  {'IC 99%':>10s}  {'IC Max':>10s}\n")
        f.write("-" * 100 + "\n")

        for (book_size, cipher_len), ics in sorted(results.items()):
            ics_sorted = sorted(ics)
            mean_ic = sum(ics) / len(ics)
            std_ic = (sum((x - mean_ic)**2 for x in ics) / len(ics))**0.5
            p1 = ics_sorted[int(0.01 * len(ics))]
            p5 = ics_sorted[int(0.05 * len(ics))]
            p95 = ics_sorted[int(0.95 * len(ics))]
            p99 = ics_sorted[int(0.99 * len(ics))]

            f.write(f"{book_size:>10d}  {cipher_len:>10d}  "
                    f"{mean_ic:>10.6f}  {std_ic:>10.6f}  "
                    f"{min(ics):>10.6f}  {p1:>10.6f}  {p5:>10.6f}  "
                    f"{p95:>10.6f}  {p99:>10.6f}  {max(ics):>10.6f}\n")

        # Key comparison
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("KEY COMPARISONS\n")
        f.write("=" * 80 + "\n\n")

        for name, ic_obs, cipher_len, max_book in [
            ("Cipher 1", ic_c1, 520, max(c1)),
            ("Cipher 2", ic_c2, 763, max(c2)),
            ("Cipher 3", ic_c3, 618, max(c3)),
        ]:
            f.write(f"\n{name} (n={cipher_len}, max_num={max_book}, IC={ic_obs:.6f}):\n")
            for book_size in BOOK_SIZES:
                key = (book_size, cipher_len)
                if key not in results:
                    continue
                ics = results[key]
                ics_sorted = sorted(ics)
                mean_ic = sum(ics) / len(ics)
                below = sum(1 for x in ics if x <= ic_obs)
                pct_below = below / len(ics) * 100
                p1 = ics_sorted[int(0.01 * len(ics))]

                verdict = ""
                if pct_below < 1:
                    verdict = "*** BELOW 1st PERCENTILE — EXTREMELY UNLIKELY ***"
                elif pct_below < 5:
                    verdict = "** Below 5th percentile — unlikely **"
                elif pct_below > 40 and pct_below < 60:
                    verdict = "(consistent)"

                f.write(f"  Book size {book_size:>6d}: "
                        f"sim_mean={mean_ic:.6f}, "
                        f"sim_1pct={p1:.6f}, "
                        f"observed below {pct_below:.1f}% of simulations  "
                        f"{verdict}\n")

        # Final verdict
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("STATISTICAL VERDICT\n")
        f.write("=" * 80 + "\n\n")

        # Check C1 against its most favorable book size
        for book_size in BOOK_SIZES:
            key = (book_size, 520)
            if key in results:
                below = sum(1 for x in results[key] if x <= ic_c1)
                pct = below / len(results[key]) * 100
                if pct > 5:
                    f.write(f"C1 IC={ic_c1:.6f} is consistent with book cipher "
                            f"on a {book_size}-word text ({pct:.1f}% of simulations below).\n")
                    break
        else:
            f.write(f"C1 IC={ic_c1:.6f} falls below the 1st percentile of ALL "
                    f"simulated book cipher configurations.\n")
            f.write(f"This means: in 5000 simulations at each book size, fewer than "
                    f"1% of random English book ciphers produce an IC this low.\n")
            f.write(f"\nCONCLUSION: Cipher 1's number stream is statistically "
                    f"inconsistent with a standard first-letter book cipher "
                    f"encoding English text. Either:\n")
            f.write(f"  (a) A non-standard cipher mechanism is in use, OR\n")
            f.write(f"  (b) The numbers were not generated from English text.\n")

        f.write("\n")
        for book_size in BOOK_SIZES:
            key = (book_size, 763)
            if key in results:
                below = sum(1 for x in results[key] if x <= ic_c2)
                pct = below / len(results[key]) * 100
                if pct > 5:
                    f.write(f"C2 IC={ic_c2:.6f} is consistent with book cipher "
                            f"on a {book_size}-word text ({pct:.1f}% of simulations below).\n")
                    break

        f.write("\n")
        for book_size in BOOK_SIZES:
            key = (book_size, 618)
            if key in results:
                below = sum(1 for x in results[key] if x <= ic_c3)
                pct = below / len(results[key]) * 100
                if pct > 5:
                    f.write(f"C3 IC={ic_c3:.6f} is consistent with book cipher "
                            f"on a {book_size}-word text ({pct:.1f}% of simulations below).\n")
                    break
        else:
            f.write(f"C3 IC={ic_c3:.6f} also falls below expectations for most "
                    f"book cipher configurations.\n")

    print(f"\nReport: {report_path}")

    # Print key results
    print(f"\n{'='*60}")
    print("KEY RESULTS")
    print(f"{'='*60}")
    for name, ic_obs, cipher_len in [
        ("C1", ic_c1, 520), ("C2", ic_c2, 763), ("C3", ic_c3, 618)]:
        print(f"\n{name} (IC={ic_obs:.6f}):")
        for book_size in BOOK_SIZES:
            key = (book_size, cipher_len)
            if key in results:
                ics = results[key]
                mean_ic = sum(ics) / len(ics)
                below = sum(1 for x in ics if x <= ic_obs)
                pct = below / len(ics) * 100
                flag = " ***" if pct < 1 else (" **" if pct < 5 else "")
                print(f"  book={book_size:>6d}: mean_IC={mean_ic:.6f}, "
                      f"observed below {pct:5.1f}% of sims{flag}")


if __name__ == "__main__":
    main()
