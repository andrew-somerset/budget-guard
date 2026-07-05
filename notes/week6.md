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
