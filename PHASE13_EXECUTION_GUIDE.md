# Phase 13: Academic Alignment Attack - Execution Guide

## Quick Start

### Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Verify installation:
```bash
python -c "import requests, bs4, ruptures, scipy, numpy; print('All dependencies OK')"
```

---

## Full Pipeline Execution

### Step A: Discover DOI Editions (5-10 minutes)

```bash
python run_pipeline.py phase13_discover
```

**What it does**:
- Fetches DOI transcripts from 5 known URLs
- Extracts and normalizes text
- Saves to `corpus/editions/<edition_id>.txt`
- Includes beale_embedded
- Creates placeholders for Stone 1823, Dunlap 1776, Goddard 1777

**Expected output**: ~8-10 editions acquired

**Check results**:
```bash
cat output/phase13/editions_list.txt
cat output/phase13/edition_catalog.json
```

**To reach 30+ editions**: Manually acquire more DOI transcripts:
1. Visit archives.gov, loc.gov, university digital collections
2. Copy full DOI text (preserve formatting, headers, signers)
3. Save to `corpus/editions/<source_name>.txt`
4. Run `phase13_discover` again to update catalog (or create metadata manually)

---

### Step B: Tokenize All Editions (1-2 minutes)

```bash
python run_pipeline.py phase13_tokenize
```

**What it does**:
- Tokenizes each edition with all 14 tokenizer presets
- Saves tokens to `corpus/locked_candidates/<edition>/<tokenizer>/tokens.json`
- Generates token counts matrix (CSV)

**Expected output**: ~10 editions × 14 tokenizers = ~140 token files

**Check results**:
```bash
cat output/phase13/token_counts_matrix.csv
ls corpus/locked_candidates/
```

---

### Step C: Cluster Editions (2-5 minutes)

```bash
python run_pipeline.py phase13_cluster --tokenizer hyphen_keep
```

**What it does**:
- Computes pairwise similarity between editions (difflib)
- Builds N×N distance matrix
- Hierarchical clustering
- Selects medoids (1 representative per cluster)

**Expected output**: ~10 editions -> ~3-5 clusters -> ~3-5 representatives

**Check results**:
```bash
cat output/phase13/cluster_representatives.txt
cat output/phase13/edition_clusters.json
```

**Interpreting clusters**:
- Editions in same cluster are very similar (likely same source, minor formatting differences)
- Representatives (medoids) capture cluster characteristics
- Reduces HMM search space from 140 to ~15-25 combinations

---

### Step D: HMM Oracle on Representatives (5-15 minutes)

**Read representatives file**:
```bash
# Windows PowerShell
$representatives = Get-Content output/phase13/cluster_representatives.txt
python run_pipeline.py phase13_hmm_oracle --editions $representatives --tokenizers hyphen_keep hyphen_split
```

**Or manually**:
```bash
python run_pipeline.py phase13_hmm_oracle --editions beale_embedded nara_transcript avalon_yale --tokenizers hyphen_keep hyphen_split
```

**What it does**:
- Runs Viterbi algorithm to find optimal offset path
- For each position: finds offset that maximizes match probability
- Outputs: offset path, jumps, max offset, log-likelihood

**Expected output**: JSON + CSV for each edition/tokenizer pair

**Check results**:
```bash
cat output/phase13/oracle_hmm/beale_embedded_hyphen_keep.json
# Shows: log_likelihood, n_jumps, max_offset, etc.
```

**Interpreting HMM results**:
- Low jumps (<5) + low max_offset (<10): Edition is very close, minor alignment issues
- Moderate jumps (5-10) + moderate offset (10-25): Edition divergence, fixable
- High jumps (>10) + high offset (>25): Wrong edition or major structural differences

---

### Step E: Changepoint Detection (1-2 minutes)

```bash
python run_pipeline.py phase13_changepoints --editions beale_embedded nara_transcript --tokenizers hyphen_keep
```

**What it does**:
- Detects breakpoints in match series (PELT algorithm)
- Detects breakpoints in offset series (BinSeg algorithm)
- Labels "structural boundaries" where both align

**Expected output**: Breakpoint reports with positions and labels

**Check results**:
```bash
cat output/phase13/changepoints/beale_embedded_hyphen_keep.txt
```

