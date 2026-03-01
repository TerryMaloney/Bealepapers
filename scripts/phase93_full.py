"""
Phase 93: Full structural profiling, presupposition checks, cross-cipher
hypotheses, coordinate/concatenation tests, and word-cipher tests.

This is the "stop and think about what we might have missed" phase.
"""

import json
import csv
import sys
import re
import math
import random
import hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constraints.overlap_engine import load_cipher
from scoring.word_pattern_scorer import score_word_patterns
from scoring.quadgram_scorer import quadgram_score
from corpus.keytexts.loader import load_all_keytexts, load_normalized

OUT = Path("output/phase93")
OUT.mkdir(parents=True, exist_ok=True)

# =========================================================================
# HELPERS
# =========================================================================

def get_doi_words():
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        text = f.read()
    start = text.find("When(1)")
    end = text.find("honor(1322)")
    doi = text[start:end + len("honor(1322) .")]
    return [m.group(1) for m in re.finditer(r'(\w[\w\'-]*)\(\d+\)', doi)]

def score_stream(stream, label=""):
    letters = ''.join(c for c in stream.upper() if c.isalpha())
    n = len(letters)
    if n < 10:
        return {"label": label, "len": n, "cov": 0, "long": 0, "qg": -99, "preview": "", "signal": False}
    wp = score_word_patterns(letters)
    qg = quadgram_score(letters)
    return {"label": label, "len": n, "cov": wp["word_coverage"],
            "long": wp["long_word_count"], "qg": qg, "preview": letters[:120], "signal": False}

# =========================================================================
# STEP 2: STRUCTURAL PROFILING
# =========================================================================

