"""
Key-Text Hunter: screen candidate key texts for Beale Ciphers 1 and 3.

Pipeline:
  1. Load all registered keytexts from corpus/keytexts/
  2. Discard any with token_count < max(cipher_numbers)
  3. For each surviving keytext:
     a) Run constraint prefilter (Cipher 2 overlap)
     b) Decode the target cipher using a small set of cheap extractors
     c) Score decoded streams with word_pattern_scorer
  4. Rank by combined score and output results

Usage:
  python scripts/keytext_hunt.py --cipher 1 --topk 20
"""

import argparse
import csv
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus.keytexts.loader import load_all_keytexts, list_registered
from constraints.overlap_constraints import build_overlap_constraint_set, screen_keytext
from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score


CHEAP_EXTRACTORS = [
    "first_letter", "second_letter", "third_letter", "last_letter",
    "middle_letter",
]


def decode_with_keytext(tokens, cipher_nums, extractor_name):
    """Decode cipher numbers against a token list using a named extraction rule."""
    result = []
    max_idx = len(tokens)
    for cn in cipher_nums:
        idx = cn - 1
        if idx < 0 or idx >= max_idx:
            result.append("?")
            continue
        word = tokens[idx]
        if not word:
            result.append("?")
            continue

        if extractor_name == "first_letter":
            ch = word[0].upper()
        elif extractor_name == "second_letter":
            ch = word[1].upper() if len(word) >= 2 else "_"
        elif extractor_name == "third_letter":
            ch = word[2].upper() if len(word) >= 3 else "_"
        elif extractor_name == "last_letter":
            ch = word[-1].upper()
        elif extractor_name == "middle_letter":
            mid = len(word) // 2
            ch = word[mid].upper()
        else:
            ch = word[0].upper()

        result.append(ch)
    return "".join(result)


