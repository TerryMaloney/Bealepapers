"""
Virginia Dragnet v1: fetch, register, normalize all candidate texts
from corpus/keytexts/dragnet_virginia_v1.json.

Supports:
  - Project Gutenberg plain text download by URL
  - Skips entries marked as TODO
  - Updates registry.json with provenance
  - Normalizes and caches tokens via loader.py
  - Reports failures and minimum-length compliance
"""

import json
import sys
import time
import ssl
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus.keytexts.loader import (
    register_keytext, normalize_and_cache, load_normalized,
    RAW_DIR, NORM_DIR
)

DRAGNET_PATH = Path("corpus/keytexts/dragnet_virginia_v1.json")

C1_MIN_TOKENS = 2906
C3_MIN_TOKENS = 975


def fetch_url(url, timeout=30):
    """Fetch a URL with SSL bypass for Gutenberg. Returns text or None."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BealeCipherResearch/1.0"
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = resp.read()
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("latin-1", errors="replace")
    except Exception as e:
        return None


def gutenberg_urls(gutenberg_id):
    """Generate possible Gutenberg plaintext URLs for a given ID."""
    gid = gutenberg_id
    return [
        f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt",
        f"https://www.gutenberg.org/files/{gid}/{gid}-0.txt",
        f"https://www.gutenberg.org/ebooks/{gid}.txt.utf-8",
    ]


def main():
    print("=" * 80)
    print("VIRGINIA DRAGNET v1 — BATCH FETCHER")
    print("=" * 80)

    with open(DRAGNET_PATH, "r", encoding="utf-8") as f:
        dragnet = json.load(f)

    entries = dragnet["entries"]
    print(f"Loaded {len(entries)} entries from dragnet")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORM_DIR.mkdir(parents=True, exist_ok=True)

    fetched = 0
    skipped = 0
    failed = 0
    todos = 0
    status_log = []

    for entry in entries:
        eid = entry["id"]
        title = entry["title"]
        source_url = entry.get("source_url", "TODO")
        source_type = entry.get("source_type", "todo")
        gid = entry.get("gutenberg_id")

        raw_path = RAW_DIR / f"{eid}.txt"
        norm_path = NORM_DIR / f"{eid}.json"

        # Register in main registry
        register_keytext(
            kid=eid,
            title=title,
            year=entry.get("year", 0),
            source=source_url if source_url != "TODO" else "todo",
            notes=entry.get("notes", ""),
        )

        # Check if already normalized
        if norm_path.exists():
            norm = load_normalized(eid)
            tc = norm["token_count"] if norm else 0
            ok_c1 = tc >= C1_MIN_TOKENS
            print(f"  [SKIP] {eid:35s} {tc:6d} tokens  {'C1-OK' if ok_c1 else 'C3-only'}")
            skipped += 1
            status_log.append((eid, "skip", tc))
            continue

        # TODO entries — skip with note
        if source_type == "todo" or source_url == "TODO":
            print(f"  [TODO] {eid:35s} — needs manual acquisition")
            todos += 1
            status_log.append((eid, "todo", 0))
            continue

        # Try to fetch
        text = None
        if raw_path.exists():
            text = raw_path.read_text(encoding="utf-8", errors="replace")
            print(f"  [RAW ] {eid:35s} — raw file exists, normalizing")
        else:
            urls = []
            if gid:
                urls = gutenberg_urls(gid)
            elif source_url and source_url != "TODO":
                urls = [source_url]

            for url in urls:
                print(f"  [GET ] {eid:35s} <- {url[:65]}...")
                text = fetch_url(url)
                if text and len(text) > 500:
                    raw_path.write_text(text, encoding="utf-8")
                    print(f"         {len(text):,d} chars saved")
                    break
                text = None
                time.sleep(0.3)

        if text:
            try:
                result = normalize_and_cache(eid, text)
                tc = result["token_count"]
                ok_c1 = tc >= C1_MIN_TOKENS
                print(f"  [NORM] {eid:35s} {tc:6d} tokens  "
                      f"{'C1-OK' if ok_c1 else 'C3-only' if tc >= C3_MIN_TOKENS else 'TOO-SHORT'}")
                fetched += 1
                status_log.append((eid, "fetched", tc))
            except Exception as e:
                print(f"  [ERR ] {eid:35s} normalization failed: {e}")
                failed += 1
                status_log.append((eid, "error", 0))
        else:
            print(f"  [FAIL] {eid:35s} — could not fetch")
            failed += 1
            status_log.append((eid, "failed", 0))

    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"  Fetched & normalized: {fetched}")
    print(f"  Already cached:       {skipped}")
    print(f"  TODO (manual):        {todos}")
    print(f"  Failed:               {failed}")

    # Token count report
    print(f"\n{'='*80}")
    print("TOKEN COUNTS (eligible for C1 need >= 2906)")
    print("-" * 60)
    c1_eligible = 0
    c3_eligible = 0
    for eid, status, tc in status_log:
        if tc >= C1_MIN_TOKENS:
            c1_eligible += 1
        if tc >= C3_MIN_TOKENS:
            c3_eligible += 1
    print(f"  C1-eligible (>= {C1_MIN_TOKENS} tokens): {c1_eligible}")
    print(f"  C3-eligible (>= {C3_MIN_TOKENS} tokens): {c3_eligible}")
    print(f"  TODO entries:                    {todos}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
