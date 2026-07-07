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
2. Marginal -> conditional coverage (Mondrian) — **In progress** (2026-07-07: core done —
   `run_conditional.py` gives per-env × 5-seed by-depth coverage + worst-slice with
   cluster-bootstrap CIs; Mondrian confirmed to close the sokoban k=1 hole 0.860→0.927,
   reproducing week5; figure + synthetic test added. Honest: the hole is sokoban-specific
   — swebench over-covers, searchr1 too small.)
3. Kill hyperparameter / trivial-baseline objections — **In progress / partly confirmed**
   - Confirmed 2026-07-07: DtACI + constant-quantile ARE default-on in `run_coverage`
     (both present in tables/coverage.csv). Honest gap: the constant-quantile baseline
     reaches within ~0.03–0.05 coverage of the fitted guard but at 20–56% WIDER
     intervals — the guard's value is sharpness, not raw coverage. Still to do: confirm
     default-on across the *other* run_*.py table scripts.
4. Honest uncertainty everywhere — **Not started**
5. One external, non-BAGEN dataset — **Done (cheapest option) / strong version Blocked**
   (2026-07-07: unmodified guard hits ~0.90 coverage on a real local non-BAGEN
   source-code corpus via `scripts/run_external.py`; a pipeline-generality smoke test,
   NOT agent-domain. Strong agent-domain validation — real agent logs / AssetOpsBench /
   GM units — Blocked-needs-resources; proposal in log.)
6. Transfer-led main figure — **In progress** (2026-07-07: cross-env transfer figure done
   + reproduced with 5-seed cluster-bootstrap CIs — frozen split-CQR collapses to 0.10 on
   sokoban->swebench, SPCI self-heals to 0.90 at 0% unbounded. Model-SWAP (run_transfer)
   DATA-BLOCKED: needs other-model swebench dialogues, only opus on disk.)
   - `run_transfer.py` and `run_transfer_env.py` exist on disk already. run_transfer_env
     VERIFIED reproducing week3/4; run_transfer verified to import but target_runs()
     returns empty here (data-blocked).
