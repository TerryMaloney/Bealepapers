"""
Phase 102 Task 3: Alignment of cipher variants.

Needleman-Wunsch for integer sequences. Output disagreement CSVs and alignment summary.
"""

import csv
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VARIANTS_DIR = PROJECT_ROOT / "corpus" / "cipher_variants"
OUT = PROJECT_ROOT / "output" / "phase102"

MATCH_SCORE = 1
MISMATCH_PENALTY = -1
GAP_PENALTY = -1


def nw_int(seq_a: List[int], seq_b: List[int]) -> Tuple[List[Any], List[Any]]:
    """Needleman-Wunsch for integer sequences. Returns (aligned_a, aligned_b) with None for gap."""
    m, n = len(seq_a), len(seq_b)
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
            aligned_b.append(None)
            i -= 1
        else:
            aligned_a.append(None)
            aligned_b.append(seq_b[j - 1])
            j -= 1
    return list(reversed(aligned_a)), list(reversed(aligned_b))


def load_variant(path: Path) -> List[int]:
    raw = path.read_text(encoding="utf-8")
    return [int(x.strip()) for x in raw.replace("\n", ",").split(",") if x.strip().isdigit()]


def alignment_to_disagreements(
    aligned_a: List[Any], aligned_b: List[Any],
    name_a: str, name_b: str
) -> List[Dict[str, Any]]:
    """Convert alignment to list of disagreement rows (pos_canonical, values_by_source, majority_value, confidence, edit_ops)."""
    rows = []
    pos_canonical = 0
    for i, (a, b) in enumerate(zip(aligned_a, aligned_b)):
        if a is None and b is None:
            continue
        if a is not None:
            pos_canonical = i
        vals = {}
        if a is not None:
            vals[name_a] = a
        if b is not None:
            vals[name_b] = b
        if a == b and a is not None:
            rows.append({
                "pos_canonical": pos_canonical,
                "aligned_pos": i,
                "values_by_source": str(vals),
                "majority_value": a,
                "confidence": "match",
                "edit_ops": "M",
            })
            continue
        if a is None:
            edit_ops = "I"
            majority = b
            confidence = "insert_in_b"
        elif b is None:
            edit_ops = "D"
            majority = a
            confidence = "delete_from_b"
        else:
            edit_ops = "S"
            majority = a
            confidence = "substitute"
        rows.append({
            "pos_canonical": pos_canonical,
            "aligned_pos": i,
            "values_by_source": str(vals),
            "majority_value": majority,
            "confidence": confidence,
            "edit_ops": edit_ops,
        })
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # Load all C1 variants
    c1_sources = list(VARIANTS_DIR.glob("c1_*.txt"))
    c1_sources.sort(key=lambda p: p.name)
    c1_variants = {p.stem.replace("c1_", ""): load_variant(p) for p in c1_sources}

    # C1: use canonical as reference; align each other against canonical
    c1_canonical = load_variant(VARIANTS_DIR / "c1_canonical.txt")
    all_c1_disagreements = []
    for name, seq in c1_variants.items():
        if name == "canonical":
            continue
        al_a, al_b = nw_int(c1_canonical, seq)
        rows = alignment_to_disagreements(al_a, al_b, "canonical", name)
        for r in rows:
            if r["edit_ops"] != "M":
                r["source_pair"] = f"canonical_vs_{name}"
                all_c1_disagreements.append(r)

    # Build c1_disagreements.csv: one row per canonical position where any source disagrees
    c1_by_pos = {}
    for r in all_c1_disagreements:
        p = r["pos_canonical"]
        if p not in c1_by_pos:
            c1_by_pos[p] = {"pos_canonical": p, "values_by_source": [], "edit_ops": []}
        c1_by_pos[p]["values_by_source"].append(r["values_by_source"])
        c1_by_pos[p]["edit_ops"].append(r["edit_ops"])
    c1_disagree_list = []
    for p in sorted(c1_by_pos.keys()):
        v = c1_by_pos[p]
        vals_str = "; ".join(v["values_by_source"])
        ops_str = ",".join(v["edit_ops"])
        majority = c1_canonical[p] if p < len(c1_canonical) else ""
        c1_disagree_list.append({
            "pos_canonical": p,
            "aligned_pos": p,
            "values_by_source": vals_str,
            "majority_value": majority,
            "confidence": "disagree" if len(set(v["edit_ops"])) > 0 else "match",
            "edit_ops": ops_str,
        })
    with open(OUT / "c1_disagreements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pos_canonical", "aligned_pos", "values_by_source", "majority_value", "confidence", "edit_ops"])
        w.writeheader()
        w.writerows(c1_disagree_list if c1_disagree_list else [{"pos_canonical": -1, "aligned_pos": -1, "values_by_source": "none", "majority_value": "", "confidence": "no_disagreements", "edit_ops": ""}])

    # C1 alignment summary
    summary_lines = [
        "Phase 102 C1 Alignment Summary",
        "=" * 50,
        "",
        f"Canonical length: {len(c1_canonical)}",
        f"Sources aligned: {list(c1_variants.keys())}",
        "",
    ]
    if not all_c1_disagreements:
        summary_lines.append("FINDING: Zero disagreements between sources. beale_papers, FSU Burkardt, and canonical are identical.")
        summary_lines.append("Alignment is trivial. Phase 102 discriminating power rests on 4-digit merge/split hypothesis.")
    else:
        summary_lines.append(f"Disagreements: {len(c1_disagree_list)} positions")
        for r in c1_disagree_list[:20]:
            summary_lines.append(f"  pos {r['pos_canonical']}: {r['values_by_source']} ops={r['edit_ops']}")
    with open(OUT / "c1_alignment_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    # C3
    c3_sources = list(VARIANTS_DIR.glob("c3_*.txt"))
    c3_sources.sort(key=lambda p: p.name)
    c3_variants = {p.stem.replace("c3_", ""): load_variant(p) for p in c3_sources}
    c3_canonical = load_variant(VARIANTS_DIR / "c3_canonical.txt")
    all_c3_disagreements = []
    for name, seq in c3_variants.items():
        if name == "canonical":
            continue
        al_a, al_b = nw_int(c3_canonical, seq)
        rows = alignment_to_disagreements(al_a, al_b, "canonical", name)
        for r in rows:
            if r["edit_ops"] != "M":
                all_c3_disagreements.append(r)
    c3_by_pos = {}
    for r in all_c3_disagreements:
        p = r["pos_canonical"]
        if p not in c3_by_pos:
            c3_by_pos[p] = {"pos_canonical": p, "values_by_source": [], "edit_ops": []}
        c3_by_pos[p]["values_by_source"].append(r["values_by_source"])
        c3_by_pos[p]["edit_ops"].append(r["edit_ops"])
    c3_disagree_list = []
    for p in sorted(c3_by_pos.keys()):
        v = c3_by_pos[p]
        c3_disagree_list.append({
            "pos_canonical": p,
            "aligned_pos": p,
            "values_by_source": "; ".join(v["values_by_source"]),
            "majority_value": c3_canonical[p] if p < len(c3_canonical) else "",
            "confidence": "disagree",
            "edit_ops": ",".join(v["edit_ops"]),
        })
    with open(OUT / "c3_disagreements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["pos_canonical", "aligned_pos", "values_by_source", "majority_value", "confidence", "edit_ops"])
        w.writeheader()
        w.writerows(c3_disagree_list)

    print(f"Task 3: wrote c1_disagreements.csv ({len(c1_disagree_list)} rows), c3_disagreements.csv ({len(c3_disagree_list)} rows), c1_alignment_summary.txt")


if __name__ == "__main__":
    main()
