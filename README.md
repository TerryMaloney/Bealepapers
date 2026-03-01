# Beale Ciphers Analysis

Analysis of the Beale ciphers (C1, C2, C3): structural tests, DOI/keytext decodes, nomenclator-capable homophonic solver (Phase 103), and audit of test-result patterns. Python 3, POSIX-friendly paths; runs on Linux/macOS/Windows and in Cursor Cloud Agents (Ubuntu).

## Cloud Agent Setup

Use this section when running the repo in Cursor Cloud Agents or any fresh Ubuntu VM.

- **Install** (from repo root):
  ```bash
  pip install -r requirements.txt
  ```
- **Run tests:**
  ```bash
  pytest tests/ -v
  ```
  Or: `python -m pytest tests/ -v`
- **Run Phase 103 solver** (C2 validation, then C3 Modes A/B/C if C2 passes):
  ```bash
  python scripts/nomenclator_solver.py
  ```
  Writes to `output/phase103/` (e.g. `c2_solver_validation.txt`, `c3_modeA_ranked.csv`, `c3_controls_summary.txt`, `top_streams/`).
- **Secrets:** None required for the core solver. Optional env: `BEALE_PAMPHLET_PDF_PATH` for pamphlet PDF extraction; agents can run without it.

## Pushing to GitHub (for Cloud Agents)

Cloud Agents need the repo on GitHub and Cursor connected with write access (to open PRs).

**Option A — existing folder (this repo):**

1. Create a new **empty** repo on GitHub (no README, no license).
2. From the project folder:
   ```bash
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/<you>/<repo>.git
   git branch -M main
   git push -u origin main
   ```
   If `git add` fails with `index.lock` exists, another git process is using the repo; close it or wait, then retry.

**Option B:** Create the repo on GitHub, clone it, copy this code in, then push.

In Cursor: sign in, connect GitHub in settings, and ensure the repo is authorized so Cloud Agents can create PRs.

## Example Cloud Agent prompts

- **Agent 1 — Phase 103 run:** Run `python scripts/nomenclator_solver.py`, summarize C2/C3 results in `output/phase103/cloud_run_report.md`, commit artifacts and open a PR titled "Phase 103 solver cloud run artifacts".
- **Agent 2 — Compass/address C3 test:** Implement the compass/address test from `output/phase103/audit_patterns_and_potential_solutions.md` (script under `scripts/`, results in `output/phase103/compass_address_report.txt`), add a unit test, commit and open a PR.
- **Agent 3 — C2 bootstrap for C3:** Implement C2 mapping bootstrap for C3 per the audit (script e.g. `scripts/c2_bootstrap_c3.py`, notes in `output/phase103/c2_bootstrap_notes.md`), commit and open a PR.

See the plan in `.cursor/plans/` or **docs/cloud_agents.md** for full prompt text.
