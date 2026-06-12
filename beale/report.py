"""Plaintext-first reporting: every solver's output is rendered as aligned,
human-readable candidate text so forming sentences can be eyeballed.

Rendering rules:
* PINNED letters (verified, e.g. from the C2 key table) -> UPPERCASE
* HYPOTHESIS / SOLVER letters -> lowercase
* UNKNOWN -> the middle dot

Each 60-character block shows a 1-based position ruler, the text, a
confidence glyph line (' .:*#' quintiles), and dictionary-segmentation
marks so half-formed words pop out visually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from .scoring import ScoreReport, letters_only

UNKNOWN_CHAR = "·"  # ·
_CONF_GLYPHS = " .:*#"
BLOCK = 60


class Tier(IntEnum):
    UNKNOWN = 0
    SOLVER = 1
    HYPOTHESIS = 2
    PINNED = 3


@dataclass(frozen=True)
class AnnotatedText:
    chars: str  # a-z or UNKNOWN_CHAR; 1:1 with cipher positions
    conf: tuple[float, ...]
    tier: tuple[Tier, ...]
    label: str
    scores: ScoreReport | None = None
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        assert len(self.chars) == len(self.conf) == len(self.tier)

    @property
    def coverage(self) -> float:
        known = sum(1 for c in self.chars if c != UNKNOWN_CHAR)
        return known / len(self.chars) if self.chars else 0.0


def from_decode(
    text: str, tier: Tier = Tier.SOLVER, label: str = "", conf: float = 0.5,
    oor_char: str = "?", scores: ScoreReport | None = None, params: dict | None = None,
) -> AnnotatedText:
    chars, confs, tiers = [], [], []
    for ch in text:
        if ch == oor_char or ch == UNKNOWN_CHAR:
            chars.append(UNKNOWN_CHAR); confs.append(0.0); tiers.append(Tier.UNKNOWN)
        else:
            chars.append(ch.lower()); confs.append(conf); tiers.append(tier)
    return AnnotatedText("".join(chars), tuple(confs), tuple(tiers),
                         label, scores, params or {})


def merge_pins(base: AnnotatedText, pins: dict[int, str], conf: float = 1.0) -> AnnotatedText:
    """Overlay PINNED letters at given 0-based positions."""
    chars, confs, tiers = list(base.chars), list(base.conf), list(base.tier)
    for pos, letter in pins.items():
        chars[pos] = letter.lower()
        confs[pos] = conf
        tiers[pos] = Tier.PINNED
    return AnnotatedText("".join(chars), tuple(confs), tuple(tiers),
                         base.label, base.scores, base.params)


def dict_spans(text: str, words: frozenset[str], min_len: int = 3,
               max_len: int = 12) -> list[tuple[int, int]]:
    """Greedy longest-match dictionary spans over a rendered char string.

    Unknown characters break words. Returns (start, end) half-open spans.
    """
    spans = []
    i = 0
    n = len(text)
    while i < n:
        match = 0
        for ln in range(min(max_len, n - i), min_len - 1, -1):
            chunk = text[i : i + ln]
            if UNKNOWN_CHAR in chunk:
                continue
            if chunk.lower() in words:
                match = ln
                break
        if match:
            spans.append((i, i + match))
            i += match
        else:
            i += 1
    return spans


def render(at: AnnotatedText, words: frozenset[str] | None = None) -> str:
    from .scoring import default_wordlist

    words = words if words is not None else default_wordlist()
    display = "".join(
        c.upper() if t == Tier.PINNED and c != UNKNOWN_CHAR else c
        for c, t in zip(at.chars, at.tier)
    )
    spans = dict_spans(at.chars, words)
    span_line = [" "] * len(at.chars)
    for s, e in spans:
        for j in range(s, e):
            span_line[j] = "-"
        span_line[s] = "|"

    lines = []
    header = at.label
    if at.scores:
        header += (f"    quad {at.scores.quadgram:.2f}  ioc {at.scores.ioc:.3f}"
                   f"  dict {at.scores.dict_coverage:.2f}")
    header += f"  coverage {at.coverage:.0%}"
    lines.append(header)
    for start in range(0, len(display), BLOCK):
        block = display[start : start + BLOCK]
        ruler = "".join(
            str(((start + i) // 10) % 10) if (start + i) % 10 == 0 else " "
            for i in range(len(block))
        )
        confs = "".join(
            _CONF_GLYPHS[min(4, int(c * 5))] for c in at.conf[start : start + BLOCK]
        )
        lines.append(f"  pos {start:4d}  {ruler}")
        lines.append(f"            {block}")
        lines.append(f"            {confs}")
        lines.append(f"            {''.join(span_line[start : start + BLOCK])}")
    return "\n".join(lines)


def render_compare(ats: list[AnnotatedText], words: frozenset[str] | None = None) -> str:
    """Side-by-side hypotheses with a divergence marker line."""
    n = max(len(a.chars) for a in ats)
    out = []
    for start in range(0, n, BLOCK):
        for a in ats:
            seg = "".join(
                c.upper() if t == Tier.PINNED and c != UNKNOWN_CHAR else c
                for c, t in zip(a.chars[start : start + BLOCK],
                                a.tier[start : start + BLOCK])
            )
            out.append(f"  {a.label[:14]:14s} {seg}")
        cols = []
        for j in range(start, min(start + BLOCK, n)):
            vals = {a.chars[j] for a in ats if j < len(a.chars)
                    and a.chars[j] != UNKNOWN_CHAR}
            cols.append("^" if len(vals) > 1 else " ")
        out.append(f"  {'':14s} {''.join(cols)}")
        out.append("")
    for a in ats:
        if a.scores:
            out.append(f"  {a.label[:14]:14s} quad {a.scores.quadgram:7.3f}  "
                       f"ioc {a.scores.ioc:.4f}  dict {a.scores.dict_coverage:.2f}")
    return "\n".join(out)