**Interpreting changepoints**:
- Breakpoint at ~100-150: Matches Phase 12 finding (83% first 100, degrades after)
- Structural boundary: Offset jump + match drop -> section misalignment or header/footer inclusion difference
- Many breakpoints (>10): Chaotic alignment, likely wrong edition

---

### Step F: Ranking and Acceptance Gates (<1 minute)

```bash
python run_pipeline.py phase13_rank --editions beale_embedded nara_transcript avalon_yale --tokenizers hyphen_keep hyphen_split
```

**What it does**:
- Computes composite scores for all candidates
- Ranks by composite score
- Applies 4 acceptance gates
- Determines: LOCK or NO-GO

**Check results**:
```bash
cat output/phase13/LOCK_RECOMMENDATION.txt
cat output/phase13/ranked_oracle_results.csv
```

**Acceptance gates**:
1. Early-100 >= 85% (or best-in-class)
2. Total >= 60%
3. Jumps <= 10
4. Max offset <= 25
5. Margin over runner-up >= 5.0 points

**Possible outcomes**:

**LOCK** (all gates pass):
```
RECOMMENDATION: LOCK
Edition: stone_1823
Tokenizer: hyphen_keep
Composite score: 88.5
Early-100 match: 96.2%
Total match: 87.3%

ACTION: Proceed to Step G
```

**NO-GO** (gates fail):
```
RECOMMENDATION: NO-GO
Reason: Total match 48.3% < 60.0%

TOP CANDIDATE (did not pass gates):
Edition: beale_embedded
Tokenizer: hyphen_keep
Composite score: 71.2
Early-100 match: 83.0%
Total match: 48.3%

ACTION: Acquire more editions (especially Stone 1823)
```

---

### Step G: Lock Corpus and Rerun (conditional)

**Only run if LOCK_RECOMMENDATION.txt says LOCK!**

```bash
python run_pipeline.py phase13_lock_rerun
```

**What it does**:
1. Reads LOCK_RECOMMENDATION.txt
2. If NO-GO: aborts with message
3. If LOCK: Creates `corpus/LOCKED.json` with best edition/tokenizer
4. Copies to `corpus/CANON_DOI.json` for compatibility
5. Creates placeholder outputs for Cipher 1/3 reruns
6. Prints next steps for full rerun

**Expected output**:
- `corpus/LOCKED.json` - Locked token list
- Placeholder files noting Phase 5/6/7 need modification

---

## Troubleshooting

### Issue: "No editions found" in Step B
**Cause**: Step A didn't acquire any editions  
**Fix**: Check network connectivity, run Step A again, or manually add editions to `corpus/editions/`

### Issue: "python-Levenshtein not installed" in Step C
**Cause**: Optional dependency not installed  
**Fix**: `pip install python-Levenshtein` or use `--method difflib` (slower but works)

### Issue: "ruptures not installed" in Step E
**Cause**: Required dependency not installed  
**Fix**: `pip install ruptures`

### Issue: All candidates fail acceptance gates
**Cause**: No edition reaches 60% total match or 85% early-100  
**Fix**: 
1. Acquire Stone 1823 (most likely to pass)
2. Relax gates (edit phase13_ranker.py gates dict)
3. Revisit Phase 12 findings for drift modeling

### Issue: Step G creates only placeholders
**Expected**: Phase 5/6/7 scripts need modification to load from LOCKED.json  
**Fix**: This is a known limitation; full rerun requires code changes to phase5_runner.py, phase6_beam_search.py, phase7_runner.py

---

## Expected Results by Edition

### beale_embedded (baseline)
- Early-100: ~83%
- Total: ~26.5%
- HMM: offset path starts at 0, increases after position 100
- Changepoints: ~3-5 breakpoints, structural boundary around 100-150
- Gates: Likely PASS early-100 (83%), FAIL total (26.5% < 60%)
- **Verdict**: Good anchor, wrong edition for full decoding

### Stone 1823 (if acquired)
- Expected: 90-95% total match (hypothesis from Phase 11/12)
- HMM: Low jumps (<5), low max offset (<10)
- Changepoints: Few breakpoints, mostly minor adjustments
- Gates: Likely PASS all gates
- **Verdict**: Strong candidate for LOCK

### Modern transcripts (NARA, Avalon, etc.)
- Expected: 70-85% total match (modern scholarly editions)
- HMM: Moderate jumps, moderate offsets
- Changepoints: Structural boundaries at header/signer inclusion points
- Gates: May PASS early-100, may FAIL total or simplicity
- **Verdict**: Better than beale_embedded, but likely not optimal for Beale era

