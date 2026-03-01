"""
Phase 102 Task 5: Impact evaluation of cipher candidates.

For each of 50 candidates: decode with DOI first_letter, B3 first_letter, B3 position_mod_wordlen.
Score with quadgram + word_pattern. Control: shuffle sequence 200 times per candidate.
Output: c1_candidate_eval_ranked.csv, top_streams/c1_candidate_<id>_<method>.txt for top 10.
"""

import csv
import json
import random
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from corpus.beale_doi_adjusted import get_adjusted_tokens
from scoring.quadgram_scorer import quadgram_score
from scoring.word_pattern_scorer import score_word_patterns

VARIANTS_DIR = PROJECT_ROOT / "corpus" / "cipher_variants"
OUT = PROJECT_ROOT / "output" / "phase102"
TOP_STREAMS = OUT / "top_streams"
N_SHUFFLE = 200
SEED = 102500


def load_candidate(candidate_id: str) -> List[int]:
    path = VARIANTS_DIR / f"{candidate_id}.txt"
    raw = path.read_text(encoding="utf-8")
    return [int(x.strip()) for x in raw.replace("\n", ",").split(",") if x.strip().isdigit()]


def extract_first_letter(tokens: List[str], n: int) -> str:
    idx = n - 1
    if 0 <= idx < len(tokens) and tokens[idx]:
        return tokens[idx][0].upper()
    return "?"


def extract_position_mod_wordlen(tokens: List[str], cipher_nums: List[int], position: int, n: int) -> str:
    idx = n - 1
    if 0 <= idx < len(tokens):
        w = tokens[idx]
        if w:
            i = position % len(w)
            return w[i].upper()
    return "?"


def decode(tokens: List[str], cipher_nums: List[int], extractor: str) -> str:
    if extractor == "first_letter":
        return "".join(extract_first_letter(tokens, n) for n in cipher_nums)
    if extractor == "position_mod_wordlen":
        return "".join(
            extract_position_mod_wordlen(tokens, cipher_nums, i, n)
            for i, n in enumerate(cipher_nums)
        )
    return "".join(extract_first_letter(tokens, n) for n in cipher_nums)


def main():
    TOP_STREAMS.mkdir(parents=True, exist_ok=True)
    doi_tokens = get_adjusted_tokens()
    with open(PROJECT_ROOT / "corpus" / "keytexts" / "normalized" / "bundle_b3.json", "r", encoding="utf-8") as f:
        b3 = json.load(f)
    b3_tokens = b3["tokens"]
    rng = random.Random(SEED)

    configs = [
        ("doi", "first_letter", doi_tokens),
        ("b3", "first_letter", b3_tokens),
        ("b3", "position_mod_wordlen", b3_tokens),
    ]
    all_rows = []
    stream_cache = []

    for rank in range(1, 51):
        cid = f"c1_candidate_{rank:03d}"
        try:
            nums = load_candidate(cid)
        except FileNotFoundError:
            continue
        for keystream, extractor, tokens in configs:
            stream = decode(tokens, nums, extractor)
            wp = score_word_patterns(stream)
            qg = quadgram_score(stream)
            ctrl_qg = []
            for _ in range(N_SHUFFLE):
                shuffled = nums[:]
                rng.shuffle(shuffled)
                s = decode(tokens, shuffled, extractor)
                ctrl_qg.append(quadgram_score(s))
            mean_c = sum(ctrl_qg) / len(ctrl_qg)
            var_c = sum((x - mean_c) ** 2 for x in ctrl_qg) / len(ctrl_qg)
            std_c = var_c ** 0.5 if var_c > 0 else 1e-10
            z = (qg - mean_c) / std_c
            all_rows.append({
                "candidate_id": cid,
                "keystream": keystream,
                "extractor": extractor,
                "quadgram": round(qg, 4),
                "word_coverage": round(wp["word_coverage"], 4),
                "long_words": wp["long_word_count"],
                "ctrl_mean": round(mean_c, 4),
                "ctrl_std": round(std_c, 4),
                "z_score": round(z, 4),
            })
            stream_cache.append((z, cid, keystream, extractor, stream, qg))

    all_rows.sort(key=lambda r: r["z_score"], reverse=True)
    with open(OUT / "c1_candidate_eval_ranked.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["candidate_id", "keystream", "extractor", "quadgram", "word_coverage", "long_words", "ctrl_mean", "ctrl_std", "z_score"])
        w.writeheader()
        w.writerows(all_rows)

    stream_cache.sort(key=lambda x: x[0], reverse=True)
    for i, (z, cid, ks, ext, stream, qg) in enumerate(stream_cache[:10]):
        safe = f"{cid}_{ks}_{ext}".replace(" ", "_")
        with open(TOP_STREAMS / f"c1_candidate_{cid.replace('c1_candidate_', '')}_{ks}_{ext}.txt", "w", encoding="utf-8") as f:
            f.write(f"candidate_id={cid} keystream={ks} extractor={ext}\n")
            f.write(f"z_score={z:.4f} quadgram={qg:.4f}\n\n")
            f.write(stream + "\n")

    print(f"Task 5: wrote c1_candidate_eval_ranked.csv ({len(all_rows)} rows), top_streams/ (top 10)")
    best = all_rows[0]
    print(f"  Best z_score: {best['z_score']:.2f} ({best['candidate_id']} {best['keystream']} {best['extractor']})")


if __name__ == "__main__":
    main()
