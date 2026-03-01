"""
Phase 93 Step 1: Forensic audit of all prior phase artifacts.
Checks: existence, file size, modification time, content validity.
"""

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime

OUT = Path("output/phase93")
OUT.mkdir(parents=True, exist_ok=True)

EXPECTED = {
    "output/phase90": [
        "tricks_scanner_report.txt",
        "number_distribution_report.txt",
        "ic_simulation_v2_report.txt",
        "next_move_recommendation.txt",
    ],
    "output/dragnet_v1": [
        "calibration_check.txt",
        "cipher1_screen_ranked.csv",
        "cipher1_screen_top30.txt",
        "cipher3_screen_ranked.csv",
        "cipher3_screen_top30.txt",
        "triage_report.txt",
    ],
    "output/phase92": [
        "calibration.json",
        "calibration.txt",
        "c1_ranked.csv",
        "c3_ranked.csv",
        "triage_report.txt",
        "next_move.txt",
    ],
}


def audit():
    manifest = []
    missing = []
    suspect = []

    for directory, files in EXPECTED.items():
        for fname in files:
            fpath = Path(directory) / fname
            entry = {"path": str(fpath), "exists": fpath.exists()}

            if fpath.exists():
                stat = fpath.stat()
                entry["size_bytes"] = stat.st_size
                entry["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                entry["sha256"] = hashlib.sha256(fpath.read_bytes()).hexdigest()[:16]

                if stat.st_size == 0:
                    entry["status"] = "EMPTY_FILE"
                    suspect.append(str(fpath))
                elif stat.st_size < 50:
                    entry["status"] = "SUSPICIOUSLY_SMALL"
                    suspect.append(str(fpath))
                else:
                    entry["status"] = "OK"
            else:
                entry["status"] = "MISSING"
                entry["size_bytes"] = 0
                entry["modified"] = None
                entry["sha256"] = None
                missing.append(str(fpath))

            manifest.append(entry)

    # Check CSV row counts for ranked files
    for entry in manifest:
        if entry["path"].endswith("_ranked.csv") and entry["exists"]:
            with open(entry["path"], "r", encoding="utf-8") as f:
                lines = f.readlines()
            entry["csv_rows"] = len(lines) - 1  # minus header
            if entry["csv_rows"] < 5:
                entry["status"] = "TOO_FEW_ROWS"
                suspect.append(entry["path"])

    # Check for normalized keytext count
    norm_dir = Path("corpus/keytexts/normalized")
    norm_count = len(list(norm_dir.glob("*.json"))) if norm_dir.exists() else 0

    # Check registry
    reg_path = Path("corpus/keytexts/registry.json")
    reg_count = 0
    if reg_path.exists():
        with open(reg_path) as f:
            reg = json.load(f)
        reg_count = len(reg.get("keytexts", []))

    # Check for interactive blocking calls
    import subprocess
    result = subprocess.run(
        ["rg", "-l", r"input\(", "scripts/"],
        capture_output=True, text=True, cwd=str(Path.cwd())
    )
    interactive_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

    summary = {
        "audit_time": datetime.now().isoformat(),
        "total_expected": sum(len(v) for v in EXPECTED.values()),
        "found": sum(1 for e in manifest if e["exists"]),
        "missing": missing,
        "suspect": suspect,
        "normalized_keytexts": norm_count,
        "registry_entries": reg_count,
        "interactive_blocking_files": interactive_files,
        "manifest": manifest,
    }

    # Write JSON
    with open(OUT / "audit_manifest.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Write human-readable
    with open(OUT / "audit_manifest.txt", "w") as f:
        f.write(f"{'='*70}\n")
        f.write(f"PHASE 93 — FORENSIC AUDIT\n")
        f.write(f"Generated: {summary['audit_time']}\n")
        f.write(f"{'='*70}\n\n")

        f.write(f"Expected artifacts: {summary['total_expected']}\n")
        f.write(f"Found:             {summary['found']}\n")
        f.write(f"Missing:           {len(missing)}\n")
        f.write(f"Suspect:           {len(suspect)}\n")
        f.write(f"Normalized keytexts: {norm_count}\n")
        f.write(f"Registry entries:    {reg_count}\n\n")

        if missing:
            f.write("MISSING FILES:\n")
            for m in missing:
                f.write(f"  !! {m}\n")
            f.write("\n")
        else:
            f.write("NO MISSING FILES — all expected artifacts exist.\n\n")

        if suspect:
            f.write("SUSPECT FILES (empty or very small):\n")
            for s in suspect:
                f.write(f"  ?? {s}\n")
            f.write("\n")

        if interactive_files:
            f.write("WARNING: Files with input() calls (potential interactive blocking):\n")
            for fi in interactive_files:
                f.write(f"  !! {fi}\n")
            f.write("\n")
        else:
            f.write("No interactive blocking calls found in scripts/.\n\n")

        f.write("ARTIFACT DETAILS:\n")
        f.write(f"{'Path':55s} {'Size':>8s} {'Status':15s} {'Modified':25s}\n")
        f.write("-" * 105 + "\n")
        for e in manifest:
            f.write(f"{e['path']:55s} {e['size_bytes']:>8d} {e['status']:15s} {str(e['modified'] or 'N/A'):25s}\n")

        f.write(f"\nVERDICT: {'ALL ARTIFACTS PRESENT' if not missing else 'MISSING ARTIFACTS — investigate'}\n")

    print(f"Audit: {OUT / 'audit_manifest.txt'}")
    print(f"  Expected: {summary['total_expected']}, Found: {summary['found']}, Missing: {len(missing)}")
    if interactive_files:
        print(f"  WARNING: interactive blocking in: {interactive_files}")
    return summary


if __name__ == "__main__":
    audit()
