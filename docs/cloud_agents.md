# Cloud Agents: Full task prompts

Copy these into **New Agent** (Cursor web or editor) once the repo is on GitHub and Cursor is connected.

---

## Agent 1 — Run Phase 103 C3 and record artifacts

From repo root, run `python scripts/nomenclator_solver.py`. Ensure `output/phase103/` contains at least `c2_solver_validation.txt`. If the run completes the C3 section, there should also be `c3_modeA_ranked.csv`, `c3_modeB_ranked.csv`, `c3_controls_summary.txt`, and files in `output/phase103/top_streams/`. Summarize in a short markdown report: C2 validation pass/fail, C3 Mode A and B z-scores vs controls, and whether any decode meets the gate (z ≥ 6). Add that report as `output/phase103/cloud_run_report.md`. Commit the new/changed artifacts under `output/phase103/` and the report, then open a PR with title "Phase 103 solver cloud run artifacts".

---

## Agent 2 — Compass/address C3 test from audit

Implement the "compass/address C3 test" from `output/phase103/audit_patterns_and_potential_solutions.md`: a script that scores C3 decodes (and optionally C1 80-char windows) only for directional/address phrases (e.g. miles NE/NW/SE, ELM, MR, county). Use a small built-in lexicon of such terms. Compare score vs shuffled-cipher control; report z-score and any repeated fragments. Add the script under `scripts/` (e.g. `compass_address_c3_test.py`), run it, and write results to `output/phase103/compass_address_report.txt`. Add a unit test that checks the scorer returns higher score for a string containing "NE" and "COUNTY" than for random letters. Commit script, output, and test; open a PR with title "Compass/address C3 test and artifacts".

---

## Agent 3 — C2 mapping bootstrap for C3

Implement the "C2 mapping bootstrap for C3" from `output/phase103/audit_patterns_and_potential_solutions.md`: (1) From the DOI and C2 known plaintext, build the true C2 number→letter mapping. (2) Identify numbers that appear in both C2 and C3. (3) In the nomenclator solver (or a small separate script), fix those symbols to the C2-derived letters and optimize only the remaining symbols for C3. Compare score vs the existing full-hillclimb C3 run (or vs shuffled control). Add the bootstrap script under `scripts/` (e.g. `c2_bootstrap_c3.py`), document assumptions and edge cases in a short docstring or `output/phase103/c2_bootstrap_notes.md`, and open a PR with title "C2 mapping bootstrap for C3".
