"""Workstream K3: the key-document dossier — "Guess Who in reverse".

Everything inferable about the UNKNOWN key documents of Ciphers 1 and 3
from the cipher numbers alone, with confidence levels. Companion artifact
to the wanted poster: even without solving, these characteristics narrow
the archive search for the physical text(s).

Run:  python -m beale.exp_dossier   (writes runs/c3_dossier.md)
"""

from __future__ import annotations

import statistics
from collections import Counter
from pathlib import Path

from .data import load_beale
from .softskel import (calibrate_count_posteriors, refine_with_bigrams,
                       soft_skeleton)


def lag1(nums) -> float:
    mu = statistics.mean(nums)
    sd = statistics.pstdev(nums)
    return sum((a - mu) * (b - mu) for a, b in zip(nums, nums[1:])) / (
        (len(nums) - 1) * sd * sd)


def dossier_for(name: str, nums, post) -> list[str]:
    counts = Counter(nums)
    # per-index posteriors: count buckets sharpened by positional context
    skel = refine_with_bigrams(list(nums), soft_skeleton(nums, post))
    mx = max(nums)
    # density tail: how much of the top decile of the range is actually used
    used_hi = sum(1 for v in set(nums) if v > 0.9 * mx)
    lines = [f"## Cipher {name[-1]} key document", ""]
    lines.append(f"- **Length**: at least {mx} words"
                 f" (highest index used). Usage density in the top decile "
                 f"of the range: {used_hi} distinct indices — "
                 + ("the document likely ends near word "
                    f"{mx} (dense usage to the edge)." if used_hi >= 8 else
                    "sparse near the top; the document may extend well "
                    f"beyond word {mx}."))
    lines.append(f"- **Indices used**: {len(counts)} distinct of "
                 f"{len(nums)} positions; "
                 f"{sum(1 for v in counts.values() if v == 1)} used once.")
    z = lag1(list(nums))
    lines.append(f"- **Usage habit**: lag-1 number autocorrelation "
                 f"{z:+.2f} — " + (
                     "the encoder worked LOCALLY, drifting through nearby "
                     "words rather than jumping freely (unlike the C2 "
                     "encoder, who jumped)." if z > 0.15 else
                     "no locality; indices jump freely (like C2)."))
    lines.append("- **Most-consulted words** (count -> most likely "
                 "initials, calibrated on C2's verified key):")
    top = sorted(counts.items(), key=lambda x: -x[1])[:20]
    for n, k in top:
        dist = skel.get(n)
        if not dist:
            continue
        best = sorted(dist.items(), key=lambda x: -x[1])[:3]
        probs = ", ".join(f"{ch} ({p:.0%})" for ch, p in best)
        lines.append(f"    - word #{n} (used {k}x): starts with {probs}")
    lines.append("")
    return lines


def main() -> None:
    data = load_beale()
    post = calibrate_count_posteriors(data)
    out = [
        "# Key-document dossier — what the cipher numbers alone reveal",
        "",
        "*Method: count->letter posteriors calibrated on Cipher 2's verified",
        "key table; structural statistics vs the known-genuine C2 baseline.*",
        "",
    ]
    out += dossier_for("C3", data.cipher3, post)
    out += dossier_for("C1", data.cipher1, post)
    out += [
        "## Cross-cutting verdicts (phase 4)",
        "",
        "- Repeated-pattern test: genuine encoding (C2) leaves repeated",
        "  number n-grams that decode to top English bigrams (ed, ve, th,",
        "  in / her, nds, ove); **C1 and C3 contain none** (z ~ 0). Number",
        "  VALUE locality without PATTERN repetition is the opposite of",
        "  what encoded English produced for this encoder.",
        "- Soft fingerprint matcher: validated to rank the true key #1 on",
        "  C2's numbers alone, but with sub-threshold margin; C3/C1 scans",
        "  produced no lead separating from noise.",
        "- If C3 encodes anything by first letters, its key is an",
        "  alphabetized or locally-scanned word list rather than prose",
        "  consulted at random — see the dictionary-key attack verdict.",
    ]
    p = Path("runs/c3_dossier.md")
    p.parent.mkdir(exist_ok=True)
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out[:40]))
    print(f"\n... written to {p}")


if __name__ == "__main__":
    main()
