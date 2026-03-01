# Beale Cipher Hypothesis Tree

**Last Updated**: 2026-02-15
**Status Tags**: CONFIRMED | TENTATIVE | REJECTED | UNTESTED

---

## I. KEY TEXT / CORPUS HYPOTHESES

### A. DOI Edition Mismatch

- **Status**: **CONFIRMED** (critical blocker)
- **Hypothesis**: Cipher uses specific DOI edition with unique wording/numbering
- **Evidence**: 
  - Oracle test: beale_embedded DOI only matches 26.5% of Cipher 2 known plaintext
  - Should be >90% for correct book cipher key
  - See: `output/oracle_sweep/sweep_20260215_165715.txt`
- **Candidates tested**:
  - beale_embedded: 26.5% match (best available)
  - dunlap_1776: Placeholder (TO BE ACQUIRED)
  - goddard_1777: Placeholder (TO BE ACQUIRED)
  - stone_1823: Placeholder (TO BE ACQUIRED)
- **Test**: Phase A oracle sweep
- **Next**: Acquire historical editions OR implement drift models (Phase A2)

### B. Tokenization Rule Mismatch

- **Status**: **TENTATIVE**
- **Hypothesis**: Word splitting differs (hyphens, apostrophes, contractions)
- **Evidence**: 
  - Phase 7 tested 16 variants: all scored identically at 5.67% (reconstructed DOI)
  - Phase A tested 8 tokenizers: all scored 26.5% (beale_embedded)
  - Tokenization alone cannot fix the mismatch
- **Test**: Included in Phase A oracle sweep
- **Verdict**: Tokenization is NOT the primary issue

### C. Numbering Unit Mismatch

- **Status**: **REJECTED**
- **Hypothesis**: Words vs letters vs tokens
- **Evidence**: 
  - All tokenizers preserve word-unit indexing
  - No evidence of letter-based indexing
- **Test**: Implicit in Phase A

### D. Layout/Numbering Drift

- **Status**: **UNTESTED** (Phase A2 pending)
- **Hypothesis**: Printing artifacts cause progressive numbering drift
- **Models to test**:
  - Progressive offset (drift accumulates linearly)
  - Periodic heading insertion (headers counted/skipped)
  - Line-wrap artifacts (double-counting first word per line)
  - Column-based numbering (down column 1, then column 2)
- **Test**: Phase A2 drift model fitting
- **Trigger**: Phase A oracle failed (<50%), proceed to Phase A2

### E. Simple Numbering Offset

- **Status**: **REJECTED**
- **Hypothesis**: DOI word indices have uniform offset of +/-1 to +/-10
- **Evidence**: 
  - Tested offsets -10 to +10 on both Cipher 1 and Cipher 2
  - No improvement: Cipher 2 stays at 26.5%, Cipher 1 max 35.42/100 at offset=-5
  - See: `output/phase7/h1_offset_test_20260215_164445.txt`
- **Test**: H1 offset test (post-Phase 7)
- **Verdict**: Simple uniform offset is not the cause

### F. Multi-Key System (DOI + Auxiliary Text)

- **Status**: **REJECTED** for main hypothesis
- **Hypothesis**: Most numbers use DOI, some switch to alternate key
- **Evidence**: 
  - 98.1% coverage (510/520 numbers) with DOI-only
  - 10 OOR numbers could be alternate key, but testing shows no improvement
  - See: `output/phase7/oor_analysis_20260215_163744.txt`
- **Test**: Phase 7 G2 (OOR analysis)
- **Verdict**: May explain 10 OOR numbers only, not main method

---

## II. EXTRACTION RULE HYPOTHESES

### A. Position-Dependent Letter Selection

- **Status**: **CONFIRMED** (core method)
- **Hypothesis**: Extracted letter depends on cipher position in sequence
- **Evidence**: 
  - Repeat analysis: same cipher number yields different letters by position
  - Position-based extractors score 37/100 vs random 15/100 (15.3 sigma)
  - See: `output/phase4_verdict.txt`, repeat analysis Phase 2
- **Best formulas**: 
  - `position_times_2` (Phase 3)
  - `cycle_every_5` (Phase 3)
  - `nth_letter_by_position` (Phase 1)
  - `reverse_position` (Phase 3)
- **Score range**: 34-37/100

### B. First-Letter Only (Cipher 2 Method)

- **Status**: **REJECTED** for Cipher 1
- **Hypothesis**: Simple first-letter extraction like Cipher 2
- **Evidence**: 
  - First-letter scores only 26/100 on Cipher 1
  - Repeat numbers produce different letters (position-dependent)
- **Test**: Phase 1-2 baseline
- **Note**: CONFIRMED for Cipher 2 (historical)

