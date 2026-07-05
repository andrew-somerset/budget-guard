# Positioning & robustness plan — making this competitive for NeurIPS/ICML workshops

Drafted 2026-07-04. The bar at a top-venue workshop: one crisp claim, evidence that
survives an adversarial reviewer, honest limitations, and a usable artifact.

## The one-sentence claim (candidate)
> A training-free conformal wrapper turns any logged-agent budget predictor into
> calibrated remaining-budget intervals that *survive deployment shift* (model swaps,
> new task types) by self-calibrating from the stream's own completed runs — where
> fine-tuned self-estimates (47%) and frozen conformal (12–76%) both fail.

The transfer results are the moat. Within-run calibration is table stakes (reviewers
will say "split conformal works when exchangeability holds — of course"). Lead with
drift/deployment, not the within-run table.

## Statistical rigor upgrades (cheap, high reviewer value)
1. **Rollout-level bootstrap CIs for coverage** — prefixes within a rollout are
   correlated; per-sample binomial CIs are too tight. Cluster bootstrap by rollout.
   (Reviewers who know conformal WILL raise this.)
2. **Conditional coverage, not just marginal** — report coverage-by-depth k and
   worst-slice coverage; add **Mondrian/group-conditional conformal** (bucket by k)
   as the fix for the k=1 under-coverage we measured (0.77). This doubles as a
   methods contribution.
3. **Parameter-free online conformal** — gamma tuning is a reviewer target (ours hit
   the 0.05 grid ceiling). Add **DtACI / AgACI** (expert aggregation over gammas,
   no tuning) — kills the hyperparameter objection and is one afternoon of work.
   Same for SPCI window (we showed w matters: 0.71→0.93 on searchr1).
4. **Full SPCI** (quantile regression on the residual series) vs our windowed
   variant; cite both honestly.
5. **All 19 runs, not just opus-4.7** — the coverage table across every model×env
   run on disk. Cheap compute, big "it generalizes" signal.
6. **Seeds everywhere + fixed-seed release** (already 5 seeds on headline tables).

## Baselines reviewers will demand
- BAGEN's own SFT+RL estimator (the 47% row) — cite from paper; if their checkpoint
  is released, run it.
- Constant-quantile interval (no model, just empirical y quantiles from CAL) — if the
  guard barely beats this, the ML content is thin; measure now.
- Burn-rate extrapolation (tokens_so_far/k × remaining-turns estimate).
- Agent self-report (have it).

## Methods novelty (what makes it more than "we applied ACI")
- **Censored conformal**: 640/1280 Warehouse samples have undefined remaining-resource
  labels (can_finish=False) — infeasible runs are *censored*, not missing. Conformal
  with censored scores (lower-bound labels from aborted/failed runs) is genuinely
  underexplored for agents. This is our best shot at a real methods contribution.
- **Copula joint intervals** to beat Bonferroni's conservatism (0.95 vs 0.90 nominal
  → margins wider than needed). Empirical copula on CAL scores.
- **Interval-driven stopping**: current C3 uses a feasibility classifier; upgrade to
  "abort when tokens_so_far + calibrated-lower-bound > budget" — unifies C1 and C3,
  and should beat the hard cap on swebench where the cap is structurally strong
  (doom there = cap exceedance by definition; see week4 notes).
- Positioning table vs: MiCP, CCPO, conformal-for-LLM lines, FrugalGPT/cost-aware
  routing, uncertainty-aware agent termination. We are: post-hoc, training-free,
  guarantees under drift, multi-resource, economically actionable.

## Impact & artifact
- **Dollars, not tokens**: convert savings via public per-token prices; headline
  "X% of failed-run spend recovered at ≤5% false aborts."
- **A 50-line wrapper API**: `guard = BudgetGuard(cal_logs); guard.step(usage) ->
  (interval, abort?)` + pip install + README demo. Reviewers reward usable artifacts;
  it also makes the "training-free, drop-in" claim concrete.
- Overhead measurement (µs/step, CPU-only) — one table row.

## Honest-limitations section (pre-empt the kill)
- Within-run naive conformal is only mildly miscalibrated marginally — our gap is
  conditional + shift + sharpness (we have the figures; say it plainly).
- Logged (counterfactual-free) evaluation: aborting in deployment changes the data
  the guard later calibrates on — flag as future work (bandit/off-policy analysis).
- searchr1 sample sizes; agent-baseline vs guard evaluated on slightly different
  sample sets in C2 (fix like-for-like before submission).

## Venue targets (ask PIs)
- NeurIPS 2026 workshops: reliable/trustworthy ML, LLM agents, distribution shift.
- ICML 2026 workshops (earlier deadline — check dates NOW; may force the schedule).
- Backup: arXiv + main-conference short track later with C2–C4 fleshed out.

## Priority order (impact per hour)
1. All-19-runs coverage table (cheap, persuasive).
2. DtACI + constant-quantile baseline (kills two objections).
3. Interval-driven stopping for C3 + dollars conversion (completes the story).
4. Censored conformal (the methods contribution — scope with PIs first).
5. Copula joint + Mondrian-by-depth (nice-to-have).
