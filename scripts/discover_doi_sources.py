"""
Phase 13 Step A: Discover and Acquire DOI Editions

Web-fetches Declaration of Independence transcripts from multiple authoritative sources.
Target: at least 30 editions before ranking.

Sources:
- National Archives (archives.gov)
- Library of Congress (loc.gov)
- Yale Avalon Project (avalon.law.yale.edu)
- Wikisource
- University archives
- Digitized pamphlets
- OCR'd citizen manuals
"""

import re
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


# Known authoritative sources for DOI transcripts
SOURCE_REGISTRY = {
    "nara_transcript": {
        "url": "https://www.archives.gov/founding-docs/declaration-transcript",
        "name": "National Archives - Official Transcript",
        "date": "1776-07-04",
        "provenance": "NARA official transcript, modern scholarly edition",
        "contains_header": True,
        "contains_signers": True
    },
    "avalon_yale": {
        "url": "https://avalon.law.yale.edu/18th_century/declare.asp",
        "name": "Yale Avalon Project",
        "date": "1776-07-04",
        "provenance": "Yale Law School Avalon Project digital transcript",
        "contains_header": True,
        "contains_signers": True
    },
    "wikisource_doi": {
        "url": "https://en.wikisource.org/wiki/United_States_Declaration_of_Independence",
        "name": "Wikisource - Declaration of Independence",
        "date": "1776-07-04",
        "provenance": "Wikisource community transcription",
        "contains_header": True,
        "contains_signers": True
    },
    "ushistory_org": {
        "url": "https://www.ushistory.org/declaration/document/",
        "name": "USHistory.org Transcript",
        "date": "1776-07-04",
        "provenance": "USHistory.org educational resource",
        "contains_header": True,
        "contains_signers": True
    },
    "constitution_center": {
        "url": "https://constitutioncenter.org/the-constitution/declaration-of-independence",
        "name": "Constitution Center",
        "date": "1776-07-04",
        "provenance": "National Constitution Center digital archive",
        "contains_header": True,
        "contains_signers": True
    }
}


def compute_text_hash(text: str) -> str:
    """Compute SHA256 hash of text."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def normalize_doi_text(raw_text: str) -> str:
    """
    Normalize DOI text for consistency.
    
    - Preserve original wording
    - Normalize line breaks to spaces
    - Remove excessive whitespace
    - Preserve paragraph structure
    """
    # Replace line breaks with spaces
    text = raw_text.replace('\n', ' ').replace('\r', '')
    
    # Collapse multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def detect_doi_text(html_content: str, url: str) -> Optional[str]:
    """
    Extract DOI text from HTML content.
    
    Uses heuristics: looks for key phrases like "When in the course",
    "self-evident", "pursuit of happiness", etc.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Look for canonical start phrase (USHistory has "W" as image, so "hen in the Course")
    start_patterns = [
        (r"When in the course of human events", ""),
        (r"When in the Course of human Events", ""),
        (r"WHEN in the Course of human events", ""),
        (r"hen in the [Cc]ourse of human events", "W"),  # USHistory: W is in img
        (r"it becomes necessary for one people to dissolve", "When in the Course of human events, "),
    ]
    
    for pattern, prefix in start_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Found start, extract from here
            start_idx = match.start()
            if prefix:
                # Prepend missing text (e.g., "W" for USHistory)
                text = prefix + text[start_idx:]
                start_idx = 0
            
            # Look for end (signers or final statement)
            end_patterns = [
                r"for the support of this Declaration.*?sacred honor",
                r"And for the support of this declaration.*?sacred Honor",
                r"mutually pledge.*?sacred honor"
            ]
            
            end_idx = len(text)
            for end_pattern in end_patterns:
                end_match = re.search(end_pattern, text[start_idx:], re.IGNORECASE | re.DOTALL)
                if end_match:
                    end_idx = start_idx + end_match.end()
                    break
            
            extracted = text[start_idx:end_idx]
            return normalize_doi_text(extracted)
    
    return None