### C. Feature-Based Extraction

- **Status**: **REJECTED**
- **Hypothesis**: Extract based on word features (vowels, consonants, digraphs, word shape)
- **Evidence**: 
  - Phase 7 G3 tested 10 feature extractors
  - No improvement over simple position-based methods
  - Best strategies still use position_times_2, cycle_every_5
  - See: `output/phase7/phase7_verdict.txt`
- **Tested extractors**: 
  - LastVowel, LastConsonant
  - VowelPosition, ConsonantPosition
  - DigraphIndex, LetterClassIndex
  - WordShape, AlternateVowelConsonant
  - CipherProductMod, WordLengthModulated

### D. Multi-Letter Extraction

- **Status**: **UNTESTED**
- **Hypothesis**: Extract 2+ letters per cipher number
- **Rationale**: Would explain higher character output vs cipher number count
- **Test**: Phase D (post-oracle resolution)
- **Priority**: LOW

### E. Homophonic Behavior

- **Status**: **TENTATIVE**
- **Hypothesis**: Multiple cipher numbers map to same plaintext element
- **Evidence**: 
  - High-frequency numbers: 807 (appears 61 times), 1005 (appears 12 times)
  - May be intentional variants or nulls
- **Test**: Phase D (frequency analysis)
- **Priority**: MEDIUM

---

## III. TRANSPOSITION HYPOTHESES

### A. Route Ciphers (Geometric Rectangle Reads)

- **Status**: **CONFIRMED** as best family
- **Hypothesis**: Extracted letters read from rectangle in spiral/diagonal patterns
- **Evidence**: 
  - Phase 5-6: Route ciphers consistently +3-5 points over sequential
  - Best: rect_w26_spiral_ccw, rect_w13_spiral_ccw, rect_w40_diagonal
  - Scores: 37-38/100
  - See: `output/phase5/phase5_summary.txt`, `output/phase6/phase6_verdict.txt`
- **Test**: Extensive testing Phases 5-7

### B. Columnar with Keyword

- **Status**: **TENTATIVE** (limited testing)
- **Hypothesis**: Classical columnar transposition with keyword
- **Evidence**: 
  - Phase 5 tested with keywords: no breakthrough
  - May need correct DOI edition first
- **Test**: Phase 5 (limited), Phase D (expand if oracle passes)
- **Priority**: MEDIUM

### C. Two-Stage Transposition

- **Status**: **REJECTED** in simple form
- **Hypothesis**: Apply two transpositions sequentially (route then columnar)
- **Evidence**: 
  - Phase 7 G4 tested 15 two-stage combinations
  - Best two-stage: 37.80/100 vs single-stage: 37.88/100 (no improvement)
  - See: `output/phase7/phase7_verdict.txt`
- **Test**: Phase 7 G4
- **Verdict**: No evidence of layered transposition with current methods

### D. Grille Masks

- **Status**: **UNTESTED**
- **Hypothesis**: Read through holes in rotating mask over rectangle
- **Rationale**: Common in 19th century hand ciphers
- **Test**: Phase D (low priority)
- **Priority**: LOW

---

## IV. POST-EXTRACTION PROCESSING

### A. Caesar Shift

- **Status**: **REJECTED** (definitively)
- **Hypothesis**: Simple alphabet rotation after extraction
- **Evidence**: 
  - Phase 5 tested all 26 Caesar shifts
  - Zero improvement (best always shift=0)
  - Top 50 strategies tested: all show shift=0 as optimal
  - See: `output/phase5/phase5_caesar_top20_20260215_160029.txt`
- **Test**: Phase 5 Caesar sweep
- **Verdict**: No Caesar layer exists

### B. Vigenere Cipher

- **Status**: **REJECTED** (implicitly)
- **Hypothesis**: Polyalphabetic substitution with keyword
- **Evidence**: 
  - Phase 5 tested limited Vigenere search
  - No improvement found
- **Test**: Phase 5 (limited)
- **Priority**: LOW for retesting

### C. Monoalphabetic Substitution

- **Status**: **UNTESTED** (comprehensive search)
- **Hypothesis**: Simple letter-to-letter substitution after extraction
- **Evidence**: 
  - Phase 5 tested via hillclimb (limited runs)
  - Inconclusive
- **Test**: Phase D (if oracle passes and plateau persists)
- **Priority**: MEDIUM

---

## V. ENCODING STRUCTURE HYPOTHESES

### A. Uniform Encoding (Single Method Throughout)