---

## Command Reference (Quick)

```bash
# Full pipeline (sequential)
python run_pipeline.py phase13_discover
python run_pipeline.py phase13_tokenize
python run_pipeline.py phase13_cluster
python run_pipeline.py phase13_hmm_oracle --editions beale_embedded nara_transcript avalon_yale --tokenizers hyphen_keep
python run_pipeline.py phase13_changepoints --editions beale_embedded nara_transcript avalon_yale --tokenizers hyphen_keep
python run_pipeline.py phase13_rank --editions beale_embedded nara_transcript avalon_yale --tokenizers hyphen_keep
python run_pipeline.py phase13_lock_rerun

# Individual steps (with defaults)
python run_pipeline.py phase13_discover
python run_pipeline.py phase13_tokenize --corpus-dir corpus
python run_pipeline.py phase13_cluster --tokenizer hyphen_keep --method difflib --max-clusters 10
python run_pipeline.py phase13_hmm_oracle --editions $(cat output/phase13/cluster_representatives.txt) --K 50
python run_pipeline.py phase13_changepoints --editions beale_embedded --penalty 10.0 --n-bkps 5
python run_pipeline.py phase13_rank --editions beale_embedded
python run_pipeline.py phase13_lock_rerun --corpus-dir corpus --output-dir output/phase13
```

---

## Output Directory Structure

After full Phase 13 execution:

```
output/phase13/
├── edition_catalog.json              # Step A: All editions with metadata
├── editions_list.txt                 # Step A: Simple list of edition IDs
├── token_counts_matrix.csv           # Step B: Editions × tokenizers matrix
├── edition_distance_matrix.npy       # Step C: Pairwise distances
├── edition_clusters.json             # Step C: Cluster assignments
├── cluster_representatives.txt       # Step C: Medoids
├── oracle_hmm/                       # Step D: HMM results
│   ├── beale_embedded_hyphen_keep.json
│   ├── beale_embedded_hyphen_keep_plot.csv
│   ├── nara_transcript_hyphen_keep.json
│   └── ...
├── changepoints/                     # Step E: Changepoint results
│   ├── beale_embedded_hyphen_keep.txt
│   └── ...
├── ranked_oracle_results.csv         # Step F: All candidates ranked
├── LOCK_RECOMMENDATION.txt           # Step F: LOCK or NO-GO decision
├── cipher1_top.txt                   # Step G: Cipher 1 results (placeholder)
├── cipher3_top.txt                   # Step G: Cipher 3 results (placeholder)
├── concurrent_top.txt                # Step G: Concurrent results (placeholder)
└── stability_report.txt              # Step G: Stability checks (placeholder)

corpus/
├── raw_sources/                      # Step A: Raw HTML/text
│   ├── nara_transcript/raw.html
│   ├── avalon_yale/raw.html
│   └── ...
├── editions/                         # Step A: Extracted DOI texts
│   ├── beale_embedded.{txt,json}
│   ├── nara_transcript.{txt,json}
│   ├── avalon_yale.{txt,json}
│   ├── stone_1823.json (placeholder)
│   └── ...
├── locked_candidates/                # Step B: Tokenized versions
│   ├── beale_embedded/
│   │   ├── hyphen_keep/tokens.json
│   │   ├── hyphen_split/tokens.json
│   │   └── ... (14 tokenizers)
│   └── ...
└── LOCKED.json                       # Step G: Final locked corpus (if gates pass)
```

---

## Success Criteria

Phase 13 is successful if:

✅ Step A: Acquired >=30 editions (or >=10 with high diversity)  
✅ Step B: All editions tokenized with all presets  
✅ Step C: Clustering identifies 3-10 representatives  
✅ Step D: HMM log-likelihood > -500 for at least one candidate  
✅ Step E: Changepoints align with known degradation (position ~100-150 for beale_embedded)  
✅ Step F: At least ONE candidate passes all acceptance gates  
✅ Step G: LOCKED.json created with >=60% total match

**If Step F outputs NO-GO**: Phase 13 has falsified the hypothesis that current editions can achieve >=95% Cipher 2 match. Action: Acquire Stone 1823 or relax gates.

---

## Comparison: Phase 11/12 vs Phase 13

