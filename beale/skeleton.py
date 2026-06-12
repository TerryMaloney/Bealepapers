"""Key-document skeleton: reverse-engineering the key text from plaintext.

In a book cipher every accepted (number -> letter) hypothesis pins the
first letter of key-document word #number. Accumulate pins and you get a
first-letter fingerprint of the key document itself — enough of one and an
unknown key text (e.g. a pamphlet we don't possess) becomes identifiable
by sliding the skeleton across digitized candidates (see fingerprint.py).

The skeleton is rebuilt from an append-only ledger so any crib can be
retracted and everything downstream recomputed.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Crib:
    """One hypothesis: cipher positions -> plaintext fragment."""

    id: str
    cipher: str               # "c1" | "c2" | "c3"
    start: int                # 0-based cipher position
    text: str                 # hypothesized plaintext letters
    source: str = "human"     # "human" | "c2table" | "solver:<run>"
    retracted: bool = False


@dataclass
class Skeleton:
    votes: dict[int, Counter] = field(default_factory=dict)   # word idx -> letters
    provenance: dict[int, list[str]] = field(default_factory=dict)

    def add(self, index: int, letter: str, crib_id: str) -> None:
        self.votes.setdefault(index, Counter())[letter] += 1
        self.provenance.setdefault(index, []).append(crib_id)

    def pin(self, index: int, min_share: float = 0.8) -> str | None:
        c = self.votes.get(index)
        if not c:
            return None
        letter, k = c.most_common(1)[0]
        return letter if k / sum(c.values()) >= min_share else None

    def pins(self) -> dict[int, str]:
        out = {}
        for idx in self.votes:
            letter = self.pin(idx)
            if letter:
                out[idx] = letter
        return out

    def conflicts(self) -> dict[int, Counter]:
        return {i: c for i, c in self.votes.items() if len(c) > 1}

    def consistency(self) -> float:
        """Weighted fraction of votes agreeing with their index majority."""
        agree = total = 0
        for c in self.votes.values():
            k = sum(c.values())
            agree += c.most_common(1)[0][1]
            total += k
        return agree / total if total else 1.0

    def as_overrides(self) -> dict[int, str]:
        """Plug into engine.DecodeConfig.overrides (1-based numbers)."""
        return self.pins()


def build_skeleton(cribs: list[Crib], numbers_of: dict[str, tuple[int, ...]],
                   ) -> Skeleton:
    sk = Skeleton()
    for crib in cribs:
        if crib.retracted:
            continue
        nums = numbers_of[crib.cipher]
        for j, letter in enumerate(crib.text):
            pos = crib.start + j
            if 0 <= pos < len(nums):
                sk.add(nums[pos], letter, crib.id)
    return sk


def c2_table_cribs(data) -> list[Crib]:
    """The entire known C2 plaintext as one verified crib."""
    from .oracle import known_c2_plaintext

    return [Crib(id="c2:known-plaintext", cipher="c2", start=0,
                 text=known_c2_plaintext(), source="c2table")]


# ---------------------------------------------------------------- ledger --

LEDGER_DIR = Path("runs")


def ledger_path(cipher: str) -> Path:
    return LEDGER_DIR / f"skeleton_{cipher}.jsonl"


def append_crib(crib: Crib) -> None:
    LEDGER_DIR.mkdir(exist_ok=True)
    with open(ledger_path(crib.cipher), "a", encoding="utf-8") as f:
        rec = crib.__dict__ | {"ts": time.time()}
        f.write(json.dumps(rec) + "\n")


def load_cribs(cipher: str) -> list[Crib]:
    p = ledger_path(cipher)
    if not p.exists():
        return []
    out: dict[str, Crib] = {}
    with open(p, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            rec.pop("ts", None)
            crib = Crib(**rec)
            out[crib.id] = crib  # later lines supersede (retraction)
    return list(out.values())