def fetch_url(url: str, timeout: int = 30) -> Optional[str]:
    """
    Fetch URL content with timeout and error handling.
    
    Returns HTML content or None if failed.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  [ERROR] Failed to fetch {url}: {e}")
        return None


def save_raw_source(source_id: str, content: str, output_dir: Path):
    """Save raw HTML/text to corpus/raw_sources/<source_id>/raw.html"""
    source_dir = output_dir / "raw_sources" / source_id
    source_dir.mkdir(parents=True, exist_ok=True)
    
    raw_file = source_dir / "raw.html"
    with open(raw_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  Saved raw: {raw_file}")


def save_edition(edition_id: str, text: str, metadata: Dict, editions_dir: Path):
    """Save edition text and metadata to corpus/editions/"""
    editions_dir.mkdir(parents=True, exist_ok=True)
    
    # Save text
    text_file = editions_dir / f"{edition_id}.txt"
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(text)
    
    # Save metadata
    json_file = editions_dir / f"{edition_id}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  Saved edition: {text_file}")
    print(f"  Saved metadata: {json_file}")


def create_edition_metadata(edition_id: str, text: str, source_info: Dict) -> Dict:
    """Create metadata dict for edition."""
    words = text.split()
    
    return {
        "edition_id": edition_id,
        "source_url": source_info.get("url", ""),
        "source_name": source_info.get("name", ""),
        "provenance": source_info.get("provenance", ""),
        "acquisition_date": datetime.now().strftime("%Y-%m-%d"),
        "edition_date": source_info.get("date", "unknown"),
        "word_count": len(words),
        "char_count": len(text),
        "contains_signers": source_info.get("contains_signers", False),
        "contains_header": source_info.get("contains_header", False),
        "sha256": compute_text_hash(text)
    }


def discover_and_fetch_sources(output_dir: Path = None) -> List[Dict]:
    """
    Discover and fetch DOI editions from SOURCE_REGISTRY.
    
    Returns list of edition metadata dicts.
    """
    if output_dir is None:
        output_dir = Path("corpus")
    
    editions_dir = output_dir / "editions"
    editions_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("PHASE 13 STEP A: DISCOVER AND ACQUIRE DOI EDITIONS")
    print("=" * 80)
    print(f"\nSources to fetch: {len(SOURCE_REGISTRY)}")
    print()
    
    acquired_editions = []
    seen_hashes = set()
    
    for source_id, source_info in SOURCE_REGISTRY.items():
        print(f"[{len(acquired_editions) + 1}] Fetching: {source_info['name']}")
        print(f"    URL: {source_info['url']}")
        
        # Fetch content
        content = fetch_url(source_info['url'])
        if content is None:
            print(f"  [SKIP] Could not fetch content")
            continue
        
        # Save raw
        save_raw_source(source_id, content, output_dir)
        
        # Extract DOI text
        doi_text = detect_doi_text(content, source_info['url'])
        if doi_text is None:
            print(f"  [SKIP] Could not extract DOI text")
            continue
        
        # Check for duplicates
        text_hash = compute_text_hash(doi_text)
        if text_hash in seen_hashes:
            print(f"  [SKIP] Duplicate (same text as previous edition)")
            continue
        
        seen_hashes.add(text_hash)
        
        # Create edition ID
        edition_id = source_id
        
        # Create metadata
        metadata = create_edition_metadata(edition_id, doi_text, source_info)
        
        # Save edition
        save_edition(edition_id, doi_text, metadata, editions_dir)
        
        acquired_editions.append(metadata)
        print(f"  [SUCCESS] Acquired: {edition_id} ({len(doi_text.split())} words)")
        print()
    
    return acquired_editions


def include_beale_embedded(output_dir: Path = None) -> Dict:
    """
    Include beale_embedded edition in catalog.
    
    This is already in beale_papers.txt line 55, but we extract and
    save it to corpus/editions/ for consistency.
    """
    if output_dir is None:
        output_dir = Path("corpus")
    
    editions_dir = output_dir / "editions"
    
    print("[SPECIAL] Including beale_embedded from beale_papers.txt")
    
    # Load from beale_papers
    with open("beale_papers.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    doi_line = lines[54].strip()
    
    # Extract words from pattern: word(number)
    pattern = r'(\w+)\((\d+)\)'
    matches = re.findall(pattern, doi_line)
    
    # Build ordered text
    max_num = max(int(num) for word, num in matches)
    words = [''] * (max_num + 1)
    for word, num in matches:
        words[int(num)] = word.lower()
    
    # Join words (skip index 0)
    text = ' '.join(words[1:])
    
    # Create metadata
    metadata = {
        "edition_id": "beale_embedded",
        "source_url": "beale_papers.txt line 55",
        "source_name": "Beale Papers Embedded DOI",
        "provenance": "Extracted from beale_papers.txt line 55 (1885 Beale Papers publication)",
        "acquisition_date": datetime.now().strftime("%Y-%m-%d"),
        "edition_date": "1885",
        "word_count": len(words[1:]),
        "char_count": len(text),
        "contains_signers": False,
        "contains_header": False,
        "sha256": compute_text_hash(text)
    }
    
    # Save
    save_edition("beale_embedded", text, metadata, editions_dir)
    
    print(f"  [SUCCESS] Included: beale_embedded ({metadata['word_count']} words)")
    print()
    
    return metadata


def create_placeholders(output_dir: Path = None) -> List[Dict]:
    """
    Create placeholder entries for editions that need manual acquisition.
    
    These are Stone 1823, Dunlap 1776, Goddard 1777.
    """
    if output_dir is None:
        output_dir = Path("corpus")
    
    editions_dir = output_dir / "editions"
    
    print("[PLACEHOLDERS] Creating entries for manually acquired editions")
    
    placeholders = {
        "dunlap_1776": {
            "name": "Dunlap Broadside 1776",
            "provenance": "Original printing by John Dunlap, Philadelphia, July 4-5, 1776 - TO BE ACQUIRED",
            "date": "1776-07-04",
            "notes": "First printed version, distributed to Continental Congress"
        },
        "stone_1823": {
            "name": "Stone Engraving 1823",
            "provenance": "Stone engraving facsimile by William Stone, commissioned by John Quincy Adams - TO BE ACQUIRED",
            "date": "1823",
            "notes": "Facsimile of original document, common in 1820s America (Beale era)"
        },
        "goddard_1777": {
            "name": "Goddard Printing 1777",
            "provenance": "Official printing by Mary Katherine Goddard, Baltimore, January 1777 - TO BE ACQUIRED",
            "date": "1777-01",
            "notes": "First printing with signer names, official Congressional version"
        }
    }
    
    placeholder_list = []
    
    for edition_id, info in placeholders.items():
        metadata = {
            "edition_id": edition_id,
            "source_url": "",
            "source_name": info["name"],
            "provenance": info["provenance"],
            "acquisition_date": datetime.now().strftime("%Y-%m-%d"),
            "edition_date": info["date"],
            "word_count": 0,
            "char_count": 0,
            "contains_signers": True,
            "contains_header": True,
            "sha256": "",
            "status": "PLACEHOLDER",
            "notes": info["notes"]
        }
        
        # Save metadata only (no text file)
        json_file = editions_dir / f"{edition_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        placeholder_list.append(metadata)
        print(f"  Created placeholder: {edition_id}")
    
    print()
    return placeholder_list


def save_catalog(editions: List[Dict], project_root: Path = None):
    """Save edition catalog to output/phase13/edition_catalog.json"""
    if project_root is None:
        project_root = Path(".")
    catalog_dir = project_root / "output" / "phase13"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    
    catalog_file = catalog_dir / "edition_catalog.json"
    with open(catalog_file, 'w', encoding='utf-8') as f:
        json.dump({
            "generated": datetime.now().isoformat(),
            "total_editions": len(editions),
            "editions": editions
        }, f, indent=2)
    
    print(f"Catalog saved: {catalog_file}")
    
    # Also save simple list
    list_file = catalog_dir / "editions_list.txt"
    with open(list_file, 'w', encoding='utf-8') as f:
        for ed in editions:
            f.write(f"{ed['edition_id']}\n")
    
    print(f"Edition list saved: {list_file}")


def run_discovery(output_dir: Path = None, corpus_dir: Path = None):
    """Main entry point for Step A."""
    if output_dir is None:
        output_dir = Path(".")
    if corpus_dir is None:
        corpus_dir = Path("corpus")
    
    # Fetch from registry (saves to corpus/editions, corpus/raw_sources)
    acquired = discover_and_fetch_sources(corpus_dir)
    
    # Include beale_embedded
    beale_meta = include_beale_embedded(corpus_dir)
    all_editions = [beale_meta] + acquired
    
    # Create placeholders
    placeholders = create_placeholders(corpus_dir)
    all_editions.extend(placeholders)
    
    # Save catalog to output/phase13
    save_catalog(all_editions, output_dir)
    
    print("=" * 80)
    print("DISCOVERY SUMMARY")
    print("=" * 80)
    print(f"Total editions: {len(all_editions)}")
    print(f"  Acquired: {len(acquired) + 1}")  # +1 for beale_embedded
    print(f"  Placeholders: {len(placeholders)}")
    print()
    
    if len(all_editions) < 30:
        print(f"[WARNING] Target is 30+ editions, currently have {len(all_editions)}")
        print("          Add more sources to SOURCE_REGISTRY or manually acquire editions")
    else:
        print(f"[SUCCESS] Target of 30+ editions met!")
    
    print("\nNext step: Run phase13_tokenize to create token candidates")
    print("=" * 80)
    
    return all_editions


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 13 Step A: Discover DOI Editions")
    parser.add_argument('--output-dir', default='.', help='Output directory (default: current)')
    
    args = parser.parse_args()
    
    run_discovery(Path(args.output_dir))
