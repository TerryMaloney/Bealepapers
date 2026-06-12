"""Iterate candidate key texts and build document stacks for Cipher 1."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from .keytext import KeyText, from_normalized_json

DEFAULT_CORPUS_DIR = Path("corpus/keytexts/normalized")
CACHE_DIR = Path("corpus/cache")

# Pre-built concatenations from the legacy corpus; skip as primary candidates
# (their components are tested individually and via document_stack).
_SKIP = {"bundle_b1", "bundle_b2", "bundle_b3"}


def iter_corpus(
    corpus_dir: str | Path = DEFAULT_CORPUS_DIR, min_tokens: int = 0
) -> Iterator[KeyText]:
    for p in sorted(Path(corpus_dir).glob("*.json")):
        if p.stem in _SKIP:
            continue
        try:
            kt = from_normalized_json(p)
        except (KeyError, ValueError):
            continue
        if len(kt) >= min_tokens:
            yield kt


def document_stack(keytexts: list[KeyText], id: str | None = None) -> KeyText:
    """Concatenate key texts; segment boundaries are recorded in meta."""
    tokens: list[str] = []
    boundaries: list[tuple[str, int, int]] = []  # (id, start_word_1idx, end_word_1idx)
    for kt in keytexts:
        start = len(tokens) + 1
        tokens.extend(kt.tokens)
        boundaries.append((kt.id, start, len(tokens)))
    return KeyText(
        id=id or "+".join(kt.id for kt in keytexts),
        tokens=tuple(tokens),
        source="stack",
        meta={"boundaries": boundaries},
    )
