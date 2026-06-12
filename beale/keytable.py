"""Beale's verified key table, reconstructed from Cipher 2's known plaintext.

For every number Beale used in Cipher 2, the plaintext pins the first letter
of that word in HIS key copy — no DOI edition assumptions. 177 of 180
numbers are perfectly self-consistent across all their occurrences; the 3
conflicts (53, 84, 96) each deviate exactly once and majority-vote cleanly
(the deviations are cipher copy errors, e.g. 84 written where 85 was meant).

This table is ground truth for cross-cipher work: under a shared-key
hypothesis it pins 53% of Cipher 1's positions and 57% of Cipher 3's.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .data import BealeData
from .oracle import known_c2_plaintext


@dataclass(frozen=True)
class KeyTableEntry:
    number: int
    letter: str
    occurrences: int
    agreements: int  # occurrences voting for the majority letter

    @property
    def confidence(self) -> float:
        return self.agreements / self.occurrences


@dataclass(frozen=True)
class KeyTable:
    entries: dict[int, KeyTableEntry]

    def letter(self, number: int) -> str | None:
        e = self.entries.get(number)
        return e.letter if e else None

    def as_overrides(self, min_occurrences: int = 1) -> dict[int, str]:
        """Plug directly into engine.DecodeConfig.overrides."""
        return {
            n: e.letter
            for n, e in self.entries.items()
            if e.occurrences >= min_occurrences
        }

    def coverage(self, numbers: tuple[int, ...]) -> float:
        return sum(1 for n in numbers if n in self.entries) / len(numbers)

    @property
    def verified(self) -> dict[int, KeyTableEntry]:
        """Entries seen 2+ times (cross-checked, not just read off once)."""
        return {n: e for n, e in self.entries.items() if e.occurrences >= 2}


def reconstruct(data: BealeData) -> KeyTable:
    plaintext = known_c2_plaintext()
    votes: dict[int, Counter] = {}
    for num, letter in zip(data.cipher2, plaintext):
        votes.setdefault(num, Counter())[letter] += 1
    entries = {}
    for num, c in votes.items():
        letter, agree = c.most_common(1)[0]
        entries[num] = KeyTableEntry(
            number=num, letter=letter, occurrences=sum(c.values()), agreements=agree
        )
    return KeyTable(entries=entries)
