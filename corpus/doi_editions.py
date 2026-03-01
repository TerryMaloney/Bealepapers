"""
DOI Edition Manager - Multi-edition corpus loader for oracle validation.

Manages multiple Declaration of Independence editions and their provenance.
"""

import re
import json
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class DOIEdition:
    """Represents a specific edition of the Declaration of Independence."""
    edition_id: str
    source_text: str
    provenance: str
    date: str
    notes: str = ""
    
    def __repr__(self):
        return f"DOIEdition(id='{self.edition_id}', words={len(self.source_text.split())}, date='{self.date}')"


class DOICorpusLoader:
    """Loader for multiple DOI editions with provenance tracking."""
    
    def __init__(self, editions_dir: str = "corpus/editions"):
        self.editions_dir = Path(editions_dir)
        self.editions_dir.mkdir(parents=True, exist_ok=True)
    
    def load_edition(self, edition_id: str) -> DOIEdition:
        """Load a specific DOI edition by ID."""
        
        if edition_id == "beale_embedded":
            return self._load_beale_embedded()
        
        if edition_id == "nara_beale_patched":
            return self._load_nara_beale_patched()

        if edition_id == "beale_pamphlet_pdf":
            return self._load_beale_pamphlet_pdf()

        if edition_id == "beale_adjusted_doi":
            return self._load_beale_adjusted_doi()
        
        # Try to load from editions directory
        edition_file = self.editions_dir / f"{edition_id}.txt"
        if edition_file.exists():
            with open(edition_file, 'r', encoding='utf-8') as f:
                source_text = f.read()
            
            return DOIEdition(
                edition_id=edition_id,
                source_text=source_text,
                provenance=f"Loaded from {edition_file}",
                date="unknown",
                notes="Manually acquired edition"
            )
        
        # Edition not found - return placeholder
        return self._create_placeholder(edition_id)
    
    def _load_beale_embedded(self) -> DOIEdition:
        """Load the DOI embedded in beale_papers.txt (line 55)."""
        with open("beale_papers.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Line 55 (index 54) contains numbered Declaration
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
        source_text = ' '.join(words[1:])
        
        return DOIEdition(
            edition_id="beale_embedded",
            source_text=source_text,
            provenance="Extracted from beale_papers.txt line 55",
            date="1885 (Beale Papers publication)",
            notes="DOI text as numbered in the 1885 Beale pamphlet"
        )
    
    def _load_nara_beale_patched(self) -> DOIEdition:
        """
        Load nara_beale_patched edition.
        
        Expects corpus/editions/nara_beale_patched.txt to exist (created by
        beale_patch_validate). Contains space-joined patched tokens.
        """
        patched_file = self.editions_dir / "nara_beale_patched.txt"
        if patched_file.exists():
            with open(patched_file, 'r', encoding='utf-8') as f:
                source_text = f.read()
            return DOIEdition(
                edition_id="nara_beale_patched",
                source_text=source_text,
                provenance="NARA (Stone) + Beale structural patches + letter overrides",
                date="1823 (Stone) / 1885 (Beale pamphlet)",
                notes="Run beale_patch_validate to regenerate"
            )
        return self._create_placeholder("nara_beale_patched")

    def _load_beale_pamphlet_pdf(self) -> DOIEdition:
        """
        Load beale_pamphlet_pdf edition from PDF or beale_papers.txt fallback.
        """
        try:
            from corpus.beale_pamphlet_pdf import get_pamphlet_source_text
            source_text = get_pamphlet_source_text()
            if source_text:
                return DOIEdition(
                    edition_id="beale_pamphlet_pdf",
                    source_text=source_text,
                    provenance="Beale Papers PDF (or beale_papers.txt fallback)",
                    date="1885",
                    notes="Run beale_pamphlet_validate to validate marker anchors"
                )
        except Exception:
            pass
        return self._create_placeholder("beale_pamphlet_pdf")

    def _load_beale_adjusted_doi(self) -> DOIEdition:
        """
        Load beale_adjusted_doi - standard DOI with 5 FSU-documented Beale adjustments.
        Aligns word numbering with cipher 2 (807=valuable, etc.).
        """
        try:
            from corpus.beale_doi_adjusted import get_adjusted_tokens
            tokens = get_adjusted_tokens()
            if tokens:
                return DOIEdition(
                    edition_id="beale_adjusted_doi",
                    source_text=" ".join(tokens),
                    provenance="Standard DOI + 5 FSU Beale adjustments (807=valuable)",
                    date="1885",
                    notes="corpus/beale_doi_adjusted.py"
                )
        except Exception:
            pass
        return self._create_placeholder("beale_adjusted_doi")
    
    def _create_placeholder(self, edition_id: str) -> DOIEdition:
        """Create placeholder for edition that needs to be acquired."""
        
        placeholders = {
            "nara_beale_patched": {
                "provenance": "NARA (Stone) + Beale structural patches - Run beale_patch_validate to generate",
                "date": "1823/1885",
                "notes": "python run_pipeline.py beale_patch_validate"
            },
            "beale_pamphlet_pdf": {
                "provenance": "Beale Papers PDF - Run beale_pamphlet_validate to validate",
                "date": "1885",
                "notes": "python run_pipeline.py beale_pamphlet_validate"
            },
            "beale_adjusted_doi": {
                "provenance": "Standard DOI + 5 FSU Beale adjustments",
                "date": "1885",
                "notes": "corpus/beale_doi_adjusted.py"
            },
            "dunlap_1776": {
                "provenance": "Dunlap broadside - TO BE ACQUIRED from Library of Congress",
                "date": "1776-07-04",
                "notes": "Original printing by John Dunlap, Philadelphia. Most historically accurate."
            },
            "goddard_1777": {
                "provenance": "Goddard printing - TO BE ACQUIRED",
                "date": "1777-01",
                "notes": "Baltimore printing by Mary Katherine Goddard"
            },
            "stone_1823": {
                "provenance": "Stone engraving facsimile - TO BE ACQUIRED",
                "date": "1823",
                "notes": "Stone engraving common in 1820s Virginia, plausible for Beale era"
            }
        }
        
        info = placeholders.get(edition_id, {
            "provenance": f"Edition '{edition_id}' - TO BE ACQUIRED",
            "date": "unknown",
            "notes": "Historical edition not yet obtained"
        })
        
        # Create placeholder file
        placeholder_file = self.editions_dir / f"{edition_id}.txt"
        placeholder_content = f"""[PLACEHOLDER - TO BE ACQUIRED]

Edition: {edition_id}
Provenance: {info['provenance']}
Date: {info['date']}
Notes: {info['notes']}

This file is a placeholder. Replace with actual DOI text when acquired.

Acquisition sources:
- Library of Congress: https://www.loc.gov/
- National Archives: https://www.archives.gov/
- Founders Online: https://founders.archives.gov/
"""
        
        with open(placeholder_file, 'w', encoding='utf-8') as f:
            f.write(placeholder_content)
        
        return DOIEdition(
            edition_id=edition_id,
            source_text="",  # Empty until acquired
            provenance=info['provenance'],
            date=info['date'],
            notes=info['notes']
        )
    
    def list_available_editions(self) -> List[str]:
        """List all available DOI editions (including placeholders)."""
        editions = ["beale_embedded", "beale_pamphlet_pdf", "beale_adjusted_doi"]
        
        # Add historical editions (will be placeholders until acquired)
        editions.extend(["dunlap_1776", "goddard_1777", "stone_1823"])
        
        # Add any manually added edition files
        if self.editions_dir.exists():
            for file in self.editions_dir.glob("*.txt"):
                edition_id = file.stem
                if edition_id not in editions:
                    editions.append(edition_id)
        
        return editions
    
    def list_all_editions(self, include_placeholders: bool = False) -> List[dict]:
        """
        List all DOI editions with metadata.
        
        Returns list of dicts with edition_id, status, word_count, date, provenance.
        
        Args:
            include_placeholders: If True, include placeholder editions (not yet acquired)
        """
        editions_info = []
        
        # beale_embedded
        editions_info.append({
            "edition_id": "beale_embedded",
            "status": "available",
            "source": "beale_papers.txt",
            "date": "1885",
            "provenance": "Embedded in Beale Papers",
            "has_text": True
        })

        # beale_pamphlet_pdf
        try:
            from corpus.beale_pamphlet_pdf import get_pamphlet_source_text
            has_pamphlet = bool(get_pamphlet_source_text())
        except Exception:
            has_pamphlet = False
        editions_info.append({
            "edition_id": "beale_pamphlet_pdf",
            "status": "available",
            "source": "PDF or beale_papers.txt",
            "date": "1885",
            "provenance": "Beale Papers pamphlet",
            "has_text": has_pamphlet
        })

        try:
            from corpus.beale_doi_adjusted import get_adjusted_tokens
            has_adjusted = bool(get_adjusted_tokens())
        except Exception:
            has_adjusted = False
        editions_info.append({
            "edition_id": "beale_adjusted_doi",
            "status": "available",
            "source": "beale_doi_adjusted.py",
            "date": "1885",
            "provenance": "Standard DOI + 5 FSU Beale adjustments",
            "has_text": has_adjusted
        })
        
        # Check for acquired editions in corpus/editions/
        if self.editions_dir.exists():
            for txt_file in self.editions_dir.glob("*.txt"):
                edition_id = txt_file.stem
                
                # Check if placeholder
                with open(txt_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    is_placeholder = first_line.startswith("[PLACEHOLDER")
                
                if is_placeholder and not include_placeholders:
                    continue
                
                # Load metadata if available
                json_file = self.editions_dir / f"{edition_id}.json"
                if json_file.exists():
                    with open(json_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    editions_info.append({
                        "edition_id": edition_id,
                        "status": metadata.get("status", "available"),
                        "source": metadata.get("source_url", ""),
                        "date": metadata.get("edition_date", "unknown"),
                        "provenance": metadata.get("provenance", ""),
                        "has_text": not is_placeholder,
                        "word_count": metadata.get("word_count", 0)
                    })
                else:
                    # Text file exists but no metadata
                    editions_info.append({
                        "edition_id": edition_id,
                        "status": "available",
                        "source": str(txt_file),
                        "date": "unknown",
                        "provenance": "Manually acquired",
                        "has_text": not is_placeholder,
                        "word_count": 0
                    })
        
        return editions_info
    
    def get_edition_info(self, edition_id: str) -> dict:
        """Get metadata about an edition without loading full text."""
        edition = self.load_edition(edition_id)
        return {
            'edition_id': edition.edition_id,
            'provenance': edition.provenance,
            'date': edition.date,
            'notes': edition.notes,
            'available': bool(edition.source_text),
            'word_count': len(edition.source_text.split()) if edition.source_text else 0
        }


def test_doi_loader():
    """Test DOI edition loader."""
    print("=" * 80)
    print("DOI EDITION LOADER TEST")
    print("=" * 80)
    
    loader = DOICorpusLoader()
    
    print("\n[Step 1] Listing available editions...")
    editions = loader.list_available_editions()
    print(f"Found {len(editions)} editions:")
    for edition_id in editions:
        print(f"  - {edition_id}")
    
    print("\n[Step 2] Loading edition metadata...")
    for edition_id in editions:
        info = loader.get_edition_info(edition_id)
        print(f"\n{edition_id}:")
        print(f"  Provenance: {info['provenance']}")
        print(f"  Date: {info['date']}")
        print(f"  Available: {info['available']}")
        print(f"  Word count: {info['word_count']}")
    
    print("\n[Step 3] Loading beale_embedded edition (full test)...")
    beale_doi = loader.load_edition("beale_embedded")
    print(f"Edition: {beale_doi}")
    print(f"First 100 chars: {beale_doi.source_text[:100]}")
    
    print("\n" + "=" * 80)
    print("DOI LOADER TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_doi_loader()
