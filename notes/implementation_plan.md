# Implementation plan — the three ceiling-raisers

Drafted 2026-07-04, after Weeks 1–5 results (see `notes/week*.md`). Ordered by
impact-per-day and dependency: **P3 first (half day), P1 next (~1 day), P2 last
(3–5 days, needs PI sign-off on the guarantee).** The lit-review team's questions
are at the bottom — please answer those before P2 starts.

---

## P3 (do first) — the agent's own estimate as a feature / as the predictor

**Why:** reframes the paper from "replace the agent's self-knowledge" to
"*calibrate* it" — ties directly to BAGEN, likely sharpens intervals for free, and
adds the fairest possible baseline ("agent estimate + conformal wrapper, zero
training").

**Data (verified):** every estimation record's `prediction` field carries the
parsed per-turn estimate — `remaining_token_interval: [lo, hi]` and `can_finish` —
keyed by `sample_id` that matches our extractor's IDs exactly (0-mismatch join
already proven on 3 envs).

**Changes:**
1. `data.py`: `load_agent_estimates(env) -> DataFrame[sample_id, agent_lo,
   agent_hi]` from the estimation record; inner-join onto the extractor df
   (expect ~100% match on the 19 runs with records).
2. `features.py`: `build_xy(df, agent_est=False)` — adds `agent_mid`, `agent_width`,
   `agent_lo`, `agent_hi` when requested. These are legal features (produced at
   turn k from prefix-only context) — but confirm the estimation run's prompting
   model matches the origin run's agent (dir naming encodes both; use the paired
   dirs only).
3. `conformal.py`: nothing new — two evaluation variants in `run_coverage`:
   - **guard+self-est**: LGBM features ∪ agent features (ablation row);
   - **conformalized-agent**: `split_conformal_absres` with the *agent_mid* as the
     point prediction (no fitted model at all). One line via a shim regressor.
4. Report: sharpness delta at matched coverage; add "conformalized agent" to the
   headline figure — if it alone reaches ~0.9 coverage with decent width, that IS
   the paper's cleanest zero-training claim.

**Risks:** some runs' predictions may be missing/degenerate (qwen searchr1 coverage
0.02 suggests wild estimates — width features may be noise there). Handle NaNs;
report per-run.

**Deliverable:** updated `coverage.csv` + 2 new rows in headline figure + a
paragraph in notes. **Est: 0.5 day.**

---

## P1 — C3 + C4 on Warehouse (the env they were designed for)

**Why:** the current economics results half-lose to a hard cap because sokoban runs
are short and swebench doom = cap exceedance. Warehouse has long runs (~20 turns),
failure-driven doom (target-cash unreachable), THREE budget axes, and **native
dollars** — if the guard's frontier doesn't shine here it never will (and we need
to know either way).

**Data (verified):** per-prefix `ground_truth` carries legal features
(`completed_turns/weeks`, `current_cash_usd`, `target_cash_usd`, `budget_*`) AND
realized totals `actual_total_{time,warehouse,cost}` — for censored rows too. So
spend-so-far and doom labels are all computable. 1280 samples × 5 models; 64
rollouts each; 50% infeasible (great class balance).

**Changes:**
1. `multiresource.py::load_warehouse(keep_censored=True)`: keep censored rows with
   a `censored` flag; add `cost_so_far ≈ actual_total_cost_usd −
   actual_remaining_cost_usd` for feasible rows — for censored rows derive
   spend-so-far from `completed_weeks`-proportional interpolation OR (better) check
   whether per-turn spend is recoverable from `rollout_history_messages`; if not,
   use `completed_weeks / actual_total_time_weeks × actual_total_cost_usd` and
   state the approximation.
