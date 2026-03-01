"""
Phase 100 Task D: Beacon lexicon scan over candidate decoded streams.

Scans all available decoded streams from prior phases for directional,
surveying, terrain, and burial words. Compares hit rate against random
shuffled controls.

Output: output/phase100/beacon_hits_top200.csv
"""

import csv
import glob
import random
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scoring.lexicon_beacons import scan_beacons, beacon_summary
from constraints.overlap_engine import load_cipher
from corpus.beale_doi_adjusted import get_adjusted_tokens

OUT = PROJECT_ROOT / "output" / "phase100"
SEED_BEACON = 88001
N_CONTROL = 200


def load_stream_from_file(path: Path) -> str:
    """Extract letter stream from a top_streams/*.txt file."""
    lines = path.read_text(encoding="utf-8", errors="replace").strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 50 and stripped.isalpha():
            return stripped
    if len(lines) > 5:
        candidate = lines[-1].strip()
        if len(candidate) > 30:
            return "".join(c for c in candidate if c.isalpha())
    return ""


def load_stream_from_csv(path: Path, col: str = "stream_preview") -> List[Dict]:
    """Load streams from ranked CSVs."""
    results = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stream = row.get(col, row.get("stream", "")).strip()
                if len(stream) > 30:
                    label = "|".join(row.get(k, "") for k in ["bundle", "cipher", "extractor"]
                                     if k in row and row[k])
                    if not label:
                        label = "|".join(row.get(k, "") for k in reader.fieldnames[:3] if row.get(k))
                    results.append({"source": path.name, "label": label, "stream": stream})
    except Exception:
        pass
    return results


def collect_streams() -> List[Dict]:
    """Collect all available decoded streams from prior phases."""
    streams = []

    # DOI first-letter decode for C1, C2, C3
    tokens = get_adjusted_tokens()
    for cn, name in [(1, "c1"), (2, "c2"), (3, "c3")]:
        nums = load_cipher(cn)
        s = ""
        for n in nums:
            idx = n - 1
            if 0 <= idx < len(tokens) and tokens[idx]:
                s += tokens[idx][0].upper()
            else:
                s += "?"
        s = s.replace("?", "")
        streams.append({"source": f"doi_first_letter_{name}", "label": f"doi_adjusted_{name}", "stream": s})

    # top_streams from phase92, phase93, phase98
    for phase_dir in ["phase92", "phase93", "phase98"]:
        ts_dir = PROJECT_ROOT / "output" / phase_dir / "top_streams"
        if not ts_dir.exists():
            continue
        for f in sorted(ts_dir.glob("*.txt"))[:30]:
            s = load_stream_from_file(f)
            if s and len(s) > 50:
                streams.append({"source": f"{phase_dir}/{f.name}", "label": f.stem, "stream": s})

    # Ranked CSVs
    for csv_path in [
        PROJECT_ROOT / "output" / "phase92" / "c1_ranked.csv",
        PROJECT_ROOT / "output" / "phase92" / "c3_ranked.csv",
        PROJECT_ROOT / "output" / "phase93" / "quick_hypotheses_ranked.csv",
        PROJECT_ROOT / "output" / "phase98" / "bundle_decode_ranked_c1.csv",
        PROJECT_ROOT / "output" / "phase98" / "bundle_decode_ranked_c3.csv",
    ]:
        if csv_path.exists():
            streams.extend(load_stream_from_csv(csv_path)[:10])

    return streams


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    streams = collect_streams()
    print(f"Collected {len(streams)} candidate streams")

    rng = random.Random(SEED_BEACON)
    rows = []
    for entry in streams:
        stream = entry["stream"]
        if len(stream) < 30:
            continue
        summ = beacon_summary(stream)

        # Control: shuffle stream N_CONTROL times, compute mean beacon hits
        ctrl_hits = []
        letters = list(stream)
        for _ in range(N_CONTROL):
            rng.shuffle(letters)
            cs = beacon_summary("".join(letters))
            ctrl_hits.append(cs["total_hits"])
        ctrl_mean = sum(ctrl_hits) / len(ctrl_hits) if ctrl_hits else 0
        ctrl_std = (sum((x - ctrl_mean) ** 2 for x in ctrl_hits) / len(ctrl_hits)) ** 0.5 if ctrl_hits else 1

        z = (summ["total_hits"] - ctrl_mean) / ctrl_std if ctrl_std > 0 else 0

        rows.append({
            "source": entry["source"],
            "label": entry["label"],
            "stream_len": len(stream),
            "total_hits": summ["total_hits"],
            "unique_beacons": summ["unique_beacons"],
            "density_per_100": summ["density_per_100"],
            "ctrl_mean_hits": round(ctrl_mean, 2),
            "ctrl_std_hits": round(ctrl_std, 2),
            "z_vs_ctrl": round(z, 4),
            "beacons_found": "; ".join(summ["beacon_list"][:15]),
        })

    rows.sort(key=lambda r: r["z_vs_ctrl"], reverse=True)

    path = OUT / "beacon_hits_top200.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows[:200])
    print(f"Saved {path} ({min(len(rows), 200)} of {len(rows)} rows)")

    # Print top 10
    print("\nTop 10 by z-score vs control:")
    for r in rows[:10]:
        print(f"  z={r['z_vs_ctrl']:+.2f}  hits={r['total_hits']}  "
              f"unique={r['unique_beacons']}  {r['source']}: {r['label']}")

    return rows


if __name__ == "__main__":
    main()