def run_hunt(cipher_num: int = 1, topk: int = 20, out_dir_path: str = "output/keyhunt"):
    """Main hunt pipeline."""
    print("=" * 80)
    print(f"KEY-TEXT HUNTER  --  Cipher {cipher_num}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 80)

    cipher_nums = load_cipher(cipher_num)
    max_cn = max(cipher_nums)
    print(f"\nCipher {cipher_num}: {len(cipher_nums)} numbers, max={max_cn}")
    print(f"Key text must have >= {max_cn} tokens")

    # Load constraint set
    print("\n[1] Building overlap constraints...")
    constraints = build_overlap_constraint_set(cipher_num)
    print(f"    {len(constraints)} constraints from Cipher 2 overlap")
    print(f"    Expected random pass rate: {1/26*100:.1f}%")

    # Load keytexts
    print("\n[2] Loading registered keytexts...")
    registered = list_registered()
    print(f"    {len(registered)} registered, ", end="")

    all_kt = load_all_keytexts(min_tokens=0)
    print(f"{len(all_kt)} with cached tokens")

    eligible = [kt for kt in all_kt if kt["token_count"] >= max_cn]
    too_short = [kt for kt in all_kt if kt["token_count"] < max_cn]
    print(f"    {len(eligible)} have >= {max_cn} tokens (eligible)")
    if too_short:
        print(f"    {len(too_short)} too short:")
        for kt in too_short:
            print(f"      - {kt['id']}: {kt['token_count']} tokens")

    if not eligible:
        print("\n[RESULT] No eligible keytexts. Populate corpus/keytexts/ first.")
        return []

    # Screen each keytext
    print(f"\n[3] Screening {len(eligible)} keytexts x {len(CHEAP_EXTRACTORS)} extractors...")
    results = []
    t0 = time.time()

    for ki, kt in enumerate(eligible):
        kid = kt["id"]
        tokens = kt["tokens"]
        title = kt.get("title", kid)

        # Constraint prefilter
        cscreen = screen_keytext(tokens, cipher_num, constraints)
        cpass = cscreen["pass_rate"]

        # Decode with each cheap extractor
        best_ext = None
        best_score = -1
        best_stream = ""
        best_wp = {}

        best_qg = -99.0

        for ext_name in CHEAP_EXTRACTORS:
            stream = decode_with_keytext(tokens, cipher_nums, ext_name)
            letters_only = "".join(c for c in stream if c.isalpha())
            if len(letters_only) < 20:
                continue
            wp = score_word_patterns(letters_only)
            qg = quadgram_score(letters_only)
            combined = (
                wp["word_coverage"] * 50 +
                min(wp["long_word_count"], 20) * 5
            )
            if combined > best_score:
                best_score = combined
                best_ext = ext_name
                best_stream = letters_only
                best_wp = wp
                best_qg = qg
            elif qg > best_qg:
                best_qg = qg

        # Combined ranking score (quadgram adds up to 30 pts for English-like text)
        constraint_bonus = cpass * 30
        word_score = best_wp.get("word_coverage", 0) * 50
        long_word_score = min(best_wp.get("long_word_count", 0), 20) * 5
        qg_bonus = max(0, (best_qg + 4.5) * 15) if best_qg > -99 else 0
        ranking_score = constraint_bonus + word_score + long_word_score + qg_bonus

        row = {
            "rank": 0,
            "keytext_id": kid,
            "title": title,
            "tokens": kt["token_count"],
            "constraint_pass_rate": cpass,
            "constraint_passed": cscreen["passed"],
            "constraint_total": cscreen["total"],
            "above_chance": cscreen["above_chance"],
            "best_extractor": best_ext or "none",
            "word_coverage": best_wp.get("word_coverage", 0),
            "long_word_count": best_wp.get("long_word_count", 0),
            "quadgram_score": best_qg,
            "ranking_score": ranking_score,
            "decoded_stream_preview": best_stream[:120] if best_stream else "",
        }
        results.append(row)

        if (ki + 1) % 5 == 0 or ki == len(eligible) - 1:
            elapsed = time.time() - t0
            print(f"    [{ki+1}/{len(eligible)}] {elapsed:.1f}s  "
                  f"last={kid}  score={ranking_score:.1f}  "
                  f"coverage={best_wp.get('word_coverage',0):.3f}")

    # Sort by ranking score
    results.sort(key=lambda r: r["ranking_score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    # Output
    out_dir = Path(out_dir_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"cipher{cipher_num}_screen_ranked.csv"
    fieldnames = [
        "rank", "keytext_id", "title", "tokens",
        "constraint_pass_rate", "constraint_passed", "constraint_total",
        "above_chance", "best_extractor", "word_coverage",
        "long_word_count", "quadgram_score", "ranking_score",
        "decoded_stream_preview",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"\n[4] Ranked output: {csv_path}")

    # Top N streams
    txt_path = out_dir / f"cipher{cipher_num}_screen_top{topk}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"KEY-TEXT HUNT RESULTS -- Cipher {cipher_num}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Eligible keytexts: {len(eligible)}\n")
        f.write(f"Constraints: {len(constraints)} (C2 overlap)\n")
        f.write("=" * 80 + "\n\n")

        for r in results[:topk]:
            f.write(f"--- Rank {r['rank']}: {r['keytext_id']} ---\n")
            f.write(f"Title: {r['title']}\n")
            f.write(f"Tokens: {r['tokens']}\n")
            f.write(f"Constraint pass rate: {r['constraint_pass_rate']:.1%} "
                    f"({r['constraint_passed']}/{r['constraint_total']})"
                    f" {'** ABOVE CHANCE **' if r['above_chance'] else ''}\n")
            f.write(f"Best extractor: {r['best_extractor']}\n")
            f.write(f"Word coverage: {r['word_coverage']:.3f}\n")
            f.write(f"Long word count (6+): {r['long_word_count']}\n")
            f.write(f"Quadgram score: {r['quadgram_score']:.4f} per qg\n")
            f.write(f"Ranking score: {r['ranking_score']:.1f}\n")
            f.write(f"Stream preview: {r['decoded_stream_preview']}\n\n")

        # Diagnostic summary
        f.write("=" * 80 + "\n")
        f.write("DIAGNOSTIC SUMMARY\n")
        f.write("=" * 80 + "\n")
        any_signal = any(r["long_word_count"] >= 3 and r["word_coverage"] >= 0.20
                         for r in results)
        if any_signal:
            f.write("\n** SIGNAL DETECTED ** -- At least one keytext produced:\n")
            f.write("   long_word_count >= 3 AND word_coverage >= 20%\n")
            f.write("   Proceed to FULL SCAN (Branch A).\n")
            hits = [r for r in results
                    if r["long_word_count"] >= 3 and r["word_coverage"] >= 0.20]
            for h in hits:
                f.write(f"   -> {h['keytext_id']}: coverage={h['word_coverage']:.3f}, "
                        f"long_words={h['long_word_count']}\n")
        else:
            f.write("\n** NO SIGNAL ** -- No keytext passed the quality threshold:\n")
            f.write("   long_word_count >= 3 AND word_coverage >= 20%\n")
            f.write("   Calibration reminder: Cipher 2 (known-correct) yields:\n")
            f.write("     word_coverage ~0.367, long_word_count ~12\n")
            f.write("   Top candidate coverage was only: "
                    f"{results[0]['word_coverage']:.3f}\n" if results else "N/A\n")
            f.write("\n   RECOMMENDATION: Expand keytext corpus (Branch B).\n")

        # Constraint analysis
        above_chance = [r for r in results if r["above_chance"]]
        f.write(f"\n\nCONSTRAINT ANALYSIS:\n")
        f.write(f"  Texts above chance ({2/26*100:.1f}%): {len(above_chance)}\n")
        if above_chance:
            for ac in above_chance:
                f.write(f"    {ac['keytext_id']}: {ac['constraint_pass_rate']:.1%}\n")
        else:
            f.write("  None. This rules out the 'same key text as DOI' hypothesis\n")
            f.write("  for all tested candidates.\n")

    print(f"[5] Top {topk} report: {txt_path}")

    # Print top results to console
    print(f"\n{'='*80}")
    print(f"TOP {min(topk, len(results))} RESULTS")
    print(f"{'='*80}")
    for r in results[:topk]:
        flag = "*" if r["long_word_count"] >= 3 and r["word_coverage"] >= 0.20 else " "
        print(f"  {flag} #{r['rank']:2d}  {r['keytext_id']:30s}  "
              f"score={r['ranking_score']:6.1f}  "
              f"cov={r['word_coverage']:.3f}  "
              f"long={r['long_word_count']:2d}  "
              f"qg={r['quadgram_score']:.3f}  "
              f"cpass={r['constraint_pass_rate']:.1%}  "
              f"ext={r['best_extractor']}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Key-Text Hunter")
    parser.add_argument("--cipher", type=int, default=1, choices=[1, 3])
    parser.add_argument("--topk", type=int, default=20)
    parser.add_argument("--outdir", type=str, default="output/keyhunt")
    args = parser.parse_args()
    run_hunt(cipher_num=args.cipher, topk=args.topk, out_dir_path=args.outdir)
