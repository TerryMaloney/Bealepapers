"""
Historical DOI Edition Acquisition Script

Acquires Declaration of Independence editions from authoritative sources:
- Library of Congress
- National Archives
- Yale Avalon Project
- Other primary historical sources

Priority editions:
1. Dunlap Broadside 1776 (original printing)
2. Stone Engraving 1823 (1820s facsimile)
3. Goddard Printing 1777 (Baltimore)
4. 1819-1820s reprints (Beale era)
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Note: Using WebSearch and WebFetch tools instead of requests/BeautifulSoup
# since we're in Cursor environment


def save_edition_metadata(edition_id: str, metadata: Dict, output_dir: str = "corpus/editions"):
    """Save edition metadata to JSON file."""
    output_path = Path(output_dir) / f"{edition_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved metadata: {output_path}")


def save_edition_text(edition_id: str, text: str, output_dir: str = "corpus/editions"):
    """Save edition text to file."""
    output_path = Path(output_dir) / f"{edition_id}.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"Saved edition text: {output_path}")
    return output_path


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
    import re
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def create_edition_metadata(edition_id: str, text: str, source_url: str,
                           provenance: str, date: str, notes: str = "",
                           includes_signers: bool = False,
                           includes_header: bool = True) -> Dict:
    """Create metadata dict for edition."""
    words = text.split()
    
    return {
        "edition_id": edition_id,
        "source_url": source_url,
        "provenance": provenance,
        "acquisition_date": datetime.now().strftime("%Y-%m-%d"),
        "edition_date": date,
        "word_count": len(words),
        "char_count": len(text),
        "includes_signers": includes_signers,
        "includes_header": includes_header,
        "notes": notes,
        "sha256": compute_text_hash(text)
    }


# Known authoritative URLs for DOI editions
KNOWN_EDITIONS = {
    "dunlap_1776": {
        "name": "Dunlap Broadside 1776",
        "search_query": "Dunlap broadside 1776 Declaration of Independence transcript Library of Congress",
        "known_urls": [
            "https://www.archives.gov/founding-docs/declaration-transcript",
            "https://avalon.law.yale.edu/18th_century/declare.asp"
        ],
        "provenance": "Original printing by John Dunlap, Philadelphia, July 4-5, 1776",
        "date": "1776-07-04",
        "notes": "First printed version, distributed to Continental Congress"
    },
    "stone_1823": {
        "name": "Stone Engraving 1823",
        "search_query": "William Stone engraving Declaration of Independence 1823 transcript",
        "known_urls": [
            "https://www.archives.gov/founding-docs/declaration-transcript"
        ],
        "provenance": "Stone engraving facsimile, commissioned by John Quincy Adams",
        "date": "1823",
        "notes": "Facsimile of original document, common in 1820s America (Beale era)"
    },
    "goddard_1777": {
        "name": "Goddard Printing 1777",
        "search_query": "Mary Katherine Goddard Declaration of Independence 1777 Baltimore transcript",
        "known_urls": [
            "https://www.archives.gov/founding-docs/declaration-transcript"
        ],
        "provenance": "Official printing by Mary Katherine Goddard, Baltimore, January 1777",
        "date": "1777-01",
        "notes": "First printing with signer names, official Congressional version"
    },
    "avalon_modern": {
        "name": "Yale Avalon Project (Modern Transcript)",
        "search_query": "Yale Avalon Project Declaration of Independence",
        "known_urls": [
            "https://avalon.law.yale.edu/18th_century/declare.asp"
        ],
        "provenance": "Yale Law School Avalon Project digital transcript",
        "date": "1776-07-04",
        "notes": "Modern scholarly transcript, likely based on Stone engraving or National Archives"
    }
}


def manual_acquisition_guide():
    """
    Print guide for manual acquisition of DOI editions.
    
    Since automated web scraping may not work reliably across all sources,
    this provides instructions for manual acquisition.
    """
    print("=" * 80)
    print("MANUAL DOI EDITION ACQUISITION GUIDE")
    print("=" * 80)
    print("\nTo acquire historical DOI editions:")
    print("\n1. Visit authoritative sources:")
    print("   - National Archives: https://www.archives.gov/founding-docs/declaration-transcript")
    print("   - Yale Avalon Project: https://avalon.law.yale.edu/18th_century/declare.asp")
    print("   - Library of Congress: https://www.loc.gov/")
    print("\n2. Copy the full text (body text only, no headers/footers)")
    print("\n3. Save to: corpus/editions/<edition_id>.txt")
    print("   Examples:")
    print("   - corpus/editions/dunlap_1776.txt")
    print("   - corpus/editions/stone_1823.txt")
    print("   - corpus/editions/goddard_1777.txt")
    print("   - corpus/editions/avalon_modern.txt")
    print("\n4. Run this script to generate metadata:")
    print("   python scripts/acquire_doi_editions.py --register <edition_id>")
    print("\n" + "=" * 80)
    print("\nKEY CONSIDERATIONS:")
    print("- Include or exclude header line: 'IN CONGRESS, JULY 4, 1776'")
    print("- Include or exclude title: 'The unanimous Declaration...'")
    print("- Include or exclude signer names (usually at end)")
    print("- Preserve hyphenation: 'self-evident' vs 'self evident'")
    print("- Preserve capitalization in proper nouns")
    print("=" * 80)


def register_manually_acquired_edition(edition_id: str, edition_dir: str = "corpus/editions"):
    """
    Register a manually acquired edition by generating metadata.
    
    Assumes the .txt file already exists at corpus/editions/<edition_id>.txt
    """
    text_path = Path(edition_dir) / f"{edition_id}.txt"
    
    if not text_path.exists():
        print(f"[ERROR] Edition text not found: {text_path}")
        print(f"Please save edition text to this location first.")
        return False
    
    # Load text
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Check if metadata exists
    if edition_id in KNOWN_EDITIONS:
        info = KNOWN_EDITIONS[edition_id]
        metadata = create_edition_metadata(
            edition_id=edition_id,
            text=text,
            source_url=info['known_urls'][0] if info['known_urls'] else "manually_acquired",
            provenance=info['provenance'],
            date=info['date'],
            notes=info['notes']
        )
    else:
        # Generic metadata
        metadata = create_edition_metadata(
            edition_id=edition_id,
            text=text,
            source_url="manually_acquired",
            provenance=f"Manually acquired edition: {edition_id}",
            date="unknown",
            notes="Custom edition - update metadata as needed"
        )
    
    # Save metadata
    save_edition_metadata(edition_id, metadata, edition_dir)
    
    print(f"\n[SUCCESS] Registered edition: {edition_id}")
    print(f"  Words: {metadata['word_count']}")
    print(f"  Chars: {metadata['char_count']}")
    print(f"  Hash: {metadata['sha256'][:16]}...")
    
    return True


def create_placeholder_editions():
    """
    Create placeholder editions for manual acquisition.
    
    This creates stub files that guide user to acquire actual texts.
    """
    output_dir = Path("corpus/editions")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n[Creating placeholder editions for manual acquisition]")
    
    for edition_id, info in KNOWN_EDITIONS.items():
        text_path = output_dir / f"{edition_id}.txt"
        
        if text_path.exists():
            print(f"  {edition_id}: Already exists, skipping")
            continue
        
        # Create placeholder
        placeholder_text = f"""[PLACEHOLDER - TO BE ACQUIRED]

