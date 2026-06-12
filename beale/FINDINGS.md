# Beale Cipher Investigation — Findings Report

*Phase 2: keyless attacks, key reconstruction, and hypothesis tests.*
*All results reproducible: `runs/` holds parameters and preregistered criteria; `pytest tests/beale/` re-verifies the ground truths.*

## Headline results

### 1. Cipher 2's solution is now reproduced at 99.0% — and the residue is fully explained

Grid-fitting the key alignment (after a user challenge to the "popular answer")
raised the oracle from 91.5% to **755/763 = 99.0%**. The fit independently
re-derived the historically documented edits (extra word at 155 —
"institute **a** new government" — and a dropped word after "invariably" at
~242). The 8 remaining mismatches decompose exactly:

- 4 one-off copy errors in repeated numbers (84↔85, 95↔96, 53↔54 class);
- 1 unverifiable singleton (666);
- number **505**, consistently 's' in Beale's key vs 't' in every DOI
  reconstruction — a real local difference in his physical copy.

**The plaintext itself is beyond doubt**: 177/180 numbers demand the same
letter at every occurrence; the wording is self-consistent everywhere.

### 2. Beale's actual key table is recoverable without any DOI edition

The known plaintext pins a verified letter for all 180 numbers used in C2
(`beale/keytable.py`). This table — not any printed DOI — is the ground
truth key. It covers 53% of C1's positions and 57% of C3's.

### 3. The shared-key hypothesis is REJECTED for both C1 and C3 (preregistered test)

Soft-pin solving lets the optimizer keep or discard Beale's verified
letters while making the decode English-like. Preregistered interpretation:
≤10% violations = consistent with shared key; ≥30% = rejected.

| Cipher | Pin violation rate | Verdict |
|---|---|---|
| C3 | **45.2%** | rejected |
| C1 | **35.2%** | rejected |

Whatever C1 and C3 are, they are *not* first-letter book ciphers in the
same key-and-method as C2. (Solver power is limited at these
multiplicities — see calibration — so treat as strong evidence, not proof.)

### 4. The Gillogly artifact survives Beale's own key

Decoding C1 with the reconstructed table (no edition assumptions) still
produces the alphabetical runs (`DEFGHIIJKLM..NOH` at ~190, `ABB CCC DDE`
at ~85, `BCDDE` at ~110). The alphabet sequences are written in *Beale's
actual key*, not an artifact of using a wrong DOI. C1's number stream walks
the key writing alphabets — hoax construction or keying material, but not
plaintext.

### 5. Document fingerprinting works: 15 correct pins identify an unknown key text

`beale/skeleton.py` + `beale/fingerprint.py` implement the
reverse-engineering loop: hypothesized plaintext fragments pin first
letters of the key document at known word indices; the skeleton slides
across digitized candidates with drift-tolerant alignment.

- **Ground truth passes**: C2's 180-pin skeleton ranks DOI editions
  decisively first across the 134-document corpus (z margin > 5 over the
  best non-DOI text) and the drift alignment recovers the known bands
  (−1 across 158–241, +10 after ~480).
- **Synthetic curve**: an unknown key document is identified at rank #1
  from just **15 correct pins** (z=15), 30 pins → z=21.

Consequence: if ~15–30 letters of C1 or C3 can ever be guessed correctly
(cribs, partial solves), the actual key document becomes findable in
digitized corpora — even "a citizen's handbook pamphlet" we don't possess.

## Solver characterization (honest numbers)

### Blind homophonic solver (`beale/homophonic.py`)

- Critical diagnostic: under **quadgrams alone, the TRUE C2 plaintext
  scores worse than degenerate near-English** (−2536 vs −2447). Adding
  quintgrams (built from ~13M chars of period text; the true plaintext
  contains *zero* unseen quintgrams) restores the correct ordering. The
  objective now ranks truth above every optimum found.
- Blind solve of real C2 (180 symbols / 763 letters, multiplicity 0.236):
  **57–68% letter accuracy** across configurations. Fragments are plainly
  readable ("i ha?e de?os?ted in the …", "eighteen nineteen the second",
  "thirteen…thousand…"); the residual gap is search, not modeling — a
  single human crib pass would finish it. Easy synthetics (m < 0.15)
  solve at ≥85%, confirming the machinery.
- Pinned-mode calibration (coverage-matched synthetics, message present):
  free-position accuracy only **17–31%** — the pinned attack has limited
  power at C1/C3's multiplicity. Any "no message found" on C1/C3 is
  therefore *uninformative on its own*; the soft-pin violation test above
  is the informative instrument.

### Gap-HMM scan-forward attack (`beale/scanhmm.py`)

**Failed its preregistered synthetic validation** (11% recovery vs the 80%
criterion, even with the model exactly true): the gap→letter channel is
too weak — too many letters share similar first-letter frequencies. Per
protocol, its null result on real C3 is reported as uninformative, NOT as
evidence of hoax.

