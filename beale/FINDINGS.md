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

---

# Phase 4 — Function words, the soft skeleton, and the dictionary attack

## J. Repeated-pattern / function-word attack (user-proposed; mechanism VALIDATED)
- On the solved C2, repeated number n-grams are unmistakable (bigram z=+4.7,
  trigram z=+8.7 vs shuffles) and decode to exactly the top English
  fragments: 'ed' 've' 'th' 'in' 'ne' 'es' 'on' 'ng' / 'her' 'nds' 'ove'.
  The reverse-engineering logic works as conceived.
- **C1 and C3 contain NO repeated-pattern structure** (z ~ 0; 0-2 repeated
  patterns vs C2's 39+3). New discriminator: C3 has strong number-VALUE
  locality but zero number-PATTERN repetition — the opposite signature of
  encoded English for this encoder. J2 mapping on C1/C3: unpowered by
  preregistered gate; not run on real ciphers.

## K. Soft skeleton — "Guess Who in reverse"
- Count->letter calibration from C2's verified table behaves exactly as
  theory predicts (5+ uses -> e/t/n/o/r/i).
- Soft fingerprint matcher: on C2's numbers ALONE (no plaintext) it ranks
  the DOI #1 at the correct offset — but with z-margin +1.5 over the best
  non-DOI doc (< the preregistered 3): **gate FAILED**, so C3/C1 scans are
  leads-only. Neither cipher produced a lead separating from noise.
- Dossier (`runs/c3_dossier.md`): C3's key document is >=975 words and
  likely ends near there (dense usage to the edge), was consulted LOCALLY
  (lag-1 +0.61; C2's encoder jumped freely), with its most-consulted words
  listed (e.g. word #96 used 13x, most likely e/t-initial). C1 sheet
  included. This is the archive-hunting companion to the wanted poster.

## L. NEW THREAD: alphabetized-key (dictionary) attack — REJECTED
- A monotone 25-threshold number->letter fit (the signature of any
  alphabetized key: dictionary, index, gazetteer) with full controls:
  synthetic dictionary cipher recovered 87% (PASS), C2 negative control
  does not fire (z=-1.76, PASS).
- **C3: z=-2.47 — not an alphabetized key. C1: z=+0.28 — no hit.**
  C3's ascending runs are NOT explained by dictionary-column scanning.

## Phase-4 bottom line
The user's function-word mechanism is real — proven on C2 — and its
absence in C1/C3 is now one of the cleanest quantitative discriminators in
the literature: genuine Beale encoding leaves repeated-pattern structure
and C1/C3 have none, while C3's number-value locality matches no encoding
model tested (book-cipher, scan-forward, lazy-forward, dictionary). The
dossier and wanted poster together define what any candidate key document
must look like; the burden now sits on undigitized archives.

## Phase 4b — outside-the-box quick probes (all null, all cheap)

Preregistered as a screening battery: chase only z>=4 signals; none appeared.

| Probe | Result |
|---|---|
| Caesar shift k=1..25 on keytable decode (C1 "one off", C3 "three off") | k=0 best for both; no shift helps |
| Modular wraparound indexing (count past the end, restart) mod 1322/1311 | scores below even shuffled-wrap null |
| Wraparound x Caesar grid (52 cells/cipher) | best cell is k=0; nothing |
| Numbers as letters directly (n mod 26, offsets 0/1) | deep random (-8.2 to -8.5) |
| Pamphlet-prose acrostics (paragraph/sentence initials, every-Nth-word of the Jan 4 letter) | all at/below random (-6.7 to -8.2); prose numbers are just the story's dates |
| C2's decoded plaintext as the key for C1/C3 (letter-wise and word-wise, with wrap) | within shuffle null (z ~ +1) |

## Phase 4c — C1 examined fresh (no C2 knowledge assumed)

Raw-stream profile of C1's 520 numbers:
- Heavily low-skewed: median 123; 44% <=100, 75% <=350, 98% <=1322. Ten
  high outliers (>1322), arriving early (pos 3, 8, 33) and in two ADJACENT
  PAIRS at positions (170,171) and (390,391).
- Stationary along its length (thirds have near-identical means, distinct
  counts, and repeat shares) - the process that generated C1 did not
  change mid-stream.
- Mild sequential locality (lag-1 +0.25 vs shuffle 0) - between C2's none
  (+0.04) and C3's extreme (+0.61).
- No arithmetic progressions, no consecutive-integer steps.
- **Temporal reuse clustering: C1 re-uses a number sooner than chance
  (median repeat gap 97 vs 173 expected) - and this matches the GENUINE
  encoder's habit exactly (C2: 72 vs 254). First structural property
  linking C1's generation to real encoding behavior (memory effect:
  "just looked that one up") rather than to free doodling.**
- Methodological save: last-digit bias is NOT a construction tell -
  genuine C2 is the most biased of the three (chi2=138) because of
  favorite-number reuse. C3 is actually the most digit-uniform.

The "what C1 is NOT" ledger (all calibrated): not a first-letter book
cipher on Beale's own key; not any of ~1500 extraction/shift/affine/
reversal DOI variants; not dictionary/alphabetized-keyed; not mono-sub/
columnar/decimation over its keyed decode; not Caesar-shifted, wrapped,
mod-26, or keyed by C2's plaintext; lacks the repeated-pattern structure
genuine English encoding leaves. Yet decisively non-random (locality,
reuse-memory, alphabet walks under the key).

Open thread this suggests: C1's plaintext, if any, may not be PROSE -
surveyor/bearing notation ("N32E 40 poles"-style, abbreviation- and
number-dense) would defeat every English language model used so far while
matching a "locality of the vault" document. A notation-aware scoring
model is the natural next instrument.

## Phase 4d — survey/deed-notation instrument (built, validated, verdict null)

- New `exp_survey.py`: period metes-and-bounds language model (mined from
  Hening's statutes land grants + template-generated bearing calls), a
  ~85-word survey lexicon (directions incl. single-letter abbreviations,
  units: poles/perches/chains, landmarks: white oak/branch/ford, spelled
  numbers, connector phrases "near the"/"under a"/"thence").
- Instrument validation PASSES with teeth: survey samples prefer the
  survey LM (+1.47), prose prefers English (-0.81), and the genuine C2
  decode rejects survey decisively (z=-9.0).
- **Verdicts**: C1's keyed decode shows NO survey-language preference
  beyond its letter bag (z=+0.77; C3 +0.75). Corpus-wide re-sweep of C1
  under the survey LM: all docs at the shuffled-reference level. Survey
  crib pings against verified pins: 2 found vs 2.2±1.5 expected by chance
  (the lone reviewable lead: 'west(erly)' @ position 313).
- Scope caveat: this tests survey notation under Beale's key and under
  every corpus key text; a survey plaintext under an UNKNOWN key remains
  untestable until a key candidate exists. The LM and lexicon are now
  permanent equipment for scoring any future candidate decode.

## Phase 4e — unconscious-pattern battery on C1 (10 probes) + hunt re-check

Poster hunt re-run: still no fetchable printing showing any Beale variant
(5 clean DOI sources; IA full-text unreachable from this network). The
archive search remains a human task with runs/wanted_poster.md.

10-probe battery on C1's raw numbers (shuffle-calibrated):
- **SIGNAL: leading-digit alternation (z=-3.6).** Adjacent numbers share a
  leading digit far LESS than chance (53 vs 79) - even though their VALUES
  correlate positively. The author hopped between adjacent magnitude bands
  (80s -> 110s -> 90s...) while avoiding same-band repeats: a deliberate-
  variation fingerprint typical of hand-fabricated "random" sequences.
- **SIGNAL: median-runs (z=-4.9).** Long stretches above/below the median -
  the banding behind the +0.25 locality, now quantified.
- Null: near-duplicate clustering, round-number rhythm, zigzag entropy,
  periodicity (lags 2-40), second-digit chi2, block trends, small-number
  burstiness (|z| < 1.2 each).
- **Same-hand evidence: the habit vectors of C1, C2, C3 are IDENTICAL on
  sign-entropy (2.86-2.87) and leading-1 share (0.27-0.29)** while
  differing only on locality/reuse - consistent with one author (or one
  generation pipeline) behind all three streams, operating with different
  discipline per cipher.

## Phase 4f — C3 number-pattern battery (5 signals) + name-ping hunt

10 shuffle-calibrated probes on C3's raw numbers:
- **Suppressed resets (z=-9.2)**: only 57 big downward jumps vs 106
  expected - the stream climbs in long ascents and avoids dropping.
- **Irregular segment lengths (z=+3.2)**: ascent lengths range 1-41,
  MORE irregular than chance. A tidy 30-record list (618/30 ~ 20.6) is
  NOT what the structure shows; if it is a list, record lengths vary
  wildly (long residences/heir clauses?) or the segmentation is illusory.
- **Weak periodicity at lags 15-35 (z=+3.0).**
- **Extreme banding (runs z=-10.0).**
- **Cross-segment number sharing (z=+12.4)**: the ~58 ascending sweeps
  re-draw from a SHARED low-number pool - the author restarts near the
  "top of the page" and re-walks the same region, sweep after sweep.
  Generative picture: restart-and-walk with wildly varying sweep lengths.
- Null: within-segment slope, #96 spacing, lead-digit repeats,
  near-duplicates, segment-start concentration (|z| < 3).

Known-associates name hunt (34 period names incl. beale/morriss/buford/
ward/witcher/otey/leftwich/callaway...) against C3's verified pins
(>=4 pinned letters, 0 conflicts): **0 pings** (chance 0.0) - no associate
name is compatible with Beale's-key letters at any C3 position; consistent
with the established shared-key rejection. Caveat: tests first-letter
encoding under Beale's key only; names under an unknown key remain open.

## Phase 5 — external test-packet triage (GPT/Gemini lists) + new battery

Already answered by prior phases: changepoints (C1 stationary), C3
generator fit (lazy-local-forward closest), key-string provenance (the
Gillogly string survives Beale's own reconstructed key, appears in no
other transform, absent from controls), cross-cipher overlap counts, C3
source-size density, segment scans, structural fingerprints.

New tests run (with the packet's evidence labels):
- Grid-coordinate split (page/word): KILLED BY CONTROL - genuine C2 shows
  the same "bounded remainder" pattern as C1/C3 (low-skew artifact).
- Deinterleaving k=2..4 (polyalphabetic rotation): substreams LOSE all
  locality (lag-1 ~ 0 vs whole-stream +0.25) - C1's structure lives in
  directly adjacent pairs; no rotation. HARD FACT, hypothesis killed.
- Delta-as-cipher (|diff| mod 26): null for C1 and C3.
- Table-width residue scan w=2..80: C2 (genuine) has the LARGEST peak
  (z=29.8 at w=65, favorite-number reuse) - residue peaks are NOT table
  evidence. C1's w=2 parity bias and C3's w=50 noted as curiosities.
- **C2 author-selection generator (HARD FACTS, the packet's best test)**:
  the genuine encoder picked the LOWEST-index homophone with massive bias
  (mean chosen rank 0.10 vs 0.5 uniform) and a near-quartile option 74%
  of the time. All three ciphers share extreme low-bias (median/max:
  C1 0.042, C2 0.085, C3 0.097) - C1 is even more low-biased than the
  genuine cipher. The author habit transfers.
- **WORKSHEET HYPOTHESIS (new, ours): EXPLORATORY LEAD.** C2's numbers
  preferentially coincide with C1's alphabetical-run regions (50% vs 35%
  of non-run numbers, z=+2.7 raw) - consistent with C1's alphabet runs
  being table-building scratch work connected to the C2 encoding session.
  Magnitude-controlled (<=350) the differential persists but shrinks
  (65% vs 53%, ~z 1.7): lead, not signal. A targeted test (do C2's
  homophones for letter X concentrate inside C1's letter-X run?) is the
  natural follow-up.

## Phase 5b — the worksheet test resolves the Gillogly run: PRACTICE BEHAVIOR

Letter-resolved rank analysis (rank of each run number within its letter's
full index list in Beale's adjusted DOI):
- Across all 12 runs: mean rank-std 30 vs random-pick baseline 44, mean
  within-run ascending fraction 56% - neither pure worksheet-column
  (rank-std ~0) nor pure forward-scan doodle (ascending ~100%).
- **The famous Gillogly run @187-204 converges to RANK 1**:
  a17 b13 c8 d11 e3 f2 g2 h1 i6 i2 j1 k1 l1 m1. Its tail takes the FIRST
  occurrence in the document of each successive letter (first h-word,
  first j/k/l/m-words). Under random same-letter choice the rank-1
  convergence on the tail letters is ~1e-3 improbable.
- Interpretation (new): the cleanest alphabet run is PRACTICE or
  DEMONSTRATION encoding - someone learning or showing the DOI system by
  enciphering the alphabet, grabbing each letter's most findable (first)
  instance, starting sloppily (a17, b13) and becoming systematic (rank 1)
  as the alphabet proceeds. Run @82-94 shows the same low-rank tendency
  (b2 c3 c4 d4...); the other runs are messier.
- This sharpens the C1 verdict: at least its cleanest alphabetical
  structure is encoding PRACTICE with the real C2 key, embedded inside a
  number stream that otherwise matches the author's habits but no message
  model - strongly consistent with C1 being a constructed/filler document
  produced by someone who possessed and practiced the genuine C2 system.

## Phase 5c — C3 letter-intent test: the walker wasn't hunting letters

The discriminating question for C3's ascending sweeps: when stepping from
number a to number b, did the author land on the FIRST instance of b's
letter after position a (letter-targeting = encoding intent), or land at
positions whose letters are incidental (position-dragging)?

- **C3: exactly chance (87 first-instance landings vs 88 expected,
  z=-0.1).** Zero letter-targeting with respect to Beale's DOI. The
  sweeps are movement through POSITIONS, not searches for letters.
- C1: z=+1.2 (mild); genuine C2: z=+1.7 (weak positive, as expected for
  a non-walking encoder).
- Scope: this is decisive only against Beale's own key; letter-intent
  toward an unknown second text remains untestable without that text.

Combined verdict across phases: one hand produced all three streams
(habit-vector match); C2 is genuine encoding; C1 embeds rank-1-converging
PRACTICE alphabets in habit-bearing filler; C3 is a mechanical position
walk with no letter intent toward the only key known to exist. The
remaining live hypothesis for a genuine C1/C3 message requires a second
physical key text - precisely the object the wanted poster and dossier
were built to find.

## Phase 5d — user-supplied volume: "The American's Guide" (HathiTrust, 1820s-30s)

Tested THE AMERICAN'S GUIDE (Declaration, Articles of Confederation, US
Constitution, and the state constitutions; 222,742 tokens) - the exact
compilation genre the one-book hypothesis predicted:
- **WANTED-POSTER PING: predicate P1 HITS** - this volume reads "to
  institute A new government", the extra-word variant of Beale's copy
  (base rate 0.0 among all modern transcriptions). Beale's DOI belonged
  to this textual family. The line-skip (P3) and other variants are
  absent: same family, not his exact printing.
- C2 keytable drift-aligns to the volume's DOI (159/180 within a small
  drift band) - close to, but not identical with, Beale's copy.
- Full-volume offset sweep of C1 and C3 (two-stage, ~110k offsets each):
  best offsets reach raw z~4 but fail the extreme-value standard for that
  search budget, decode to non-language, and C1/C3 "peak" at the same two
  text regions (letter-frequency artifacts of those pages). NO KEY MATCH.

Net: the volume eliminates itself as the key but CONFIRMS the hunt
strategy - the American's Guide family carries Beale's P1 variant, so the
target printing is a sibling edition of this genre with the dropped line.
Earlier editions/printings of The American's Guide (and its sources) are
now the top archive targets.