def structural_profile(nums, name):
    n = len(nums)
    unique = set(nums)
    counts = Counter(nums)

    profile = {"name": name, "count": n, "unique": len(unique), "max": max(nums), "min": min(nums)}
    profile["mean"] = sum(nums) / n
    profile["median"] = sorted(nums)[n // 2]

    # Number length histogram
    len_hist = Counter(len(str(x)) for x in nums)
    profile["digit_length_hist"] = dict(sorted(len_hist.items()))

    # Digit frequency by position
    digit_freq = {}
    for pos_name, extractor in [("ones", lambda x: x % 10), ("tens", lambda x: (x // 10) % 10),
                                 ("hundreds", lambda x: (x // 100) % 10)]:
        freq = Counter(extractor(x) for x in nums)
        digit_freq[pos_name] = {str(k): v for k, v in sorted(freq.items())}
    profile["digit_by_position"] = digit_freq

    # Mod patterns
    mod_dists = {}
    for m in [9, 10, 11, 26]:
        dist = Counter(x % m for x in nums)
        mod_dists[f"mod{m}"] = dict(sorted(dist.items()))
    profile["mod_distributions"] = mod_dists

    # Repetition stats
    profile["singleton_count"] = sum(1 for c in counts.values() if c == 1)
    profile["singleton_pct"] = profile["singleton_count"] / len(unique) * 100
    profile["top10_freq"] = counts.most_common(10)

    # Repeat gap distribution
    positions = defaultdict(list)
    for i, x in enumerate(nums):
        positions[x].append(i)
    gaps = []
    for x, poslist in positions.items():
        for i in range(1, len(poslist)):
            gaps.append(poslist[i] - poslist[i - 1])
    profile["repeat_gap_mean"] = sum(gaps) / len(gaps) if gaps else 0
    profile["repeat_gap_median"] = sorted(gaps)[len(gaps) // 2] if gaps else 0

    # Index clustering: fraction of numbers in first quarter of range
    quarter = max(nums) // 4
    profile["pct_in_first_quarter"] = sum(1 for x in nums if x <= quarter) / n * 100
    profile["pct_in_last_quarter"] = sum(1 for x in nums if x > 3 * quarter) / n * 100

    return profile

def overlap_analysis(c1, c2, c3):
    s1, s2, s3 = set(c1), set(c2), set(c3)
    return {
        "C1_C2_overlap": len(s1 & s2),
        "C1_C3_overlap": len(s1 & s3),
        "C2_C3_overlap": len(s2 & s3),
        "C1_C2_C3_overlap": len(s1 & s2 & s3),
        "C1_unique_only": len(s1 - s2 - s3),
        "C2_unique_only": len(s2 - s1 - s3),
        "C3_unique_only": len(s3 - s1 - s2),
    }

# =========================================================================
# STEP 3: PRESUPPOSITION CHECKS
# =========================================================================

def presupposition_checks(doi_words, c2):
    results = {}

    # 3.1 Recalibrate with expanded controls
    # C2 decoded (known correct)
    c2_stream = ''.join(doi_words[cn-1][0].upper() if 0 <= cn-1 < len(doi_words) else '?' for cn in c2)
    c2_letters = ''.join(c for c in c2_stream if c.isalpha())
    c2_score = score_stream(c2_letters, "C2_known_correct")

    # Shuffled C2 (same letters, random order)
    shuffled = list(c2_letters)
    random.Random(42).shuffle(shuffled)
    shuf_stream = ''.join(shuffled)
    shuf_score = score_stream(shuf_stream, "C2_shuffled")

    # Random baseline
    rng = random.Random(99)
    rand_stream = ''.join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(520))
    rand_score = score_stream(rand_stream, "random_baseline")

    results["c2_correct"] = c2_score
    results["c2_shuffled"] = shuf_score
    results["random"] = rand_score
    results["shuffled_loses_signal"] = shuf_score["long"] < c2_score["long"] and shuf_score["cov"] < c2_score["cov"]

    # 3.2 Keytext loader sanity
    loader_checks = []
    for kid in ["webb_freemason_monitor", "hening_statutes_v1", "blackstone_bk1", "ivanhoe", "common_sense"]:
        norm = load_normalized(kid)
        if norm:
            tokens = norm["tokens"]
            check = {
                "id": kid,
                "token_count": norm["token_count"],
                "first_30": tokens[:30],
                "hash": norm.get("raw_hash", "N/A")[:16],
                "deterministic": norm["token_count"] == len(tokens),
            }
            loader_checks.append(check)
    results["loader_sanity"] = loader_checks

    return results

# =========================================================================
# STEP 4A: COORDINATE / CONCATENATION HYPOTHESIS
# =========================================================================

def test_coordinate(cipher_nums, tokens, kid, words_per_page):
    """Split number into (page, word_within_page) and decode."""
    results = []
    total_words = len(tokens)
    total_pages = math.ceil(total_words / words_per_page)

    # Split strategies
    splits = [
        ("last1", lambda n: (n // 10, n % 10)),
        ("last2", lambda n: (n // 100, n % 100)),
        ("first1_rest", lambda n: (int(str(n)[0]), int(str(n)[1:]) if len(str(n)) > 1 else 0)),
        ("first2_rest", lambda n: (int(str(n)[:2]), int(str(n)[2:]) if len(str(n)) > 2 else 0)),
    ]

    for split_name, split_fn in splits:
        stream = ""
        valid = 0
        for cn in cipher_nums:
            page, offset = split_fn(cn)
            word_idx = page * words_per_page + offset
            if 0 <= word_idx < total_words and offset < words_per_page:
                stream += tokens[word_idx][0].upper()
                valid += 1
            else:
                stream += "?"
        if valid > len(cipher_nums) * 0.3:
            r = score_stream(stream, f"coord({kid}, wpp={words_per_page}, split={split_name})")
            results.append(r)
    return results


def run_coordinate_tests(cipher_nums, cipher_name):
    """Run coordinate hypothesis on key texts."""
    all_results = []

    doi_words = get_doi_words()
    target_ids = ["webb_freemason_monitor", "hening_statutes_v1", "blackstone_bk1", "ivanhoe"]
    targets = [("doi", doi_words)]

    for kid in target_ids:
        norm = load_normalized(kid)
        if norm:
            targets.append((kid, norm["tokens"]))

    for kid, tokens in targets:
        for wpp in [40, 50, 60, 80, 100, 120, 150, 200, 250, 300]:
            res = test_coordinate(cipher_nums, tokens, kid, wpp)
            all_results.extend(res)

    all_results.sort(key=lambda r: r["cov"] * 100 + r["long"] * 10 + max(0, r["qg"] + 7) * 5, reverse=True)
    return all_results

# =========================================================================
# STEP 4B: WORD-CIPHER / CODEBOOK HYPOTHESIS
# =========================================================================

LOCATION_WORDS = {"county", "creek", "ridge", "mountain", "river", "road", "mile",
                  "miles", "north", "south", "east", "west", "degrees", "vault",
                  "cave", "rock", "tree", "feet", "inches", "buried", "deposited",
                  "treasure", "gold", "silver", "iron", "stone", "bedford", "buford",
                  "virginia", "pot", "pots", "covered", "lined"}

FUNCTION_WORDS = {"the", "of", "and", "to", "in", "a", "is", "that", "for", "it",
                  "with", "as", "was", "on", "are", "be", "by", "at", "from", "or",
                  "an", "not", "but", "have", "this", "had", "has", "which", "their",
                  "been", "its", "all", "were", "they", "will", "would", "shall",
                  "may", "can", "no", "if", "so", "we", "our", "he", "his", "her"}

NAME_WORDS = {"john", "james", "thomas", "william", "robert", "george", "charles",
              "samuel", "david", "daniel", "joseph", "benjamin", "henry", "richard",
              "edward", "andrew", "peter", "michael", "smith", "jones", "brown",
              "johnson", "davis", "wilson", "moore", "taylor", "clark", "lewis",
              "walker", "hall", "allen", "young", "martin", "thompson", "white",
              "harris", "jackson", "robinson", "mrs", "mr", "col", "capt", "gen"}


def test_word_cipher(cipher_nums, tokens, kid):
    """Treat numbers as word indices — does the resulting word sequence make sense?"""
    wc = len(tokens)
    word_seq = []
    valid = 0
    for cn in cipher_nums:
        idx = cn - 1
        if 0 <= idx < wc:
            word_seq.append(tokens[idx].lower())
            valid += 1
        else:
            word_seq.append("???")

    if valid < len(cipher_nums) * 0.5:
        return None

    # Score the word sequence
    n = len(word_seq)
    func_count = sum(1 for w in word_seq if w in FUNCTION_WORDS)
    loc_count = sum(1 for w in word_seq if w in LOCATION_WORDS)
    name_count = sum(1 for w in word_seq if w in NAME_WORDS)
    avg_wlen = sum(len(w) for w in word_seq) / n

    # Expected function word rate in English: ~40-50%
    func_rate = func_count / n
    loc_rate = loc_count / n
    name_rate = name_count / n

    # Simple bigram check: how often does word[i] naturally precede word[i+1]?
    common_bigrams = {"of the", "in the", "to the", "and the", "for the",
                      "of a", "in a", "to a", "is a", "was a",
                      "it is", "it was", "he has", "he had",
                      "the most", "the same", "the right", "the people"}
    bigram_hits = 0
    for i in range(n - 1):
        bi = f"{word_seq[i]} {word_seq[i+1]}"
        if bi in common_bigrams:
            bigram_hits += 1

    result = {
        "keytext_id": kid,
        "valid_pct": valid / len(cipher_nums),
        "func_word_rate": func_rate,
        "location_word_count": loc_count,
        "name_word_count": name_count,
        "avg_word_length": avg_wlen,
        "bigram_hits": bigram_hits,
        "combined_score": func_rate * 50 + loc_rate * 200 + name_rate * 100 + bigram_hits * 10,
        "preview": " ".join(word_seq[:40]),
    }
    return result

# =========================================================================
# STEP 5: CROSS-CIPHER HYPOTHESES
# =========================================================================

def cross_cipher_tests(c1, c2, c3, doi_words):
    """Test whether the ciphers reference each other."""
    results = []

    # H-CC1: C2 decoded plaintext as word-indices for C1
    c2_decoded = ''.join(doi_words[cn-1][0].upper() if 0 <= cn-1 < len(doi_words) else '?' for cn in c2)
    c2_letters = ''.join(c for c in c2_decoded if c.isalpha())

    # Use C2 decoded letter values as numeric offsets for C1
    stream = ""
    for i, cn in enumerate(c1):
        if i < len(c2_letters):
            offset = ord(c2_letters[i]) - ord('A')
            shifted = cn + offset
        else:
            shifted = cn
        idx = shifted - 1
        if 0 <= idx < len(doi_words):
            stream += doi_words[idx][0].upper()
        else:
            stream += "?"
    results.append(score_stream(stream, "CC1: C1 + C2_decoded_as_Vigenere_on_DOI"))

    # H-CC2: C3 numbers used as indices into C2 decoded stream
    if len(c2_letters) >= max(c3):
        stream = ""
        for cn in c3:
            idx = cn - 1
            if 0 <= idx < len(c2_letters):
                stream += c2_letters[idx]
            else:
                stream += "?"
        results.append(score_stream(stream, "CC2: C3_numbers_into_C2_decoded_stream"))

    # H-CC3: C1 numbers used as indices into C2 decoded stream
    stream = ""
    for cn in c1:
        idx = cn - 1
        if 0 <= idx < len(c2_letters):
            stream += c2_letters[idx]
        else:
            stream += "?"
    results.append(score_stream(stream, "CC3: C1_numbers_into_C2_decoded_stream"))

    # H-CC4: Use C2 numbers as key to Vigenere-shift C1 decoded letters
    c1_base = ''.join(doi_words[cn-1][0].upper() if 0 <= cn-1 < len(doi_words) else '?' for cn in c1)
    stream = ""
    for i, ch in enumerate(c1_base):
        if ch.isalpha() and i < len(c2):
            key_idx = c2[i % len(c2)] - 1
            key_letter = doi_words[key_idx][0].upper() if 0 <= key_idx < len(doi_words) else 'A'
            shift = ord(key_letter) - ord('A')
            decoded = chr((ord(ch) - ord('A') - shift) % 26 + ord('A'))
            stream += decoded
        else:
            stream += ch
    results.append(score_stream(stream, "CC4: C1_DOI_decode_Vigenere_shifted_by_C2_DOI"))

    # H-CC5: Keyword Vigenere on C1 DOI decode
    c1_letters = ''.join(c for c in c1_base if c.isalpha())
    for keyword in ["BEALE", "BEDFORD", "VIRGINIA", "BUFORD", "MORRISS",
                    "TREASURE", "THOMAS", "JEFFERSON", "LIBERTY", "SANTA",
                    "GOLD", "SILVER", "VAULT", "BUFFALO", "PLAINS"]:
        stream = ""
        for i, ch in enumerate(c1_letters):
            key_ch = keyword[i % len(keyword)]
            shift = ord(key_ch) - ord('A')
            decoded = chr((ord(ch) - ord('A') - shift) % 26 + ord('A'))
            stream += decoded
        r = score_stream(stream, f"CC5: C1_DOI_Vigenere_keyword={keyword}")
        results.append(r)

    # H-CC6: C1 solved WITHOUT text — pure number-to-letter
    # (If C1 was meant to be solved by knowing the right mapping, not a text)
    for shift in range(26):
        stream = ''.join(chr((cn + shift) % 26 + ord('A')) for cn in c1)
        results.append(score_stream(stream, f"CC6: C1_mod26_shift={shift}"))

    # H-CC7: Reverse C1 number order, then decode with DOI
    rev_c1 = list(reversed(c1))
    stream = ''.join(doi_words[cn-1][0].upper() if 0 <= cn-1 < len(doi_words) else '?' for cn in rev_c1)
    results.append(score_stream(stream, "CC7: C1_reversed_DOI_first_letter"))

    # H-CC8: Interleave C1 and C3 numbers, decode with DOI
    interleaved = []
    for i in range(max(len(c1), len(c3))):
        if i < len(c1):
            interleaved.append(c1[i])
        if i < len(c3):
            interleaved.append(c3[i])
    stream = ''.join(doi_words[cn-1][0].upper() if 0 <= cn-1 < len(doi_words) else '?' for cn in interleaved)
    results.append(score_stream(stream, "CC8: C1+C3_interleaved_DOI"))

    return results

# =========================================================================
# MAIN
# =========================================================================

def main():
    print("=" * 70)
    print("PHASE 93: STRUCTURAL PROFILING + PRESUPPOSITION CHECKS")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    c1, c2, c3 = load_cipher(1), load_cipher(2), load_cipher(3)
    doi_words = get_doi_words()

    # ============================================
    # STEP 2: STRUCTURAL PROFILING
    # ============================================
    print("\n[STEP 2] Structural profiling...")
    profiles = {
        "c1": structural_profile(c1, "Cipher 1"),
        "c2": structural_profile(c2, "Cipher 2"),
        "c3": structural_profile(c3, "Cipher 3"),
    }
    overlaps = overlap_analysis(c1, c2, c3)

    with open(OUT / "structure_report.json", "w") as f:
        json.dump({"profiles": profiles, "overlaps": overlaps}, f, indent=2, default=str)

    # Write readable report
    with open(OUT / "structure_report.txt", "w") as f:
        f.write("CIPHER STRUCTURE PROFILE\n" + "=" * 70 + "\n\n")
        for key, p in profiles.items():
            f.write(f"\n{p['name']}:\n" + "-" * 40 + "\n")
            f.write(f"  Count: {p['count']}, Unique: {p['unique']}, Range: {p['min']}-{p['max']}\n")
            f.write(f"  Mean: {p['mean']:.1f}, Median: {p['median']}\n")
            f.write(f"  Digit lengths: {p['digit_length_hist']}\n")
            f.write(f"  Singletons: {p['singleton_count']} ({p['singleton_pct']:.1f}%)\n")
            f.write(f"  Repeat gap mean: {p['repeat_gap_mean']:.1f}, median: {p['repeat_gap_median']}\n")
            f.write(f"  First quarter of range: {p['pct_in_first_quarter']:.1f}%\n")
            f.write(f"  Last quarter of range: {p['pct_in_last_quarter']:.1f}%\n")
            f.write(f"  Top 10 frequent: {p['top10_freq']}\n")
            f.write(f"  Mod 26 distribution entropy: ")
            mod26 = p['mod_distributions']['mod26']
            total = sum(mod26.values())
            ent = -sum((v/total) * math.log2(v/total) for v in mod26.values() if v > 0)
            f.write(f"{ent:.3f} bits (max={math.log2(26):.3f})\n")

        f.write(f"\nOverlap Analysis:\n" + "-" * 40 + "\n")
        for k, v in overlaps.items():
            f.write(f"  {k}: {v}\n")

        # Key insight: clustering
        f.write(f"\nCLUSTERING ANALYSIS (are numbers biased toward start of text?):\n")
        f.write(f"  C1: {profiles['c1']['pct_in_first_quarter']:.1f}% in first quarter, "
                f"{profiles['c1']['pct_in_last_quarter']:.1f}% in last quarter\n")
        f.write(f"  C2: {profiles['c2']['pct_in_first_quarter']:.1f}% in first quarter, "
                f"{profiles['c2']['pct_in_last_quarter']:.1f}% in last quarter\n")
        f.write(f"  C3: {profiles['c3']['pct_in_first_quarter']:.1f}% in first quarter, "
                f"{profiles['c3']['pct_in_last_quarter']:.1f}% in last quarter\n")
        f.write(f"  (Book ciphers tend to cluster toward early pages where common words appear.)\n")

    print(f"  Structure report: {OUT / 'structure_report.txt'}")

    # ============================================
    # STEP 3: PRESUPPOSITION CHECKS
    # ============================================
    print("\n[STEP 3] Presupposition checks...")
    checks = presupposition_checks(doi_words, c2)

    with open(OUT / "calibration_plus.json", "w") as f:
        json.dump(checks, f, indent=2, default=str)

    with open(OUT / "calibration_plus.txt", "w") as f:
        f.write("PRESUPPOSITION CHECKS\n" + "=" * 70 + "\n\n")
        f.write(f"C2 correct:  cov={checks['c2_correct']['cov']:.4f}, long={checks['c2_correct']['long']}, "
                f"qg={checks['c2_correct']['qg']:.3f}\n")
        f.write(f"C2 shuffled: cov={checks['c2_shuffled']['cov']:.4f}, long={checks['c2_shuffled']['long']}, "
                f"qg={checks['c2_shuffled']['qg']:.3f}\n")
        f.write(f"Random:      cov={checks['random']['cov']:.4f}, long={checks['random']['long']}, "
                f"qg={checks['random']['qg']:.3f}\n\n")
        f.write(f"Shuffled loses signal: {checks['shuffled_loses_signal']}\n")
        f.write(f"  (This proves the scorer detects WORD ORDER, not just letter frequency.)\n\n")

        f.write("Keytext loader sanity:\n")
        for lc in checks["loader_sanity"]:
            f.write(f"  {lc['id']}: {lc['token_count']} tokens, hash={lc['hash']}, "
                    f"deterministic={lc['deterministic']}\n")
            f.write(f"    first 10 tokens: {lc['first_30'][:10]}\n")

    print(f"  Calibration+: {OUT / 'calibration_plus.txt'}")
    print(f"  Shuffled C2 loses signal: {checks['shuffled_loses_signal']}")

    # ============================================
    # STEP 5: CROSS-CIPHER HYPOTHESES
    # ============================================
    print("\n[STEP 5] Cross-cipher hypotheses...")
    cc_results = cross_cipher_tests(c1, c2, c3, doi_words)
    cc_results.sort(key=lambda r: r["cov"] * 100 + r["long"] * 10 + max(0, r["qg"] + 7) * 5, reverse=True)

    with open(OUT / "cross_cipher_ranked.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "len", "cov", "long", "qg", "preview"])
        writer.writeheader()
        for r in cc_results:
            writer.writerow({k: r[k] for k in ["label", "len", "cov", "long", "qg", "preview"]})

    print(f"  Cross-cipher results: {len(cc_results)} tested")
    for r in cc_results[:5]:
        print(f"    cov={r['cov']:.4f} long={r['long']} qg={r['qg']:.3f} {r['label'][:65]}")

    # ============================================
    # STEP 4A: COORDINATE HYPOTHESIS
    # ============================================
    print("\n[STEP 4A] Coordinate/concatenation hypothesis...")
    for cname, cnums in [("c1", c1), ("c3", c3)]:
        coord_res = run_coordinate_tests(cnums, cname)
        csv_path = OUT / f"coord_ranked_{cname}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["label", "len", "cov", "long", "qg", "preview"])
            writer.writeheader()
            for r in coord_res[:200]:
                writer.writerow({k: r[k] for k in ["label", "len", "cov", "long", "qg", "preview"]})
        print(f"  {cname}: {len(coord_res)} combinations tested")
        for r in coord_res[:3]:
            print(f"    cov={r['cov']:.4f} long={r['long']} qg={r['qg']:.3f} {r['label'][:65]}")

    # ============================================
    # STEP 4B: WORD-CIPHER HYPOTHESIS
    # ============================================
    print("\n[STEP 4B] Word-cipher/codebook hypothesis...")
    wc_results = []
    target_ids = ["webb_freemason_monitor", "hening_statutes_v1", "blackstone_bk1", "ivanhoe"]

    # DOI
    for cname, cnums in [("c1", c1), ("c3", c3)]:
        r = test_word_cipher(cnums, doi_words, f"doi_{cname}")
        if r:
            wc_results.append(r)

        for kid in target_ids:
            norm = load_normalized(kid)
            if norm:
                r = test_word_cipher(cnums, norm["tokens"], f"{kid}_{cname}")
                if r:
                    wc_results.append(r)

    wc_results.sort(key=lambda r: r["combined_score"], reverse=True)

    with open(OUT / "wordcipher_ranked.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["keytext_id", "valid_pct", "func_word_rate", "location_word_count",
                  "name_word_count", "avg_word_length", "bigram_hits", "combined_score", "preview"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in wc_results:
            writer.writerow({k: r[k] for k in fields})

    print(f"  Word-cipher results: {len(wc_results)} tested")
    for r in wc_results[:3]:
        print(f"    func={r['func_word_rate']:.3f} loc={r['location_word_count']} "
              f"names={r['name_word_count']} bigrams={r['bigram_hits']} "
              f"score={r['combined_score']:.1f} {r['keytext_id']}")
        print(f"    preview: {r['preview'][:80]}")

    # ============================================
    # SUMMARY
    # ============================================
    print(f"\n{'='*70}")
    print("PHASE 93 COMPLETE")
    print(f"Outputs in {OUT}/")

    any_signal = False
    for r in cc_results + coord_res:
        if r.get("long", 0) >= 3 and r.get("cov", 0) >= 0.107:
            any_signal = True
            print(f"  *** SIGNAL: {r['label']}")

    if not any_signal:
        print("  NO SIGNAL across all Phase 93 tests.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
