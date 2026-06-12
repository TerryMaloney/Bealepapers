"""Key-text edits and cipher-number overrides.

Two deliberately separate mechanisms (pitfall #3):

* ``WordEdit`` mutates the *key text* (insert/delete/replace a word), which
  shifts the indices of every later word. Used to reconcile DOI editions.
* An *override map* sends a specific cipher number straight to a letter
  without touching the key text. Used for the documented C2 homophones
  (811 -> 'y', 1005 -> 'x'; the DOI has no x-/y-initial words).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

_RESOURCES = Path(__file__).parent / "resources"


@dataclass(frozen=True)
class WordEdit:
    op: str  # "insert" | "delete" | "replace"
    at: int  # 1-indexed word position in the current list
    word: str | None = None


def apply_edits(tokens: Sequence[str], edits: Sequence[WordEdit]) -> tuple[str, ...]:
    out = list(tokens)
    for e in edits:
        i = e.at - 1
        if e.op == "insert":
            out.insert(i, e.word or "")
        elif e.op == "delete":
            del out[i]
        elif e.op == "replace":
            out[i] = e.word or ""
        else:
            raise ValueError(f"unknown edit op: {e.op!r}")
    return tuple(out)


def load_overrides(path: str | Path | None = None) -> dict[int, str]:
    p = Path(path) if path else _RESOURCES / "overrides_c2.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {int(k): v for k, v in raw["overrides"].items()}
