"""Uniform candidate key-text model and loaders."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .data import BealeData, normalize_word


@dataclass(frozen=True)
class KeyText:
    id: str
    tokens: tuple[str, ...]  # tokens[0] is word #1
    source: str  # "normalized_json" | "edition" | "embedded_doi" | "web" | "stack"
    meta: dict = field(default_factory=dict, compare=False)

    def __len__(self) -> int:
        return len(self.tokens)


def from_normalized_json(path: str | Path) -> KeyText:
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    return KeyText(
        id=raw.get("id", p.stem),
        tokens=tuple(raw["tokens"]),
        source="normalized_json",
        meta={"path": str(p)},
    )


def from_text(text: str, id: str, source: str = "edition") -> KeyText:
    tokens = tuple(t for t in (normalize_word(w) for w in text.split()) if t)
    return KeyText(id=id, tokens=tokens, source=source)


def from_text_file(path: str | Path, source: str = "edition") -> KeyText:
    p = Path(path)
    return from_text(p.read_text(encoding="utf-8"), id=p.stem, source=source)


def from_doi(data: BealeData) -> KeyText:
    return KeyText(id="embedded_doi", tokens=data.doi_words, source="embedded_doi")
