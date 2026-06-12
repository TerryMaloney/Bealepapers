"""Book-cipher decode engine. Pure functions, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .data import normalize_word

OOR_CHAR = "?"


@dataclass(frozen=True)
class DecodeConfig:
    extraction: str = "first"  # "first" | "last" | "nth"
    nth: int = 1  # 1-indexed letter position, for extraction == "nth"
    index_base: int = 1  # cipher numbers are 1-indexed into the key
    offset: int = 0
    overrides: Mapping[int, str] = field(default_factory=dict)  # cipher number -> letter
    oor: str = OOR_CHAR


@dataclass(frozen=True)
class DecodeResult:
    text: str
    n_oor: int
    n_total: int

    @property
    def oor_fraction(self) -> float:
        return self.n_oor / self.n_total if self.n_total else 0.0


def extract_letter(word: str, cfg: DecodeConfig) -> str | None:
    w = normalize_word(word)
    if not w:
        return None
    if cfg.extraction == "first":
        return w[0]
    if cfg.extraction == "last":
        return w[-1]
    if cfg.extraction == "nth":
        return w[cfg.nth - 1] if len(w) >= cfg.nth else None
    raise ValueError(f"unknown extraction rule: {cfg.extraction!r}")


def decode(
    numbers: Sequence[int], tokens: Sequence[str], cfg: DecodeConfig | None = None
) -> DecodeResult:
    """Decode a number stream against a key text.

    Out-of-range numbers and empty extractions emit ``cfg.oor`` so output
    positions always align 1:1 with the cipher (pitfall #5).
    """
    cfg = cfg or DecodeConfig()
    letters: list[str] = []
    n_oor = 0
    for num in numbers:
        if num in cfg.overrides:
            letters.append(cfg.overrides[num])
            continue
        idx = (num - cfg.index_base) + cfg.offset
        if idx < 0 or idx >= len(tokens):
            letters.append(cfg.oor)
            n_oor += 1
            continue
        ch = extract_letter(tokens[idx], cfg)
        if ch is None:
            letters.append(cfg.oor)
            n_oor += 1
        else:
            letters.append(ch)
    return DecodeResult(text="".join(letters), n_oor=n_oor, n_total=len(numbers))
