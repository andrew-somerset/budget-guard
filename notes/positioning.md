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

### Closed-loop / counterfactual-free evaluation (limitation + preliminary evidence)

**Limitation (stated unconditionally).** All results here are on *logged* rollouts, which
is counterfactual-free: in real deployment the guard's own abort decisions change the
data it later calibrates on. When it aborts a doomed run, that run never completes, so its
label never enters the online calibration stream — the calibration set becomes a
self-selected sample of only the runs the guard let finish. The online-conformal coverage
guarantee assumes the stream self-labels; under closed-loop selection that assumption is
violated. This is a genuine threat to the deployment claim and is future work
(off-policy / bandit-style correction).

**Preliminary evidence (toy, synthetic — `scripts/run_closed_loop.py`, 5 seeds).** A toy
simulation makes the failure mode concrete (real numbers from the sim; the DGP is
synthetic and tuned only to expose the mechanism). Runs arrive over rounds; the guard
aborts predicted-doom runs (which then never feed calibration); harder runs carry larger
residual spread. Over 25 rounds the closed-loop guard's TRUE coverage on the full
population it faces drifts from ~0.92 to **0.83**, while an oracle that counterfactually
sees every label holds at **0.90** — and, crucially, the closed-loop guard's
*self-measured* coverage (on its self-selected completed stream) stays at **0.91**, so it
is blind to the bias it induces. Illustrative only, but the direction is real; it
motivates an off-policy correction as the key next step for any deployment claim. See
`figures/closed_loop.png`.

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

## Robustness pass — results

Outcome of the automated robustness loop (see `notes/robustness_progress.md` for the
per-item log + exact reproduce commands). Verified this pass on the 3 opus runs available
locally; tables needing the full 19-run × multi-model download are flagged DATA-BLOCKED.

**Verified reproductions (re-derived this pass, not just quoted).** C1 coverage reproduces
week3/4 exactly (sokoban ACI 0.920±0.019 / SPCI 0.916±0.019 / DtACI 0.936±0.011; swebench
ACI 0.946±0.032 / SPCI 0.916±0.024 / DtACI 0.950±0.015); C2 joint 0.80 / 0.95 / 0.885; C3
86.3% doomed-$ saved @ 0% false-abort; C4 −46% cost-of-pass; censored rungs 1–3. Synthetic
audit tests pin the two load-bearing guarantees: split conformal hits nominal on i.i.d.
data (within a rollout cluster-bootstrap CI), and under injected drift FROZEN conformal
degrades while ONLINE recovers.

**Lead = deployment shift.** The headline is transfer, not within-distribution: calibrated
on sokoban and deployed cross-env, frozen split-CQR collapses to 0.10 [0.08, 0.13] on
swebench while SPCI self-heals to 0.90 [0.86, 0.94] at 0% unbounded (ACI recovers only by
surrendering to 58–86% unbounded intervals). Model-swap adds more scenarios but is
data-blocked here.

**Conditional coverage is what actually holds.** Marginal coverage is a mirage where
trajectories are short: on sokoban the pooled 0.916 hides a k=1 slice at 0.860 — the
first, highest-leverage abort decision — because one global qhat is set by the many easy
late-turn prefixes. Mondrian-by-depth restores k=1 to 0.927 (worst-slice 0.855→0.895) at
no cost where there is no hole (swebench over-covers throughout). Honest scope: a
short-horizon phenomenon, not universal.

**Honest baselines.** The trivial constant-quantile baseline is reported by default and is
closer than comfortable — within ~0.03–0.05 coverage of the fitted guard, which earns its
keep on SHARPNESS (20–56% narrower on BAGEN). Off-domain (a non-BAGEN source-code corpus)
the unmodified pipeline still hits ~0.90 coverage but the baseline nearly matches (~10%
width edge) — the guard's advantage is domain-dependent.

**Label efficiency.** A handful of logged runs suffices: 5–8 calibration rollouts give
~0.90 coverage; below that the finite-sample correction fails SAFE (2 rollouts → ~1.0
over-coverage, never silent under-coverage). Curve carries a 5-seed band per env.

