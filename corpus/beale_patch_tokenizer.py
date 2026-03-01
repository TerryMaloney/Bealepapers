"""
Beale Patch Tokenizer - NARA (Stone) with Beale tokenization quirks.

Produces base token list for structural patch search:
- Hard-slice When -> Honor (exclude header/signers)
- .-- and -- as separators (Happiness.--That -> Happiness, That)
- Standalone & as separator (Cruelty & perfidy -> Cruelty, perfidy)
- hyphen_split: self-evident -> self, evident
- "mean time" counted as two words (meantime -> mean time)
- Keep apostrophes inside words (Nature's stays one token)
"""

import re
from typing import List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus.doi_editions import DOICorpusLoader
from corpus.tokenizers import TokenizerRegistry


def slice_doi_body(text: str) -> str:
    """
    Hard-slice DOI body: first 'When' through last 'Honor'.

    Beale numbering assumes this word count. Excludes header (e.g. "The unanimous
    Declaration...") and signers.
    """
    text_lower = text.lower()
    when_idx = text_lower.find("when")
    if when_idx < 0:
        return text
    honor_idx = text_lower.rfind("honor")
    if honor_idx < 0:
        return text[when_idx:]
    end = honor_idx + len("honor")
    return text[when_idx:end]


def tokenize_nara_beale_quirks(text: str) -> List[str]:
    """
    Tokenize DOI text with Beale quirks.

    Order: slice, lowercase, pre-split punctuation, hyphen split, meantime,
    remove other punctuation (keep apostrophe), split on whitespace.
    """
    text = slice_doi_body(text)
    text = text.lower()

    # Pre-split punctuation (before removing)
    text = re.sub(r'\.--|--', ' ', text)
    # Em-dash (U+2014) and en-dash (U+2013) as separators
    text = re.sub(r'[\u2013\u2014]', ' ', text)
    # .& and &. patterns (no space before/after & can fuse words)
    text = re.sub(r'\.&|&\.', ' . ', text)
    # Any & as separator (handles "Cruelty & perfidy" and "word&word")
    text = re.sub(r'\s*&\s*|&', ' ', text)

    # Hyphen split (Beale counts self-evident as 2 words)
    text = text.replace("-", " ")

    # meantime -> mean time
    text = re.sub(r'\bmeantime\b', 'mean time', text, flags=re.IGNORECASE)

    # Remove punctuation except apostrophe (keep Nature's as one token)
    text = re.sub(r"[^\w\s']", '', text)

    # Split on whitespace
    tokens = text.split()

    # Filter empty
    tokens = [t for t in tokens if t]

    return tokens


def load_nara_base_tokens() -> List[str]:
    """
    Load nara_transcript and tokenize with Beale quirks.

    Returns base token list ready for structural patch search.
    """
    loader = DOICorpusLoader()
    edition = loader.load_edition("nara_transcript")

    if not edition.source_text or edition.source_text.startswith("[PLACEHOLDER"):
        raise FileNotFoundError(
            "nara_transcript not available. Run phase13_discover first."
        )

    return tokenize_nara_beale_quirks(edition.source_text)


def get_beale_patch_tokens(run_patch_search: bool = True) -> List[str]:
    """
    Get the full Beale-patched token list.

    If run_patch_search=True, runs structural patch search and returns best.
    If False, returns only the base token list (nara + quirks, no structural edits).

    Returns:
        Patched token list (or base if run_patch_search=False)
    """
    base = load_nara_base_tokens()

    if not run_patch_search:
        return base

    from corpus.beale_structural_patch import run_structural_patch_search

    patched, score, _ = run_structural_patch_search(base, verbose=True)
    return patched
