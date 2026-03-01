"""
Pamphlet bundle builder: DOI + Articles of Confederation + Constitution + Bill of Rights.

DOI segment MUST come from get_adjusted_tokens() (validated). Sibling texts are
fetched from Avalon Project / existing raw files and normalized with the same
tokenization as the pamphlet (tokenize_pamphlet). Produces B1, B2, B3 bundles
and a manifest.
"""

import json
import re
import urllib.request
import ssl
from pathlib import Path
from typing import List, Dict, Tuple

from corpus.beale_doi_adjusted import get_adjusted_tokens
from corpus.beale_pamphlet_pdf import clean_pamphlet_text, tokenize_pamphlet

_BASE = Path(__file__).resolve().parent
_RAW = _BASE / "raw_sources"
_NORM = _BASE / "normalized"
_PROJECT_ROOT = _BASE.parent.parent

# URLs for sibling texts (Avalon Project, Yale Law)
ARTICLES_URL = "https://avalon.law.yale.edu/18th_century/artconf.asp"
BILL_OF_RIGHTS_URL = "https://avalon.law.yale.edu/18th_century/rights1.asp"

# Known good text for Articles of Confederation (fallback if fetch fails)
ARTICLES_FALLBACK_PATH = _RAW / "articles_of_confederation_avalon.txt"
BILL_OF_RIGHTS_FALLBACK_PATH = _RAW / "bill_of_rights_avalon.txt"


def _strip_gutenberg(text: str) -> str:
    """Strip Project Gutenberg header/footer."""
    for start in ["*** START OF THIS PROJECT GUTENBERG", "*** START OF THE PROJECT GUTENBERG",
                  "***START OF THE PROJECT GUTENBERG"]:
        idx = text.find(start)
        if idx >= 0:
            nl = text.find("\n", idx)
            text = text[nl + 1:] if nl >= 0 else text[idx + len(start):]
            break
    for end in ["*** END OF THIS PROJECT GUTENBERG", "*** END OF THE PROJECT GUTENBERG",
                "End of the Project Gutenberg", "End of Project Gutenberg"]:
        idx = text.find(end)
        if idx >= 0:
            text = text[:idx]
            break
    return text.strip()


def _fetch_url(url: str, timeout: int = 30) -> str:
    """Fetch URL and return decoded text."""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "BealeCipherResearch/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _html_to_plain(html: str) -> str:
    """Extract main text from HTML: strip tags, collapse whitespace."""
    # Remove script/style
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Strip all tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Decode common entities
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_articles_body(html: str) -> str:
    """Extract Articles of Confederation body from Avalon page."""
    text = _html_to_plain(html)
    # Start after "To all to whom these Presents"
    start = text.find("To all to whom these Presents shall come")
    if start < 0:
        start = text.find("Articles of Confederation and perpetual Union")
    if start < 0:
        start = 0
    # End before "Agreed to by Congress" or "Source:"
    for end_marker in ["Agreed to by Congress 15 November", "Source: Documents Illustrative",
                       "Lillian Goldman Law Library", "© 2008"]:
        end = text.find(end_marker)
        if end > start:
            text = text[start:end]
            break
    else:
        text = text[start:]
    return text.strip()


def _extract_bill_of_rights_body(html: str) -> str:
    """Extract Bill of Rights amendments text from Avalon page."""
    text = _html_to_plain(html)
    # Start at first amendment
    start = text.find("Congress shall make no law respecting")
    if start < 0:
        start = text.find("Freedom of Speech, Press, Religion")
    if start < 0:
        start = 0
    # End before "Rights of the States" trailing or "Article 7" link
    for end_marker in ["Article 7", "United States Constitution", "Amendments 11-27",
                       "Lillian Goldman Law Library", "© 2008"]:
        end = text.find(end_marker)
        if end > start and end - start > 200:
            text = text[start:end]
            break
    else:
        text = text[start:]
    return text.strip()


def fetch_articles_of_confederation() -> str:
    """Fetch Articles of Confederation. Returns raw text for normalization."""
    if ARTICLES_FALLBACK_PATH.exists():
        return ARTICLES_FALLBACK_PATH.read_text(encoding="utf-8")
    try:
        html = _fetch_url(ARTICLES_URL)
        return _extract_articles_body(html)
    except Exception:
        return ""


def fetch_bill_of_rights() -> str:
    """Fetch Bill of Rights. Returns raw text for normalization."""
    if BILL_OF_RIGHTS_FALLBACK_PATH.exists():
        return BILL_OF_RIGHTS_FALLBACK_PATH.read_text(encoding="utf-8")
    try:
        html = _fetch_url(BILL_OF_RIGHTS_URL)
        return _extract_bill_of_rights_body(html)
    except Exception:
        return ""


def load_constitution_raw() -> str:
    """Load US Constitution from existing raw_sources file; strip Gutenberg."""
    path = _RAW / "us_constitution.txt"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    text = _strip_gutenberg(text)
    # Start at "We the people" if still present
    we = text.find("We the people of the United States")
    if we >= 0:
        text = text[we:]
    return text.strip()


def normalize_sibling(raw: str) -> List[str]:
    """Normalize sibling text with same policy as pamphlet: clean_pamphlet_text + tokenize_pamphlet."""
    if not raw or not raw.strip():
        return []
    cleaned = clean_pamphlet_text(raw)
    return tokenize_pamphlet(cleaned)