**Artifact.** Pip-installable (`pip install -e .`) + a runnable no-data demo; a fresh-env
install caught and fixed a missing scikit-learn dependency.

**Loop-engineering generalization (development branch).** The wrapper is no longer tied to
tokens or Warehouse columns: a versioned RunStart/StepUsage/UsageCorrection/RunFinish/
RunAbort contract, resource ledger, generic features, stateful multi-resource guard,
separate intervention policy, and framework telemetry adapters now share one live path.
At the stress-selected 10-completed-run window, five-seed online-joint coverage is 0.912
on Sokoban→SWE-bench tokens and 0.943–0.963 across four Warehouse model swaps, with
0–3.1% automatic false stops and 71–78% failed-run catches. An independent sequential-
source-text corpus reaches 0.958 but remains a **pipeline smoke test, not an agent-domain
result**. Order/window stress (200 replay runs) and oracle-vs-closed-loop replay are now
explicit scripts rather than prose-only limitations.

**Audit correction (2026-07-20).** Those online-joint numbers now carry rollout-cluster 90%
CIs, and `guard.last_operative_level` is ~1.0 on every agent scenario: at window=10 the joint
qhat is the componentwise sample maximum (worst-of-window), not a tight 0.90 interval. So
per-prefix over-coverage coexists with trajectory coverage *below* nominal (0.80–0.85) under
shift, the per-resource baseline is structurally +inf at that window (its "win" is
definitional), and this rollout-max online method is a different object from the per-prefix
`multiresource.adaptive_joint_qhats`. Do not headline these as calibrated 0.90 intervals;
headline them as a conservative, self-adapting worst-of-window monitor, and unify the two
joint calibrators before the write-up.

**Claim boundary:** provider/task-neutral for measurable additive resource loops is now a
software and BAGEN-supported claim. "Works across real agent domains" is not yet supported:
we still need a second independent coding/browser/workflow-agent dataset and preferably an
anonymized pilot. Do not promote source files into fake agent evidence.

**Limitation, stated plainly.** Logged evaluation is counterfactual-free; a toy closed-loop
sim shows the guard's own aborts self-select its calibration stream, so its TRUE coverage
drifts (0.92→0.83) while its self-measured coverage stays ~nominal (0.91) — off-policy
correction is the deployment next-step.

**Open (blocked, not skipped).** ~~DATA-BLOCKED~~ **Resolved 2026-07-20**: the full 19-run
× multi-model BAGEN download was fetched and both the all-19 breadth table (`run_allruns`,
19/19 rows — split-CQR/SPCI/DtACI all clear 0.85 on the great majority of runs) and the
model-swap transfer bars (`run_transfer`, 4/4 target models — frozen split-CQR collapses
to 0.38–0.76, SPCI recovers to 0.91–0.93 at 0% unbounded) are now complete; see
`notes/robustness_progress.md`'s 2026-07-20 entry for the full numbers. Still PI-BLOCKED:
the censored-conformal next increment (gated-IPCW / positivity — proposal in the progress
log) and whether the by-depth cut belongs on the warehouse tables. **Also resolved
2026-07-20**: the internal-vs-external transfer gap now has a first answer —
`run_transfer_warehouse.py` (new, reuses existing code only) shows frozen joint coverage
on Warehouse degrades more gently under model-swap (0.67–0.81 joint vs 0.90 nominal, 4
target models) than the token-budget collapse did, but is still a real, honest shortfall.
**Adaptive-joint follow-up (development branch, five seeds):** a rollout-safe recent-error
window now updates both each resource margin and their shared empirical-copula rank, but
only after each whole rollout finishes. It raises joint coverage from frozen Bonferroni's
0.66–0.79 to **0.86–0.88 overall** and **0.87–0.90 in the late half**, with 0% unbounded
intervals; every rollout-cluster 90% CI contains the 0.90 target. Honest claim: substantial,
statistically target-compatible recovery — not perfect 0.90 point coverage and not a proof
under arbitrary shift. It only learns from feasible/completed rollouts; connecting it to
the censored feasibility gate remains PI-scoped like item 8.
