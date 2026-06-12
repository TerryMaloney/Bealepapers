"""Search driver: sweep candidate key texts x variants over Ciphers 1 and 3."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Iterator

from .corpus import CACHE_DIR, document_stack, iter_corpus
from .data import BealeData
from .engine import DecodeConfig, decode
from .keytext import KeyText, from_doi
from .ngrams import Quadgrams
from .scoring import ScoreReport, default_wordlist, score_text

OOR_MAX = 0.15  # skip decodes with more than this fraction out-of-range


@dataclass(frozen=True)
class Candidate:
    cipher: str
    key_id: str
    extraction: str
    offset: int
    quadgram: float
    ioc: float
    chi2: float
    dict_coverage: float
    n_oor: int
    preview: str

    @classmethod
    def build(
        cls, cipher: str, key: KeyText, cfg: DecodeConfig, text: str,
        n_oor: int, score: ScoreReport,
    ) -> "Candidate":
        return cls(
            cipher=cipher,
            key_id=key.id,
            extraction=cfg.extraction,
            offset=cfg.offset,
            quadgram=round(score.quadgram, 4),
            ioc=round(score.ioc, 5),
            chi2=round(score.chi2, 1),
            dict_coverage=round(score.dict_coverage, 4),
            n_oor=n_oor,
            preview=text[:120],
        )


def variant_key(cipher: str, key_id: str, extraction: str, offset: int) -> str:
    return f"{cipher}|{key_id}|{extraction}|{offset}"


def _load_done(checkpoint: Path) -> set[str]:
    done: set[str] = set()
    if checkpoint.exists():
        with open(checkpoint, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done.add(variant_key(rec["cipher"], rec["key_id"],
                                     rec["extraction"], rec["offset"]))
    return done


def run_search(
    data: BealeData,
    ciphers: tuple[str, ...] = ("C1", "C3"),
    keytexts: Iterable[KeyText] | None = None,
    extractions: tuple[str, ...] = ("first", "last"),
    offsets: tuple[int, ...] = (0,),
    checkpoint: str | Path = CACHE_DIR / "search_ckpt.jsonl",
    quad: Quadgrams | None = None,
) -> list[Candidate]:
    """Decode every cipher x key x variant, score, checkpoint, and rank."""
    quad = quad or Quadgrams.load()
    words = default_wordlist()
    checkpoint = Path(checkpoint)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    done = _load_done(checkpoint)

    results: list[Candidate] = []
    with open(checkpoint, "a", encoding="utf-8") as ckpt:
        for key in keytexts if keytexts is not None else _default_keytexts(data):
            for cipher in ciphers:
                numbers = data.cipher_for(cipher)
                if max(numbers) > len(key.tokens):
                    continue  # key too short; stacks handle the long cases
                for extraction in extractions:
                    for offset in offsets:
                        vk = variant_key(cipher, key.id, extraction, offset)
                        if vk in done:
                            continue
                        cfg = DecodeConfig(extraction=extraction, offset=offset)
                        res = decode(numbers, key.tokens, cfg)
                        if res.oor_fraction > OOR_MAX:
                            continue
                        sc = score_text(res.text, quad, words)
                        cand = Candidate.build(cipher, key, cfg, res.text, res.n_oor, sc)
                        results.append(cand)
                        ckpt.write(json.dumps(asdict(cand)) + "\n")
    results.sort(key=lambda c: c.quadgram, reverse=True)
    return results


def _default_keytexts(data: BealeData) -> Iterator[KeyText]:
    """Embedded DOI, every corpus text, and DOI-stacks for C1's high numbers."""
    doi = from_doi(data)
    yield doi
    for kt in iter_corpus():
        yield kt
        # C1 needs >= 2906 words; the era hypothesis is DOI followed by a
        # second document. Try DOI + each corpus text as a stack.
        if len(kt) >= 1600:
            yield document_stack([doi, kt])


def load_ranked(
    checkpoint: str | Path = CACHE_DIR / "search_ckpt.jsonl",
    cipher: str | None = None,
    top: int = 25,
) -> list[Candidate]:
    cands: dict[str, Candidate] = {}
    with open(checkpoint, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            c = Candidate(**rec)
            if cipher and c.cipher != cipher:
                continue
            cands[variant_key(c.cipher, c.key_id, c.extraction, c.offset)] = c
    ranked = sorted(cands.values(), key=lambda c: c.quadgram, reverse=True)
    return ranked[:top]