- **Status**: **TENTATIVE** (likely correct)
- **Hypothesis**: Same extraction + transposition rules for entire cipher
- **Evidence**: 
  - Phase 6 tested segment-specific rules: no improvement
  - Stitched decoder (best per segment) scored worse than uniform
  - See: `output/phase6/phase6_verdict.txt`
- **Test**: Phase 6 comprehensive

### B. Segment-Based Encoding (Different Rules Per Section)

- **Status**: **REJECTED**
- **Hypothesis**: Cipher divided into segments with different extraction rules
- **Evidence**: 
  - Phase 6 tested 3, 4, and 6 segment configurations
  - Segment 4 anomaly (44/100 alone) was local artifact
  - Best stitched: 37.88/100 vs uniform: 37.88/100 (no gain)
  - See: `output/phase6/phase6_verdict.txt`
- **Test**: Phase 6 full investigation

### C. Progressive Drift (Gradual Method Change)

- **Status**: **UNTESTED**
- **Hypothesis**: Encoding method drifts gradually through cipher
- **Evidence**: 
  - Could explain 26.5% Cipher 2 match (early words correct, late drift)
  - H2 hypothesis from post-Phase 7 analysis
- **Test**: H2 test (pending)
- **Priority**: HIGH (explains partial signal)

---

## VI. REJECTED HYPOTHESES (Definitively Ruled Out)

### VDR Offset (335-word offset)

- **Status**: **REJECTED**
- **Evidence**: Phase 3 coverage collapse, scores degrade
- **Test**: Phase 3 full-corpus tests
- **File**: `output/phase3_verdict.txt`

### Stacked Corpus (VDR + DOI + Signers + Articles)

- **Status**: **REJECTED**
- **Evidence**: Phase 3 direct comparison, DOI-only superior
- **Test**: Phase 3 stacked vs DOI-only
- **File**: `output/phase3_verdict.txt`

### Simple Caesar Shift (Post-Extraction)

- **Status**: **REJECTED**
- **Evidence**: Phase 5 tested all 26 rotations, zero improvement
- **Test**: Phase 5 Caesar sweep (2,362 strategies)
- **File**: `output/phase5/phase5_caesar_top20_20260215_160029.txt`

### Discrete Segment Rules

- **Status**: **REJECTED**
- **Evidence**: Phase 6 stitched decoder, no improvement
- **Test**: Phase 6 (optimal, beam, boundary tests)
- **File**: `output/phase6/phase6_verdict.txt`

### Simple Uniform Numbering Offset

- **Status**: **REJECTED**
- **Evidence**: H1 test, offsets -10 to +10, no significant improvement
- **Test**: H1 offset test (post-Phase 7)
- **File**: `output/phase7/h1_offset_test_20260215_164445.txt`

### Feature-Based Extraction (Vowel/Consonant/Digraph)

- **Status**: **REJECTED**
- **Evidence**: Phase 7 G3, no improvement over position-based
- **Test**: Phase 7 G3 (10 feature extractors)
- **File**: `output/phase7/phase7_verdict.txt`

### Two-Stage Transposition (Simple Form)

- **Status**: **REJECTED**
- **Evidence**: Phase 7 G4, no improvement (37.80 vs 37.88)
- **Test**: Phase 7 G4 (15 two-stage combinations)
- **File**: `output/phase7/phase7_verdict.txt`

---

## VII. CURRENT BEST METHODS (Confirmed Working)

### Extraction

1. **position_times_2** - idx = (cipher_pos * 2) % word_length
2. **cycle_every_5** - idx cycles through positions 0,1,2,3,4 every 5 positions
3. **nth_letter_by_position** - idx = cipher_pos % word_length
4. **reverse_position** - idx = word_length - 1 - (cipher_pos % word_length)

All score: 34-37/100 (depending on transposition)

### Transposition

1. **rect_w26_spiral_ccw** - 26-column rectangle, spiral counter-clockwise
2. **every_3th** - Read every 3rd character
3. **rect_w13_spiral_ccw** - 13-column rectangle, spiral counter-clockwise
4. **rect_w40_diagonal** - 40-column rectangle, diagonal read

Best combinations: 37-38/100

### Combined Best

- **position_times_2** + **rect_w26_spiral_ccw**: 37.88/100 (Phase 6 best)
- **cycle_every_5** + **rect_w13_spiral_ccw**: 37.28/100 (Phase 7)

---

## VIII. STATISTICAL FACTS

### Signal Strength

- **Best score**: 37.88/100 (Phase 6)
- **Random baseline**: Mean 9.84/100, Max 15.88/100
- **Sigma above mean**: 15.3σ (highly significant)
- **Coverage**: 98.1% (510/520 numbers within DOI range)
- **File**: `output/phase4/phase4_random_baseline.txt`

### Out-of-Range Numbers

