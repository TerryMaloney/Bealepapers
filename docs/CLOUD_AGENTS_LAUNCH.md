# Cloud Agents Launch: Phase 104, 105, 107

Use this after the repo is on GitHub and `git push -u origin main` has succeeded.

---

## Part A — Local status (done)

- **Git:** No stuck process; `git status` succeeded.
- **Staged and committed:** `git add .` then `git commit -m "Initial commit"` (621 files).
- **Remote:** Not set. You must:
  1. Create an **empty** repo on GitHub (no README, no license).
  2. Run:
     ```powershell
     cd d:\BealeCiphers
     git remote add origin https://github.com/<YOUR_USER>/<YOUR_REPO>.git
     git push -u origin main
     ```
  3. Verify: `git log --oneline -5` and `git remote -v`.

---

## Part B — Three Cloud Agent prompts (run in parallel)

In Cursor Cloud Agents, select this repo and start these three runs.

### Agent 1 — Phase 104: C2 mapping bootstrap → constrained C3 solver (highest ROI)

**PROMPT:**

TASK: Phase 104 — C2 mapping bootstrap → constrained C3 solver.
Goal: anchor C3 solving to ground truth from validated Cipher 2, to prevent quadgram overfitting.

Steps:
1) Build true mapping for C2: number->letter using the validated C2 decode pipeline (NOT the overfitting solver).
   Save output/phase104/c2_number_to_letter.json
2) Compute overlap O = numbers(C2) ∩ numbers(C3).
   Save output/phase104/c2_c3_overlap.csv
3) Constrained C3 solver:
   - Fix mapping for any number in O to the C2-derived letter.
   - Optimize remaining mappings under objective:
     0.5*names_kin_scorer + 0.3*quadgram + 0.2*word_pattern
   - Include SPACE.
   - 10 restarts + 200 shuffled-cipher controls. Report z-scores.
   Save output/phase104/c3_constrained_ranked.csv and output/phase104/top_streams/
4) Sanity upgrade: show C2 recovery improves vs the previous ~7% match case.
   If C2 recovery does not materially improve, do NOT trust any C3 result.

Deliverables:
- output/phase104/* (json/csv/top_streams/controls_summary.txt/next_move.md)
- next_move.md must include exact commands run and whether C2 recovery improved.

---

### Agent 2 — Phase 105: OCR consensus + uncertain decode (C3-first)

**PROMPT:**

TASK: Phase 105 — OCR consensus + uncertain-letter decode on C3.
Goal: if OCR noise is masking the key text, recover signal using consensus + beam/Viterbi.

Steps:
1) Identify keytexts with multiple OCR sources/editions (if any exist locally).
2) Build consensus token/first-letter stream via alignment (store provenance).
   Save corpus/keytexts/normalized_consensus/*.json
3) Implement uncertain-letter decoding for C3:
   - each position yields a small candidate letter set (from OCR variants/consensus)
   - beam search maximizing names_kin_scorer + quadgram
   - 200 shuffled-cipher controls + report z-scores
Outputs:
- output/phase105/c3_uncertain_ranked.csv
- output/phase105/top_streams/
- output/phase105/controls_summary.txt
- output/phase105/next_move.md

---

### Agent 3 — Phase 107: Generator-family classifier (structure-only, no books)

**PROMPT:**

TASK: Phase 107 — Generator-family classifier for C1/C2/C3.
Goal: determine which generator family best fits C1/C3 (book-sampling vs homophonic vs engineered/marker), using C2 as a control.

Steps:
1) Fit models:
   - book-sampling (uniform + Zipf bias + "laziness" parameter)
   - homophonic symbol stream model
   - engineered stream (book-sampling + flattening + planted-marker likelihood proxy)
2) Compare with multiple stats: singleton %, repeat gaps, digit histograms, IC proxy, repeated n-grams.
3) Validate: classifier must label C2 as "book-like" more than alternatives.

Outputs:
- output/phase107/generator_fit_report.txt
- output/phase107/model_params.json
- output/phase107/next_move.md

---

## Part C — Acceptance rules (apply to all agents)

- **Tests:** Must run tests if present: `pytest tests/ -v`
- **Controls:** Any "signal" claim must include control comparisons (shuffle baselines).
- **Artifacts:** Must write outputs under `output/phaseXXX/` for the phase number.
- **next_move.md:** Every phase must produce `output/phaseXXX/next_move.md` with:
  - Commands run (exact)
  - Key metrics
  - What changed list

---

## Quick reference: exact commands for Part A (already run)

```powershell
cd d:\BealeCiphers
git status
# If index.lock error: Get-Process git -ErrorAction SilentlyContinue; Remove-Item -Force .git\index.lock
git add .
git commit -m "Initial commit"
git remote -v
# If no origin: git remote add origin https://github.com/<YOUR_USER>/<YOUR_REPO>.git
# git push -u origin main
git log --oneline -5
```
