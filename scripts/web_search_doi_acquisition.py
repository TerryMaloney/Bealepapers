"""
Web-Based DOI Edition Acquisition

Uses WebSearch tool to find authoritative DOI transcripts from:
- Library of Congress
- National Archives (NARA)
- Yale Avalon Project
- University archives

Provides ranked URLs for manual text acquisition.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple


# Priority editions with search queries
EDITION_SEARCH_QUERIES = {
    "stone_1823": {
        "name": "Stone Engraving 1823",
        "queries": [
            "William Stone engraving 1823 Declaration Independence full text transcript",
            "Stone facsimile 1823 Declaration Independence LOC NARA",
            "John Quincy Adams Stone engraving Declaration 1823"
        ],
        "priority": 1,
        "notes": "Temporally closest to Beale era (1819-1821), most widely distributed in 1820s"
    },
    "dunlap_1776": {
        "name": "Dunlap Broadside 1776",
        "queries": [
            "Dunlap broadside 1776 Declaration Independence transcript Library Congress",
            "John Dunlap original printing Declaration 1776 full text",
            "Dunlap broadside Philadelphia July 1776 transcript"
        ],
        "priority": 2,
        "notes": "Original printing, distributed to Continental Congress"
    },
    "goddard_1777": {
        "name": "Goddard Printing 1777",
        "queries": [
            "Mary Katherine Goddard Declaration Independence 1777 Baltimore transcript",
            "Goddard printing 1777 Declaration signers names",
            "Goddard broadside January 1777 full text"
        ],
        "priority": 3,
        "notes": "Official Congressional version with signer names"
    },
    "virginia_1820s": {
        "name": "Virginia 1820s Political Handbook",
        "queries": [
            "Declaration Independence Virginia 1820s reprint political handbook",
            "Virginia political manual 1820s Declaration text",
            "Bedford County Virginia 1820s Declaration Independence"
        ],
        "priority": 4,
        "notes": "Period-appropriate reprints in Beale operational geography"
    }
}


def rank_url_authority(url: str) -> int:
    """
    Rank URL by authority for DOI transcripts.
    
    Returns priority score (higher = more authoritative):
    - 100: .gov domains (LOC, NARA, Archives.gov)
    - 80: Major university archives (.edu from Yale, Harvard, etc.)
    - 60: Academic institutions (.edu general)
    - 40: Historical societies (.org)
    - 20: Other sources
    """
    url_lower = url.lower()
    
    # Government archives (highest authority)
    if any(domain in url_lower for domain in ['loc.gov', 'archives.gov', 'nara.gov']):
        return 100
    
    # Major university digital collections
    if any(domain in url_lower for domain in ['yale.edu', 'harvard.edu', 'princeton.edu']):
        if any(keyword in url_lower for keyword in ['avalon', 'library', 'archive', 'collection']):
            return 80
    
    # General .edu
    if '.edu' in url_lower:
        return 60
    
    # Historical societies
    if '.org' in url_lower and any(keyword in url_lower for keyword in ['history', 'historical', 'archive']):
        return 40
    
    return 20


def generate_acquisition_guide(edition_id: str) -> str:
    """Generate detailed acquisition guide for an edition."""
    
    if edition_id not in EDITION_SEARCH_QUERIES:
        return f"[ERROR] Unknown edition: {edition_id}"
    
    edition = EDITION_SEARCH_QUERIES[edition_id]
    
    guide = f"""
================================================================================
ACQUISITION GUIDE: {edition['name']}
================================================================================

Edition ID: {edition_id}
Priority: {edition['priority']} (1=highest)
Notes: {edition['notes']}

RECOMMENDED SEARCH QUERIES:
"""
    
    for i, query in enumerate(edition['queries'], 1):
        guide += f"\n{i}. {query}"
    
    guide += """

AUTHORITATIVE SOURCES (in priority order):
1. Library of Congress (LOC): https://www.loc.gov/
   - Search their digital collections
   - Look for "Founding Documents" or "Declaration of Independence"

2. National Archives (NARA): https://www.archives.gov/
   - Visit: https://www.archives.gov/founding-docs/declaration-transcript
   - Check for historical editions and facsimiles

3. Yale Avalon Project: https://avalon.law.yale.edu/
   - Browse 18th century documents
   - Direct link: https://avalon.law.yale.edu/18th_century/declare.asp

ACQUISITION STEPS:
1. Use web search with queries above
2. Visit top-ranked authoritative URLs (.gov, .edu)
3. Copy ONLY the Declaration text body (no modern commentary)
4. Save to: corpus/editions/{edition_id}.txt

