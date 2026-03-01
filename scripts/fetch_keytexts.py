"""
Batch fetch and register key texts for the Beale cipher key-text hunt.

This script:
1. Defines a list of candidate texts with their sources
2. Attempts to download each from public-domain sources
3. Registers them in the keytext registry
4. Normalizes and caches tokens

For texts that can't be fetched (network issues), creates TODO stubs.
"""

import sys
import time
import urllib.request
import ssl
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus.keytexts.loader import (
    register_keytext, normalize_and_cache, RAW_DIR, NORM_DIR
)

CANDIDATES = [
    {
        "id": "us_constitution",
        "title": "United States Constitution (original + amendments 1-12)",
        "year": 1787,
        "source": "https://www.archives.gov/founding-docs/constitution-transcript",
        "notes": "Original 7 articles + Bill of Rights + Amendments 11-12. Available in 1820.",
        "urls": [
            "https://www.gutenberg.org/files/5/5-0.txt",
            "https://www.gutenberg.org/cache/epub/5/pg5.txt",
        ],
    },
    {
        "id": "common_sense",
        "title": "Common Sense - Thomas Paine (1776)",
        "year": 1776,
        "source": "project_gutenberg",
        "notes": "Hugely popular pamphlet, widely available in early America. ~20k words.",
        "urls": [
            "https://www.gutenberg.org/files/147/147-0.txt",
            "https://www.gutenberg.org/cache/epub/147/pg147.txt",
        ],
    },
    {
        "id": "age_of_reason_p1",
        "title": "The Age of Reason Part 1 - Thomas Paine (1794)",
        "year": 1794,
        "source": "project_gutenberg",
        "notes": "Part 1 of Paine's deist work. Controversial but widely read. ~30k words.",
        "urls": [
            "https://www.gutenberg.org/files/3743/3743-0.txt",
            "https://www.gutenberg.org/cache/epub/3743/pg3743.txt",
        ],
    },
    {
        "id": "rights_of_man",
        "title": "Rights of Man - Thomas Paine (1791)",
        "year": 1791,
        "source": "project_gutenberg",
        "notes": "Defense of the French Revolution. Very widely circulated. ~60k words.",
        "urls": [
            "https://www.gutenberg.org/files/31270/31270-0.txt",
            "https://www.gutenberg.org/cache/epub/31270/pg31270.txt",
        ],
    },
    {
        "id": "federalist_papers",
        "title": "The Federalist Papers - Hamilton, Madison, Jay (1788)",
        "year": 1788,
        "source": "project_gutenberg",
        "notes": "85 essays on the Constitution. ~200k words total. Widely available.",
        "urls": [
            "https://www.gutenberg.org/files/1404/1404-0.txt",
            "https://www.gutenberg.org/cache/epub/1404/pg1404.txt",
        ],
    },
    {
        "id": "articles_of_confederation",
        "title": "Articles of Confederation (1777)",
        "year": 1777,
        "source": "manual",
        "notes": "Predecessor to the Constitution. ~3,500 words.",
        "urls": [],
    },
    {
        "id": "washington_farewell",
        "title": "Washington's Farewell Address (1796)",
        "year": 1796,
        "source": "manual",
        "notes": "Published in newspapers. ~6,000 words. Well-known in 1820.",
        "urls": [
            "https://www.gutenberg.org/cache/epub/5024/pg5024.txt",
        ],
    },
    {
        "id": "notes_virginia",
        "title": "Notes on the State of Virginia - Thomas Jefferson (1785)",
        "year": 1785,
        "source": "project_gutenberg",
        "notes": "Jefferson's only full-length book. ~80k words. Very long.",
        "urls": [
            "https://www.gutenberg.org/files/19002/19002-0.txt",
            "https://www.gutenberg.org/cache/epub/19002/pg19002.txt",
        ],
    },
    {
        "id": "prince_machiavelli",
        "title": "The Prince - Nicolo Machiavelli (1532, English trans.)",
        "year": 1532,
        "source": "project_gutenberg",
        "notes": "Classic political treatise. English translations available in 1820. ~26k words.",
        "urls": [
            "https://www.gutenberg.org/cache/epub/1232/pg1232.txt",
        ],
    },
    {
        "id": "declaration_independence",
        "title": "Declaration of Independence (1776)",
        "year": 1776,
        "source": "manual",
        "notes": "Known key for Cipher 2. Too short for C1 (max=2906) but useful as baseline.",
        "urls": [],
    },
    {
        "id": "monroe_doctrine",
        "title": "Monroe's 7th Annual Message / Monroe Doctrine (1823)",
        "year": 1823,
        "source": "manual",
        "notes": "Contemporary with Beale papers. ~4,000 words.",
        "urls": [],
    },
    {
        "id": "autobiography_franklin",
        "title": "Autobiography of Benjamin Franklin (1791)",
        "year": 1791,
        "source": "project_gutenberg",
        "notes": "Very popular in early America. ~62k words.",
        "urls": [
            "https://www.gutenberg.org/files/20203/20203-0.txt",
            "https://www.gutenberg.org/cache/epub/20203/pg20203.txt",
        ],
    },
    {
        "id": "pilgrims_progress",
        "title": "Pilgrim's Progress - John Bunyan (1678)",
        "year": 1678,
        "source": "project_gutenberg",
        "notes": "Most widely read book in early America after the Bible. ~100k words.",
        "urls": [
            "https://www.gutenberg.org/files/39452/39452-0.txt",
            "https://www.gutenberg.org/cache/epub/39452/pg39452.txt",
        ],
    },
    {
        "id": "robinson_crusoe",
        "title": "Robinson Crusoe - Daniel Defoe (1719)",
        "year": 1719,
        "source": "project_gutenberg",
        "notes": "Extremely popular in early America. ~120k words.",
        "urls": [
            "https://www.gutenberg.org/files/521/521-0.txt",
            "https://www.gutenberg.org/cache/epub/521/pg521.txt",
        ],
    },
    {
        "id": "paradise_lost",
        "title": "Paradise Lost - John Milton (1667)",
        "year": 1667,
        "source": "project_gutenberg",
        "notes": "Major literary work available in 1820s America. ~80k words.",
        "urls": [
            "https://www.gutenberg.org/files/26/26-0.txt",
            "https://www.gutenberg.org/cache/epub/26/pg26.txt",
        ],
    },
    {
        "id": "wealth_of_nations",
        "title": "Wealth of Nations - Adam Smith (1776)",
        "year": 1776,
        "source": "project_gutenberg",
        "notes": "Influential economic treatise. Available in early America. ~200k+ words.",
        "urls": [
            "https://www.gutenberg.org/cache/epub/3300/pg3300.txt",
        ],
    },
    {
        "id": "two_treatises_govt",
        "title": "Second Treatise of Government - John Locke (1689)",
        "year": 1689,
        "source": "project_gutenberg",
        "notes": "Foundational influence on American government. ~40k words.",
        "urls": [
            "https://www.gutenberg.org/files/7370/7370-0.txt",
            "https://www.gutenberg.org/cache/epub/7370/pg7370.txt",
        ],
    },
    {
        "id": "last_of_mohicans",
        "title": "The Last of the Mohicans - James F. Cooper (1826)",
        "year": 1826,
        "source": "project_gutenberg",
        "notes": "Hugely popular American novel from the Beale era. ~120k words.",
        "urls": [
            "https://www.gutenberg.org/files/27681/27681-0.txt",
            "https://www.gutenberg.org/cache/epub/27681/pg27681.txt",
        ],
    },
    {
        "id": "spy_cooper",
        "title": "The Spy: A Tale of the Neutral Ground - James F. Cooper (1821)",
        "year": 1821,
        "source": "project_gutenberg",
        "notes": "First major American novel. Published 1821, contemporary with Beale. ~100k words.",
        "urls": [
            "https://www.gutenberg.org/cache/epub/9845/pg9845.txt",
        ],
    },
    {
        "id": "king_james_genesis",
        "title": "King James Bible - Book of Genesis",
        "year": 1611,
        "source": "manual",
        "notes": "The Bible was the most common book in 1820s America. Genesis alone ~38k words.",
        "urls": [
            "https://www.gutenberg.org/cache/epub/8001/pg8001.txt",
        ],
    },
    {
        "id": "king_james_full",
        "title": "King James Bible (complete)",
        "year": 1611,
        "source": "project_gutenberg",
        "notes": "Complete KJV Bible. ~790k words. The single most available book in 1820s Virginia.",
        "urls": [
            "https://www.gutenberg.org/cache/epub/10/pg10.txt",
        ],
    },
    {
        "id": "virginia_religious_freedom",
        "title": "Virginia Statute for Religious Freedom - Jefferson (1786)",
        "year": 1786,
        "source": "manual",
        "notes": "Short but historically significant Virginia document. ~1000 words. For C3 only.",
        "urls": [],
    },
    {
        "id": "kentucky_resolutions",
        "title": "Kentucky Resolutions - Thomas Jefferson (1798)",
        "year": 1798,
        "source": "manual",
        "notes": "States' rights document. ~3,500 words.",
        "urls": [],
    },
    {
        "id": "magna_carta",
        "title": "Magna Carta (1215, English translation)",
        "year": 1215,
        "source": "manual",
        "notes": "Available in English translation in 1820s. ~3,500 words.",
        "urls": [],
    },
]


