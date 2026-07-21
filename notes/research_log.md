# Research log — weekly notes (weeks 1–6, consolidated 2026-07-21)

> One file instead of six; content unchanged, in order. Newer running logs live in
> robustness_progress.md (per-item + dated entries) and positioning.md.

---

# Week 1 — notes & deliverables

## Self-check answers (write 1–2 sentences each)
1. Why is `y_t` online / partly self-induced, and why do logged rollouts make it tractable?
   -
2. Why does plain split-conformal under-cover here?
   -
3. Why split by rollout, never by prefix?
   -

## Reproduced BAGEN number (done LOCALLY from HF estimation records — no Colab needed)
- env: sokoban (claude-opus-4.7 run)
- metric: `remaining_token_interval_coverage_rate` (agent's own interval contains true remaining tokens)
- value: **0.5132** (355 samples); recomputed from per-sample `metrics.remaining_token_interval_contains_actual` → identical.
- across all 19 downloaded runs with this metric: mean **0.2742**, min 0.0249 (qwen3-235b searchr1), max 0.5239
  (sonnet-4.6 sokoban) — every run far below a 0.90 target. Motivating gap confirmed.
- date: 2026-07-03

## Fidelity check (done LOCALLY — the HF estimation records carry official ground truth)
- The official per-sample records (`results[*].ground_truth.actual_remaining_total_tokens`) let us diff
  without running the Colab harness.
- Raw dialogues: `origin/sokoban-origin-claude-opus-4.7-low-thinking-128-main/..._dialogues.json` (9.6 MB).
- First diff: all 355 sample_ids aligned, but **355/355 y mismatches** — extract.py used raw request
  totals (input re-counts history each turn), official default is `turn_usage_mode="turn_excluding_history"`.
- Fix: ported `_convert_request_usage_to_turn_usage` (+ visible-output estimate, history-vote heuristic)
  from `ragen/env/token_estimation/env.py` into extract.py.
- After port: extractor `y_t` vs official `actual_remaining_total_tokens`: mismatches = **0 / 355** (target 0). ✅

## Environment record (Windows work machine)
- Miniconda user-scope at `%USERPROFILE%\miniconda3` (conda 26.3.2), JustMe, AddToPath=0.
- env `budget` (python 3.12.13) created via **conda-forge** (`--override-channels`) to avoid
  Anaconda default-channel Terms of Service / commercial licensing on a work machine.
- conda-forge python shipped without pip → bootstrapped with `python -m ensurepip --upgrade`.
- pip stack: pandas numpy scikit-learn lightgbm scipy matplotlib jupyter pytest huggingface_hub.

## Environment record (Mac — personal machine)
- miniforge3 at `~/miniforge3` (osx-arm64, Apple Silicon); conda 25.3.1.
- env `budget` (python 3.12.13) created via conda-forge (`--override-channels`).
- pip stack installed from `requirements.txt`: pandas 3.0.3, numpy 2.5.0, scikit-learn 1.9.0,
  lightgbm 4.6.0, scipy 1.18.0, matplotlib 3.11.0, jupyter/jupyterlab 4.6.0, pytest 9.1.1,
  huggingface_hub 1.21.0.
- BAGEN repo cloned (depth=1) at `~/budget-guard/BAGEN` (sibling of `budget-guard/`).
- HF estimation data downloaded to `data/bagen_hf/` (gitignored): manifest + all 24 estimation dirs.
- Smoke test passes: `python budget_guard/extract.py` → 3 prefix samples, 0 invariant failures.
- Note: `data/bagen_hf/estimation/` is turn-level model-prediction records, NOT the raw rollout
  dialogue JSON that `extract.py` expects. Use BAGEN `_smoke/sokoban_dialogues.json` or a separate
  raw-rollouts download for the extractor.

## Status / blockers
- [done] Windows env: Miniconda + conda-forge `budget` env (py 3.12) + CPU stack.
- [done] Repo scaffolded, committed, pushed → github.com/andrew-somerset/budget-guard (private).
- [done] `extract.py` validated on `_smoke` (3 samples) and on real Sokoban dialogues (123 rollouts → 355 prefix samples); invariants pass.
- [done] HF dataset reachable (public, unauthenticated); manifest + smallest Sokoban dialogues (9.6 MB) downloaded to `data/bagen_hf/` (gitignored).
- [done 2026-07-03] Mac env repair: lightgbm failed to load (missing libomp) → fixed via
  `conda install -n budget -c conda-forge llvm-openmp`. Full CPU stack imports clean.
- [done 2026-07-03] Ported history-excluded usage (`turn_excluding_history`) into extract.py;
  fidelity diff vs official ground truth = **0/355 mismatches**. Week-1 "done when" met.
- [done 2026-07-03] Extractor also validated on all 5 SWE-bench dialogue sets:
  316 rollouts → 9,325 prefix samples, 0 invariant failures (run with max_ctx=512_000).
- [done 2026-07-03] Reproduced BAGEN coverage numbers (see above): 0.513 sokoban-opus-4.7;
  mean 0.274 across 19 runs.
- [todo — you] Readings + 3 self-check answers (§ top of this file).
- [note] Colab is now only needed for the optional official-harness DRY_RUN sanity pass
  (nice-to-have), not for the fidelity check — that's done.
- [next → Week 2] `features.py`, `split.py` (group split by rollout), `conformal.py`
  (split-conformal + CQR), `run_gap.py` → `figures/gap_sokoban.png` showing naive under-coverage.

---

# Week 2–3 — offline harness, online conformal, first headline results

All run on 2026-07-04, seed 0, alpha = 0.1, model fixed to claude-opus-4.7 across envs
(so cross-env differences are env effects). Reproduce with:
`python -m budget_guard.run_gap`, `python -m budget_guard.run_coverage`, `python -m budget_guard.run_transfer`.

## Code added
- `features.py` — leak-free `build_xy` (k, tokens_so_far, burn rate, per-turn stats; LEAK set asserted out).
- `split.py` — `group_split` by rollout, 50/25/25.
- `conformal.py` — `split_conformal_absres`, `cqr_split`, `aci_cqr` (proper ACI: the
  interval goes unbounded when the adapted level demands it — this is what lets it
  recover after hard shift), `spci` (windowed variant; window updates from the test
  stream), `tune_gamma` (CAL-only).
- `metrics.py`, `data.py` (env registry w/ official max_ctx: sokoban 2500, searchr1 3500, swebench 7060).
- `tests/` — 8 tests incl. the 0-mismatch fidelity test and a synthetic-shift test
  that caught a real ACI bug (capped intervals → 0.01 coverage under shift).

## Fidelity (now on all three envs)
extractor `y_t` vs official: sokoban 0/355, swebench 0/512, searchr1 0/87 mismatches.

## Result 1 — the "gap" is not where the plan predicted (within-run)
With cal/test split by rollout *within one run*, exchangeability roughly holds, so naive
split conformal is NOT catastrophically miscalibrated marginally (sokoban 0.87–0.89 vs
0.90 nominal). The real within-run failures:
- **conditional coverage**: sokoban k=1 covers only ~0.77–0.80, over-covers late turns
  (see `figures/gap_sokoban.png` right panel);
- **sharpness**: swebench naive intervals are 2–3.3× the y-range (coverage 1.0 but useless).

## Result 2 — coverage_main (within-run, all methods)
agent self-report 0.23–0.51 everywhere. Guard: sokoban ACI-CQR **0.911** / SPCI **0.900**;
swebench ACI-CQR **0.919** / SPCI **0.919** (and ~20% sharper than split-CQR); searchr1
n_test=23, everything saturates at 1.0 (too small, need more runs).

**Week-3 KILL CHECK: GO.** Within ±0.03 of 0.90 on sokoban + swebench, beats split-CQR,
nothing anywhere near the ≤0.65 kill floor.

## Result 3 — the headline: model-swap transfer (deployment story)
Guard trained+calibrated on opus-4.7 swebench logs, deployed on other models' streams
(labels arrive online as each run completes — answers the PI's "no ground-truth labels"
question empirically):

| target | frozen split-CQR | ACI-CQR | SPCI |
|---|---|---|---|
| sonnet-4.6 | 0.61 | 0.90 (33% unbounded) | **0.906** |
| gemini-3.1 | 0.51 | 0.90 (38% unbounded) | **0.924** |
| gpt-5.2-instant | 0.76 | 0.90 (13% unbounded) | **0.916** |
| qwen3-235b | 0.38 | 0.90 (50% unbounded) | **0.925** |

Frozen conformal breaks under model swap; ACI restores coverage but only by frequently
surrendering to unbounded intervals; **SPCI restores ~0.92 coverage with 0% unbounded**
and moderate widths. "Recover-by-surrender vs recover-by-adaptation" is a nice framing.

## Caveats / next
- searchr1 needs more runs pooled (only 87 samples in the opus run).
- gamma grid topped out at 0.05 → widen the grid (0.1, 0.2) in ablations.
- Figures/tables are gitignored by design — regenerate with the run commands above.
- Next: cross-env transfer + label-efficiency curve (the other PI-question experiments),
  then C2 (Warehouse multi-resource) and C3 (economic stopping).

---

# Week 3–4 — generalization experiments (the PI question) + C2 multi-resource

Run 2026-07-04. Reproduce: `python -m budget_guard.run_label_efficiency`,
`run_transfer_env`, `run_coverage` (now 5 seeds), `run_multiresource`.

## Label efficiency (sokoban, split-CQR, 30 redraws per budget)
- 5–8 calibration rollouts already give ~0.88–0.91 coverage; 2 rollouts → coverage 1.0
  because the finite-sample correction demands unbounded intervals — the guard
  **fails safe** at tiny n (over-wide, never silently under-covered).
- Answer to the PI's cold-start worry: a handful of completed runs is enough to start,
  and the failure mode before that is conservative.

## Cross-ENV transfer (sokoban → new task types, opus-4.7)
| target | frozen split-CQR | ACI-CQR | SPCI (w=100) |
|---|---|---|---|
| searchr1 | 0.51 | 0.87 (61% unbounded) | 0.71 |
| swebench | **0.12** | 0.90 (84% unbounded) | **0.903** (0% unbounded) |

- SPCI's searchr1 miss is diagnostic, not fatal: the stream (87 samples) is shorter than
  the window, so sokoban scores never flush. Window ablation on searchr1:
  w=100 → 0.713, w=50 → 0.828, **w=25 → 0.931**, w=10 → 0.931.
  Rule of thumb: window ≪ expected deployment stream length.

## Multi-seed robustness (run_coverage now aggregates 5 seeds)
- sokoban: ACI 0.920±0.019, SPCI 0.916±0.019; swebench: ACI 0.946±0.032, SPCI 0.916±0.024.
- Online methods have ~3–4× lower seed variance than split methods AND ~30% narrower
  intervals on swebench. KILL CHECK still GO, now robustly.

## C2 — multi-resource joint coverage (Warehouse, opus-4.7, 5 seeds)
Official records carry per-prefix ground truth for {time_weeks, warehouse_item_weeks,
cost_usd} directly (`multiresource.load_warehouse`) — no dialogue extraction needed.

| | time | warehouse | cost | JOINT |
|---|---|---|---|---|
| agent self-report | 0.88 | 0.67 | 0.70 | **0.42** |
| guard, independent margins (alpha=.1) | 0.99 | 0.89 | 0.92 | 0.80 |
| guard, Bonferroni (alpha/3) | 1.00 | 0.98 | 0.97 | **0.95** |

- Joint story: 0.42 → 0.95. Bonferroni's union bound holds; independent margins
  demonstrably don't (0.80). Copula/less-conservative joint = future refinement.
- **Censoring found in the data**: exactly half the Warehouse samples (640/1280) have
  `can_finish=False` and hence NO remaining-resource labels (undefined when the run
  can't complete). C2 uses the feasible half; the censored half is precisely the
  C3 economic-stopping signal — and validates the "censored labels" idea pitched
  to the PIs.
- Caveat: agent baseline is computed by BAGEN over all their samples; guard is
  evaluated on the feasible subset. Check like-for-like before the paper.

## Next
- C3 `economic.py`: calibrate feasibility (can_finish classifier + conformal risk),
  stopping rule, savings-vs-false-abort frontier (`figures/abort_frontier.png`).
- C4 `costofpass.py`.
- Copula joint intervals; pool searchr1 runs; widen gamma grid (hit 0.05 ceiling).

---

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

---

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

---

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
