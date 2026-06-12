"""Parse the three Beale ciphers and the numbered DOI from beale_papers.txt.

Layout of beale_papers.txt (0-indexed physical lines):
  line 2   Cipher 1 numbers  ("THE LOCALITY OF THE VAULT. [1]")
  line 6   Cipher 3 numbers  (header reads "NAMES AND RESIDENCES. [3]")
  line 54  the Declaration of Independence with inline word numbers,
           tokens shaped like ``word(N)`` plus the quirk ``and(&)(908)``
  line 58  Cipher 2 numbers
  lines 62-66  the pamphlet's prettified rendering of the C2 plaintext
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CIPHER1_LINE = 2
CIPHER3_LINE = 6
DOI_LINE = 54
CIPHER2_LINE = 58

EXPECTED = {
    "cipher1": {"count": 520, "max": 2906},
    "cipher2": {"count": 763, "max": 1005},
    "cipher3": {"count": 618, "max": 975},
    "doi_words": 1322,
}

# A word followed by one or more parenthetical groups, e.g. ``When(1)`` or
# ``and(&)(908)``. The integer index lives in one of the groups.
_DOI_TOKEN_RE = re.compile(r"([^\s()]+)((?:\([^)]*\))+)")
_INDEX_RE = re.compile(r"\((\d+)\)")


class BealeDataError(ValueError):
    """Raised when beale_papers.txt does not parse to the expected shape."""


@dataclass(frozen=True)
class BealeData:
    cipher1: tuple[int, ...]
    cipher2: tuple[int, ...]
    cipher3: tuple[int, ...]
    doi_words: tuple[str, ...]  # doi_words[0] is DOI word #1
    pamphlet_c2_plaintext: str  # raw prettified rendering from the pamphlet

    def cipher_for(self, name: str) -> tuple[int, ...]:
        try:
            return {"C1": self.cipher1, "C2": self.cipher2, "C3": self.cipher3}[name]
        except KeyError:
            raise BealeDataError(f"unknown cipher name: {name!r}") from None


def normalize_word(word: str) -> str:
    """Lowercase and strip everything but letters.

    Pinned normalization used for both key-text words and ground-truth
    plaintext so the two sides always agree (pitfall #6).
    """
    return re.sub(r"[^a-z]", "", word.lower())


def parse_cipher_line(line: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", line))


def parse_numbered_doi(line: str) -> tuple[str, ...]:
    """Extract the ordered DOI word list from the inline-numbered text.

    Words are returned normalized. The printed indices are validated to be
    contiguous 1..N; positional order is authoritative.
    """
    words: list[str] = []
    indices: list[int] = []
    for word, parens in _DOI_TOKEN_RE.findall(line):
        m = _INDEX_RE.search(parens)
        if not m:
            raise BealeDataError(f"DOI token {word!r}{parens!r} has no integer index")
        norm = normalize_word(word)
        if not norm:
            raise BealeDataError(f"DOI token {word!r} normalizes to empty")
        words.append(norm)
        indices.append(int(m.group(1)))
    if indices != list(range(1, len(indices) + 1)):
        gaps = [
            (want, got)
            for want, got in zip(range(1, len(indices) + 1), indices)
            if want != got
        ][:5]
        raise BealeDataError(f"DOI printed indices not contiguous; first gaps: {gaps}")
    return tuple(words)


def load_beale(path: str | Path = "beale_papers.txt") -> BealeData:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    data = BealeData(
        cipher1=parse_cipher_line(lines[CIPHER1_LINE]),
        cipher2=parse_cipher_line(lines[CIPHER2_LINE]),
        cipher3=parse_cipher_line(lines[CIPHER3_LINE]),
        doi_words=parse_numbered_doi(lines[DOI_LINE]),
        pamphlet_c2_plaintext="\n".join(lines[62:67]).strip(),
    )
    validate(data)
    return data


def validate(data: BealeData) -> None:
    for name in ("cipher1", "cipher2", "cipher3"):
        nums = getattr(data, name)
        want = EXPECTED[name]
        if len(nums) != want["count"]:
            raise BealeDataError(f"{name}: expected {want['count']} numbers, got {len(nums)}")
        if max(nums) != want["max"]:
            raise BealeDataError(f"{name}: expected max {want['max']}, got {max(nums)}")
        if min(nums) < 1:
            raise BealeDataError(f"{name}: cipher numbers must be >= 1")
    if len(data.doi_words) != EXPECTED["doi_words"]:
        raise BealeDataError(
            f"DOI: expected {EXPECTED['doi_words']} words, got {len(data.doi_words)}"
        )
    # Sentinel words that catch tokenization drift (1-indexed: 811, 908, 1005).
    sentinels = {810: "taking", 907: "and", 1004: "petitioned"}
    for idx, want in sentinels.items():
        got = data.doi_words[idx]
        if got != want:
            raise BealeDataError(f"DOI word #{idx + 1}: expected {want!r}, got {got!r}")
