# Week 4 — C3 economic stopping: first frontier results

Run 2026-07-04, 5 seeds. Reproduce: `python -m budget_guard.run_economic {sokoban,swebench}`.

## Design
- Feasibility score s(x_t) = P(can_finish | x_t), LGBM classifier on TRAIN.
- Stopping rule: abort at first prefix with s < tau.
- **Rollout-level calibration**: tau = delta-quantile (finite-sample) of feasible CAL
  rollouts' *minimum* prefix scores, so the sequential rule's false-abort rate is
  controlled per-run (abort-iff-min-score<tau ⟺ threshold on the min).
- Baseline: hard token cap swept over cap values.

## Results (test, mean over 5 seeds)
**sokoban** (doom = task failure, mostly): guard dominates the cap at the useful end —
e.g. guard (δ=0.30): 21% of doomed spend saved @ 31% false aborts vs cap: 17.5% @ 37%.
At low false-abort rates both are weak (~7% saved) — sokoban runs are short; there is
little left to save by the time doom is detectable.

**swebench** (doom ≈ exceeding the 7060-token cap, by definition): the hard cap at the
budget boundary is structurally near-optimal — 40% saved @ 0% false aborts — and beats
the classifier guard there. Honest and explainable: when infeasibility IS cap
exceedance, "did you cross the cap" is an oracle feature.

## The fix (next, and it unifies C1+C3)
Interval-driven stopping: abort when `tokens_so_far + calibrated_lower_bound(y_t) >
budget` with a one-sided conformal bound at level delta (rollout-level calibrated as
above). Fires *before* the cap is hit (the cap only triggers at the boundary), uses
C1's intervals, and should dominate on both doom types. Then convert to dollars and
to cost-of-pass (C4).

## Addendum (same day): breadth, DtACI, baselines, interval-rule finding
- **All-19-runs table** (`run_allruns.py`): SPCI >= 0.85 coverage on **19/19** runs
  (agent: 0.02–0.52); DtACI 18/19; split-CQR only 14/19. Online adaptation is what
  makes the guard reliable across models.
- **DtACI added** (no gamma tuning): best headline method — 0.936±0.011 (sokoban),
  0.950±0.015 (swebench), narrowest widths (13.3k vs SPCI's 16.4k) — kills the
  hyperparameter objection.
- **Constant-quantile baseline added**: covers (0.88/0.92) but 30–130% wider than the
  guard and under-covers searchr1 (0.77) — the features/model earn their keep.
- **Interval-driven stopping tried honestly**: rollout-level conformal calibration of
  the lower bound is data-starved at 64–123 rollouts/run (qhat=inf below δ≈0.3), and
  the trigger only addresses cap-exceedance doom. Feasibility rule stays C3's
  workhorse; refinement path = pooled rollouts, per-prefix calibration w/ sequential
  correction, or e-value tests. Code kept in economic.py (evaluate_interval_stopping).
