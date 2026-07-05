# Week 5 — C4 + reviewer-proofing round: the four contributions are now all live

Run 2026-07-04. Reproduce: `python -m budget_guard.run_costofpass {sokoban,swebench}`,
`run_multiresource`, `run_gap sokoban`, `run_coverage`.

## C4 — cost-of-pass (tokens & $ per correct answer; $15/Mtok stated assumption)
- **swebench**: agent alone 21,254 tok/pass → guard (δ=0.20) **17,134 (−19.4%)** while
  retaining 94% of passes. Hard cap at the budget boundary does even better (−31%,
  100% retained) — consistent with doom-by-cap-exceedance there.
- **sokoban**: flat (~3,600 tok/pass all policies) — runs too short for stopping to
  pay; false aborts cost passes faster than savings accrue. Honest env-dependence:
  stopping pays where trajectories are long and doomed spend is large.

## Copula joint intervals (C2 upgrade)
agent 0.42 / independent 0.80 / **copula 0.885** / Bonferroni 0.95 (target 0.90).
Copula calibrates the shared rank level on CAL's empirical joint — tighter margins
(0.94–0.96 per resource vs Bonferroni's 0.97–1.0), joint ≈ nominal within seed noise
(±0.06). The expected independent < copula < Bonferroni ordering, demonstrated.

## Mondrian-CQR by depth (conditional-coverage fix)
k=1 coverage 0.860 → **0.927** (5 seeds), marginal 0.867 → 0.900. The k=1
under-coverage found in Week 2 is fixed by bucketing qhat by turn depth (k=1 / k=2 /
k>=3, fallback to global under 10 cal scores). Now in `run_gap` + figure.

## Rollout-level bootstrap CIs
`metrics.rollout_bootstrap_ci` (vectorized, resamples rollouts not prefixes) — 90% CI
columns now in `tables/coverage.csv`. e.g. sokoban DtACI: 0.936 CI [0.88, 0.98].

## State of the plan
- C1 ✅ (coverage + transfer + all-19-runs + DtACI) · C2 ✅ (Bonferroni + copula)
- C3 ✅ (feasibility frontier; interval-rule finding documented) · C4 ✅ (cost-of-pass)
- Remaining for submission (Week 6 work): fixed-seed final figures, 4-pager draft,
  related-work table, like-for-like C2 baseline check, censored conformal (scope with
  PIs — the methods-contribution candidate), README + wrapper API demo.