2. `economic.py`: generalize `evaluate_stopping`/`hard_cap_baseline` to take
   `(spent_col, total_col)` column names instead of hard-coded token columns
   (small refactor, keep token defaults so existing runners don't change).
3. `run_economic_warehouse.py`: feasibility classifier on warehouse features →
   frontier in **USD saved on doomed runs vs false-abort rate**; hard-cap baselines
   on weeks and on dollars (two heuristics, both must be beaten).
4. `run_costofpass warehouse`: passes = feasible & not aborted; costs natively in $
   (no price assumption needed — this kills the $15/Mtok hand-wave for one env).

**Success criterion:** guard frontier dominates BOTH hard caps at δ ≤ 0.2, and
cost-of-pass drops ≥10% at ≥90% passes retained. If it doesn't: report honestly;
the paper's economics claim narrows to "failure-driven, long-horizon settings" with
warehouse as the boundary case.

**Deliverables:** `figures/abort_frontier_warehouse.png`,
`figures/cost_of_pass_warehouse.png`, tables, notes. **Est: 1 day.**

---

## P2 — Censored conformal (the methods contribution; scope with PIs FIRST)

**Why:** the only path from "careful application paper" to "methods contribution."
The data motivates it natively: infeasible runs have their remaining-to-completion
undefined; context-truncated token runs are cut mid-flight (true right-censoring).

**Key design asset (verified today):** Warehouse censored rows retain
`actual_total_*`, so we can **mask labels to simulate censoring and measure true
coverage** — a validation most censored-conformal papers can't do on real data.

**Method plan (two rungs, climb until time runs out):**
1. *Rung 1 — one-sided lower bounds under censoring (defensible, simple):* a
   censored run observed to turn k has already spent `spent_k`; its true
   remaining-to-completion exceeds `budget − spent_k` (that's WHY it's censored).
   So censored samples contribute exact lower-bound labels. Calibrate the interval's
   LOWER endpoint using all samples (censored ones via their bound); upper endpoint
   from uncensored only, with an inflation correction. Guarantee claimable:
   valid lower-bound coverage marginally; upper bound valid on the feasible
   subpopulation (state it, don't oversell).
2. *Rung 2 — IPCW-weighted split conformal* (inverse-probability-of-censoring
   weights, à la conformalized survival analysis): estimate P(uncensored | x) with
   the feasibility classifier we already have; weight cal scores by 1/p̂;
   approximate marginal coverage on the full population. More powerful, weaker
   finite-sample story — this is exactly what the PI conversation should decide.

**Changes:** new `budget_guard/censored.py` (+ `run_censored.py`), ~150 lines;
validation = warehouse mask-and-measure + synthetic censoring on sokoban.

**Blockers:** (a) PI sign-off on which guarantee we claim; (b) lit-review answer on
prior art (below) — if conformalized survival analysis already covers this setting,
we cite and position as adaptation, not invention. **Est: 3–5 days after sign-off.**

---

## Questions for the literature review team (needed before P2, useful before writing)

1. Any existing work on **conformal / calibrated remaining-budget or remaining-cost
   prediction for LLM agents**? (Search: "conformal" × "LLM agent", "budget
   forecasting agents", "anytime cost prediction", MiCP, CCPO follow-ups.)
2. State of **conformalized survival analysis / censored conformal** (Candès et al.
   line, IPCW-weighted conformal): what guarantee forms exist, what's the standard
   citation set, has anyone applied it to agent/compute trajectories?
3. **Online conformal under distribution shift**: DtACI/AgACI/NexCP — any agent or
   systems applications we'd be scooped by?
4. Economic stopping for agents: anything beyond BAGEN's threshold heuristic
   (early-exit LLMs, FrugalGPT-style routing counts as related, not blocking)?
5. BAGEN team activity: any new preprint/workshop entry from MLL-Lab since 2606.00198.

## Sequencing at a glance
P3 (0.5d) → P1 (1d) → [PI meeting: P2 guarantee + lit answers] → P2 (3–5d)
→ Week-6 freeze: fixed seeds, 4-pager, related-work table, wrapper-API README demo.
