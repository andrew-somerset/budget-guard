# budget-guard — architecture & decision map

*Reference map · v1 · living document. Built from a direct read of the code and notes in the
`budget-guard/budget-guard/` clone — not summarized by a subagent, so follow-up questions on any
section can go as deep as needed. Treat this as a living map; expand it as we go deeper.*

**Status:** Research complete, robustness-hardened · Target: NeurIPS/ICML 2026 workshop ·
Entering write-up · Last snapshot: 2026-07-07

> A training-free conformal wrapper turns any logged-agent budget predictor into calibrated
> remaining-budget intervals that survive deployment shift — model swaps, new task types — by
> self-calibrating from the stream's own completed runs, where fine-tuned self-estimates (47%) and
> frozen conformal (12–76%) both fail. Built on BAGEN rollout logs (arXiv:2606.00198); CPU-only, no
> GPU, no fine-tuning.

## Contents

1. [The pipeline](#the-pipeline)
2. [Conformal prediction, in the amount you need](#conformal-prediction-in-the-amount-you-need)
3. [The four contributions (C1–C4)](#the-four-contributions-c1c4)
4. [Censored conformal — the methods contribution](#censored-conformal--the-methods-contribution)
5. [The BudgetGuard wrapper](#the-budgetguard-wrapper)
6. [The robustness pass](#the-robustness-pass)
7. [Honest limitations](#honest-limitations-stated-not-hidden)
8. [Defend-it-at-a-conference](#defend-it-at-a-conference)
9. [Repo state](#repo-state-worth-fixing)
10. [Where it actually stands](#where-it-actually-stands)

---

## The pipeline

One data flow, six modules. Every headline number in the project is this chain run with a
different tail end. If you can trace a coverage number back through this diagram, you can defend
it.

```
Raw BAGEN rollouts                 data/bagen_hf/…
(per-turn token JSON, 3 envs on disk)
        │
        ▼
extract.py — flatten_to_samples    rollout JSON → prefix rows (x_t, y_t)
        │
        ▼
features.py — build_xy             leak-free X, asserts LEAK_COLUMNS absent
        │
        ▼
split.py — group_split             TRAIN / CAL / TEST — by rollout, never by prefix
        │
        ▼
conformal.py                       split · CQR · ACI · SPCI · DtACI · Mondrian
        │
        ├──▶ censored.py           upper_qhat — when doom hides the true label
        ├──▶ multiresource.py      joint_intervals — 3 resources at once
        └──▶ economic.py           stopping_rule — abort / continue
        │
        ▼
run_*.py (14 scripts)               figures/ · tables/ — one script per headline result
        │
        ▼
guard.py — BudgetGuard              pip-installable wrapper — the artifact
```

The one rule repeated in nearly every module's docstring: **split and calibrate by
`rollout_index`, never by prefix.** Prefixes from the same rollout share
`total_rollout_tokens` — they're correlated, not exchangeable with each other. Split at the
prefix level and you leak each test rollout's own answer into its calibration, and every coverage
number in the project becomes fiction. This single invariant is worth being able to explain
unprompted — it's the first thing a reviewer who knows conformal prediction will check.

### Worked example: real data through extract → features → split

**Raw turn 1 of rollout 0 (sokoban), verbatim fields:** `api_total_tokens=None`,
`api_input_tokens=None`, `api_output_tokens=None`, `actual_token=0`, `success=False`,
`actions=[]`, `parsed_response=""` — a dead turn: no tokens logged anywhere, no assistant output.
Raw turn 2 has `api_total_tokens=1223`. This messiness is why `extract.py` exists as a standalone
module rather than a one-line token sum.

**`extract.py` — `flatten_to_samples`, in order:**
1. Sort turns by `turn_idx`; walk forward; stop at the first context-truncated turn (nothing
   downstream in that rollout can be trusted after an overflow).
2. Keep only turns with non-blank assistant content — this drops raw turn 1 above, so the first
   *emitted* prefix (`k=1`) corresponds to raw turn 2, not raw turn 1.
3. Resolve each kept turn's token total via a fallback chain (`resolve_turn_total`): try
   `api_total_tokens`/`total_tokens` directly, else input+output, else `actual_token` — different
   logging paths populate different subsets of these fields.
4. Undo history double-counting (`convert_request_usage_to_turn_usage`): some logged turns report
   "input tokens" that already include the entire prior transcript (each API call resends history),
   so a majority-vote heuristic detects this and subtracts the baseline out to get the turn's true
   marginal cost. This is the piece Week 1's "0 mismatches vs. the official BAGEN harness" was
   validating.
5. Cumulative-sum resolved per-turn totals; emit one row per `k = 1..N-1` (never `k=N` — a
   completed rollout has nothing left to predict).

Real output for rollout 0:
```
PrefixSample(rollout_index=0, sample_id='rollout-0-turn-1', k=1, N=5,
             tokens_so_far=1223, total_rollout_tokens=2427, y=1204,
             can_finish=True, rollout_success=True, per_turn_total=[1223])
```
5 usable turns (after dropping the dead one) → 4 prefix rows (`k=1..4`). At `k=1`, 1223 tokens
spent; 2427 total by rollout's end; `y = 2427 − 1223 = 1204` remaining; `can_finish=True` since
2427 ≤ the 2500-token Sokoban budget.

**`features.py` — real `X` rows for rollout 0's first two prefixes:**

| | k | tokens_so_far | burn_rate | last_turn_tokens | mean | std | turn_trend |
|---|---:|---:|---:|---:|---:|---:|---:|
| k=1 | 1 | 1223 | 1223.0 | 1223 | 1223.0 | 0.0 | 0.0 |
| k=2 | 2 | 1557 | 778.5 | 334 | 778.5 | 444.5 | −444.5 |

LightGBM can't take a variable-length per-turn-cost sequence directly, so `build_xy` compresses it
into fixed summary stats. Turn 2 only cost 334 against a 1223-token first turn —
`turn_trend=−444.5` is what tells the model "this rollout is decelerating," a signal a bare
`tokens_so_far` can't carry. `LEAK_COLUMNS` is asserted absent from `X` on every call — fail loud,
not a quietly-inflated backtest number.

**`split.py` — proof it actually holds, not just a docstring claim:**
```
train:  181 rows across  62 rollouts
cal:     84 rows across  31 rollouts
test:    90 rows across  30 rollouts

rollout 0 has 4 prefix rows total (k=1..4)
  in train: False   in cal: True   in test: False
```
All 4 of rollout 0's rows landed in `cal` together — none leaked into `train` or `test`.

---

## Conformal prediction, in the amount you need

Everything downstream — all four contributions, the censored-data methods work, the whole
robustness pass — is a variation on one idea. Get this section solid and the rest is application,
not new theory.

**The core idea.** Turn a point prediction into an interval with a guaranteed hit-rate, by
calibrating on held-out residuals. Not "how confident is the model" (that's often miscalibrated) —
instead, measure how wrong the model actually was on data it didn't train on, and use *that*
empirical error distribution to size the interval. Distribution-free: no assumption about the
shape of the underlying data, only that calibration and test scores are exchangeable.

**Split conformal / CQR.** Fit a model on TRAIN. On held-out CAL data, measure the nonconformity
score (absolute residual, or how far *y* falls outside a predicted quantile band for CQR). The
`(n+1)(1−α)`-th smallest CAL score becomes the margin added to every test prediction. Valid in one
shot — but only while calibration and test scores are exchangeable.
📁 `conformal.py: split_conformal_absres, cqr_split`

**Why exchangeability breaks here.** Two ways: within a trajectory, later turns are less
uncertain than early ones (temporal drift) — a frozen global margin either overcovers late or
undercovers early. Across deployment, swapping the model or the task type shifts the whole score
distribution — a margin calibrated on Sokoban has no license to bound SWE-bench.

**Online conformal (ACI / SPCI / DtACI).** ACI (Gibbs & Candès 2021) nudges the working
miscoverage level α<sub>t</sub> after each revealed label — persistent undercoverage sinks
α<sub>t</sub> toward 0, which forces the interval open (even to +∞) rather than stay wrong. SPCI
keeps a sliding window of recent scores so the score *distribution itself* tracks drift. DtACI
runs many ACI copies at different γ and lets them vote — no γ to tune by hand.
📁 `conformal.py: aci_cqr, spci, dtaci`

**The finite-sample correction.** The conformal quantile isn't the plain empirical quantile —
it's `⌈(n+1)(1−α)⌉ / n`, which can exceed 1. When it does, the only valid interval is unbounded.
This is a feature: it's what lets ACI "fail safe" under severe drift instead of quietly reporting
a wrong bound. 📁 `conformal.py: _finite_sample_quantile`

**Mondrian / group-conditional conformal.** One global margin can be valid *on average* while
badly wrong on a slice that matters — e.g. the very first decision point. Mondrian conformal
calibrates a separate margin per group (here, turn-depth bucket) so the guarantee holds within
each bucket, not just pooled. 📁 `conformal.py: mondrian_cqr`

**Cluster-bootstrap CIs.** Prefixes within one rollout are correlated, so a per-sample binomial CI
on coverage is too tight — it counts correlated observations as if independent. Resample whole
*rollouts* with replacement instead. Every headline coverage number in this project carries one of
these, not a binomial CI. 📁 `metrics.py: rollout_bootstrap_ci`

### Worked example, on your real Sokoban data (355 prefix samples, 123 rollouts, seed 0)

| Method | qhat | test coverage (target 0.90) | mean width |
|---|---:|---:|---:|
| `split_conformal_absres` (symmetric) | 590.9 | 0.889 | 1081.1 |
| `cqr_split` (adaptive band) | 87.7 | 0.867 | **844.0** |

CQR's band is already shaped by `x` (tighter late in a rollout, wider early), so its conformal
correction is much smaller (87.7 vs 590.9) yet the final interval is narrower overall. Sample test
rows show the width shrinking as `k` rises within a rollout:

```
k=1  y=1090  interval=[ 460, 1582]  width=1122  covered
k=2  y= 571  interval=[ 210, 1102]  width= 892  covered
k=3  y= 267  interval=[ 162,  902]  width= 740  covered
k=1  y=1875  interval=[ 319, 1509]  width=1191  MISS
k=2  y=1491  interval=[ 186, 1046]  width= 859  MISS
k=3  y=1188  interval=[ 153,  988]  width= 835  MISS
```

Both methods land a little under 0.90 here — expected on a single seed / 90 test rows, not a
bug. It's exactly why every headline table in the project uses 5 seeds and a rollout-level
cluster-bootstrap CI rather than one draw.

**The finite-sample correction, concretely** (toy draws from Normal(100,15)):

| n | required level `⌈(n+1)(1−α)⌉/n` | qhat |
|---:|---:|---:|
| 5 | 1.200 | **inf** |
| 9 | 1.000 | 119.6 |
| 20 | 0.950 | 120.5 |
| 100 | 0.910 | 122.7 |

At `n=5` the level demands the 120th percentile of only 5 numbers — impossible, so the only
honest answer is an unbounded interval. This is the exact mechanism behind the robustness pass's
"2 calibration rollouts → 1.0 over-coverage, never silent under-coverage" finding.

**ACI reacting in real time** (γ=0.05, streamed over real test data):

```
step:   1     2     3     4     5     6     7     8     9    10    11    12    13    14    15
α_t:  .100  .105  .110  .115  .070  .025  .030  .035  .040  .045  .050  .055  .060  .065  .070
```

Four correct calls push α_t up (tighter intervals). A miss at step 5 drops α_t by exactly
`γ·(α−1) = −0.045`; another miss drops it again. A miss makes α_t *smaller*, and a smaller α_t
means a *lower* required quantile level → wait, means a **wider** interval next time (lower α_t →
higher `1−α_t` → bigger quantile). Persistent misses drive α_t toward/below 0 — exactly when
`_finite_sample_quantile` returns `inf`. In this run, 3.3% of test intervals went unbounded. This
is the whole mechanism behind why frozen split-CQR collapses to 0.10 under cross-env transfer
while ACI "recovers by surrendering" to wide-open intervals instead of staying falsely narrow.

---

## The four contributions (C1–C4)

The project's own vocabulary for its claims — use these labels verbatim with your team and in the
write-up.

### C1 — AdaptiveBudgetCP: calibrated remaining-budget intervals

BAGEN's own finding: agents' fine-tuned (SFT+RL) self-estimate of remaining budget hits the true
value only **47%** of the time. A training-free conformal wrapper — no retraining, just
calibration on completed runs — raises that to **~0.90–0.95** depending on method and env.

| Method (swebench) | Coverage | vs nominal 0.90 |
|---|---:|---|
| Agent self-report | 0.354 | collapsed |
| DtACI | 0.950 | slightly over |

*Rejected: fine-tuning a better self-estimator — BAGEN already tried SFT+RL and the ceiling was
calibration, not estimation accuracy.*
📁 `conformal.py` · `run_coverage.py`

### C2 — Multi-resource: joint intervals over {time, warehouse, cost}

Getting three separate 90% margins is easy; getting all three to hold *simultaneously* is the
hard part reviewers will probe.

| Scheme | Joint coverage |
|---|---:|
| Independent (each resource at α) | 0.80 |
| Bonferroni (each resource at α/3) | 0.95 |
| Copula (shared rank calibrated once on CAL) | 0.885 |

Bonferroni guarantees the target but over-covers (wider than needed); the copula approach adapts
to the actual dependence between resources and splits the difference.

*Rejected: reporting only marginal per-resource coverage — reviewers would ask about the joint
event immediately.*
📁 `multiresource.py` · `run_multiresource.py`

#### C2 under model swap — rollout-safe adaptive joint calibration (development branch)

The original C2 methods were frozen after source calibration. Calibrating on Opus 4.7 and
deploying unchanged on four other Warehouse models dropped joint coverage to **0.66–0.79**
(Bonferroni, five-seed means) against the 0.90 target. The new method keeps the prediction models
frozen but self-corrects the calibration layer:

1. Keep a window of recent three-resource error vectors, warm-started from source CAL.
2. Before a target rollout begins, find one shared rank whose three resource thresholds cover
  enough recent error vectors *simultaneously*.
3. Use those same thresholds for every prefix in that rollout.
4. Only after the rollout finishes, add all its errors to the window. This prevents an early
  prefix from seeing the completed rollout's future totals.

| Target model | Frozen Bonferroni joint | Adaptive joint | Late-half adaptive |
|---|---:|---:|---:|
| Gemini 3.1 | 0.676 | **0.863** | 0.871 |
| GPT-5.2 | 0.665 | **0.872** | 0.879 |
| Qwen3-235B | 0.716 | **0.871** | 0.882 |
| Sonnet 4.6 | 0.793 | **0.877** | 0.898 |

All three individual adaptive margins exceed 0.90; requiring all three at once leaves the point
estimate slightly under target, but every rollout-cluster 90% CI contains 0.90. No interval is
unbounded. Honest wording: **substantial recovery to statistically target-compatible coverage, not
perfect point coverage**. This is empirical online adaptation, not a proof under arbitrary shift.
It currently covers feasible/completed rollouts only; censored runs still require the feasibility
gate in `censored.py`.

📁 `multiresource.py: adaptive_joint_qhats, adaptive_joint_intervals` ·
`run_transfer_warehouse.py` · `tests/test_multiresource_adaptive.py`

### C3 — Economic stopping: a formal abort-or-continue rule

Two error costs: abort a run that would've finished (lose its value) vs. ride a doomed run to the
end (burn its remaining budget). Calibrated at the *rollout* level — abort iff the minimum
feasibility score ever drops below τ, with τ set so P(falsely abort a feasible run) ≤ δ.

**Result on Warehouse: 86.3% of doomed-run spend recovered at 0% false aborts.**

*Rejected: a fixed spend cap (the "hard cap" baseline) — structurally strong only where doom is
defined as cap-exceedance (swebench); elsewhere it's blind to runs doomed for other reasons.*
📁 `economic.py` · `run_economic_warehouse.py`

### C4 — Cost-of-pass: dollars per correct answer, trajectory-level

Tokens saved don't mean much outside ML; dollars-per-correct-answer does. Converting the C3
stopping rule into a cost-of-pass frontier: **−46% cost-of-pass** vs. running every trajectory to
completion unmonitored.

*Rejected: reporting raw token savings alone — doesn't establish economic materiality to a
non-ML or broader-impact reviewer.*
📁 `run_costofpass.py`

---

## Censored conformal — the methods contribution

C1–C4 apply existing conformal methods well. This is the piece that's arguably new enough to be a
contribution in its own right, not just an application.

**The setting.** On Warehouse, **640 of 1280** samples have `can_finish = False` — the run cannot
complete inside its budget, so "remaining resource to completion" is undefined by BAGEN's own
convention. These aren't missing values; they're *censored* — you know only that the true
remaining cost *exceeded* the budget. Censoring bites the upper endpoint: censored scores are
systematically large, so calibrating on uncensored data alone under-covers exactly the runs a
budget guard exists to flag.

| Method | What it does | Failure mode it avoids / hits |
|---|---|---|
| `drop` | Uncensored scores only | The naive thing — under-covers, as expected |
| `infinity` | Treat censored scores as +∞ | Always valid, but qhat = ∞ once censored fraction > α |
| `bound` | Censored scores → their known lower bound | Informed middle ground; validity depends on bound tightness |
| `ipcw` | Inverse-censoring-probability weighting | The survival-analysis route — fails when doom is near-deterministic from features (positivity violated) |
| `resource_bound` | A censored run only bounds resource *r* when *r* is the operative constraint | Removes `bound`'s false cross-resource inflation and `ipcw`'s positivity failure |
| `km` (diagnostic) | Kaplan–Meier survival quantile | Rigorously returns +∞ when no finite valid bound exists, rather than a false one |

The complementary fix — **gated (selective) intervals** — abstains instead of bounding: predict
feasibility first, emit an interval only for runs the gate predicts will finish. On that kept set,
exchangeability is ~restored, and cost coverage recovers from a naive **0.46 to 0.92** —
conditional on passing the gate, not marginal over every run. Which guarantee to claim
(selective-on-kept vs. marginal-via-gated-IPCW) is explicitly **still PI-blocked** — see
[the robustness pass, item 8](#the-robustness-pass).
📁 `censored.py` · `run_censored.py`

---

## The BudgetGuard wrapper

Everything above is the research harness. This is the one artifact meant to leave the repo and be
dropped into someone else's agent loop.

- `BudgetGuard.from_logs(df, budget=…)` fits the CQR band on TRAIN rollouts and caches CAL
  conformity scores in a bounded `deque` (default window 100) — that deque *is* the online SPCI
  mechanism.
- `guard.step(turn_tokens)` featurizes the live partial run with the exact same
  `features.build_xy` path used offline (no train/serve skew by construction), predicts the
  quantile band, and reads the margin off the current window. Returns `lo`, `hi`, and `abort`.
- **Abort condition:** `spent + lo > budget` — the guard only aborts when even the *optimistic*
  projection is hopeless. Deliberate asymmetry: false aborts are the expensive error class (C3's
  calibration target).
- `guard.observe()` folds a naturally-finished run's per-prefix scores back into the window — the
  "self-recalibrates from the deployment stream" claim, in code. Set `online=False` for the frozen
  split-CQR baseline instead.

A clean-room install of this exact package (fresh venv, `pip install -e .`) caught a real bug
during the robustness pass: `scikit-learn` was undeclared even though LightGBM's sklearn API
requires it at import time. The bug only surfaced because someone finally ran the install
somewhere that wasn't the main dev `.venv` — worth remembering next time "works on my machine" is
the whole test plan.
📁 `guard.py` · `examples/quickstart.py` · `pyproject.toml`

### Loop engineering — the generalized wrapper (development branch)

The original `BudgetGuard` is token-only. The generalized path separates five concerns so a new
task needs an adapter/configuration, not new statistical code:

1. **Contract and ledger** — `RunStart`, `StepUsage`, `UsageCorrection`, `RunFinish`, and
  `RunAbort` over named additive `ResourceSpec`s. The ledger rejects missing/unknown resources,
  duplicate steps, invalid totals, and post-close changes. Events round-trip through JSONL.
2. **Generic features** — the same spent/budget-left/last/mean/std/trend summaries for every
  resource, with explicitly declared numeric context/progress keys. Failed or aborted traces
  never receive invented remaining-resource labels.
3. **Stateful estimator** — `LoopBudgetGuard` fits frozen prediction models, then updates one
  rollout-level vector-error window only after a naturally completed successful run. It cannot
  see its active run's future. Delayed telemetry replaces prior usage instead of double-counting.
4. **Policy** — estimator output becomes a recommendation (`continue`, `replan`, `reduce_scope`,
  `ask_human`, `pause`, `abort`). Low shifted gate scores escalate to a human by default rather
  than automatically destroying useful work. Policy is replaceable without retraining.
5. **Adapters** — OpenAI-style, LangChain-style, and arbitrary mapping adapters translate
  telemetry only. Provider prices are supplied by the caller, never hardcoded.

**Five-seed unchanged-core validation (default = 10 completed rollout vectors):**

| Scenario | Frozen joint | Adaptive joint | Trajectory-level joint | Auto false-stop | Failed caught |
|---|---:|---:|---:|---:|---:|
| Sokoban → SWE-bench tokens | 0.519 | **0.912** | 0.837 | 0.000 | 0.784 |
| Opus → Gemini Warehouse | 0.787 | **0.963** | 0.838 | 0.000 | 0.719 |
| Opus → GPT-5.2 Warehouse | 0.939 | **0.943** | 0.822 | 0.009 | 0.719 |
| Opus → Qwen Warehouse | 0.887 | **0.949** | 0.847 | 0.031 | 0.713 |
| Opus → Sonnet Warehouse | 0.973 | **0.957** | 0.800 | 0.009 | 0.713 |
| Non-agent sequential text (pipeline smoke) | 0.956 | 0.958 | 0.911 | 0.000 | — |

The independent per-resource adaptive baseline reaches nominal by becoming unbounded on nearly
every three-resource Warehouse run, triggering fail-safe pauses 97–99% of the time. The shared
joint rank remains finite and operational; this is why joint adaptation is not cosmetic.

**Predeclared order/window stress test:** 10 target permutations × windows {5,10,20,40} × five
transfer scenarios = 200 replay runs. Window 5 is mathematically too small for finite 90%
calibration and correctly fails safe. Window 10 is the stable cross-family default: token joint
coverage 0.937–0.951 across orderings; Warehouse 0.938–0.975; automatic false stops 0–4.7%.
Windows 20–40 adapt too slowly on token shift (mean 0.899 / 0.874), so no task-specific tuning was
used to rescue them.

**Closed-loop audit:** at the conservative default, oracle and deployment replay match over five
seeds (tokens 0.912; Warehouse Gemini 0.963) because no successful run is automatically stopped;
failed-run catch remains 78% / 72%. A replay bug found during this audit—obeying a stop
recommendation *after* the terminal step and incorrectly censoring an already observed label—was
fixed and locked by a regression test.

**Honest remaining gap:** BAGEN is still the only real agent benchmark suite. The local source-
text case proves the generic software path, not external agent validity. A second independent
agent benchmark and an anonymized production/pilot log are still required before claiming broad
real-world impact.

📁 `loop_schema.py` · `loop_features.py` · `loop_guard.py` · `loop_policy.py` ·
`loop_adapters.py` · `loop_evaluation.py` · `run_loop_{validation,stress,closed_loop}.py`

---

## The robustness pass

This is the part built across 9 commits without close supervision, so it's worth understanding as
a *process*, not just a diff. It was driven by a literal master prompt
(`notes/robustness_loop_prompt.md`), resubmitted verbatim every iteration, that reads its own
progress log (`notes/robustness_progress.md`) to self-resume.

**Ground rules it operated under:**
- **Verify before extending** — nothing from weeks 2–6 had been reproduced by anyone but the
  original author; re-derive a number yourself before building on it.
- **No fabricated results** — every number comes from code actually run this session; if it can't
  run (missing data), say so, don't approximate.
- **Negative results are first-class** — a weak transfer result or a barely-beaten baseline gets
  written down, not buried.
- **5+ seeds, cluster-bootstrap CIs** on anything called a headline number.
- **Escalate, don't improvise** — anything needing a human call gets marked "Blocked — needs PI
  sign-off" with a scoped proposal, not a unilateral new direction.
- **Git hygiene** — small focused commits, never rewrite history, never delete `notes/week*.md`
  (append new dated sections instead).

| Item | Outcome | Status |
|---|---|---|
| 1. Audit + reproduce | C1–C4 + censored numbers reproduced exactly; synthetic tests pin frozen-degrades / online-recovers | Done (19-run set data-blocked) |
| 2. Marginal → conditional coverage | Sokoban k=1 hole 0.860 → Mondrian 0.927; swebench has no hole; searchr1 too small to conclude | Done |
| 3. Kill baseline objections | Constant-quantile within 0.03–0.05 coverage of the fitted guard — guard wins on sharpness (20–56% narrower), not raw coverage | Done |
| 4. Honest uncertainty everywhere | 5-seed label-efficiency curve: 5–8 rollouts → ~0.90 coverage; 2 rollouts fails *safe* to ~1.0 over-coverage | In progress |
| 5. One external, non-BAGEN dataset | Unmodified guard on 621 local source files: ~0.90 coverage, but baseline nearly matches (~10% width edge vs 20–56% on BAGEN) | Cheap option done |
| 6. Transfer-led headline figure | Sokoban→swebench: frozen collapses to **0.10**, SPCI self-heals to **0.90** at 0% unbounded, ACI "recovers by surrendering" (58–86% unbounded) | In progress (model-swap data-blocked) |
| 7. Ship the wrapper | pip-installable; clean-room install caught the missing scikit-learn dependency | Done |
| 8. Censored refinement | Rungs 1–3 re-verified; gated-IPCW next increment proposed, deliberately not started | Blocked — PI |
| 9. Closed-loop limitation | Named unconditionally + toy pilot (below) | Done |

### The headline evidence (item 6) — why it leads the paper

Calibrate on Sokoban, deploy unchanged on SWE-bench — deliberately the hardest transfer the repo
can currently test, chosen as the lead figure over any within-distribution table:

| Method | Coverage | 90% CI | Unbounded fraction |
|---|---:|---|---:|
| Frozen split-CQR | **0.10** | [0.08, 0.13] | 0% |
| ACI-CQR | 0.89 | — | 86% |
| SPCI | **0.90** | [0.86, 0.94] | 0% |

ACI's 0.89 isn't the same win as SPCI's 0.90: ACI gets there by opening 86% of its intervals to
unbounded width — technically valid, practically useless as a monitor. SPCI hits nominal coverage
*and* stays finite every time. That distinction is exactly the kind of thing a sharp reviewer
probes, and it's already in the notes.

### Item 9 in detail — the closed-loop pilot

A synthetic simulation where the guard's own aborts remove runs from its future calibration
stream. Over 25 rounds: an oracle that counterfactually sees every label holds at **0.90**
coverage; the closed-loop guard's *true* coverage on the full population drifts to **0.83**; but
the guard's *self-measured* coverage (on its own self-selected, survivorship-biased stream) stays
at **0.91** — it is blind to the bias it's inducing. Illustrative and synthetic, not a measurement
of the real system, but the mechanism is real and stated as an open limitation, not smoothed over.
📁 `notes/robustness_loop_prompt.md` · `notes/robustness_progress.md` · `scripts/run_closed_loop.py`

---

## Honest limitations (stated, not hidden)

All from `notes/positioning.md`'s own "honest-limitations" section — worth internalizing
verbatim, because a workshop reviewer will ask about at least one of these.

- **Counterfactual-free evaluation.** Everything here runs on *logged* rollouts. In real
  deployment, the guard's own abort decisions change the data it later calibrates on — see the
  closed-loop pilot above. Off-policy/bandit-style correction is named future work, not solved.
- **Marginal coverage can be a mirage.** Pooled numbers hide per-slice holes (the sokoban k=1
  case) — always ask for conditional, not just marginal, coverage.
- **The ML content is genuinely thin on raw coverage.** A constant-quantile, no-model baseline
  gets within 0.03–0.05 coverage everywhere tested. The honest claim is sharpness (interval
  width), not "the model knows something a quantile doesn't."
- **The guard's edge is domain-dependent.** Off-domain (the external source-code corpus), the
  baseline nearly closes the sharpness gap too (~10% vs 20–56% on BAGEN agent data).
- **Sample-size asymmetry.** searchr1 is small and noisy (n≈24 test rows); explicitly flagged as
  not headline-worthy within-run.

---

## Defend-it-at-a-conference

The questions most likely to come from someone who actually knows conformal prediction, drawn
straight from the project's own honest-limitations notes — plus a couple flagged as open, so you
don't overclaim in the room.

**Q — Split conformal already gives valid coverage — why do you need anything fancier?**
A — Only under exchangeability. Scores drift within a trajectory (early vs. late turns) and
across deployment (model swaps, new tasks). Frozen split-CQR calibrated on Sokoban collapses to
0.10 coverage deployed on SWE-bench — that's the whole reason the online variants
(ACI/SPCI/DtACI) exist.

**Q — Your fitted guard barely beats a constant-quantile baseline on coverage — so what's the
actual contribution?**
A — Sharpness. At matched coverage the fitted guard is 20–56% narrower on BAGEN agent data. We
report the baseline explicitly rather than hiding it, including the one domain (external source
code) where the sharpness edge shrinks to ~10% — the honesty here is itself part of the pitch.

**Q — Why split calibration/test by rollout instead of by prefix?**
A — Prefixes of one rollout share `total_rollout_tokens` and are highly correlated. A
prefix-level split leaks each test rollout's own answer into calibration and inflates every
coverage number in the paper.

**Q — This is all offline, logged evaluation — does any of it hold once you actually deploy the
guard?**
A — Named directly as the key limitation: logged evaluation is counterfactual-free. A toy
closed-loop simulation shows true coverage drifting 0.92→0.83 under self-selection while the
guard's self-measured coverage stays blind at ~0.91. Off-policy correction is future work, stated
as such, not glossed over.

**Q — Why conformal prediction rather than a Bayesian credible interval?**
A — *Not explicitly argued in the project notes.* The strongest honest answer is that conformal's
guarantee is distribution-free and finite-sample-valid without needing a prior over agent
behavior, which matters with as few as 5–8 calibration rollouts. ⚠️ **Not documented in-repo —
confirm with your PI before claiming this in a real Q&A.**

**Q — Which censored-conformal guarantee are you actually claiming — marginal, or conditional on
passing the feasibility gate?**
A — *Open.* Explicitly PI-blocked in the repo right now (robustness item 8) — the gated-IPCW
experiment that would help decide it is scoped but not yet run pending sign-off. ⚠️ **Genuinely
unresolved — say so if asked.**

---

## Repo state (worth fixing)

Two things found while mapping this out, unrelated to the science:

- **This outer clone's `main` is 22 commits behind `origin/main`** — it only has the two original
  "Week 1" commits. All of C1–C4, the censored-conformal work, and the entire robustness pass
  exist on the remote but not in that checkout.
- **A second, independent clone of the same repo is nested inside the first one**, at
  `budget-guard/budget-guard/` — already at `origin/main`'s tip, with its own venv and an editable
  install already done. Everything in this document was read from that inner clone.
- **A collaborator branch, `origin/Ritchie`**, exists and sits behind current `main` (not
  diverged) — one more reason to get the outer clone's `main` fast-forwarded before your next sync
  with them.

Recommended, low-risk fix: fast-forward the outer clone's `main` (`git pull` — a clean
fast-forward, no conflicts possible) and keep working out of the inner clone since its environment
is already set up. Whether to collapse the duplicate nesting into one folder can wait.

---

## Where it actually stands

| Blocked on | What |
|---|---|
| **Data** | Full 19-run × multi-model BAGEN download (only 3 opus runs local) — blocks the all-19 breadth table and model-swap transfer bars |
| **PI** | Which censored-conformal guarantee to claim; the gated-IPCW next increment; whether the by-depth cut belongs on warehouse tables; target venue confirmation |

Per `notes/current_state.md`: research is considered complete and robustness-hardened; next is a
PI meeting, then downloading the full dataset elsewhere, then a 4-pager led by the transfer
figure, aimed at a NeurIPS 2026 workshop (watch the slate confirm around Sep 29) — flagged as
time-sensitive since the BAGEN team itself is targeting NeurIPS 2026 main with public code.
