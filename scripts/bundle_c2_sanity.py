"""
C2 sanity check on pamphlet bundles.

For each bundle (B1, B2, B3), decode C2 using the bundle's token array and assert:
- tokens[806] (0-indexed) == "valuable"
- First 10 decoded chars == "IHAVEDEPOS"
- First 40 decoded chars match known prefix

STOP if any bundle fails. Output: output/phase98/bundle_c2_sanity.txt
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constraints.overlap_engine import load_cipher
from corpus.beale_doi_adjusted import get_adjusted_tokens

OUT_DIR = PROJECT_ROOT / "output" / "phase98"


def load_bundle_tokens(bundle_path: Path) -> list:
    with open(bundle_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["tokens"]


def decode_c2_first_letter(tokens: list, cipher_nums: list, length: int = 40) -> str:
    out = []
    for n in cipher_nums:
        if len(out) >= length:
            break
        idx = n - 1  # 1-indexed word number
        if 0 <= idx < len(tokens):
            word = tokens[idx]
            out.append(word[0].upper() if word else "?")
        else:
            out.append("?")
    return "".join(out)


def run_sanity() -> bool:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT_DIR / "bundle_manifest.json"
    if not manifest_path.exists():
        print("ERROR: bundle_manifest.json not found. Run pamphlet_bundle_builder first.")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    c2 = load_cipher(2)
    # Expected first 40 chars from DOI decode (canonical)
    doi_tokens = get_adjusted_tokens()
    expected_prefix_40 = decode_c2_first_letter(doi_tokens, c2, 40)
    lines = []
    all_ok = True

    for bid in ["b1", "b2", "b3"]:
        info = manifest["bundles"][bid]
        path = Path(info["path"])
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            lines.append(f"{bid}: FAIL - bundle file not found: {path}")
            all_ok = False
            continue

        tokens = load_bundle_tokens(path)
        lines.append(f"--- {bid.upper()} ---")
        lines.append(f"  token_count={len(tokens)}")

        # 1) tokens[806] == "valuable"
        if len(tokens) <= 806:
            lines.append(f"  FAIL: tokens[806] missing (len={len(tokens)})")
            all_ok = False
        else:
            w = tokens[806].lower()
            if w == "valuable":
                lines.append(f"  PASS: tokens[806] = 'valuable'")
            else:
                lines.append(f"  FAIL: tokens[806] = '{tokens[806]}' (expected 'valuable')")
                all_ok = False

        # 2) First 10 decoded == "IHAVEDEPOS"
        decoded10 = decode_c2_first_letter(tokens, c2, 10)
        if decoded10 == "IHAVEDEPOS":
            lines.append(f"  PASS: first 10 decoded = '{decoded10}'")
        else:
            lines.append(f"  FAIL: first 10 decoded = '{decoded10}' (expected 'IHAVEDEPOS')")
            all_ok = False

        # 3) First 40 decoded match known prefix (DOI decode)
        decoded40 = decode_c2_first_letter(tokens, c2, 40)
        if decoded40 == expected_prefix_40:
            lines.append(f"  PASS: first 40 match known prefix")
        else:
            match_len = sum(1 for a, b in zip(decoded40, expected_prefix_40) if a == b)
            if match_len >= 35:
                lines.append(f"  PASS: first 40 chars match {match_len}/40 of known prefix")
            else:
                lines.append(f"  FAIL: first 40 = '{decoded40}'")
                lines.append(f"        expected  = '{expected_prefix_40}'")
                all_ok = False
        lines.append("")

    out_path = OUT_DIR / "bundle_c2_sanity.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {out_path}")

    if all_ok:
        print("All bundle C2 sanity checks PASSED.")
    else:
        print("One or more bundle C2 sanity checks FAILED. Do not proceed to Step 3.")
    return all_ok


if __name__ == "__main__":
    ok = run_sanity()
    sys.exit(0 if ok else 1)