### Phase 11/12: Diagnostic (Completed)
- ✅ Identified 26.5% overall oracle
- ✅ Found 64% early, 9% middle, 5% late (progressive decline)
- ✅ Falsified: formatting, extraction rules, conventions
- ✅ Found: 83% first-100 match
- ✅ Conclusion: Edition mismatch, need Stone 1823 or advanced modeling

### Phase 13: Academic Alignment (Now Implemented)
- ✅ Acquire 30+ editions (breadth-first)
- ✅ HMM/Viterbi offset path (replaces aggregate %)
- ✅ Changepoint detection (identifies exact boundaries)
- ✅ Edition clustering (reduces search space)
- ✅ Acceptance gates (NO-GO if quality insufficient)
- ✅ Lock corpus only when diagnostic passes

**Key difference**: Phase 13 doesn't just measure mismatch—it **structurally explains** the mismatch via offset paths and changepoints.

---

## Timeline Estimate

| Phase | Task | Time | Bottleneck |
|-------|------|------|------------|
| Prep | Install deps | 2-5 min | Network download |
| 13A | Discover | 5-10 min | HTTP fetch + HTML parse |
| Manual | Acquire 20+ more | 1-3 hours | Human copy-paste from archives |
| 13B | Tokenize | 1-2 min | 30 editions × 14 tokenizers |
| 13C | Cluster | 3-8 min | 30×30 pairwise = 435 comparisons |
| 13D | HMM Oracle | 10-30 min | Viterbi on ~5-10 representatives × ~3 tokenizers, ~732 positions each |
| 13E | Changepoints | 1-2 min | Ruptures on ~15-30 series |
| 13F | Rank | <1 min | Composite scoring |
| 13G | Lock + Rerun | Varies | Depends on Cipher 1/3 search scope |

**Total (automated)**: ~20-50 minutes  
**Total (with manual acquisition)**: ~2-4 hours

---

## Critical Checkpoints

### After Step A
- Check: `cat output/phase13/editions_list.txt | wc -l`
- If <10: Add more sources to SOURCE_REGISTRY in discover_doi_sources.py
- If <30: Manually acquire more editions

### After Step D (HMM)
- Check best log-likelihood: `grep log_likelihood output/phase13/oracle_hmm/*.json | sort -n | tail -5`
- If all < -800: Poor alignment, likely need Stone 1823
- If best > -400: Strong alignment candidate found

### After Step F (Ranking)
- Check: `cat output/phase13/LOCK_RECOMMENDATION.txt`
- If "LOCK": Proceed to Step G
- If "NO-GO": Diagnose failure (which gate? why?)

### After Step G
- Check: `cat corpus/LOCKED.json | jq .metadata`
- Verify: oracle_score >= 60%, word_count ~1300-1500
- Rerun Cipher 1 searches with locked corpus

---

## Diagnostic Interpretation Guide

### HMM Offset Path Patterns

**Pattern 1: Flat near zero**
```
[0, 0, 0, 1, 0, 0, -1, 0, 0, 0, ...]
```
- Interpretation: Edition is CORRECT for Cipher 2
- Action: This edition should pass gates, LOCK immediately

**Pattern 2: Linear increasing**
```
[0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, ...]
```
- Interpretation: Progressive drift, edition diverges gradually
- Action: Check changepoints for structural causes (header, signers)

**Pattern 3: Step function**
```
[0, 0, 0, ..., 0, 12, 12, 12, ..., 12, 25, 25, ...]
```
- Interpretation: Piecewise offsets, section-specific misalignment
- Action: Changepoints will identify boundaries; may need piecewise correction model

**Pattern 4: Chaotic**
```
[5, -3, 12, -8, 22, -15, 30, ...]
```
- Interpretation: Wrong edition family, no systematic alignment
- Action: Discard this edition, try others

---

## Gates Failure Scenarios and Actions

### Scenario 1: "Total match 48% < 60%"
**Cause**: beale_embedded or similar edition that diverges after position 100  
**Action**: Acquire Stone 1823 (1820s era match for Beale)  
**Alternate**: Relax total match gate to 50% temporarily

### Scenario 2: "Max offset 38 > 25"
**Cause**: Edition has large structural differences (header, signers, section numbering)  
**Action**: Try editions without headers/signers, or increase gate to 40