7. Ship the wrapper as generality proof — **Done** (2026-07-07: added pyproject.toml
   (pip-installable) + runnable no-data `examples/quickstart.py`; clean `pip install -e .`
   + demo verified in a FRESH isolated venv. The clean install CAUGHT + FIXED a real bug:
   scikit-learn was under-declared (required by lightgbm's sklearn API). test_guard passes.)
8. Censored conformal resource-bound refinement — **Blocked — needs PI sign-off**
   (2026-07-07: rungs 1–3 VERIFIED reproducible this pass — resource_bound cost 0.46 /
   time 0.90, qhat 64k, frac_binding 0.42 match week6; rung-3 gated + KM covered by the
   7 passing test_censored tests. A tight proposal for the next increment is in the log;
   not started pending PI scoping — no unilateral new methods direction.)
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

### 2026-07-07 — Item 2 (marginal -> conditional coverage), loop iteration 2

Status: **In progress (core done).** Built `run_conditional.py` (extends the single-env
Week-2 `run_gap.py`): per-env × 5 seeds, split-CQR vs Mondrian-CQR, coverage by depth
bucket (k=1 / k=2 / k>=3) + worst-slice, with rollout cluster-bootstrap CIs. Wrote
`figures/conditional_coverage.png` + `tables/conditional_coverage.csv`. New synthetic
test `tests/test_conditional.py` (Mondrian closes a constructed k=1 hole).

Ran: `python -m budget_guard.run_conditional`; `pytest -q` -> **23 passed, 2 skipped**.

Key numbers (5 seeds, mean; cluster-bootstrap CI):
- **sokoban: the k=1 hole is real and Mondrian closes it — reproduces week5 exactly.**
  split-CQR marginal 0.916 HIDES k=1 = **0.860** (CI [0.75, 0.95]); Mondrian k=1 = **0.927**.
  Worst-slice (min over buckets): split-CQR 0.855 -> Mondrian 0.895. week5 quoted
  0.860 -> 0.927 ✓.
- **swebench: NO hole** — over-covers at every depth (k=1 0.988 / k=2 0.988 / k>=3 0.950);
  Mondrian neutral. The conditional failure is env-specific, not universal.
- **searchr1: too small to conclude** — n≈7–17 per bucket, CIs ±0.15; k>=3 dropped (<5).
  Mondrian falls back to the global qhat (buckets < min_bucket=10). No searchr1 claim.

Framing draft (one paragraph): *Marginal coverage is a mirage where trajectories are
short. On sokoban the pooled 0.916 looks fine, but the k=1 slice — the first, highest-
leverage abort decision — sits at 0.860, below nominal, because one global qhat is set
by the many easy late-turn prefixes. Mondrian-by-depth calibrates a separate qhat per
depth bucket and restores k=1 to 0.927 (worst-slice 0.855->0.895), at no cost where
there is no hole (swebench unchanged). Honest scope: a short-horizon phenomenon, not
universal.*

Negative/honest: k=1 buckets are small (≈30 test rollouts -> wide single-seed CIs); the
hole is robust across 5 seeds (cov_std 0.064) but a single seed's CI overlaps nominal.
Item 4 practice (cluster-bootstrap CIs, 5 seeds) applied throughout this table.

Remains: (a) PI decision whether the by-depth cut belongs on the warehouse/economic
tables (there "depth" = completed_weeks and the guard is joint/economic — a different
cut); (b) promote the framing paragraph into notes/positioning.md at writeup time;
(c) by-depth for other models needs the full dataset (item-1 data blocker).

Reproduce: `.venv\Scripts\python -m budget_guard.run_conditional`;
`.venv\Scripts\python -m pytest tests/test_conditional.py -q`.

### 2026-07-07 — Item 5 (external non-BAGEN dataset), loop iteration 3

Status: **Done for the stated Done-when (cheapest option); strong agent-domain external
validation Blocked — needs resources.** AssetOpsBench is only named in the loop prompt,
not scoped in implementation_plan.md; real-agent logging needs an API key; GM cost units
need Andrew/data access. So I did the cheapest viable no-API, no-new-dep, no-fabrication
option.

Built `scripts/run_external.py`: runs the UNMODIFIED guard (same build_xy + conformal
path as BAGEN, zero per-dataset special-casing) on a real LOCAL non-BAGEN corpus — 621
source files (venv site-packages + repo), each file a "session", blank-line blocks as
"turns", per-turn "tokens" from the repo's OWN word tokenizer
(extract._rough_text_token_count), all real measured counts. 10,089 prefix samples,
median 645 tokens/session; predicts remaining-tokens-to-end from prefix-only features.

Result (5 seeds, rollout cluster-bootstrap CI):
| method | coverage | CI | norm. width |
|---|---|---|---|
| constant-quantile | 0.894 | [0.873, 0.916] | 1.27 |
| split-absres | 0.900 | [0.871, 0.928] | 1.08 |
| split-CQR | 0.905 | [0.871, 0.942] | 1.14 |

Findings:
- **POSITIVE generality:** the unmodified guard is well-calibrated off BAGEN — split-CQR
  0.905 / split-absres 0.900, both CIs contain nominal 0.90. The pipeline is not
  secretly BAGEN-specific.
- **NEGATIVE / honest (item-3 cross-cut):** on THIS domain the trivial constant-quantile
  baseline (0.894, norm width 1.27) is nearly as good — split-CQR is only ~0.01 higher
  coverage and ~10% sharper (vs 20–56% sharper on BAGEN). Burn-rate features carry much
  less signal for code length than for agent budgets. State this plainly in the writeup.
- **Limitations:** source code, NOT agent trajectories; short sessions (~645 tok);
  offline only (no drift/transfer tested); "tokens" = word-level counts, not real LLM
  tokens. A PIPELINE-GENERALITY smoke test, not deployment-transfer evidence.

Verification: `python scripts/run_external.py` runs end-to-end to the table above;
reuses already-tested library code unmodified; `pytest -q` still **23 passed, 2 skipped**.
The corpus is regenerable from the checked-in script (not committed — gitignored/large).

BLOCKED — needs PI/human for the STRONG (agent-domain) external validation:
- Option A (best): log ~30 real tool-using agent runs (Claude Code / SWE-agent) with
  per-turn token usage -> extractor schema -> guard. Needs a small API budget.
- Option B: AssetOpsBench, IF its trajectories expose per-step token/resource usage
  (unverified; not scoped in implementation_plan.md); ~1 day to parse.
- Option C: Andrew's anonymized GM cost-unit trajectories; needs data access + sign-off.
Proposal: authorize a small API budget for Option A (~30 runs) — highest-value,
self-contained agent-domain evidence.

Reproduce: `.venv\Scripts\python scripts\run_external.py`.

### 2026-07-07 — Item 6 (transfer-led figure), loop iteration 4

Status: **In progress** — cross-env transfer figure done + reproduced with CIs; model-swap
(run_transfer) DATA-BLOCKED (needs other-model swebench dialogues; only opus on disk).

Verified `run_transfer_env` (seed 0) reproduces week3/week4 cross-env EXACTLY:
sokoban->swebench frozen split-CQR 0.119 (week3 0.12), SPCI 0.903 (week3 0.903, 0%
unbounded); sokoban->searchr1 frozen 0.506 (0.51), SPCI 0.713 (0.71 at w=100 — the
documented window miss), ACI 0.87 w/ 61% unbounded. Then extended it to **5 seeds +
rollout cluster-bootstrap CIs** (item-4 hygiene) with an error-bar figure.

5-seed transfer-led headline (figures/transfer_env.png, tables/transfer_env.csv):
| scenario | frozen split-CQR | ACI-CQR | SPCI |
|---|---|---|---|
| sokoban->searchr1 | 0.51 [0.40,0.62] | 0.82 (58% unbounded) | 0.73 [0.65,0.81] |
| sokoban->swebench | **0.10 [0.08,0.13]** | 0.89 (86% unbounded) | **0.90 [0.86,0.94]** (0% unb.) |

Framing (THE LEAD): frozen conformal collapses to **0.10** on the hardest cross-env shift
(sokoban->swebench) — the "12-76% collapse" low end, reproduced. SPCI self-heals to nominal
0.90 with 0% unbounded; ACI "recovers by surrender" (near-nominal but 58-86% unbounded).
This transfer figure is the paper's LEAD; the within-distribution tables (items 1-2) are
supporting material.

Reproduced/corrected: the 12% low end -> 0.10 (5-seed mean, CI [0.08,0.13]). The 76% HIGH
end of the collapse range was the model-SWAP gpt-5.2 case (week3), DATA-BLOCKED here.

Remains: model-swap bars (sonnet/gemini/gpt/qwen) via run_transfer once the full dataset
is downloaded. Suite: **23 passed, 2 skipped**.

Reproduce: `.venv\Scripts\python -m budget_guard.run_transfer_env`.

### 2026-07-07 — Item 7 (ship the wrapper), loop iteration 5

Status: **Done.** The wrapper is pip-installable and a clean install + demo runs
end-to-end from a fresh isolated environment — and that clean install CAUGHT A REAL BUG.

What I did:
- Added `pyproject.toml` (setuptools; name budget-guard, packages=[budget_guard]). Lean
  wrapper runtime deps; the full experiment suite is behind an [experiments] extra.
- Added `examples/quickstart.py` — a runnable NO-DATA demo (synthetic runs -> calibrate
  -> stream a live run -> abort). Wired install + demo into the README.
- Verified in a FRESH isolated venv (uv, in TEMP): `pip install -e .` then
  `python examples/quickstart.py`.

**BUG FOUND + FIXED** (evidence the wrapper was new/unaudited code): the first clean
install declared deps numpy/pandas/lightgbm and the demo CRASHED with
`LightGBMError: scikit-learn is required for lightgbm.sklearn`. The guard uses LGBM's
sklearn API (LGBMRegressor/Classifier), so scikit-learn is a REQUIRED runtime dep, not
optional. The main .venv had it (masking the gap); the minimal fresh env exposed it.
Fix: moved scikit-learn into core `dependencies`; reinstall -> demo runs clean.

Demo transcript (fresh env, after fix):
    Calibrated a training-free BudgetGuard on 120 synthetic runs (budget=900).
    turn 1: spent    252 | remaining in [   368,    900]
    turn 2: spent    459 | remaining in [   288,    922]
    turn 3: spent    674 | remaining in [   167,    805]
    turn 4: spent    919 | remaining in [    87,    612]   <-- ABORT: projected spend exceeds budget

test_guard.py passes inside the suite (**23 passed, 2 skipped**).

Reproduce: `uv venv $env:TEMP\bg; uv pip install --python $env:TEMP\bg -e .;
$env:TEMP\bg\Scripts\python examples\quickstart.py`  (or plain `pip install -e .`).

### 2026-07-07 — Item 8 (censored refinement), loop iteration 6

Status: **Blocked — needs PI sign-off.** Rungs 1–3 re-verified reproducible; a concrete
next-increment proposal is below. Per the loop rules I did NOT start a new methods
direction unilaterally.

Verification this pass:
- `run_censored`: resource_bound cost cov_feasible 0.863 / cov_cens_binding **0.459** /
  qhat **63.5k** / frac_binding **0.422**; time resource_bound **0.90/0.90/0.90** — all
  match week6 "P2 rung 2". drop/bound/km rows also reproduce (drop binding 0.50, bound
  385k, km 0.58) as seen in the item-1 audit run this session.
- `test_censored.py`: 7 tests pass (resource_bound x3, gated x2, km x2) inside the suite
  (23 passed / 2 skipped). Rung-3 gated cost 0.92 was reproduced + committed earlier this
  conversation (Phase-1).

**PI-ready proposal — next increment: IPCW on the feasibility-gated (kept) subpopulation.**
- Experiment: re-run IPCW-weighted conformal (already in `censored.upper_qhat(method=
  "ipcw")`) but ONLY on the runs the gate keeps (predicted-feasible), and measure both
  the empirical positivity (min p̂(uncensored|x) on kept) and coverage.
- Hypothesis / what it would show: the un-gated IPCW failed because censoring is
  near-deterministic in x (doom decidable from config → positivity/overlap violated,
  week6 finding). The gate removes exactly that near-deterministic-doom mass, so on the
  kept set p̂(uncensored|x) should be bounded away from 0 → positivity restored → IPCW
  recovers *marginal* coverage (not just coverage-conditional-on-kept). Result either
  way is publishable: positivity restored = "selective + IPCW conformal for multi-
  resource agent budgets" (marginal guarantee); still-violated = the honest selective-
  only story stands.
- Effort: ~1–2 days (reuse ipcw + the gate; add a gated-IPCW variant, a positivity
  diagnostic, and a coverage table; +1 test).
- Why PI sign-off FIRST: (a) which guarantee to claim (marginal-on-full vs selective-
  on-kept); (b) lit-review must confirm novelty vs conformalized-survival IPCW; (c) keep
  it scoped — do NOT expand into a full survival-analysis subproject.

No code changes this iteration (proposal + verification only).
