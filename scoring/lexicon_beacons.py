"""
Beacon lexicon for Beale Cipher 3 (Names & Residences) domain detection.

Curated list of directional, surveying, terrain, and burial-related words
that would appear in a "names and residences" or treasure-location document.
"""

from typing import Dict, List, Tuple
import re

# Directional beacons
DIRECTION_BEACONS = [
    "NORTH", "SOUTH", "EAST", "WEST",
    "NE", "NW", "SE", "SW",
    "NORTHEAST", "NORTHWEST", "SOUTHEAST", "SOUTHWEST",
    "LEFT", "RIGHT",
]

# Surveying / distance beacons
SURVEY_BEACONS = [
    "MILES", "MILE", "FEET", "FOOT", "YARDS", "YARD",
    "RODS", "ROD", "CHAINS", "CHAIN",
    "PACES", "PACE", "STEPS",
    "DISTANCE", "BEARING", "DEGREES",
    "SURVEY", "MARK", "MARKER", "STAKE",
    "LINE", "POINT", "CORNER",
]

# Terrain / geographic beacons
TERRAIN_BEACONS = [
    "RIVER", "CREEK", "BRANCH", "FORK",
    "MOUNTAIN", "RIDGE", "HILL", "VALLEY",
    "HOLLOW", "GAP", "SPRING", "SPRINGS",
    "ROCK", "ROCKS", "STONE", "CAVE",
    "ROAD", "TRAIL", "PATH", "BRIDGE",
    "TREE", "OAK", "ELM", "PINE", "CEDAR",
    "FIELD", "MEADOW", "CLEARING",
    "COUNTY", "BEDFORD", "VIRGINIA",
    "BUFORD", "BUFORDS", "LYNCHBURG",
]

# Burial / treasure beacons
BURIAL_BEACONS = [
    "VAULT", "BURIED", "DEPOSIT", "DEPOSITED",
    "IRON", "POTS", "GOLD", "SILVER", "JEWELS",
    "TREASURE", "CHEST", "BOX",
    "DEEP", "BELOW", "UNDER", "ABOVE",
    "GROUND", "EARTH", "SURFACE", "DUG",
    "COVER", "COVERED", "HIDDEN",
    "FEET", "INCHES",
]

# Residence / people beacons
RESIDENCE_BEACONS = [
    "COUNTY", "PARISH", "TOWNSHIP",
    "RESIDENCE", "RESIDES", "LIVES", "LIVING",
    "STREET", "HOUSE", "FARM", "PLANTATION",
    "MR", "MRS", "ESQUIRE", "ESQ",
    "JOHN", "WILLIAM", "JAMES", "GEORGE", "THOMAS",
    "ROBERT", "HENRY", "SAMUEL", "DAVID", "BENJAMIN",
]

ALL_BEACONS = sorted(set(
    DIRECTION_BEACONS + SURVEY_BEACONS + TERRAIN_BEACONS +
    BURIAL_BEACONS + RESIDENCE_BEACONS
), key=len, reverse=True)  # longest first for greedy matching


def scan_beacons(stream: str, window_size: int = 30) -> List[Dict]:
    """
    Scan a decoded letter stream for beacon words.

    Returns list of hits with position, beacon word, and surrounding window.
    """
    upper = stream.upper()
    hits = []
    for beacon in ALL_BEACONS:
        start = 0
        while True:
            idx = upper.find(beacon, start)
            if idx < 0:
                break
            win_start = max(0, idx - 5)
            win_end = min(len(upper), idx + len(beacon) + 5)
            hits.append({
                "beacon": beacon,
                "position": idx,
                "window": upper[win_start:win_end],
                "full_window": upper[max(0, idx - window_size // 2):idx + len(beacon) + window_size // 2],
            })
            start = idx + 1
    hits.sort(key=lambda h: h["position"])
    return hits


def score_beacon_density(stream: str, window_size: int = 50) -> List[Dict]:
    """
    Score sliding windows of the stream for beacon density (co-occurrence).
    Returns top windows sorted by beacon count descending.
    """
    upper = stream.upper()
    n = len(upper)
    windows = []
    for i in range(0, n - window_size + 1, window_size // 4):
        chunk = upper[i:i + window_size]
        found = []
        for beacon in ALL_BEACONS:
            if beacon in chunk:
                found.append(beacon)
        if found:
            windows.append({
                "start": i,
                "text": chunk,
                "beacon_count": len(found),
                "beacons": ", ".join(found),
            })
    windows.sort(key=lambda w: w["beacon_count"], reverse=True)
    return windows


def beacon_summary(stream: str) -> Dict:
    """Quick summary: total unique beacons found, total hits, density."""
    hits = scan_beacons(stream)
    unique_beacons = set(h["beacon"] for h in hits)
    return {
        "total_hits": len(hits),
        "unique_beacons": len(unique_beacons),
        "beacon_list": sorted(unique_beacons),
        "density_per_100": round(100 * len(hits) / len(stream), 4) if stream else 0,
    }
