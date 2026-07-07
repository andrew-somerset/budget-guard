# Week 6 — plan P1–P3 executed: the three ceiling-raisers

Run 2026-07-04, 5 seeds. Reproduce: `python -m budget_guard.run_coverage`,
`run_economic_warehouse`, `run_censored`.

## P3 — calibrating the agent's own estimate ✅
- **conformalized-agent** (agent's interval midpoint + conformal wrapper, ZERO
  training, no features): coverage 0.51→0.93 (sokoban), 0.23→0.90 (searchr1),
  0.35→0.97 (swebench). *The paper's cleanest sentence: the agent's self-knowledge
  isn't wrong, it's uncalibrated — a statistical wrapper fixes it.*
- Sharpness: fitted guard still ~40% narrower (0.88 vs 1.44 normalized, sokoban) —
  conformal fixes calibration, the model buys sharpness. Two-step story.
- **guard+self-est ablation**: agent features add ~nothing over burn-rate features
  (0.911 vs 0.916 sokoban). Honest ablation row.

## P1 — C3+C4 on Warehouse (native USD) ✅ — the economics headline
- **Guard δ=0.10: 86.3% of doomed-run dollars saved at 0.0% false aborts** (5 seeds).
- **Cost-of-pass: $1.61M → $0.87M per pass (−46%) with 100% of passes retained.**
- Hard caps are dominated everywhere: $-caps save ≤15% while falsely aborting
  3–62% of feasible runs; week-caps are all-or-nothing.
- Caveat to state: warehouse doom is largely decidable from the initial
  budget/target configuration — information the learned guard reads and a cap
  can't. That's the point of a guard, but say it. (128 rollouts, 50% doomed.)
- Combined with sokoban (guard wins) and swebench (cap wins, doom=cap-exceedance):
  the full C3/C4 story is now "guard dominates wherever doom is scenario- or
  failure-driven; caps only suffice when doom IS the cap."

## P2 rung 1 — censored conformal, mask-and-measure on Warehouse ✅
Setup: 50% of samples censored (can_finish=False ⇒ remaining-cost label masked, only
b = budget − spent known); recovered totals used solely to measure true coverage.
Upper bound hi = pred + qhat at alpha=0.1:

| calibration | cov all | cov censored | qhat |
|---|---|---|---|
| drop censored (naive) | 0.834 | **0.786** | 66k |
| censored → +inf | 1.000 | 1.000 | **inf** (useless at 50% censoring) |
| censored → known bound | **0.999** | **0.998** | 385k (finite!) |
| IPCW (survival-analysis std.) | 0.826 | 0.777 | 65k |

Findings that could carry a methods section:
1. Naive under-covers the censored population exactly as predicted (0.79 vs 0.90).
2. **IPCW fails on real agent data**: censoring is nearly deterministic in x
   (doom decidable from config) → positivity/overlap violated → weights can't
   recover the censored region. Textbook assumption, empirically broken here.
3. Bound-informed calibration is the only one that is both valid and finite.
4. The bound y > budget−spent holds on only **42%** of censored rows — doom is
   often cross-resource (time budget exhausted, cost fine). Refinement: use the
   observed *which-budget-was-hit* indicator for resource-specific bounds.
   ← this is the concrete next idea to pitch to the PIs for the methods contribution.

## P2 rung 2 — resource-specific ("which-budget-was-hit") calibration ✅ (2026-07-07)
Developed the refinement flagged above. A censored run bounds resource r ONLY when r
is the operative (binding) constraint (total_r > budget_r); runs censored by a
*different* resource are uninformative for r and dropped. New method
`censored.upper_qhat(..., method="resource_bound", censored_binding=…)`; `run_censored`
now sweeps all three resources with stratified coverage (5 seeds, +3 unit tests).

Operative-constraint fractions of censored rows: time 30% / warehouse 34% / cost 42%
(sum > 1 — a doomed run can bind several).

| resource | method | cov feasible | cov cens-binding | qhat |
|---|---|---|---|---|
| time (exact spend)    | drop           | 1.00 | 1.00 | 3e-4 |
| time                  | bound          | 1.00 | 1.00 | 16 |
| time                  | **resource_bound** | **0.90** | **0.90** | **2e-4** |
| cost (interp. spend)  | drop           | 0.88 | 0.50 | 66k |
| cost                  | bound          | 1.00 | 0.99 | 385k |
| cost                  | **resource_bound** | 0.86 | 0.46 | 64k |

The finding (honest — sharper than a clean win):
1. **`bound`'s coverage was an artifact.** It over-covers only by borrowing large
   *false* bounds from non-operative resources — for the cost target, the 58% of
   censored runs that failed on time/warehouse spent little cost, so their
   budget−spent headroom is large and inflates qhat to 385k. Resource-attribution
   removes that false inflation.
2. **On time (exact spend), resource_bound is the clean winner**: nominal 0.90 in
   every stratum where drop and bound both over-cover (1.00) with qhat up to ~50,000×
   larger.
