"""Cipher 2 verification oracle — the correctness gate for the engine.

Cipher 2 is the solved Beale cipher: number N -> Nth word of the Declaration
of Independence -> first letter. A correct engine must reproduce the known
plaintext. Three layers contribute:

* raw decode against the pamphlet's embedded DOI:        ~83.6%
* + key-text edits reconciling Beale's miscounted DOI:   ~91.5%
* + homophone overrides 811 -> 'y', 1005 -> 'x'          (included above)

The remaining ~8% mismatches are scattered single-letter transcription
errors in the surviving copy of the cipher (documented in the literature);
they do not cluster, which is the signature of a correct alignment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .data import BealeData, normalize_word
from .edits import WordEdit, apply_edits, load_overrides
from .engine import DecodeConfig, decode

_RESOURCES = Path(__file__).parent / "resources"

PASS_THRESHOLD = 0.90


def known_c2_plaintext() -> str:
    """The canonical 763-letter C2 plaintext, normalized to a-z."""
    return normalize_word((_RESOURCES / "c2_plaintext.txt").read_text(encoding="utf-8"))


def load_doi_edits(path: str | Path | None = None) -> list[WordEdit]:
    p = Path(path) if path else _RESOURCES / "doi_edits_c2.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    return [WordEdit(e["op"], e["at"], e.get("word")) for e in raw["edits"]]


@dataclass(frozen=True)
class OracleReport:
    decoded: str
    expected: str
    matches: int
    total: int
    mismatches: tuple[tuple[int, str, str], ...]  # (position, got, want)
    n_oor: int

    @property
    def exact_pct(self) -> float:
        return self.matches / self.total if self.total else 0.0

    @property
    def passed(self) -> bool:
        return self.exact_pct >= PASS_THRESHOLD


def verify_cipher2(
    data: BealeData,
    use_edits: bool = True,
    use_overrides: bool = True,
) -> OracleReport:
    tokens = data.doi_words
    if use_edits:
        tokens = apply_edits(tokens, load_doi_edits())
    overrides = load_overrides() if use_overrides else {}
    res = decode(data.cipher2, tokens, DecodeConfig(overrides=overrides))
    expected = known_c2_plaintext()
    if len(expected) != len(data.cipher2):
        raise ValueError(
            f"ground truth is {len(expected)} letters, cipher has {len(data.cipher2)}"
        )
    mismatches = tuple(
        (i, got, want)
        for i, (got, want) in enumerate(zip(res.text, expected))
        if got != want
    )
    return OracleReport(
        decoded=res.text,
        expected=expected,
        matches=len(expected) - len(mismatches),
        total=len(expected),
        mismatches=mismatches,
        n_oor=res.n_oor,
    )
