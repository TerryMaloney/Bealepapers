"""Quadgram statistics for English-likeness scoring.

Stats are shipped as a committed resource (``resources/quadgrams.txt``,
``QUADGRAM count`` per line) generated offline from public-domain English
already in the repo corpus — no runtime fetch. Regenerate with:

    python -m beale.ngrams
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

_RESOURCES = Path(__file__).parent / "resources"
_DEFAULT_PATH = _RESOURCES / "quadgrams.txt"


class Quadgrams:
    def __init__(self, counts: dict[str, int]):
        total = sum(counts.values())
        self._logp = {q: math.log10(c / total) for q, c in counts.items()}
        self._floor = math.log10(0.01 / total)

    @classmethod
    def load(cls, path: str | Path = _DEFAULT_PATH) -> "Quadgrams":
        counts: dict[str, int] = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                q, c = line.split()
                counts[q] = int(c)
        return cls(counts)

    @classmethod
    def build_from_text(cls, text: str) -> "Quadgrams":
        return cls(count_quadgrams(text))

    def score(self, text: str) -> float:
        """Mean log10 probability per quadgram. Higher = more English.

        Typical values: real English about -3.4 to -3.8; uniform-random
        letters about -5.5 or below. Positions with non-letters (e.g. the
        out-of-range placeholder '?') break the quadgram window.
        """
        n = 0
        total = 0.0
        for i in range(len(text) - 3):
            q = text[i : i + 4]
            if not q.isalpha():
                continue
            total += self._logp.get(q.upper(), self._floor)
            n += 1
        return total / n if n else self._floor


def count_quadgrams(text: str) -> Counter:
    counts: Counter = Counter()
    # split on non-letters so quadgrams never span word-stream breaks
    for chunk in _letter_chunks(text):
        for i in range(len(chunk) - 3):
            counts[chunk[i : i + 4]] += 1
    return counts


def _letter_chunks(text: str):
    chunk = []
    for ch in text.upper():
        if "A" <= ch <= "Z":
            chunk.append(ch)
        elif chunk:
            yield "".join(chunk)
            chunk = []
    if chunk:
        yield "".join(chunk)


def _regenerate(corpus_dir: str = "corpus/keytexts/normalized") -> None:
    """Rebuild resources/quadgrams.txt from the repo's keytext corpus."""
    import json

    sources = [
        "bible_asv.json",
        "decline_fall_rome_v1.json",
        "pride_prejudice.json",
        "common_sense.json",
        "autobiography_franklin.json",
        "last_of_the_mohicans.json",
        "ivanhoe.json",
    ]
    counts: Counter = Counter()
    used = []
    for name in sources:
        p = Path(corpus_dir) / name
        if not p.exists():
            continue
        tokens = json.loads(p.read_text(encoding="utf-8"))["tokens"]
        # Concatenate WITHOUT spaces: decoded ciphers are continuous letter
        # streams, so the reference must include cross-word quadgrams.
        counts.update(count_quadgrams("".join(tokens)))
        used.append(name)
    _DEFAULT_PATH.write_text(
        "".join(f"{q} {c}\n" for q, c in sorted(counts.items())), encoding="utf-8"
    )
    print(f"wrote {len(counts)} quadgrams from {len(used)} sources -> {_DEFAULT_PATH}")


if __name__ == "__main__":
    _regenerate()