3. **On cost/warehouse (interpolated spend), it exposes the real limit**: the
   operative resource's own lower bound budget−spent is too loose — doomed runs
   overshoot budget by far more than the headroom — so no finite tight bound is valid
   there. That is *why* operative-resource doom must be caught by the feasibility gate
   (C3); the calibrated interval governs the feasible / non-operative regime.

Net methods story: censoring in multi-resource budgets is resource-specific; correct
attribution fixes naive under-coverage where spend is exact and diagnoses where
interval prediction must defer to classification.

## P2 rung 3 — feasibility-gated intervals (predict-feasible-then-bound) ✅ (2026-07-07)
The positive counterpart to rung 2. Since the operative resource can't be tightly
bounded from censored data, don't bound it — gate on the feasibility classifier and
emit an interval ONLY for runs predicted feasible-on-r (abort the rest). Unifies C1
(interval) + C3 (gate). New `censored.gated_upper_qhat`; `run_gated.py` (5 seeds, gate
false-abort budget δ=0.1). Guarantee: coverage of y_r CONDITIONAL on passing the gate
(selective coverage), where censoring is filtered out so exchangeability ~holds.

| resource | kept | gate catches doomed | false-abort | cov (kept, feasible) | qhat |
|---|---|---|---|---|---|
| time      | 88% | 93% | 0.0%  | 1.00 | 3e-4 |
| warehouse | 70% | 74% | 7.4%  | 0.95 | 10k |
| cost      | 80% | 72% | 10.5% | **0.92** | **70k** |

The win: on **cost**, un-gated resource_bound covered the doomed at only 0.46 with a
385k bound; **gating restores 0.92 coverage on the kept population with a tight 70k
bound**, catching 72% of doomed-on-cost at ~δ false-abort. Same shape for warehouse.
False-abort tracks δ (0.0 / 0.07 / 0.10), so the gate's error is controlled by design.

**Completed methods narrative (P2 rungs 1–3):** censoring in multi-resource budgets is
resource-specific (rungs 1–2); the operative resource can't be *validly* covered from
its loose lower bound (see KM below), so the guard **abstains** on predicted doom and
gives a calibrated interval on the rest (rung 3). A selective-conformal split of labour
between classification and interval. Tests: +2 (5 in test_censored).

## Phase 1 reviewer-proofing (2026-07-07): like-for-like C2, KM survival, selective frontier
- **Like-for-like C2 baseline fixed.** The agent joint coverage was BAGEN's rate over
  all 1280 samples (0.422). Recomputed on the SAME feasible test rows the guard is
  scored on (per-sample `*_interval_contains_actual` flags): **agent joint 0.36**
  (time 0.74 / warehouse 0.57 / cost 0.61). The guard's 0.95 advantage *widens* — the
  agent is worse-calibrated on completable tasks than its all-samples average implied.
  `load_warehouse` now carries `agent_cov_*`; `run_multiresource` reports it per-seed.
- **Kaplan–Meier survival estimator (`km`) added — and it corrected an over-claim.**
  Rung 2 read as "the operative resource is unboundable." KM (right-censoring the
  binding scores at their lower bound) actually returns a *finite* cost bound (≈91k),
  because doomed runs already spent most of budget, so their observed lower bound
  budget−spent is SMALL (lower tail), not large. KM gives the **best non-gated coverage
  on the doomed (cost 0.58** vs drop 0.50 / resource_bound 0.46) — but still well under
  0.90. Honest statement: a finite bound *exists*; you just can't get a *valid* (0.90)
  one from the censored data — even KM, the proper method, reaches 0.58. KM correctly
  → +inf only when the upper tail itself is censored (unit test); that regime doesn't
  arise here. This is a cleaner, quantified motivation for the gate than "diverges."
- **Selective frontier** (`run_gated` δ-sweep → `figures/selective_frontier.png`): all
  three resources sit ABOVE nominal 0.90 on the kept population across kept ∈ [0.5, 0.9];
  cost rises 0.917 → 0.931 as the gate keeps fewer. The gate buys valid coverage by
  abstaining.
- **Fixed-seed `figures/final/`** via new `run_final.py` (seeds 0–4): joint_vs_marginal,
  abort_frontier_warehouse, selective_frontier. Transfer / coverage-main need the full
  multi-model dataset (not on this box). Tests: **19 passed / 2 skipped** (+2 KM).

## Engineering
- `economic.py` generalized to arbitrary spend/total/order columns (`_run_rule`).
- `multiresource.load_warehouse(keep_censored=True)` recovers y for censored rows
  (time spend exact; cost/warehouse spend interpolated by weeks — stated approx).
- New: `censored.py`, `run_censored.py`, `run_economic_warehouse.py`,
  `data.load_agent_estimates`, `features.build_xy(agent_est=…)`. Tests 8/8.

## What remains before submission
Fixed-seed final figure pass · 4-pager draft (needs Andrew + lit-review results) ·
related-work table (waiting on teammates) · PI sign-off on the censored-conformal
guarantee framing · wrapper-API README demo.
