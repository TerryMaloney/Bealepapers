"""
Fix niche texts that were saved as HTML instead of plain text.
Extracts the actual OCR text from Internet Archive HTML wrapper pages.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from corpus.keytexts.loader import normalize_and_cache

RAW_DIR = Path("corpus/keytexts/raw_sources")

NICHE = [
    "webb_freemason_monitor",
    "anderson_constitutions",
    "hening_statutes_v1",
    "hening_statutes_v7",
    "preston_illustrations_masonry",
]


def extract_text_from_ia_html(html):
    """Extract book text from Internet Archive HTML wrapper."""
    # IA wraps the OCR text in a <pre> tag
    match = re.search(r'<pre[^>]*>(.*?)</pre>', html, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        # Fallback: look for the text container div
        match = re.search(r'class="container-ia"[^>]*>(.*?)$', html, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            return None

    # Decode HTML entities
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.strip()
    return text


def main():
    for name in NICHE:
        path = RAW_DIR / f"{name}.txt"
        if not path.exists():
            print(f"  {name}: FILE NOT FOUND")
            continue

        content = path.read_text(encoding='utf-8', errors='replace')

        if not content.startswith('<!DOCTYPE') and not content.startswith('<html'):
            print(f"  {name}: already plain text ({len(content)} chars)")
            continue

        text = extract_text_from_ia_html(content)
        if text is None or len(text) < 500:
            print(f"  {name}: EXTRACTION FAILED (got {len(text) if text else 0} chars)")
            print(f"    HTML size: {len(content)} chars")
            continue

        # Overwrite with clean text
        path.write_text(text, encoding='utf-8')
        print(f"  {name}: extracted {len(text)} chars")
        print(f"    first 120 chars: {text[:120]!r}")

        # Re-normalize
        normalize_and_cache(name, hyphen="keep")

        # Verify
        from corpus.keytexts.loader import load_normalized
        norm = load_normalized(name)
        if norm:
            print(f"    tokens: {norm['token_count']}, first 10: {norm['tokens'][:10]}")
        else:
            print(f"    WARNING: normalization failed")
        print()


if __name__ == "__main__":
    main()
