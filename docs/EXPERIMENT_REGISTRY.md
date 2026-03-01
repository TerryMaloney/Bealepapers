# Experiment Registry

**Purpose**: Log all experiments with ID, config, timestamp, and outputs for reproducibility.

**Format**: Each experiment gets unique ID, full config, output paths, and verdict.

---

## Registry

### EXP-A001: Initial Oracle Sweep (Variant Generator)
- **Phase**: 7 / G1
- **Date**: 2026-02-15 16:35:55
- **Config**: beale_embedded DOI + 16 tokenization variants (reconstructed text)
- **Output**: `output/phase7/cipher2_oracle_sweep_20260215_163555.txt`
- **Status**: COMPLETE
- **Result**: Best 5.67% match
- **Verdict**: FAILED - Reconstructed DOI lost structure

### EXP-A002: H1 Numbering Offset Test
- **Phase**: Post-7
- **Date**: 2026-02-15 16:44:45
- **Config**: Offsets -10 to +10 tested on Cipher 1 & 2
  - Extractor: position_times_2
  - Transposition: rect_w26_spiral_ccw
- **Output**: `output/phase7/h1_offset_test_20260215_164445.txt`
- **Status**: COMPLETE
- **Result**: 
  - Cipher 2 best: 26.50% at offset=0 (no improvement)
  - Cipher 1 best: 35.42/100 at offset=-5 (+2.70 points, not significant)
- **Verdict**: REJECTED - Simple uniform offset is not the cause

### EXP-A003: Oracle Sweep (Multi-Edition)
- **Phase**: A
- **Date**: 2026-02-15 16:57:15
- **Config**: 4 editions × 8 tokenizers = 32 combinations
  - Editions: beale_embedded (real), dunlap_1776 (placeholder), goddard_1777 (placeholder), stone_1823 (placeholder)
  - Tokenizers: strict_word, punct_tokens, hyphen_split, hyphen_keep, apostrophe_split, apostrophe_keep, case_preserve, minimal
- **Output**: `output/oracle_sweep/sweep_20260215_165715.txt`
- **Status**: COMPLETE
- **Result**: 
  - Best: beale_embedded + any tokenizer = 26.50% (194/732)
  - All beale_embedded tokenizers identical: 26.50%
  - Historical editions unavailable (placeholders only)
- **Verdict**: NO-GO (26.5% < 50%)
- **Decision**: Acquire historical editions OR implement drift models (Phase A2)

---

## Cumulative Statistics (Phases 1-7 + A)

### Strategies Tested
- **Phase 1-2**: ~200 (framework + baseline)
- **Phase 3**: ~150 (VDR/offset testing)
- **Phase 4**: ~50 (DOI-only validation)
- **Phase 5**: 2,362 (advanced extractors + Caesar sweep)
- **Phase 6**: ~200 (segment-specific testing)
- **Phase 7**: 100 (feature extractors + two-stage)
- **Phase A**: 32 (oracle sweep)
- **Total**: ~3,000+ strategies evaluated

### Code Artifacts
- **Extractors**: 65 implemented
- **Transpositions**: 78 implemented
- **LOC**: ~6,000+

### Plateau Analysis
- **Robust score range**: 34-38/100
- **Best ever**: 37.88/100 (Phase 6)
- **Random max**: 15.88/100
- **Signal strength**: 15.3 sigma above noise

### Key Findings
- DOI is key book (98.1% coverage)
- Position-dependent extraction confirmed
- Route ciphers best transposition family
- Caesar shift ruled out
- Segment rules ruled out
- Feature extraction ruled out
- **DOI edition mismatch confirmed** (26.5% oracle match)

---

## Pending Experiments

### EXP-A2-001: Progressive Drift Model (Conditional)
- **Phase**: A2
- **Trigger**: IF Phase A oracle fails (<90%)
- **Config**: Fit progressive drift parameters to optimize Cipher 2 oracle
- **Method**: Linear drift, piecewise offsets
- **Target**: Improve oracle from 26.5% to >50%
- **Status**: PENDING (triggered by EXP-A003 NO-GO)

### EXP-A2-002: Layout Numbering Models (Conditional)
- **Phase**: A2
- **Trigger**: IF Phase A oracle fails AND drift models insufficient
- **Config**: Test printing artifacts (line-wrap, column numbering, heading insertion)
- **Target**: Improve oracle to >90%
- **Status**: PENDING

### EXP-B001: Rebase Cipher 1 Baseline (Conditional)
- **Phase**: B
- **Trigger**: IF Phase A or A2 oracle passes (>=90%)
- **Config**: Re-run Phase 5-6 best extractors with CANON_DOI
- **Expected**: +5 to +15 point improvement
- **Status**: BLOCKED (awaiting oracle resolution)

### EXP-B002: Rebase Cipher 3 Baseline (Conditional)
- **Phase**: B
- **Trigger**: IF Phase A or A2 oracle passes (>=90%)
- **Config**: First comprehensive test of Cipher 3 with validated DOI
- **Expected**: Readable fragments emerge
- **Status**: BLOCKED (awaiting oracle resolution)

### EXP-C001: Cross-Cipher Constraints (Conditional)
- **Phase**: C
- **Trigger**: IF Phase B shows improvement
- **Config**: Use 122 Cipher 1-2 overlaps as hard constraints
- **Expected**: Eliminate >50% of invalid strategies
- **Status**: BLOCKED (awaiting oracle resolution)

### EXP-D001: Expanded Extraction Grid (Conditional)
- **Phase**: D
- **Trigger**: IF Phase C constraints applied successfully
- **Config**: General formula (a*i + b + c*(n mod m) + d*L) mod L
  - Parameter grid: a∈{1,2,3}, b∈{0,1}, c∈{0,1}, m∈{5,7,11}, d∈{0,1}
  - Total: ~90 extractors
- **Expected**: Find optimal parameters with CANON_DOI
- **Status**: BLOCKED (awaiting oracle resolution)

### EXP-D002: Systematic Route Cipher Sweep (Conditional)
- **Phase**: D
- **Trigger**: IF Phase C complete
- **Config**: All rectangle widths 5-100 with spiral/diagonal/zigzag patterns
- **Expected**: Find optimal geometric read pattern
- **Status**: BLOCKED (awaiting oracle resolution)

---

## Experiment Logging Protocol

Every experiment must include:

1. **ID**: Unique identifier (PHASE-SUBPHASE-NNN)
2. **Phase**: Which phase (A, A2, B, C, D, E)
3. **Date**: ISO timestamp
4. **Config**: Full parameters (edition, tokenizer, extractor, transposition, seeds)
5. **Output**: Path to CSV/TXT results
6. **Status**: PENDING | RUNNING | COMPLETE | FAILED
7. **Result**: Quantitative (score, match %, coverage)
8. **Verdict**: Qualitative interpretation (GO/NO-GO, CONFIRMED/REJECTED)

### Example Entry Template

```markdown
### EXP-X-NNN: Experiment Name
- **Phase**: X
- **Date**: YYYY-MM-DD HH:MM:SS
- **Config**: 
  - Parameter 1: value
  - Parameter 2: value
- **Output**: `path/to/output.txt`
- **Status**: COMPLETE
- **Result**: Metric = value
- **Verdict**: Interpretation
```

---

**Last Updated**: 2026-02-15 16:58:00
**Total Experiments Logged**: 3 complete, 10 pending
**Critical Path Status**: Phase A complete (NO-GO), awaiting historical DOI or Phase A2