CRITICAL CONSIDERATIONS:
- Include or exclude header line: "IN CONGRESS, JULY 4, 1776"
- Include or exclude title: "The unanimous Declaration..."
- Include or exclude signer names (if present)
- Preserve original hyphenation: "self-evident" vs "self evident"
- Note any structural differences in metadata

AFTER ACQUISITION:
python scripts/acquire_doi_editions.py register {edition_id}

================================================================================
"""
    
    return guide


def save_acquisition_report(edition_id: str, search_results: List[Dict], output_dir: str = "output/acquisition"):
    """Save acquisition report with search results."""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_path / f"{edition_id}_acquisition_{timestamp}.txt"
    
    edition = EDITION_SEARCH_QUERIES.get(edition_id, {})
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"DOI EDITION ACQUISITION REPORT\n")
        f.write(f"Edition: {edition.get('name', edition_id)}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("SEARCH QUERIES USED:\n")
        for i, query in enumerate(edition.get('queries', []), 1):
            f.write(f"{i}. {query}\n")
        f.write("\n")
        
        if search_results:
            f.write("CANDIDATE URLS (ranked by authority):\n")
            f.write("-" * 80 + "\n")
            
            for i, result in enumerate(search_results, 1):
                f.write(f"\n{i}. {result['title']}\n")
                f.write(f"   URL: {result['url']}\n")
                f.write(f"   Authority: {result['authority_score']}/100\n")
                f.write(f"   Source Type: {result['source_type']}\n")
                if 'snippet' in result:
                    f.write(f"   Snippet: {result['snippet'][:200]}...\n")
        else:
            f.write("NO SEARCH RESULTS AVAILABLE\n")
            f.write("Manual search recommended using queries above.\n")
    
    print(f"\nAcquisition report saved: {report_file}")


def run_acquisition_workflow(edition_ids: List[str] = None):
    """
    Run automated acquisition workflow.
    
    Note: This provides guidance and URLs. Actual text acquisition is manual
    due to need for human validation of authenticity.
    """
    
    if edition_ids is None:
        # Default to all editions in priority order
        edition_ids = sorted(EDITION_SEARCH_QUERIES.keys(), 
                           key=lambda x: EDITION_SEARCH_QUERIES[x]['priority'])
    
    print("=" * 80)
    print("DOI EDITION ACQUISITION WORKFLOW")
    print("=" * 80)
    print("\nThis tool provides:")
    print("  1. Pre-defined search queries for authoritative sources")
    print("  2. URL ranking by source authority")
    print("  3. Step-by-step acquisition guides")
    print("\nActual text acquisition is MANUAL to ensure authenticity.")
    print("=" * 80)
    
    for edition_id in edition_ids:
        print(f"\n\n{generate_acquisition_guide(edition_id)}")
        
        # Note: WebSearch tool usage would go here in actual implementation
        # For now, provide manual guidance
        
        response = input(f"\nPress Enter to continue to next edition, or 'q' to quit: ")
        if response.lower() == 'q':
            break
    
    print("\n" + "=" * 80)
    print("ACQUISITION WORKFLOW COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Visit recommended URLs and copy DOI texts")
    print("2. Save to corpus/editions/<edition_id>.txt")
    print("3. Register: python scripts/acquire_doi_editions.py register <edition_id>")
    print("4. Run oracle sweep: python run_pipeline.py oracle_sweep_enhanced")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DOI Edition Acquisition with web search guidance",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--edition', type=str, default=None,
                       help='Specific edition to acquire (stone_1823, dunlap_1776, goddard_1777)')
    parser.add_argument('--all', action='store_true',
                       help='Show acquisition guides for all editions')
    parser.add_argument('--list', action='store_true',
                       help='List available editions')
    
    args = parser.parse_args()
    
    if args.list:
        print("=" * 80)
        print("AVAILABLE DOI EDITIONS")
        print("=" * 80)
        
        for edition_id, info in sorted(EDITION_SEARCH_QUERIES.items(), 
                                      key=lambda x: x[1]['priority']):
            print(f"\n{info['priority']}. {info['name']} ({edition_id})")
            print(f"   {info['notes']}")
        
        print("\n" + "=" * 80)
        return
    
    if args.edition:
        edition_ids = [args.edition]
    elif args.all:
        edition_ids = None  # All editions
    else:
        # Default: highest priority only
        edition_ids = ['stone_1823']
    
    run_acquisition_workflow(edition_ids)


if __name__ == "__main__":
    main()
