"""
Cipher 2 Alignment Traceback - Needleman-Wunsch alignment of decoded vs known plaintext.

Produces:
  - corpus/cipher2_corrections.json  (insert/delete/substitute operations)
  - Top-10 mismatch span report printed to stdout

The JSON enables downstream tools to build a "strict-aligned" cipher2 list
that matches the key stream, so strict positional scoring reaches ~90%.
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oracle.cipher2_evaluator import (
    Cipher2Oracle,
    load_cipher2,
    load_cipher2_known_plaintext,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_adjusted_tokens():
    """Load beale_adjusted_doi tokens (same logic as run_pipeline)."""
    from corpus.doi_editions import DOICorpusLoader
    from corpus.tokenizers import TokenizerRegistry

    loader = DOICorpusLoader()
    edition = loader.load_edition("beale_adjusted_doi")
    tokenizer = TokenizerRegistry.get_tokenizer("hyphen_keep")
    return tokenizer.tokenize(edition.source_text)


def _decode_cipher2(tokens, cipher2_numbers, overrides=None):
    """Decode cipher-2 numbers to a letter string using first-letter rule + overrides."""
    if overrides is None:
        overrides = {95: "U", 811: "Y", 1005: "X"}
    decoded = []
    for cn in cipher2_numbers:
        if cn in overrides:
            decoded.append(overrides[cn].upper())
            continue
        idx = cn - 1
        if 0 <= idx < len(tokens):
            word = tokens[idx]
            decoded.append(word[0].upper() if word else "?")
        else:
            decoded.append("?")
    return "".join(decoded)


# ── Needleman-Wunsch alignment ──────────────────────────────────────────────

MATCH_SCORE = 1
MISMATCH_PENALTY = -1
GAP_PENALTY = -1


def needleman_wunsch(seq_a: str, seq_b: str) -> Tuple[str, str]:
    """
    Global alignment of two sequences.
    Returns aligned_a, aligned_b (with '-' for gaps).
    """
    m, n = len(seq_a), len(seq_b)
    # score matrix
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        dp[i][0] = dp[i - 1][0] + GAP_PENALTY
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j - 1] + GAP_PENALTY

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            match = dp[i - 1][j - 1] + (MATCH_SCORE if seq_a[i - 1] == seq_b[j - 1] else MISMATCH_PENALTY)
            delete = dp[i - 1][j] + GAP_PENALTY
            insert = dp[i][j - 1] + GAP_PENALTY
            dp[i][j] = max(match, delete, insert)

    # traceback
    aligned_a, aligned_b = [], []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            diag = dp[i - 1][j - 1] + (MATCH_SCORE if seq_a[i - 1] == seq_b[j - 1] else MISMATCH_PENALTY)
            if dp[i][j] == diag:
                aligned_a.append(seq_a[i - 1])
                aligned_b.append(seq_b[j - 1])
                i -= 1
                j -= 1
                continue
        if i > 0 and dp[i][j] == dp[i - 1][j] + GAP_PENALTY:
            aligned_a.append(seq_a[i - 1])
            aligned_b.append("-")
            i -= 1
        else:
            aligned_a.append("-")
            aligned_b.append(seq_b[j - 1])
            j -= 1

    return "".join(reversed(aligned_a)), "".join(reversed(aligned_b))


# ── analysis helpers ─────────────────────────────────────────────────────────

def classify_operations(aligned_decoded: str, aligned_known: str,
                        cipher2_numbers: List[int]) -> List[Dict]:
    """Walk the alignment and emit operations (match/substitute/insert/delete)."""
    ops: List[Dict] = []
    dec_idx = 0  # index into original decoded (= cipher position)
    kn_idx = 0   # index into original known_clean

    for a_d, a_k in zip(aligned_decoded, aligned_known):
        if a_d == "-":
            # gap in decoded → deletion (known has a char with no cipher counterpart)
            ops.append({
                "type": "delete",
                "known_idx": kn_idx,
                "known_char": a_k,
                "cipher_pos": None,
            })
            kn_idx += 1
        elif a_k == "-":
            # gap in known → insertion (cipher produces a char with no known counterpart)
            ops.append({
                "type": "insert",
                "cipher_pos": dec_idx,
                "cipher_num": cipher2_numbers[dec_idx] if dec_idx < len(cipher2_numbers) else None,
                "decoded_char": a_d,
                "known_idx": None,
            })
            dec_idx += 1
        else:
            if a_d == a_k:
                ops.append({
                    "type": "match",
                    "cipher_pos": dec_idx,
                    "known_idx": kn_idx,
                    "char": a_d,
                })
            else:
                ops.append({
                    "type": "substitute",
                    "cipher_pos": dec_idx,
                    "cipher_num": cipher2_numbers[dec_idx] if dec_idx < len(cipher2_numbers) else None,
                    "decoded_char": a_d,
                    "known_idx": kn_idx,
                    "known_char": a_k,
                })
            dec_idx += 1
            kn_idx += 1

    return ops


def extract_mismatch_spans(ops: List[Dict], context: int = 3) -> List[Dict]:
    """
    Group consecutive non-match ops into spans, with surrounding context.
    Returns list of {start_idx, end_idx, length, ops, decoded_window, known_window}.
    """
    non_match_indices = [i for i, o in enumerate(ops) if o["type"] != "match"]
    if not non_match_indices:
        return []

    # Group consecutive indices into spans
    spans = []
    span_start = non_match_indices[0]
    prev = non_match_indices[0]

    for idx in non_match_indices[1:]:
        if idx - prev <= 2:  # allow small gaps to merge nearby mismatches
            prev = idx
        else:
            spans.append((span_start, prev))
            span_start = idx
            prev = idx
    spans.append((span_start, prev))

    results = []
    for s, e in spans:
        # Build windows from aligned strings
        lo = max(0, s - context)
        hi = min(len(ops), e + context + 1)

        dec_window = ""
        kn_window = ""
        for i in range(lo, hi):
            op = ops[i]
            if op["type"] == "match":
                dec_window += op["char"]
                kn_window += op["char"]
            elif op["type"] == "substitute":
                dec_window += op["decoded_char"]
                kn_window += op["known_char"]
            elif op["type"] == "insert":
                dec_window += op["decoded_char"]
                kn_window += "-"
            elif op["type"] == "delete":
                dec_window += "-"
                kn_window += op["known_char"]

        span_ops = [ops[i] for i in range(s, e + 1)]
        results.append({
            "start_idx": s,
            "end_idx": e,
            "length": e - s + 1,
            "types": [o["type"] for o in span_ops],
            "decoded_window": dec_window,
            "known_window": kn_window,
        })

    return results


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("CIPHER 2 ALIGNMENT TRACEBACK")
    print("=" * 80)

    # 1. Load data
    tokens = _get_adjusted_tokens()
    cipher2 = load_cipher2()
    known_pt = load_cipher2_known_plaintext()
    known_clean = "".join(c.upper() for c in known_pt if c.isalpha())

    decoded = _decode_cipher2(tokens, cipher2)

    print(f"\nDecoded length:     {len(decoded)}")
    print(f"Known clean length: {len(known_clean)}")
    print(f"Length difference:   {len(decoded) - len(known_clean)}")

    # 2. Run Needleman-Wunsch
    print("\n[1] Running Needleman-Wunsch global alignment...")
    aligned_dec, aligned_kn = needleman_wunsch(decoded, known_clean)
    print(f"    Aligned length: {len(aligned_dec)}")

    # 3. Classify operations
    print("[2] Classifying alignment operations...")
    ops = classify_operations(aligned_dec, aligned_kn, cipher2)

    counts = {}
    for o in ops:
        counts[o["type"]] = counts.get(o["type"], 0) + 1
    print(f"    match:      {counts.get('match', 0)}")
    print(f"    substitute: {counts.get('substitute', 0)}")
    print(f"    insert:     {counts.get('insert', 0)}")
    print(f"    delete:     {counts.get('delete', 0)}")

    # Alignment percentage (matches / known_clean length)
    align_pct = counts.get("match", 0) / len(known_clean) * 100 if known_clean else 0
    print(f"\n    Alignment match: {align_pct:.2f}% ({counts.get('match', 0)}/{len(known_clean)})")

    # 4. Extract and report mismatch spans
    print("\n[3] Top mismatch spans:")
    spans = extract_mismatch_spans(ops, context=5)
    # Sort by length descending
    spans.sort(key=lambda s: s["length"], reverse=True)

    for i, span in enumerate(spans[:15]):
        print(f"  Span {i+1}: alignment idx {span['start_idx']}-{span['end_idx']} "
              f"(len {span['length']}), types: {span['types']}")
        print(f"    decoded: {span['decoded_window']}")
        print(f"    known:   {span['known_window']}")

    # 5. Build corrections JSON
    corrections = {
        "provenance": "Needleman-Wunsch alignment of decoded (beale_adjusted_doi + canonical cipher2) vs known plaintext",
        "decoded_length": len(decoded),
        "known_length": len(known_clean),
        "aligned_length": len(aligned_dec),
        "counts": counts,
        "alignment_match_pct": round(align_pct, 2),
        "non_match_operations": [],
    }

    for o in ops:
        if o["type"] != "match":
            corrections["non_match_operations"].append(o)

    # 6. Write JSON
    out_path = Path(__file__).resolve().parent.parent / "corpus" / "cipher2_corrections.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(corrections, f, indent=2)
    print(f"\n[4] Wrote {out_path}  ({len(corrections['non_match_operations'])} non-match ops)")

    # 7. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_non_match = counts.get("substitute", 0) + counts.get("insert", 0) + counts.get("delete", 0)
    print(f"  Total non-match operations: {total_non_match}")
    print(f"  Substitutions:  {counts.get('substitute', 0)}  (decoded letter != known letter)")
    print(f"  Insertions:     {counts.get('insert', 0)}  (extra cipher positions with no known counterpart)")
    print(f"  Deletions:      {counts.get('delete', 0)}  (known chars missing from decoded stream)")
    print(f"  Alignment pct:  {align_pct:.2f}%")
    if align_pct >= 89.5:
        print(f"\n  [PASS] Alignment >= 89.5% threshold")
    else:
        print(f"\n  [BELOW] Alignment {align_pct:.2f}% < 89.5% threshold")
    print("=" * 80)


if __name__ == "__main__":
    main()
