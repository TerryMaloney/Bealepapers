"""
C3 Dragnet v2: Mass text acquisition from Project Gutenberg.

C3 max number is 975, so any text with >= 975 words is eligible.
This dramatically expands the candidate pool vs C1 (max 2906).

Strategy: fetch popular/relevant Gutenberg texts in bulk via their
plain text API. Focus on pre-1830 English texts likely available
in Virginia.
"""

import json
import re
import sys
import time
import urllib.request
import urllib.error
import ssl
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from corpus.keytexts.loader import (
    register_keytext, normalize_and_cache, load_normalized
)
from corpus.keytexts.intake_contract import check_intake

RAW_DIR = Path("corpus/keytexts/raw_sources")
RAW_DIR.mkdir(parents=True, exist_ok=True)

# Gutenberg texts to fetch. Focus on:
# 1. Pre-1830 texts commonly available in Virginia
# 2. Religious, legal, political, literary works
# 3. Texts we DON'T already have
# Format: (gutenberg_id, short_id, title, year)
TEXTS_TO_FETCH = [
    # ===== RELIGIOUS =====
    (8001, "bible_asv", "American Standard Version Bible", 1901),
    (10, "kjv_bible", "King James Bible (Complete)", 1611),
    (8300, "psalms_metre", "Psalms of David in Metre", 1650),
    (7849, "practice_piety", "Practice of Piety", 1612),

    # ===== MASONIC / FRATERNAL =====
    (22384, "masonic_trestle", "Masonic Trestle-Board", 1846),
    (42741, "morals_dogma", "Morals and Dogma - Albert Pike", 1871),

    # ===== POLITICAL / LEGAL =====
    (5, "us_bill_of_rights", "US Bill of Rights", 1791),
    (815, "articles_confederation", "Articles of Confederation", 1781),
    (2008, "locke_civil_govt", "Second Treatise of Civil Government - Locke", 1690),
    (7370, "virginia_bill_rights", "Virginia Declaration of Rights", 1776),
    (3743, "letters_jefferson", "Letters of Thomas Jefferson", 1800),
    (16960, "virginia_code_1819", "Virginia Revised Code 1819", 1819),
    (15553, "monroe_doctrine", "Monroe Doctrine and Related Documents", 1823),
    (1404, "state_of_union_1800s", "State of the Union Addresses (early)", 1790),
    (5669, "annals_congress", "Annals of Congress Selections", 1789),
    (18993, "marshall_life_wash_sel", "Life of Washington Selections - Marshall", 1805),
    (10907, "jeffersons_bible", "Jefferson's Bible", 1820),
    (3032, "notes_virginia_jeff", "Notes on Virginia - Jefferson", 1785),

    # ===== LITERARY - American =====
    (320, "rip_van_winkle", "Rip Van Winkle - Irving", 1819),
    (2188, "legend_sleepy_hollow", "Legend of Sleepy Hollow - Irving", 1820),
    (41, "tom_sawyer", "Tom Sawyer - Twain", 1876),
    (76, "adventures_huck_finn", "Huck Finn - Twain", 1884),
    (6593, "history_ny_knickerbocker", "History of New York - Irving", 1809),
    (809, "wieland_brown", "Wieland - Charles Brockden Brown", 1798),

    # ===== LITERARY - British (widely available in US) =====
    (28885, "arabian_nights", "Arabian Nights", 1706),
    (2701, "moby_dick", "Moby Dick - Melville", 1851),
    (84, "frankenstein", "Frankenstein - Shelley", 1818),
    (98, "tale_two_cities", "Tale of Two Cities - Dickens", 1859),
    (100, "complete_shakespeare", "Complete Works of Shakespeare", 1600),
    (145, "middlemarch", "Middlemarch - Eliot", 1872),
    (161, "sense_sensibility", "Sense and Sensibility - Austen", 1811),
    (121, "northanger_abbey", "Northanger Abbey - Austen", 1817),
    (105, "persuasion", "Persuasion - Austen", 1817),
    (158, "emma", "Emma - Austen", 1815),
    (345, "dracula", "Dracula - Stoker", 1897),
    (4300, "ulysses", "Ulysses - Joyce", 1922),
    (174, "dorian_gray", "Picture of Dorian Gray - Wilde", 1890),
    (45, "anne_of_green_gables", "Anne of Green Gables", 1908),
    (1661, "sherlock_holmes", "Adventures of Sherlock Holmes", 1892),
    (730, "oliver_twist", "Oliver Twist - Dickens", 1838),
    (1260, "jane_eyre", "Jane Eyre - Bronte", 1847),
    (768, "wuthering_heights", "Wuthering Heights - Bronte", 1847),
    (2591, "grimms_fairy_tales", "Grimm's Fairy Tales", 1812),
    (17396, "aesops_fables", "Aesop's Fables", 1820),
    (14859, "night_thoughts", "Night Thoughts - Young", 1742),
    (4705, "seasons_thomson", "The Seasons - Thomson", 1730),
    (5316, "essay_on_man_pope", "Essay on Man - Pope", 1734),

    # ===== PHILOSOPHY / EDUCATION =====
    (3207, "leviathan", "Leviathan - Hobbes", 1651),
    (4363, "enquiry_understanding_hume", "Enquiry Concerning Human Understanding - Hume", 1748),
    (1497, "republic_plato", "Republic - Plato", -380),
    (5827, "meditations_aurelius", "Meditations - Marcus Aurelius", 180),
    (10616, "moral_sentiments_smith", "Theory of Moral Sentiments - Smith", 1759),
    (1228, "emile_rousseau", "Emile - Rousseau", 1762),
    (46333, "social_contract_rousseau", "Social Contract - Rousseau", 1762),

    # ===== HISTORY =====
    (3296, "annals_tacitus", "Annals of Tacitus", 116),
    (10800, "voyage_beagle", "Voyage of the Beagle - Darwin", 1839),
    (6130, "iliad_pope", "Iliad (Pope translation)", 1715),
    (3160, "odyssey_pope", "Odyssey (Pope translation)", 1726),
    (3608, "aeneid_dryden", "Aeneid (Dryden translation)", 1697),

    # ===== ALMANACS / PRACTICAL (era-appropriate) =====
    (12814, "poor_richard_almanack", "Poor Richard's Almanack - Franklin", 1758),
    (20203, "farmers_almanac", "Old Farmer's Almanac excerpts", 1792),

    # ===== SERMONS / RELIGIOUS TEXTS =====
    (1552, "pilgrims_progress_2", "Pilgrim's Progress Part 2 - Bunyan", 1684),
    (4934, "grace_abounding", "Grace Abounding - Bunyan", 1666),
    (6316, "sermons_wesley", "Sermons of John Wesley", 1771),
    (22120, "city_of_god", "City of God - Augustine", 426),
    (1581, "paradise_regained", "Paradise Regained - Milton", 1671),
    (58, "king_lear", "King Lear - Shakespeare", 1606),
    (1524, "hamlet", "Hamlet - Shakespeare", 1603),
    (1513, "romeo_juliet", "Romeo and Juliet - Shakespeare", 1597),
    (23042, "tempest_shakespeare", "The Tempest - Shakespeare", 1611),

    # ===== VIRGINIA-SPECIFIC =====
    (7466, "travels_bartram", "Travels - William Bartram", 1791),
    (4957, "virginia_comedians", "Virginia Comedians", 1854),
    (10339, "byrd_westover", "History of the Dividing Line - William Byrd", 1728),
]


