"""
Key-text loader: normalize, tokenize, and cache arbitrary plaintext documents
for use as candidate Beale cipher keys.

Design:
  - Raw texts live in corpus/keytexts/raw_sources/<id>.txt
  - Normalized (tokenized) outputs cached in corpus/keytexts/normalized/<id>.json
  - Registry at corpus/keytexts/registry.json tracks provenance
"""

import json
import hashlib
import re
from pathlib import Path
from typing import List, Optional, Dict

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw_sources"
NORM_DIR = BASE_DIR / "normalized"
REGISTRY_PATH = BASE_DIR / "registry.json"


def _load_registry() -> dict:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_registry(reg: dict):
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)


def register_keytext(kid: str, title: str, year: int = 0,
                     source: str = "manual", notes: str = "",
                     tokenizer_preset: str = "default",
                     min_tokens_required: int = 0) -> dict:
    """Add or update an entry in the registry. Returns the entry dict."""
    reg = _load_registry()
    existing = {e["id"]: e for e in reg["keytexts"]}
    entry = {
        "id": kid,
        "title": title,
        "year": year,
        "source": source,
        "notes": notes,
        "tokenizer_preset": tokenizer_preset,
        "min_tokens_required": min_tokens_required,
    }
    existing[kid] = entry
    reg["keytexts"] = list(existing.values())
    _save_registry(reg)
    return entry


def normalize_text(raw: str, join_hyphenation: bool = True,
                   strip_gutenberg_header: bool = True) -> str:
    """
    Normalize a raw text: fix line-break hyphenations, collapse whitespace,
    strip Project Gutenberg boilerplate if present.
    """
    text = raw

    if strip_gutenberg_header:
        markers_start = [
            "*** START OF THIS PROJECT GUTENBERG",
            "*** START OF THE PROJECT GUTENBERG",
            "***START OF THE PROJECT GUTENBERG",
        ]
        markers_end = [
            "*** END OF THIS PROJECT GUTENBERG",
            "*** END OF THE PROJECT GUTENBERG",
            "***END OF THE PROJECT GUTENBERG",
            "End of the Project Gutenberg",
            "End of Project Gutenberg",
        ]
        for m in markers_start:
            idx = text.find(m)
            if idx >= 0:
                nl = text.find("\n", idx)
                text = text[nl + 1:] if nl >= 0 else text[idx + len(m):]
                break
        for m in markers_end:
            idx = text.find(m)
            if idx >= 0:
                text = text[:idx]
                break

    if join_hyphenation:
        text = re.sub(r'-\s*\n\s*', '-', text)
        text = re.sub(r'(\w)-\s+(\w)', r'\1-\2', text)

    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def tokenize_simple(text: str, hyphen: str = "keep",
                    apostrophe: str = "keep") -> List[str]:
    """
    Simple tokenizer for arbitrary texts. Splits on whitespace, strips
    punctuation from edges, keeps internal hyphens/apostrophes per config.
    """
    text = re.sub(r'[.,;:!?()\[\]{}"]+(?=\s|$)', '', text)
    text = re.sub(r'(?<=\s)[.,;:!?()\[\]{}"]+', '', text)

    if hyphen == "split":
        text = text.replace("-", " ")

    tokens = text.split()

    cleaned = []
    for tok in tokens:
        t = tok.strip('.,;:!?()[]{}"\x27`~*#@^&_=+<>/\\|')
        if apostrophe == "strip":
            t = t.replace("'", "")
        if t and not t.isdigit():
            cleaned.append(t)
    return cleaned


def normalize_and_cache(kid: str, raw_text: Optional[str] = None,
                        hyphen: str = "keep",
                        apostrophe: str = "keep",
                        skip_intake_check: bool = False) -> dict:
    """
    Normalize + tokenize a key text and cache the result.
    If raw_text is None, reads from raw_sources/<id>.txt.
    Returns dict with tokens, token_count, raw_hash.
    Runs intake contract by default; set skip_intake_check=True to bypass.
    """
    if raw_text is None:
        raw_path = RAW_DIR / f"{kid}.txt"
        if not raw_path.exists():
            raise FileNotFoundError(f"Raw text not found: {raw_path}")
        raw_text = raw_path.read_text(encoding="utf-8")

    if not skip_intake_check:
        from corpus.keytexts.intake_contract import check_intake
        passed, reason = check_intake(raw_text, kid)
        if not passed:
            raise ValueError(f"Intake contract FAILED for '{kid}': {reason}")

    norm = normalize_text(raw_text)
    tokens = tokenize_simple(norm, hyphen=hyphen, apostrophe=apostrophe)
    raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    result = {
        "id": kid,
        "tokens": tokens,
        "token_count": len(tokens),
        "tokenizer_preset": f"hyphen_{hyphen}_apo_{apostrophe}",
        "raw_hash": raw_hash,
    }

    NORM_DIR.mkdir(parents=True, exist_ok=True)
    out_path = NORM_DIR / f"{kid}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    return result


def load_normalized(kid: str) -> Optional[dict]:
    """Load cached normalized tokens. Returns None if not cached."""
    path = NORM_DIR / f"{kid}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_keytexts(min_tokens: int = 0) -> List[dict]:
    """
    Load all registered keytexts that have cached normalized tokens.
    Optionally filter by minimum token count.
    Returns list of dicts with id, title, tokens, token_count, etc.
    """
    reg = _load_registry()
    results = []
    for entry in reg["keytexts"]:
        kid = entry["id"]
        norm = load_normalized(kid)
        if norm is None:
            continue
        if min_tokens > 0 and norm["token_count"] < min_tokens:
            continue
        merged = {**entry, **norm}
        results.append(merged)
    return results


def list_registered() -> List[dict]:
    """List all registry entries (without loading tokens)."""
    reg = _load_registry()
    results = []
    for entry in reg["keytexts"]:
        kid = entry["id"]
        norm_path = NORM_DIR / f"{kid}.json"
        entry_copy = dict(entry)
        if norm_path.exists():
            with open(norm_path, "r", encoding="utf-8") as f:
                n = json.load(f)
            entry_copy["token_count"] = n["token_count"]
            entry_copy["cached"] = True
        else:
            entry_copy["token_count"] = 0
            entry_copy["cached"] = False
        results.append(entry_copy)
    return results


if __name__ == "__main__":
    print("=== Key-text Registry ===")
    for e in list_registered():
        status = "OK" if e["cached"] else "TODO"
        print(f"  [{status}] {e['id']:30s}  tokens={e['token_count']:6d}  {e['title']}")