- **Count**: 10 numbers (1.9% of cipher)
- **Values**: 1431, 1496, 1629, 1701, 1706, 1780, 1817, 2018, 2160, 2906
- **Positions**: 3, 8, 33, 170, 171, 390, 391, 442, 454, 495
- **Handling**: No method significantly improves score
- **File**: `output/phase7/oor_analysis_20260215_163744.txt`

---

## IX. CRITICAL INSIGHTS

### The 26.5% vs 37/100 Paradox

**Observation**:
- Cipher 2 with first-letter on current DOI: 26.5% match
- Cipher 1 with position-extraction + transposition: 37.0% score

**Explanation**:
- First-letter extraction: ZERO error tolerance (one wrong word = one wrong letter)
- Position-modulated extraction: averages over word length, smooths some errors
- Transposition: further scrambles, masking alignment errors
- Result: Cipher 1 can score higher than Cipher 2 despite both using wrong DOI

**Implication**:
The 37/100 plateau is caused by DOI edition mismatch, NOT wrong extraction method.
With correct DOI, expect scores to jump >45/100.

---

## X. HYPOTHESIS PRIORITY (Next Steps)

### Tier 1: CRITICAL PATH (Must Resolve to Progress)

1. **Acquire Historical DOI Editions**
   - Dunlap broadside 1776 (original)
   - Stone engraving 1823 (common in 1820s)
   - Goddard 1777 (Baltimore variant)
   - **Action**: Manual acquisition from archives
   - **Impact**: Could immediately unlock cipher if oracle passes

2. **Phase A2: Drift Models** (if acquisition fails)
   - Progressive offset fitting
   - Layout-based numbering simulation
   - **Action**: Implement `corpus/drift_models.py`
   - **Impact**: May improve oracle from 26.5% to >50%

### Tier 2: POST-ORACLE (Only After Corpus Resolved)

3. **Rebase all methods on CANON_DOI**
   - Re-run Phase 5-6 extractors with correct DOI
   - Expected: >5 point improvement minimum

4. **Cross-cipher constraints**
   - Use Cipher 2 oracle (once validated) to filter Cipher 1 methods
   - 122 overlapping numbers provide constraints

5. **Expand search space**
   - General position formula grid: (a*i + b + c*(n mod m) + d*L) mod L
   - Systematic route cipher sweep (all factors)
   - Keyword columnar with historical terms

### Tier 3: ALTERNATIVE ANGLES (If Standard Methods Exhausted)

6. **H2: Progressive Drift Analysis**
   - Test if early cipher positions decode better than late
   - Evidence: Would explain partial signal

7. **H3: Homophonic Analysis**
   - Check if high-frequency numbers map to same words
   - Common in period ciphers

8. **H5: Fragment Assembly**
   - Assume 37/100 = 40% correct, try to extract fragments
   - Different analysis angle

---

## XI. COMPUTATIONAL RESOURCES EXPENDED

### Phases 1-7 Summary

- **Strategies tested**: >3,500
- **Extractors implemented**: 65
- **Transpositions implemented**: 78
- **Best score achieved**: 37.88/100
- **Plateau range**: 34-38/100 (robust)

### Phase A (Current)

- **DOI editions tested**: 4 (1 real, 3 placeholders)
- **Tokenizers tested**: 8
- **Combinations tested**: 32
- **Best oracle match**: 26.5%
- **Decision**: NO-GO (need historical editions or drift models)

---

## XII. REFERENCES (Evidence Files)

| Hypothesis | Status | Evidence File |
|------------|--------|---------------|
| DOI Edition Mismatch | CONFIRMED | `output/oracle_sweep/sweep_20260215_165715.txt` |
| Position-Dependent Extraction | CONFIRMED | `output/phase4/phase4_verdict.txt` |
| Route Ciphers Best | CONFIRMED | `output/phase5/phase5_summary.txt` |
| Caesar Shift | REJECTED | `output/phase5/phase5_caesar_top20_20260215_160029.txt` |
| Segment Rules | REJECTED | `output/phase6/phase6_verdict.txt` |
| Feature Extraction | REJECTED | `output/phase7/phase7_verdict.txt` |
| Two-Stage Transposition | REJECTED | `output/phase7/phase7_verdict.txt` |
| Simple Offset | REJECTED | `output/phase7/h1_offset_test_20260215_164445.txt` |
| OOR Numbers Critical | REJECTED | `output/phase7/oor_analysis_20260215_163744.txt` |

---

**End of Hypothesis Tree**
**Status**: Phase A complete, awaiting historical DOI acquisition or Phase A2 implementation
**Next**: Acquire Dunlap 1776 DOI or implement drift models