Edition: {info['name']}
Edition ID: {edition_id}
Date: {info['date']}
Provenance: {info['provenance']}
Notes: {info['notes']}

ACQUISITION INSTRUCTIONS:
1. Search for: {info['search_query']}

2. Known authoritative URLs:
"""
        for url in info['known_urls']:
            placeholder_text += f"   - {url}\n"
        
        placeholder_text += """
3. Copy the full Declaration text (body only, no modern commentary)

4. Replace this file's contents with the actual DOI text

5. Run: python scripts/acquire_doi_editions.py --register """ + edition_id + """

IMPORTANT NOTES:
- Preserve original spelling, capitalization, and punctuation
- Include/exclude header line based on source (note in metadata)
- Include/exclude signer names based on source (note in metadata)
- Keep hyphens as they appear: "self-evident" vs "self evident"
"""
        
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(placeholder_text)
        
        print(f"  {edition_id}: Created placeholder at {text_path}")
    
    print(f"\n[SUCCESS] Created {len(KNOWN_EDITIONS)} placeholder editions")
    print(f"\nNext steps:")
    print(f"1. Visit authoritative sources and acquire actual DOI texts")
    print(f"2. Replace placeholder files with real texts")
    print(f"3. Run: python scripts/acquire_doi_editions.py --register <edition_id>")


def list_editions(edition_dir: str = "corpus/editions"):
    """List all editions and their status."""
    output_dir = Path(edition_dir)
    
    if not output_dir.exists():
        print(f"[ERROR] Edition directory not found: {output_dir}")
        return
    
    print("=" * 80)
    print("DOI EDITIONS STATUS")
    print("=" * 80)
    
    for edition_id in KNOWN_EDITIONS.keys():
        text_path = output_dir / f"{edition_id}.txt"
        json_path = output_dir / f"{edition_id}.json"
        
        print(f"\n{edition_id}:")
        
        if not text_path.exists():
            print(f"  Status: NOT FOUND")
            continue
        
        # Check if placeholder
        with open(text_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        
        if first_line == "[PLACEHOLDER - TO BE ACQUIRED]":
            print(f"  Status: PLACEHOLDER (needs acquisition)")
        else:
            # Real edition
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            word_count = len(text.split())
            char_count = len(text)
            
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                print(f"  Status: ACQUIRED ✓")
                print(f"  Words: {metadata.get('word_count', word_count)}")
                print(f"  Date: {metadata.get('edition_date', 'unknown')}")
                print(f"  Hash: {metadata.get('sha256', 'unknown')[:16]}...")
            else:
                print(f"  Status: ACQUIRED (no metadata)")
                print(f"  Words: {word_count}")
                print(f"  Chars: {char_count}")
                print(f"  Action: Run --register {edition_id} to generate metadata")
    
    print("\n" + "=" * 80)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Acquire historical DOI editions for oracle testing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Create placeholders
    subparsers.add_parser('create_placeholders',
                         help='Create placeholder files for manual acquisition')
    
    # Register manually acquired edition
    register_parser = subparsers.add_parser('register',
                                           help='Register manually acquired edition')
    register_parser.add_argument('edition_id',
                                help='Edition ID (e.g., dunlap_1776)')
    
    # List editions
    subparsers.add_parser('list',
                         help='List all editions and their status')
    
    # Show manual guide
    subparsers.add_parser('guide',
                         help='Show manual acquisition guide')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        print("\n")
        manual_acquisition_guide()
        return
    
    if args.command == 'create_placeholders':
        create_placeholder_editions()
    elif args.command == 'register':
        register_manually_acquired_edition(args.edition_id)
    elif args.command == 'list':
        list_editions()
    elif args.command == 'guide':
        manual_acquisition_guide()


if __name__ == "__main__":
    main()
