"""
Fetch niche texts from Internet Archive (Masonic, Virginia statutes)
and normalize them for the key-text hunt.
"""

import sys
import ssl
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from corpus.keytexts.loader import register_keytext, normalize_and_cache, RAW_DIR, NORM_DIR

NICHE_TEXTS = [
    {
        "id": "webb_freemason_monitor",
        "title": "The Freemason's Monitor, or Illustrations of Masonry - Thomas Smith Webb",
        "year": 1797,
        "source": "archive.org",
        "notes": "Standard Masonic handbook in early America. HIGH PRIORITY. 1865 Cincinnati edition OCR.",
        "urls": [
            "https://archive.org/stream/webbsfreemasonsm00webb/webbsfreemasonsm00webb_djvu.txt",
            "https://archive.org/download/webbsfreemasonsm00webb/webbsfreemasonsm00webb_djvu.txt",
        ],
    },
    {
        "id": "anderson_constitutions",
        "title": "The Constitutions of the Free-Masons - James Anderson (1723)",
        "year": 1723,
        "source": "archive.org",
        "notes": "Foundational Masonic document. 1723 edition.",
        "urls": [
            "https://archive.org/stream/cu31924030299402/cu31924030299402_djvu.txt",
            "https://archive.org/download/cu31924030299402/cu31924030299402_djvu.txt",
        ],
    },
    {
        "id": "preston_illustrations_masonry",
        "title": "Illustrations of Masonry - William Preston (1867 edition)",
        "year": 1772,
        "source": "archive.org",
        "notes": "Major Masonic educational text. 1867 reprint of an 18th century classic.",
        "urls": [
            "https://archive.org/stream/Illustrations_Of_Masonry_-_William_Preston_1867/Illustrations_Of_Masonry_-_William_Preston_1867_djvu.txt",
            "https://archive.org/download/Illustrations_Of_Masonry_-_William_Preston_1867/Illustrations_Of_Masonry_-_William_Preston_1867_djvu.txt",
        ],
    },
    {
        "id": "hening_statutes_v1",
        "title": "Hening's Statutes at Large, Vol 1 (1619-1660)",
        "year": 1823,
        "source": "archive.org",
        "notes": "Virginia laws compilation. Published 1823 by William Waller Hening. Contemporary with Beale.",
        "urls": [
            "https://archive.org/stream/statutesatlargeb01virg/statutesatlargeb01virg_djvu.txt",
            "https://archive.org/download/statutesatlargeb01virg/statutesatlargeb01virg_djvu.txt",
        ],
    },
    {
        "id": "hening_statutes_v7",
        "title": "Hening's Statutes at Large, Vol 7 (1756-1763)",
        "year": 1823,
        "source": "archive.org",
        "notes": "Virginia laws, Vol 7. Published 1823.",
        "urls": [
            "https://archive.org/stream/statutesatlargeb07virg/statutesatlargeb07virg_djvu.txt",
            "https://archive.org/download/statutesatlargeb07virg/statutesatlargeb07virg_djvu.txt",
        ],
    },
]


def fetch_url(url, timeout=30):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64) BealeCipherResearch/1.0"
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("latin-1", errors="replace")
    except Exception as e:
        print(f"    [FAIL] {url}: {e}")
        return None


def main():
    print("=" * 70)
    print("NICHE TEXT FETCHER (Masonic + Virginia Statutes)")
    print("=" * 70)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_DIR.mkdir(parents=True, exist_ok=True)

    for entry in NICHE_TEXTS:
        eid = entry["id"]
        raw_path = RAW_DIR / f"{eid}.txt"
        norm_path = NORM_DIR / f"{eid}.json"

        register_keytext(
            kid=eid, title=entry["title"], year=entry["year"],
            source=entry["source"], notes=entry["notes"],
        )

        if norm_path.exists():
            print(f"  [SKIP] {eid} (already cached)")
            continue

        text = None
        if raw_path.exists():
            text = raw_path.read_text(encoding="utf-8", errors="replace")
            print(f"  [RAW ] {eid} (raw exists)")
        else:
            for url in entry["urls"]:
                print(f"  [GET ] {eid} <- {url[:70]}...")
                text = fetch_url(url, timeout=45)
                if text and len(text) > 1000:
                    raw_path.write_text(text, encoding="utf-8")
                    print(f"         {len(text):,d} chars saved")
                    break
                text = None
                time.sleep(1)

        if text:
            try:
                result = normalize_and_cache(eid, text)
                tc = result["token_count"]
                print(f"  [NORM] {eid}: {tc} tokens "
                      f"{'C1-OK' if tc >= 2906 else 'C3-only' if tc >= 975 else 'SHORT'}")
            except Exception as e:
                print(f"  [ERR ] {eid}: {e}")
        else:
            print(f"  [FAIL] {eid} - could not fetch")

    print(f"\n{'='*70}")
    print("Done.")


if __name__ == "__main__":
    main()