def fetch_gutenberg(gid, retries=2):
    """Fetch plain text from Project Gutenberg mirrors."""
    urls = [
        f"https://www.gutenberg.org/cache/epub/{gid}/pg{gid}.txt",
        f"https://www.gutenberg.org/files/{gid}/{gid}-0.txt",
        f"https://www.gutenberg.org/files/{gid}/{gid}.txt",
    ]
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for url in urls:
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "BealeCipherResearch/1.0"})
                with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                    data = resp.read()
                    for enc in ["utf-8", "latin-1", "cp1252"]:
                        try:
                            return data.decode(enc)
                        except UnicodeDecodeError:
                            continue
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
    return None


def main():
    print("=" * 70)
    print("C3 DRAGNET v2: Mass text acquisition")
    print(f"Targets: {len(TEXTS_TO_FETCH)} texts")
    print("=" * 70)

    stats = {"fetched": 0, "cached": 0, "failed": 0, "intake_rejected": 0}

    for gid, sid, title, year in TEXTS_TO_FETCH:
        raw_path = RAW_DIR / f"{sid}.txt"

        # Skip if already cached
        norm = load_normalized(sid)
        if norm and norm["token_count"] > 0:
            stats["cached"] += 1
            continue

        # Skip if raw exists but not normalized
        if raw_path.exists():
            raw = raw_path.read_text(encoding="utf-8", errors="replace")
        else:
            print(f"  Fetching: {sid} (PG#{gid})...", end=" ", flush=True)
            raw = fetch_gutenberg(gid)
            if raw is None:
                print("FAILED")
                stats["failed"] += 1
                continue

        # Intake contract check
        passed, reason = check_intake(raw, sid)
        if not passed:
            print(f"INTAKE REJECTED: {reason[:60]}")
            stats["intake_rejected"] += 1
            continue

        # Save raw
        raw_path.write_text(raw, encoding="utf-8")

        # Register + normalize
        try:
            register_keytext(sid, title, year=year,
                             source=f"gutenberg:{gid}",
                             notes=f"PG#{gid}",
                             min_tokens_required=975)
            normalize_and_cache(sid, hyphen="keep")
            norm = load_normalized(sid)
            tc = norm["token_count"] if norm else 0
            eligible = "C3-OK" if tc >= 975 else "SHORT"
            print(f"OK ({tc} tokens, {eligible})")
            stats["fetched"] += 1
        except Exception as e:
            print(f"ERROR: {e}")
            stats["failed"] += 1

        time.sleep(0.5)  # rate limit

    print(f"\n{'='*70}")
    print(f"DONE: fetched={stats['fetched']}, cached={stats['cached']}, "
          f"failed={stats['failed']}, intake_rejected={stats['intake_rejected']}")

    # Report eligible texts for C3
    from corpus.keytexts.loader import list_registered
    all_texts = list_registered()
    c3_eligible = [t for t in all_texts if t.get("token_count", 0) >= 975 and t.get("cached")]
    c1_eligible = [t for t in all_texts if t.get("token_count", 0) >= 2906 and t.get("cached")]
    print(f"Total registered: {len(all_texts)}")
    print(f"C3-eligible (>= 975 tokens): {len(c3_eligible)}")
    print(f"C1-eligible (>= 2906 tokens): {len(c1_eligible)}")


if __name__ == "__main__":
    main()
