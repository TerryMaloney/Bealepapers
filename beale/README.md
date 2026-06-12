# beale — clean-room Beale cipher engine

A small, tested, self-contained attack engine for the three Beale ciphers.
It does not import any legacy module from the repo root; its only inputs are
`beale_papers.txt` and (optionally) `corpus/keytexts/normalized/*.json`.

## Why it exists

The legacy pipeline's own Cipher 2 oracle scored 26.5% — on the *solved*
cipher — because it hardcoded a wrong offset (335) and a wrong key-text
concatenation. This package replaces it with a provably correct core.

## Results

| Test | Result |
|------|--------|
| Cipher 2 vs embedded DOI, raw first-letter decode | 83.6% |
| + fitted key-text edits + documented 811→y / 1005→x homophones | **91.5%** (gate ≥90%) |
| Remaining mismatches | 65 scattered single-letter transcription errors, max run ≤5 — the signature of correct alignment |
| Cipher 1 vs DOI | reproduces the **Gillogly alphabetical artifact** (`defghiijklmmno` at position 185): key-dependent structure, not a message |
| Cipher 3 vs DOI | statistically indistinguishable from random |
| Corpus sweep (134 texts × C1/C3 × first/last + DOI stacks, 1000+ candidates) | no candidate exceeds the z≥3 language threshold (C2 control: z=+25) |

## Usage

```
python -m beale verify                  # C2 oracle; exit 1 on regression
python -m beale report --cipher C1     # diagnostics + honest verdict
python -m beale search --ciphers C1,C3 [--web] [--gutenberg ID ...]
python -m beale rank --cipher C1 --top 25
python -m pytest tests/beale/          # 32 tests; test_oracle_c2.py is the gate
```

Search results checkpoint to `corpus/cache/search_ckpt.jsonl` (resumable).

## Module map

- `data.py` — parse ciphers + numbered DOI from `beale_papers.txt` (validated)
- `engine.py` — pure book-cipher decode (first/last/nth, offsets, overrides)
- `edits.py` — key-text word edits vs cipher-number overrides (kept separate)
- `oracle.py` — the C2 correctness gate
- `ngrams.py` / `scoring.py` — quadgram log-prob, IoC, chi², dictionary coverage
- `corpus.py` / `keytext.py` — candidate key texts + document stacks
- `diagnostics.py` — Gillogly/artifact detection, shuffled-baseline z-scores
- `search.py` — checkpointed sweep driver
- `fetch.py` — optional web fetch (NARA Stone DOI, Project Gutenberg)

Regenerate quadgram stats (committed at `resources/quadgrams.txt`) with
`python -m beale.ngrams`.