def build_bundles() -> Dict:
    """
    Build B1, B2, B3 and write to normalized/ + manifest.
    Returns manifest dict.
    """
    # DOI from validated source (do NOT re-source)
    doi_tokens = get_adjusted_tokens()
    doi_len = len(doi_tokens)
    assert doi_len >= 1005, "DOI must have at least 1005 tokens for C2"

    # Sibling segments
    articles_raw = fetch_articles_of_confederation()
    articles_tokens = normalize_sibling(articles_raw)
    constitution_raw = load_constitution_raw()
    constitution_tokens = normalize_sibling(constitution_raw)
    bor_raw = fetch_bill_of_rights()
    bor_tokens = normalize_sibling(bor_raw)

    segments = [
        {"name": "doi", "tokens": doi_tokens, "source": "beale_adjusted_doi", "provenance": "get_adjusted_tokens()"},
        {"name": "articles", "tokens": articles_tokens, "source": "avalon_artconf", "provenance": ARTICLES_URL},
        {"name": "constitution", "tokens": constitution_tokens, "source": "raw_sources/us_constitution.txt", "provenance": "Gutenberg #5"},
        {"name": "bill_of_rights", "tokens": bor_tokens, "source": "avalon_rights1", "provenance": BILL_OF_RIGHTS_URL},
    ]

    # Build bundles
    manifest = {"bundles": {}, "segment_boundaries": {}, "doi_token_count": doi_len}

    # B1 = DOI + Articles
    b1_tokens = doi_tokens + articles_tokens
    boundaries_b1 = [{"name": "doi", "start": 0, "end": doi_len}, {"name": "articles", "start": doi_len, "end": len(b1_tokens)}]
    _NORM.mkdir(parents=True, exist_ok=True)
    out_b1 = _NORM / "bundle_b1.json"
    with open(out_b1, "w", encoding="utf-8") as f:
        json.dump({"tokens": b1_tokens, "token_count": len(b1_tokens), "segments": boundaries_b1,
                   "source": "doi+articles"}, f, ensure_ascii=False)
    manifest["bundles"]["b1"] = {"token_count": len(b1_tokens), "path": str(out_b1), "segments": ["doi", "articles"]}
    manifest["segment_boundaries"]["b1"] = boundaries_b1

    # B2 = DOI + Articles + Constitution
    b2_tokens = doi_tokens + articles_tokens + constitution_tokens
    boundaries_b2 = [
        {"name": "doi", "start": 0, "end": doi_len},
        {"name": "articles", "start": doi_len, "end": doi_len + len(articles_tokens)},
        {"name": "constitution", "start": doi_len + len(articles_tokens), "end": len(b2_tokens)},
    ]
    out_b2 = _NORM / "bundle_b2.json"
    with open(out_b2, "w", encoding="utf-8") as f:
        json.dump({"tokens": b2_tokens, "token_count": len(b2_tokens), "segments": boundaries_b2,
                   "source": "doi+articles+constitution"}, f, ensure_ascii=False)
    manifest["bundles"]["b2"] = {"token_count": len(b2_tokens), "path": str(out_b2), "segments": ["doi", "articles", "constitution"]}
    manifest["segment_boundaries"]["b2"] = boundaries_b2

    # B3 = DOI + Articles + Constitution + Bill of Rights
    b3_tokens = doi_tokens + articles_tokens + constitution_tokens + bor_tokens
    boundaries_b3 = [
        {"name": "doi", "start": 0, "end": doi_len},
        {"name": "articles", "start": doi_len, "end": doi_len + len(articles_tokens)},
        {"name": "constitution", "start": doi_len + len(articles_tokens), "end": doi_len + len(articles_tokens) + len(constitution_tokens)},
        {"name": "bill_of_rights", "start": doi_len + len(articles_tokens) + len(constitution_tokens), "end": len(b3_tokens)},
    ]
    out_b3 = _NORM / "bundle_b3.json"
    with open(out_b3, "w", encoding="utf-8") as f:
        json.dump({"tokens": b3_tokens, "token_count": len(b3_tokens), "segments": boundaries_b3,
                   "source": "doi+articles+constitution+bill_of_rights"}, f, ensure_ascii=False)
    manifest["bundles"]["b3"] = {"token_count": len(b3_tokens), "path": str(out_b3), "segments": ["doi", "articles", "constitution", "bill_of_rights"]}
    manifest["segment_boundaries"]["b3"] = boundaries_b3

    manifest["segment_token_counts"] = {
        "doi": doi_len,
        "articles": len(articles_tokens),
        "constitution": len(constitution_tokens),
        "bill_of_rights": len(bor_tokens),
    }

    # Write manifest to output/phase98
    out_phase98 = _PROJECT_ROOT / "output" / "phase98"
    out_phase98.mkdir(parents=True, exist_ok=True)
    manifest_path = out_phase98 / "bundle_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest


if __name__ == "__main__":
    m = build_bundles()
    print("Bundles built:")
    for bid, info in m["bundles"].items():
        print(f"  {bid}: {info['token_count']} tokens")
    print(f"Manifest: output/phase98/bundle_manifest.json")