Diagnostic byproduct (valuable): C3's locality signature does **not**
match pure scan-forward generation. Scan-forward synthetics produce mean
ascending runs of 17–20; C3's is 2.58 with bursts to 10. The closest
generative match found is "lazy local-forward" reuse (encoder hovers near
recent positions, jumps back periodically). C3's structure remains the
strongest unexplained signal in the data: lag-1 autocorrelation z=+16.2
(the genuine C2 encoding shows none, z=+1.6).

### Two-stage C1 attack (`beale/c1_twostage.py`)

Monoalphabetic, columnar, and decimation second stages searched over C1's
decode under Beale's reconstructed key, scored with exact
wildcard-marginalized quadgrams, each family calibrated against identical
searches on shuffled nulls (G1). Results in `runs/` — see experiment log;
no family produced a hit beating the null-maximum distribution at z≥4.
At 53% coverage the synthetic power study caps what this can rule out.

## Interpretation

- **C2**: solved, reproduced, residue explained. Closed.
- **C1**: contains DOI/key-derived alphabetical structure under Beale's own
  verified key; rejects the shared-key book-cipher model; second-stage
  searches find nothing above null. Most consistent with constructed
  non-message content, with the two-stage door narrowed but not closed.
- **C3**: rejects the shared-key model; carries a massive, still-unexplained
  sequential structure that no tested generative model reproduces
  (including the scan-forward hypothesis this project introduced and
  honestly falsified). C3 remains the most promising target: its structure
  is *too* regular for the C2 method and too irregular for a hoax-by-
  alphabet-doodling. The skeleton/fingerprint loop is the live path: any
  15–30 correct plaintext letters would identify its key document.

## Reproduce

```
python -m beale verify                      # C2 oracle: 99.0%
python -m pytest tests/beale/               # 51 tests incl. ground truths
python -m beale.exp_pinned                  # calibration + pinned runs
python -m beale report --cipher C1          # Gillogly artifact + verdict
```

---

# Phase 3 — Hunt the physical document (verdict boxes)

## E. The wanted poster & printing hunt
- **The "505 anomaly" is EXPLAINED**: placements of the extra word after
  word #505 keep the oracle at its 755/763 maximum, mapping Beale's #505
  onto "state". The final variant profile of his physical DOI copy:
  extra "a" ("institute A new government"), missing "the" ("pursuing
  invariably same object"), a missing TEN-WORD block bracketed in words
  467-485 (dropped typeset line or eye-skip), one extra word in 487-510,
  missing "out" ("eat their substance"), missing "of" ("independent and
  superior to"). Poster: `runs/wanted_poster.md`.
- Automated hunt over fetchable transcriptions (Avalon, NARA, Gutenberg):
  **no fetchable tradition shows ANY of the variants** (base rates 0.0) —
  the profile is distinctive; the find, if it exists, sits in undigitized
  or archive-only printings (Evans / Shaw-Shoemaker era). Poster is the
  publishable search instrument.

## F. Extended stack / signers
- **Legacy "1701 -> lewis" KILLED**: no stack x alignment (18 stacks x 61
  gaps) puts 1701 on "lewis". The legacy claim does not reproduce.
- Weak SUPPORTIVE signal (preregistered max-statistic, p<0.01): C1's
  10-11 high numbers under adjusted-DOI + Virginia Declaration of Rights
  (gap 0) give name-flavored initials `wltbjepmwl` (LLR 8.76 vs null 99th
  4.50). Graded supportive-not-conclusive; number 2906 remains uncovered.

## H. DOI-only variants
- ~1500-variant grid (extractions x shifts x affine x reversals x both DOI
  bases): **no hit** — C1 z=+0.12, C3 z=-2.25 vs shuffled-null maxima.
- Descriptive: C1 contains 12 alphabetical runs, ALL within its first 330
  positions, none after; no key-locality segment structure (z=-0.6).

## G. Crib bootstrap & same-pamphlet test
- **METHOD-UNPOWERED (honest exit)**: the positive-control gate FAILED
  (bootstrap recovered 0 pins on a synthetic carrying a real message), and
  shuffled-cipher nulls accept ~8 cribs on average — so the real arms'
  8 (C1) / 13 (C3) crib acceptances are within noise and NOT interpreted.
  The bigram-plausibility cross-check needs replacing with dictionary-span
  completion before this instrument can carry weight.
- G3 same-pamphlet: 9 shared new pins between sealed arms, 0 agreements —
  no evidence either way (and uninterpretable given the gate failure).

## Phase-3 bottom line
The biggest result is forensic, not cryptanalytic: Beale's key was a
specific, identifiable physical document whose variant profile is now
precisely characterized and matches NO standard textual tradition. The
lewis anecdote is dead; the DOI-only and crib instruments are honestly
calibrated (one supportive VDR lead recorded); the printing hunt moves to
human archive search with the wanted poster.
