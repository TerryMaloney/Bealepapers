"""
Text Intake Contract: quality gate for all key text sources.

Rejects texts contaminated with HTML/markup, enforces minimum alphabetic
content ratio, word count, and symbol density. This prevents the Phase 92
HTML contamination bug from recurring.

Every text MUST pass this contract before being accepted into normalized cache.
"""

import re
from typing import Tuple


# Minimum thresholds for text quality
MIN_ALPHA_TOKEN_RATIO = 0.60   # at least 60% of tokens must be alphabetic words
MIN_WORD_COUNT = 100           # reject trivially short texts
MAX_MARKUP_RATIO = 0.02        # at most 2% of content can look like markup
MAX_SYMBOL_DENSITY = 0.15      # at most 15% non-alpha non-space characters


# Patterns that indicate HTML/XML/script contamination
MARKUP_PATTERNS = [
    r'</?[a-zA-Z][a-zA-Z0-9]*[^>]*>',         # HTML tags
    r'<!DOCTYPE',                                # DOCTYPE declaration
    r'<script[^>]*>',                            # script tags
    r'<style[^>]*>',                             # style tags
    r'function\s*\(',                            # JavaScript function calls
    r'var\s+\w+\s*=',                            # JS variable declarations
    r'content="[^"]*sentry',                     # Sentry telemetry
    r'archive\.org/includes',                    # IA includes
    r'\{[^}]*:\s*[^}]*;[^}]*\}',               # CSS rules
    r'xmlns[:=]',                                # XML namespaces
    r'data-[a-z]+=',                             # HTML data attributes
    r'class="[^"]*"',                            # HTML class attributes
    r'name="[^"]*"',                             # HTML name attributes
    r'content="[^"]*"',                          # HTML content attributes
]


def check_intake(raw_text: str, source_id: str = "") -> Tuple[bool, str]:
    """
    Validate a raw text against the intake contract.

    Returns:
        (passed, reason): True if text passes, with reason string.
    """
    if not raw_text or len(raw_text.strip()) == 0:
        return False, "Empty text"

    text = raw_text.strip()
    total_chars = len(text)

    # Check for HTML/markup contamination
    markup_chars = 0
    for pattern in MARKUP_PATTERNS:
        for match in re.finditer(pattern, text[:5000]):  # check first 5000 chars
            markup_chars += len(match.group())

    markup_ratio = markup_chars / min(total_chars, 5000)
    if markup_ratio > MAX_MARKUP_RATIO:
        return False, (f"MARKUP CONTAMINATION: {markup_ratio:.1%} of first 5000 chars "
                       f"match markup patterns (max {MAX_MARKUP_RATIO:.0%}). "
                       f"Source appears to be HTML/XML, not plain text.")

    # Quick DOCTYPE/html check
    if text[:100].strip().startswith('<!DOCTYPE') or text[:100].strip().startswith('<html'):
        return False, "Text starts with HTML declaration. This is a web page, not book text."

    # Word count check
    words = text.split()
    word_count = len(words)
    if word_count < MIN_WORD_COUNT:
        return False, f"Too few words: {word_count} (minimum {MIN_WORD_COUNT})"

    # Alphabetic token ratio
    alpha_tokens = sum(1 for w in words if re.match(r'^[a-zA-Z]', w))
    alpha_ratio = alpha_tokens / word_count
    if alpha_ratio < MIN_ALPHA_TOKEN_RATIO:
        return False, (f"Low alphabetic token ratio: {alpha_ratio:.1%} "
                       f"(minimum {MIN_ALPHA_TOKEN_RATIO:.0%}). "
                       f"Text may contain excessive numbers, symbols, or code.")

    # Symbol density (non-alpha, non-space, non-common-punctuation)
    alpha_space = sum(1 for c in text if c.isalpha() or c.isspace() or c in '.,;:!?\'"()-')
    symbol_density = 1 - (alpha_space / total_chars)
    if symbol_density > MAX_SYMBOL_DENSITY:
        return False, (f"High symbol density: {symbol_density:.1%} "
                       f"(maximum {MAX_SYMBOL_DENSITY:.0%}). "
                       f"Text may contain code or binary data.")

    return True, (f"PASS: {word_count} words, {alpha_ratio:.0%} alphabetic, "
                  f"{markup_ratio:.1%} markup, {symbol_density:.1%} symbols")


def validate_all_raw_sources(raw_dir="corpus/keytexts/raw_sources"):
    """Scan all raw sources and report which pass/fail the intake contract."""
    from pathlib import Path
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        print(f"Directory not found: {raw_path}")
        return

    results = {"pass": [], "fail": []}
    for f in sorted(raw_path.glob("*.txt")):
        text = f.read_text(encoding="utf-8", errors="replace")
        passed, reason = check_intake(text, f.stem)
        status = "PASS" if passed else "FAIL"
        results["pass" if passed else "fail"].append(f.stem)
        print(f"  [{status}] {f.stem:40s} {reason[:80]}")

    print(f"\nSummary: {len(results['pass'])} passed, {len(results['fail'])} failed")
    if results["fail"]:
        print(f"FAILED: {', '.join(results['fail'])}")
    return results


if __name__ == "__main__":
    validate_all_raw_sources()
