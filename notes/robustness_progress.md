# Robustness pass — progress log

Tracking file for `notes/robustness_loop_prompt.md`. Each loop iteration reads this
file first, works one item, then appends an update here before finishing. Do not
delete history — append dated entries under the relevant item.

Seeded 2026-07-07 from a repo scan; nothing below has been verified this pass yet.
Items 3 and 7 have *unverified* prior artifacts on disk (see notes) — item 1 (audit)
must confirm them before anything relies on them.

## Checklist status

1. Audit + reproduce existing numbers — **In progress** (2026-07-07: synthetic audit
   tests done + passing; C1–C4 + censored headline tables re-derived this session and
   reproduce the notes; `run_allruns` + transfer tables are DATA-BLOCKED on this box —
   only the 3 opus runs are downloaded, not the full 19 model×env set).
2. Marginal -> conditional coverage (Mondrian) — **Not started**
3. Kill hyperparameter / trivial-baseline objections — **In progress / partly confirmed**
   - Confirmed 2026-07-07: DtACI + constant-quantile ARE default-on in `run_coverage`
     (both present in tables/coverage.csv). Honest gap: the constant-quantile baseline
     reaches within ~0.03–0.05 coverage of the fitted guard but at 20–56% WIDER
     intervals — the guard's value is sharpness, not raw coverage. Still to do: confirm
     default-on across the *other* run_*.py table scripts.
4. Honest uncertainty everywhere — **Not started**
5. One external, non-BAGEN dataset — **Not started**
6. Transfer-led main figure — **Not started**
   - `run_transfer.py` and `run_transfer_env.py` exist on disk already. Unverified —
     confirm they run and reproduce the 12-76% collapse number cited in
     notes/positioning.md before building the figure on top of them.
7. Ship the wrapper as generality proof — **Not started**
   - `budget_guard/guard.py` (`BudgetGuard` class), a README wrapper-API section,
     and `tests/test_guard.py` already exist on disk (new/untracked as of 2026-07-07).
     Unverified — this is new, unaudited code; run the tests and the README demo
     before treating any of it as working.
8. Censored conformal resource-bound refinement — **Not started**
   - `budget_guard/censored.py`, `run_censored.py`, `run_gated.py` already implement
     rungs 1-3 per notes/week6.md (drop / bound / resource_bound / gated methods).
     Unverified this pass — re-run and diff against the week6.md tables first.
9. Closed-loop limitation — **Not started**

## Log

### 2026-07-07 — Item 1 (audit), loop iteration 1

Status: **In progress.** Synthetic audit tests written + passing; every headline table
runnable on this machine's data was re-derived THIS session and reproduces the notes.
`run_allruns` and the transfer tables are **data-blocked** here (only the 3 opus runs
are downloaded, not the full 19 model×env set — see `scripts/fetch_bagen.py`).

Ran (venv `.venv`, Python 3.12; seeds 0–4 unless noted):
- `pytest -q` → **22 passed, 2 skipped**. The 2 skips = BAGEN `_smoke` sample (BAGEN repo
  not checked out) + the 300-char sokoban official record Windows MAX_PATH can't open
  here. Neither is a failure.
- `tests/test_audit.py` (NEW, 3 tests): (a) clean i.i.d. data — split-CQR coverage
  contains nominal 0.90 in its rollout cluster-bootstrap CI; (b) split-absres clean
  coverage in [0.86, 0.94]; (c) injected drift (y·1.6+6 on a fresh stream) — FROZEN
  split-CQR degrades and ONLINE SPCI recovers (frozen <0.75, online ≥ frozen+0.10,
  online ≥0.80). The transfer story's direction holds on synthetic data.
- `run_coverage` (C1) → **EXACT reproduction** of week3/week4 (5 seeds):
  sokoban ACI 0.920±0.019 / SPCI 0.916±0.019 / DtACI 0.936±0.011;
  swebench ACI 0.946±0.032 / SPCI 0.916±0.024 / DtACI 0.950±0.015;
  swebench agent self-report 0.354. All match the notes to the quoted precision.
- Earlier this session: `run_multiresource` (C2) guard independent 0.80 / bonferroni
  0.95 / copula 0.885 (week5 ✓); `run_economic_warehouse` (C3/C4) 86.3% doomed-$ saved
  @ 0% false-abort, cost-of-pass −46% (week6 ✓); `run_censored` bound qhat cost 385k /
  ipcw ~65k reproduce (week6 ✓).

Findings (negative + cross-cutting flagged as prominently as positive):
- **Item 3 gap (honest):** constant-quantile reaches 0.883 (sokoban) / 0.924 (swebench)
  coverage — only ~0.03–0.05 below the fitted guard — but at **20–56% wider intervals**
  (normalized width sokoban 1.10 vs SPCI 0.86; swebench 2.87 vs DtACI 1.26). The fitted
  guard earns its keep on **sharpness, not raw coverage**. This must be stated plainly
  in the writeup, not omitted.
- **Item 4 confirmed** for run_coverage: 5 seeds + rollout cluster-bootstrap CIs
  (cov_ci90_lo/hi), not binomial.
- **Negative:** searchr1 within-run is tiny (n_test≈24) and noisy (coverage_std up to
  0.17; DtACI 15% unbounded → inf width). Unreliable — matches week2's caveat; do NOT
  headline searchr1 within-run.
- **Data limit (not a discrepancy):** sokoban/searchr1 agent-self-report baselines are
  absent here — their official estimation records are 300-char paths Windows can't open;
  swebench baseline (0.354) does load.
- **Format change (not a discrepancy):** `run_censored` was restructured this session to
  sweep all 3 resources with stratified (feasible/binding/non-binding) coverage (week6
  rungs 2–3), so it no longer emits the single "cov_censored 0.786" cell of the old
  rung-1 table; the qualitative rung-1 findings + qhat magnitudes reproduce.
- Byproduct: item 7 (`tests/test_guard.py`) and item 8 (`tests/test_censored.py`) pass
  inside the 22 — the wrapper and censored code are not broken, but item 7's *clean-install*
  and item 6's *transfer figure* are still their own items.

Remains for item 1: re-run `run_allruns` (needs the other 16 model×env dialogue sets)
and the transfer tables (item 6) on a machine with the full BAGEN download. Marked
data-blocked, not skipped.

Reproduce: `.venv\Scripts\python -m pytest -q`;
`.venv\Scripts\python -m budget_guard.{run_coverage,run_multiresource,run_economic_warehouse,run_censored}`.
Data via `python scripts/fetch_bagen.py`.
