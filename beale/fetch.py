"""Fetch candidate key texts from the web into a local cache.

Only this module touches the network. ``requests`` is imported lazily so the
rest of the package runs on the standard library alone.
"""

from __future__ import annotations

import re
from pathlib import Path

from .corpus import CACHE_DIR
from .keytext import KeyText, from_text

GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"

# National Archives transcription of the engrossed (Stone-engraved) DOI text.
STONE_DOI_URL = "https://www.archives.gov/founding-docs/declaration-transcript"


def _get(url: str, cache_dir: str | Path = CACHE_DIR) -> str:
    import requests  # lazy: optional dependency

    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.split("//", 1)[-1])[:120]
    path = cache / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    resp = requests.get(url, timeout=60, headers={"User-Agent": "beale-research/0.1"})
    resp.raise_for_status()
    path.write_text(resp.text, encoding="utf-8")
    return resp.text


def fetch_gutenberg(book_id: int, cache_dir: str | Path = CACHE_DIR) -> KeyText:
    raw = _get(GUTENBERG_URL.format(id=book_id), cache_dir)
    return from_text(_strip_gutenberg(raw), id=f"gutenberg_{book_id}", source="web")


def _strip_gutenberg(raw: str) -> str:
    start = re.search(r"\*\*\* START OF [^*]+\*\*\*", raw)
    end = re.search(r"\*\*\* END OF [^*]+\*\*\*", raw)
    return raw[start.end() if start else 0 : end.start() if end else len(raw)]


def fetch_stone_doi(cache_dir: str | Path = CACHE_DIR) -> KeyText:
    """The engrossed DOI text per the National Archives transcript page."""
    html = _get(STONE_DOI_URL, cache_dir)
    # crude but dependency-free: strip tags, take the span between the
    # opening words and the final words of the document text
    text = re.sub(r"<[^>]+>", " ", html)
    m_start = text.find("When in the Course of human events")
    m_end = text.find("our sacred Honor")
    if m_start == -1 or m_end == -1:
        raise ValueError("could not locate DOI text in archives.gov page")
    return from_text(text[m_start : m_end + len("our sacred Honor")],
                     id="stone_doi_nara", source="web")