def fetch_url(url, timeout=20):
    """Attempt to fetch a URL. Returns text or None."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    [FAIL] {url}: {e}")
        return None


def main():
    print("=" * 80)
    print("BATCH KEY-TEXT FETCHER")
    print("=" * 80)

    fetched = 0
    stubs = 0
    skipped = 0

    for cand in CANDIDATES:
        kid = cand["id"]
        raw_path = RAW_DIR / f"{kid}.txt"
        norm_path = NORM_DIR / f"{kid}.json"

        # Register
        register_keytext(
            kid=kid,
            title=cand["title"],
            year=cand["year"],
            source=cand["source"],
            notes=cand["notes"],
        )

        if norm_path.exists():
            print(f"  [SKIP] {kid} (already cached)")
            skipped += 1
            continue

        # Try to fetch
        text = None
        if raw_path.exists():
            print(f"  [RAW ] {kid} (raw file exists, normalizing)")
            text = raw_path.read_text(encoding="utf-8", errors="replace")
        else:
            for url in cand.get("urls", []):
                print(f"  [FETCH] {kid} from {url[:60]}...")
                text = fetch_url(url)
                if text and len(text) > 500:
                    raw_path.write_text(text, encoding="utf-8")
                    print(f"    [OK] {len(text)} chars saved")
                    break
                text = None
                time.sleep(0.5)

        if text:
            result = normalize_and_cache(kid, text)
            print(f"  [NORM] {kid}: {result['token_count']} tokens")
            fetched += 1
        else:
            print(f"  [STUB] {kid} (no text available - TODO: manual download)")
            stubs += 1

    print(f"\n{'='*80}")
    print(f"SUMMARY: {fetched} fetched, {skipped} skipped, {stubs} stubs")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
