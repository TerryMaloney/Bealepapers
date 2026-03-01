"""
Phase 102 Task 1: Collect cipher variants into corpus/cipher_variants/.

Sources: canonical, beale_papers, FSU Burkardt; optional Wikisource fetch.
Writes: registry.json, c1_*/c3_*.txt, output/phase102/variant_inventory.txt
"""

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VARIANTS_DIR = PROJECT_ROOT / "corpus" / "cipher_variants"
OUT = PROJECT_ROOT / "output" / "phase102"


def _parse_csv_numbers(text: str) -> List[int]:
    """Parse comma/space/newline-separated integers."""
    combined = " ".join(line.strip() for line in text.splitlines() if line.strip())
    parts = re.sub(r"[,\s]+", " ", combined).split()
    out = []
    for p in parts:
        s = p.strip().rstrip(".")
        if s and s.replace(".", "").isdigit():
            out.append(int(s))
    return out


def load_beale_papers_cipher(n: int) -> List[int]:
    with open(PROJECT_ROOT / "beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    idx = {1: 2, 2: 58, 3: 6}[n]
    line = lines[idx].strip()
    return [int(x.strip()) for x in line.split(",") if x.strip().replace(".", "").isdigit()]


def load_fsu_cipher(n: int) -> List[int]:
    path = PROJECT_ROOT / "corpus" / "raw_sources" / "fsu" / f"beale_cipher{n}.txt"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    return _parse_csv_numbers(text)


def load_canonical_cipher(n: int) -> List[int]:
    path = PROJECT_ROOT / "corpus" / f"cipher{n}_numbers_canonical.txt"
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            return [int(x.strip()) for x in line.split(",") if x.strip().replace(".", "").isdigit()]
    return []


def try_fetch_wikisource_cipher(n: int) -> Optional[List[int]]:
    """Attempt to extract cipher from Wikisource page. Returns None if fetch fails."""
    try:
        import urllib.request
        url = "https://en.wikisource.org/wiki/The_Beale_Papers"
        req = urllib.request.Request(url, headers={"User-Agent": "BealeCiphers/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Look for cipher blocks - Wikisource may wrap in <pre> or list items
        # Cipher 1 is "THE LOCALITY OF THE VAULT" section; Cipher 3 is "NAMES AND RESIDENCES"
        if n == 1:
            marker = "THE LOCALITY OF THE VAULT"
        else:
            marker = "NAMES AND RESIDENCES"
        idx = html.find(marker)
        if idx == -1:
            return None
        snippet = html[idx:idx + 8000]
        # Extract first long comma-separated number sequence after marker
        match = re.search(r"(\d[\d,\s]{100,})", snippet)
        if not match:
            return None
        nums = _parse_csv_numbers(match.group(1))
        if len(nums) < 400:  # C1 has 520, C3 has 618
            return None
        return nums[:520] if n == 1 else nums[:618]
    except Exception:
        return None


def file_hash(nums: List[int]) -> str:
    content = ",".join(str(x) for x in nums)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def main():
    VARIANTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    registry = {"c1": {}, "c3": {}}
    inventory_lines = ["Phase 102 Variant Inventory", "=" * 50, ""]

    for cipher_num in [1, 3]:
        key = f"c{cipher_num}"
        # Canonical
        nums = load_canonical_cipher(cipher_num)
        fname = f"{key}_canonical.txt"
        path = VARIANTS_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(str(x) for x in nums))
        h = file_hash(nums)
        registry[key][fname] = {"source": "corpus/cipher*_numbers_canonical.txt", "length": len(nums),
                                 "min": min(nums), "max": max(nums), "hash": h}
        inventory_lines.append(f"{fname}: length={len(nums)}, min={min(nums)}, max={max(nums)}, hash={h}")
        inventory_lines.append(f"  source: corpus/cipher{cipher_num}_numbers_canonical.txt (derived)")
        inventory_lines.append("")

        # beale_papers
        nums_bp = load_beale_papers_cipher(cipher_num)
        fname_bp = f"{key}_beale_papers.txt"
        path_bp = VARIANTS_DIR / fname_bp
        with open(path_bp, "w", encoding="utf-8") as f:
            f.write(",".join(str(x) for x in nums_bp))
        h_bp = file_hash(nums_bp)
        registry[key][fname_bp] = {"source": "beale_papers.txt", "length": len(nums_bp),
                                    "min": min(nums_bp), "max": max(nums_bp), "hash": h_bp}
        inventory_lines.append(f"{fname_bp}: length={len(nums_bp)}, min={min(nums_bp)}, max={max(nums_bp)}, hash={h_bp}")
        inventory_lines.append("  source: beale_papers.txt (Ward 1885 pamphlet)")
        inventory_lines.append("")

        # FSU Burkardt
        nums_fsu = load_fsu_cipher(cipher_num)
        fname_fsu = f"{key}_fsu_burkardt.txt"
        path_fsu = VARIANTS_DIR / fname_fsu
        with open(path_fsu, "w", encoding="utf-8") as f:
            f.write(",".join(str(x) for x in nums_fsu))
        h_fsu = file_hash(nums_fsu)
        registry[key][fname_fsu] = {"source": "corpus/raw_sources/fsu/beale_cipher*.txt", "length": len(nums_fsu),
                                     "min": min(nums_fsu), "max": max(nums_fsu), "hash": h_fsu}
        inventory_lines.append(f"{fname_fsu}: length={len(nums_fsu)}, min={min(nums_fsu)}, max={max(nums_fsu)}, hash={h_fsu}")
        inventory_lines.append("  source: FSU Burkardt dataset")
        inventory_lines.append("")

        # Optional: Wikisource
        ws = try_fetch_wikisource_cipher(cipher_num)
        if ws is not None:
            fname_ws = f"{key}_wikisource.txt"
            path_ws = VARIANTS_DIR / fname_ws
            with open(path_ws, "w", encoding="utf-8") as f:
                f.write(",".join(str(x) for x in ws))
            h_ws = file_hash(ws)
            registry[key][fname_ws] = {"source": "Wikisource The Beale Papers", "length": len(ws),
                                       "min": min(ws), "max": max(ws), "hash": h_ws}
            inventory_lines.append(f"{fname_ws}: length={len(ws)}, min={min(ws)}, max={max(ws)}, hash={h_ws}")
            inventory_lines.append("  source: en.wikisource.org/wiki/The_Beale_Papers (fetched)")
            inventory_lines.append("")
        else:
            inventory_lines.append(f"{key}_wikisource: (fetch skipped or failed; using local sources only)")
            inventory_lines.append("")

    with open(VARIANTS_DIR / "registry.json", "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    with open(OUT / "variant_inventory.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(inventory_lines))

    print(f"Task 1: wrote {VARIANTS_DIR / 'registry.json'}, {OUT / 'variant_inventory.txt'}")
    print(f"  C1 sources: {list(registry['c1'].keys())}")
    print(f"  C3 sources: {list(registry['c3'].keys())}")


if __name__ == "__main__":
    main()