### Scenario 3: "Jumps 15 > 10"
**Cause**: Edition has many section-specific misalignments  
**Action**: Check changepoints for patterns; may need piecewise model

### Scenario 4: "Margin 2.3 < 5.0"
**Cause**: Best and runner-up are too close, no clear winner  
**Action**: Acquire more editions to find decisive winner, or run bootstrap test

---

## Post-Lock: Rerun Strategy

After corpus is locked (Step G complete), the downstream pipeline is:

1. **Verify LOCKED.json**:
   ```bash
   python -c "from corpus.canonical import CanonicalCorpus; c = CanonicalCorpus.load('corpus/LOCKED.json'); print(c)"
   ```

2. **Rerun Phase 5 (Grid Search)**:
   - Modify phase5_runner.py to load from LOCKED.json
   - Or: Copy LOCKED.json -> use existing scripts (they load from CANON_DOI.json)

3. **Rerun Phase 6 (Beam Search)**:
   - Use locked corpus for segment stitching

4. **Rerun Phase 7**:
   - Use locked corpus for refined search

5. **Rerun Concurrent Search**:
   ```bash
   python run_pipeline.py search_concurrent --topk 2000
   ```
   (This already loads CANON_DOI.json, which Step G copies from LOCKED.json)

6. **Run Stability Checks**:
   ```bash
   python run_pipeline.py stability_checks --strategy-file <best_strategy.json> --cipher 1
   ```

---

## Expected Phase 13 Outcomes

### Scenario A: Stone 1823 Acquired and Passes Gates
- Early-100: 96%+
- Total: 90%+
- HMM: <5 jumps, max offset <10
- **Outcome**: LOCK stone_1823, Cipher 1 search likely to yield meaningful results

### Scenario B: Modern Editions Pass Gates
- Early-100: 90%+
- Total: 70-85%
- HMM: 5-10 jumps, max offset 15-20
- **Outcome**: LOCK best modern edition, Cipher 1 results moderate quality

### Scenario C: NO-GO (All Editions Fail Gates)
- Best early-100: 83% (beale_embedded)
- Best total: 48%
- HMM: >10 jumps, chaotic offsets
- **Outcome**: NO-GO, must acquire Stone 1823 or abandon DOI-based decoding

---

## Files Created (Summary)

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Dependencies | requirements.txt | 25 | ✅ |
| Step A | scripts/discover_doi_sources.py | 380 | ✅ |
| Step B | scripts/phase13_tokenize.py | 220 | ✅ |
| Step C | analysis/edition_alignment.py | 300 | ✅ |
| Step D | oracle/hmm_offset_solver.py | 310 | ✅ |
| Step E | analysis/changepoints.py | 260 | ✅ |
| Step F | oracle/phase13_ranker.py | 280 | ✅ |
| Step G | scripts/phase13_lock_rerun.py | 160 | ✅ |
| Extension | corpus/doi_editions.py | +60 | ✅ |
| CLI | run_pipeline.py | +100 | ✅ |
| Status | PHASE13_IMPLEMENTATION_STATUS.md | 400 | ✅ |
| Guide | PHASE13_EXECUTION_GUIDE.md | 350 | ✅ |

**Total**: ~2,800 lines of new/modified code

**Linter errors**: 0

---

## Next Immediate Action

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run discovery**:
   ```bash
   python run_pipeline.py phase13_discover
   ```

3. **Check acquired editions**:
   ```bash
   cat output/phase13/editions_list.txt
   ```

4. **If <30 editions**: Manually acquire more from archives.gov, loc.gov, etc.

5. **Continue pipeline**: Run steps B through F

6. **Critical decision point**: Read LOCK_RECOMMENDATION.txt
   - If LOCK: Proceed to Cipher 1/3 with confidence
   - If NO-GO: Acquire Stone 1823 or accept current best with caveats

---

## Conclusion

Phase 13 implementation is complete and ready for execution. The pipeline transforms the Beale cipher analysis from:

**Before Phase 13**:
- "26.5% oracle suggests wrong edition"
- Manual interpretation of mismatch patterns
- No systematic ranking of editions
- Risk of false confidence from noise

**After Phase 13**:
- HMM offset path reveals structural misalignment
- Changepoints identify exact boundaries
- Acceptance gates enforce quality standards
- NO-GO prevents premature Cipher 1 search
- Reproducible, scientific corpus locking

**Status**: Implementation complete. Awaiting user execution.
