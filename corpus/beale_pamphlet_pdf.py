"""
Beale Pamphlet PDF - DOI edition from Beale Papers pamphlet.

Loads from PDF (or fallback: beale_papers.txt line 55), extracts marker anchors,
cleans pamphlet text, and tokenizes for marker-based validation.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

_PATH = Path(__file__).resolve().parent
_PROJECT_ROOT = _PATH.parent
_DEFAULT_PDF = _PROJECT_ROOT / "corpus" / "raw_sources" / "beale_pamphlet" / "beale_papers.pdf"
_BEALE_PAPERS_TXT = _PROJECT_ROOT / "beale_papers.txt"


def load_pamphlet_raw(pdf_path: str = None) -> str:
    """
    Load raw DOI text from PDF or fallback to beale_papers.txt.

    Args:
        pdf_path: Override path. Else uses BEALE_PAMPHLET_PDF_PATH env or default.

    Returns:
        Raw text string (Declaration excerpt with or without markers).
    """
    path = pdf_path or os.environ.get("BEALE_PAMPHLET_PDF_PATH", str(_DEFAULT_PDF))
    path = Path(path)

    if path.exists() and path.suffix.lower() == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text_parts.append(t)
                raw = "\n".join(text_parts)
                # Extract Declaration excerpt: from "When" or "DECLARATION" through "honor"
                # and before Cipher 2 list ("115, 73, 24" etc)
                raw = _extract_doi_from_pdf_text(raw)
                return raw
        except ImportError:
            pass  # fallback
        except Exception:
            pass  # fallback

    # Fallback: beale_papers.txt line 55 (word(1) word(2) ... word(1322))
    if _BEALE_PAPERS_TXT.exists():
        with open(_BEALE_PAPERS_TXT, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Line 55 is 0-indexed 54; Declaration starts at "DECLARATION" header
        for i, line in enumerate(lines):
            if "When(1)" in line or (i >= 50 and "when(1)" in line.lower()):
                return line.strip()
        if len(lines) > 54:
            return lines[54].strip()

    return ""


def _extract_doi_from_pdf_text(full_text: str) -> str:
    """Extract Declaration of Independence excerpt from PDF text."""
    full_lower = full_text.lower()
    start = full_lower.find("when(")
    if start < 0:
        start = full_lower.find("when ")
    if start < 0:
        start = full_lower.find("declaration of independence")
        if start >= 0:
            when = full_lower.find("when", start)
            if when >= 0:
                start = when
    if start < 0:
        start = 0
    # End at "honor" before Cipher 2 list
    honor = full_lower.rfind("honor")
    if honor >= 0:
        end = honor + len("honor")
    else:
        end = len(full_text)
    return full_text[start:end]


def extract_marker_anchors(raw: str) -> Dict[int, str]:
    """
    Extract word-number markers from raw text.

    Supports word(n) format: "When(1) in(2) the(3)" -> {1: "when", 2: "in", 3: "the"}.
    Handles and(&)(908) -> 908: "&".
    Returns {index: expected_word} (1-based).
    """
    anchors = {}
    # (&)(n) — ampersand at position n
    for m in re.finditer(r"\(\s*&\s*\)\s*\((\d+)\)", raw, re.IGNORECASE):
        anchors[int(m.group(1))] = "&"
    # word(n) — word immediately before (n) is at position n (allow apostrophe in word)
    for m in re.finditer(r"([\w']+)\s*\((\d+)\)", raw):
        word, num = m.group(1), int(m.group(2))
        if num not in anchors:  # avoid overwriting & from above
            anchors[num] = word.lower()
    return anchors


def clean_pamphlet_text(raw: str) -> str:
    """
    Clean pamphlet text for tokenization.

    - Line-break hyphenation: alter-\\n ing -> altering
    - Merged words: small heuristic dict (lawsand -> laws and)
    - Strip marker numbers (###) but keep word order
    """
    text = raw
    # Line-break hyphenation
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    # Known pamphlet artifacts (merge fixes)
    _merge_fixes = {"lawsand": "laws and", "alterand": "alter and"}
    for bad, good in _merge_fixes.items():
        text = text.replace(bad, good)
    # and(&)(908) -> pamphlet counts only & at 908 (not "and"); replace "and (&)" with " & "
    text = re.sub(r"\band\s*\(\s*&\s*\)", " & ", text)
    # Strip marker numbers (###) — remove parenthesized numbers
    text = re.sub(r"\(\d+\)", " ", text)
    return text


def tokenize_pamphlet(text: str) -> List[str]:
    """
    Tokenize cleaned pamphlet text with Beale quirks.

    Reuses logic from beale_patch_tokenizer: lowercase, .--/--/hyphen,
    meantime, apostrophe keep. Keeps & as its own token (pamphlet word 908).
    """
    text = text.lower()
    # Pre-split punctuation (keep & as token for pamphlet word 908)
    text = re.sub(r"\.--|--", " ", text)
    text = re.sub(r"[\u2013\u2014]", " ", text)
    text = re.sub(r"\.&|&\.", " . ", text)
    text = re.sub(r"\s*&\s*", " & ", text)
    text = text.replace("-", " ")
    # Pamphlet has "meantime" as single word (519) - do NOT split
    # Keep apostrophe and & (pamphlet counts & as word 908)
    text = re.sub(r"[^\w\s'&]", "", text)
    tokens = text.split()
    return [t for t in tokens if t]


def load_and_tokenize(pdf_path: str = None) -> Tuple[List[str], Dict[int, str]]:
    """
    Load pamphlet, extract anchors, clean, tokenize.

    Returns:
        (tokens, marker_anchors)
    """
    raw = load_pamphlet_raw(pdf_path)
    anchors = extract_marker_anchors(raw)
    cleaned = clean_pamphlet_text(raw)
    tokens = tokenize_pamphlet(cleaned)
    return tokens, anchors


def get_pamphlet_source_text(pdf_path: str = None) -> str:
    """Return space-joined tokenized text for DOIEdition source_text."""
    tokens, _ = load_and_tokenize(pdf_path)
    return " ".join(tokens)
