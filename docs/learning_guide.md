# The Budget-Guard Learning Guide

*A from-zero walkthrough of everything in this repo: the problem, the math, the
architecture, every experiment, and the honest answers to hard questions. Written
for team members with little stats background. Work through it in order; answer
each "Check yourself" block in your own words BEFORE reading on (answer key at the
bottom). If you can answer everything here, you can defend this project at a
conference.*

*Every number in this guide is a real measured result reproducible from
`python -m budget_guard.run_*` (seeds and tables in `tables/`).*

---

## Part 0 — What exists (the map)

Two sibling folders:
- **`BAGEN/`** — a read-only clone of the paper we build on (arXiv:2606.00198).
  We never import its code; we only read it to port logic faithfully.
- **`budget-guard/`** — ours. The package `budget_guard/` contains ~10 small
  modules; `notes/` is the lab notebook (week1–6 + positioning + references);
  `data/bagen_hf/` (gitignored, ~2.6 GB) holds the public HuggingFace dataset
  `MLL-Lab/BAGEN`; `figures/` and `tables/` regenerate from commands.

| Module | One-line job |
|---|---|
| `extract.py` | rollout JSON → one row per prefix: features-so-far + true remaining tokens |
| `features.py` | leak-free feature matrix (asserts no future-peeking) |
| `split.py` | train/cal/test split **by rollout** |
| `conformal.py` | the interval methods: split, CQR, ACI, SPCI, DtACI, Mondrian, constant-quantile |
| `metrics.py` | coverage, widths, rollout-bootstrap confidence intervals |
| `data.py` | env registry + agent self-estimate loader |
| `multiresource.py` | C2: joint intervals over {time, storage, cost} on Warehouse |
| `economic.py` | C3: calibrated stopping rule ("abort or continue?") |
| `censored.py` | censored-label methods: rung 1 calibrations, resource-specific bounds, KM, gated intervals |
| `guard.py` | the pip-installable `BudgetGuard` wrapper API (`from_logs` / `step` / `observe`; demo in `examples/quickstart.py`) |
| `run_*.py` | one driver per experiment/figure (incl. `run_gated.py` selective frontier, `run_final.py` fixed-seed figures) |

Sync model: **code in git, data not** — anyone can `pip install -r
requirements.txt`, re-download from HF, and regenerate every figure. That is the
reproducibility story; say it proudly.

---

## Part 1 — The problem

An LLM **agent** is a model in a loop: it looks at a task state, emits an action,
sees the result, repeats — 4 turns for a puzzle, 150 for fixing a real GitHub bug.
Every turn costs **tokens**, and tokens are dollars and time.

The BAGEN paper asked a simple question: *does the agent know how much budget it
has left, mid-task?* They interrupted agents and asked for an interval — "I'll
need between 1,200 and 1,900 more tokens." Then, because the runs finish, you can
check. Result: the interval contained the truth **far** less often than stated.
In the 19 runs sitting in our `data/` folder, the agent's own interval covers the
true value between **2.5% and 52%** of the time (mean **27%**). For the estimate
to be operationally useful, you'd want ~90%.

Why anyone cares: budget knowledge is *actionable*. If you can tell a run is
doomed, you kill it early and save the remaining spend — BAGEN measured 28–64% of
failed-run cost recoverable. Miscalibration is the only thing standing between
that knowledge and real money.

**Our thesis:** BAGEN tried to fix this by fine-tuning the agent (SFT+RL) — still
badly miscalibrated. We claim calibration is a *statistics* problem, not a
training problem: wrap any agent with a lightweight statistical monitor that
turns rough predictions into intervals with a **guaranteed** hit rate. No
fine-tuning, no GPU, works for any model.

The four contributions, named C1–C4 everywhere in our notes:
- **C1 AdaptiveBudgetCP** — calibrated remaining-budget intervals, training-free.
- **C2 Multi-resource** — one *joint* interval over tokens AND dollars AND time.
- **C3 Economic stopping** — a formal abort-or-continue rule with error control.
- **C4 Cost-of-Pass** — evaluate everything in dollars per *correct* answer.

> ### 🤔 Check yourself (answers at bottom)
> **Q1.** Your PI asks: "why should anyone care whether an agent knows its
> remaining budget?" Give the two-sentence answer with a number in it.
> **Q2.** BAGEN already tried to fix this with fine-tuning. Why is "we don't
> touch the model at all" a *feature* of our approach rather than a limitation?

---

## Part 2 — The data: how a transcript becomes a dataset

Run `python budget_guard/extract.py` and you get (the bundled smoke sample):

```
 rollout_index        sample_id  k  N  tokens_so_far  total_rollout_tokens   y
             0 rollout-0-turn-1  1  4            360                   630 270
             0 rollout-0-turn-2  2  4            448                   630 182
             0 rollout-0-turn-3  3  4            549                   630  81
```

One **rollout** = one agent attempting one task, recorded. We chop it at every
prefix: after turn k, the features `x_t` are what you'd legally know mid-run, and
the target **y = total − tokens_so_far** is the true remaining spend — knowable
only because the run is already finished and logged. A 4-turn rollout yields 3
labeled examples. Free supervision: **every completed run labels itself.**

Why this works at all: live, "how much more will I need?" is a question about a
future the agent itself shapes (a rambling agent needs more tokens *because* it
rambles — the target is "self-induced"). In a log, the future is frozen; y is
subtraction. An exotic online problem becomes ordinary supervised regression.

**Leaks.** The table also carries `N` (total turns), `total_rollout_tokens`,
`rollout_success` — things you know only at the end. Using them as features =
telling the model the answer. `features.py` hard-codes a `LEAK_COLUMNS` set and
asserts none enters the feature matrix. Legal features: `k`, `tokens_so_far`,
burn rate (`tokens_so_far/k`), per-turn stats (mean/std/min/max/last/last-3/trend).

**The token-accounting war story (tell this one).** Every API request re-sends
the whole conversation, so a turn's raw "input tokens" re-counts all history. Sum
raw request usage and your labels are ~6× too big. BAGEN's official code
converts request usage to *incremental per-turn* usage
(`turn_usage_mode="turn_excluding_history"`, including a majority-vote heuristic
for whether a log's usage includes history, and a visible-vs-reasoning output
split). We ported that logic into `extract.py` and validated the only way that
counts: BAGEN's records ship their own ground-truth `y` per sample, and ours
matches with **0 mismatches on 355/355 (Sokoban), 512/512 (SWE-bench), 87/87
(Search-R1)**. When asked "why trust your labels?" — that's the answer.

**Environments** (all with agent model fixed to claude-opus-4.7 in headline
tables, so cross-env differences are env effects): **Sokoban** (puzzle, short
runs, budget 2500), **Search-R1** (search QA, 3500), **SWE-bench** (bug fixing,
long runs, 7060), **Warehouse** (logistics; the only one with time+storage+cost).
Each env also run by ~6 other models (GPT-5.2, Gemini-3.1, Qwen3-235B, …) — 19
runs total with usable data.

> ### 🤔 Check yourself
> **Q3.** Why is y "partly self-induced" for a live agent, and why do logged
> rollouts sidestep that?
> **Q4.** `total_rollout_tokens` is sitting right there in the dataframe. Explain,
> to someone who's never heard of leakage, why using it as a feature makes your
> results meaningless.
> **Q5.** One rollout contributes N−1 rows. What do those rows share, and why
> does that matter for how we split data? (Full answer in Part 3.)

---

## Part 3 — Conformal prediction from scratch

You need one concept first. A **prediction interval at level 90%** is a range
[lo, hi] produced per example, with the promise that the true value lands inside
on 90% of examples. **Coverage** = the fraction of times it actually does.
Coverage below nominal = the promise is broken (dangerous); far above = the
intervals are wider than needed (useless). Width is the price of coverage — an
interval of [0, ∞) covers 100% and helps nobody. Every result in this project is
a (coverage, width) pair.

**The whole trick of (split) conformal prediction:**
1. Fit any point predictor f(x) on **TRAIN** — quality doesn't affect validity,
   only width.
2. On a held-out **CALIBRATION** set, record residuals sᵢ = |yᵢ − f(xᵢ)| — "how
   wrong was I?"
3. Let q̂ = the 90th-percentile residual. For a new x, predict **[f(x) − q̂, f(x)
   + q̂]**.

Why it works: the new example's residual is exchangeable with the calibration
ones, so the chance it exceeds their 90th percentile is ~10%. That's the entire
proof idea. Two refinements we use everywhere:
- **Finite-sample correction:** use the ⌈(n+1)(1−α)⌉/n quantile, not the plain
  one — with n calibration points, the guarantee is exact: coverage ≥ 1−α. When
  that rank exceeds n, the honest answer is q̂ = ∞ (interval unbounded). Remember
  this — it becomes load-bearing twice (ACI under shift; tiny-data label
  efficiency).
- **Exchangeability is the only assumption.** No Gaussian, no correct model. But
  it *is* an assumption, and Parts 4–5 are about the ways our data violates it.

**Why we split by rollout, never by prefix** (`split.py::group_split`, 50/25/25).
All prefixes of one rollout share `total_rollout_tokens`. Put turn 2 in
calibration and turn 3 of the *same run* in test, and calibration has effectively
seen the test answer. Coverage would look great and be fake. So the split is by
`rollout_index` — whole runs go to one side. This is the #1 subtle-bug question
a knowledgeable reviewer asks; you now have the answer.

**The no-model baseline you must know exists** (`constant_quantile`): ignore x
entirely, output the same [5th, 95th] percentile of calibration y's for
everything. It covers (0.88 Sokoban / 0.92 SWE-bench) — conformal doesn't need a
model to cover! — but its intervals are 30–130% wider than ours, and it
under-covers Search-R1 (0.77). This baseline is what makes "our features/model
earn their keep" a measured claim instead of an assertion.

> ### 🤔 Check yourself
> **Q6.** Explain to a labmate in ≤4 sentences why conformal's 90% promise holds
> *no matter how bad the underlying model is*, and what a bad model costs instead.
> **Q7.** Coverage 1.0 sounds like a triumph. When is it actually a failure?
> **Q8.** Walk through what concretely goes wrong if we split by prefix. What
> would the coverage number look like, and why is that worse than an error?

---

## Part 4 — CQR, and the depth problem (the Week-2 findings)

**Why absolute-residual intervals are wasteful:** they're symmetric and the same
width everywhere. Remaining-budget errors are neither — early turns are wildly
uncertain, late turns are not. **CQR (Conformalized Quantile Regression)**: fit
two quantile regressors (5th and 95th percentile of y given x — LightGBM with
pinball loss), then conformalize the *band*: score E = max(q̂lo − y, y − q̂hi)
measures how far y escapes the band; pad both edges by the 90th-percentile
escape. Adaptive width, same guarantee. Measured: ~20–30% narrower than absres at
comparable coverage.

**Finding 1 (this genuinely surprised us):** within one run, naive split
conformal is NOT catastrophically miscalibrated — Sokoban marginal coverage 0.87
vs 0.90 nominal. Our plan predicted <0.80 and was wrong. Why: with a
rollout-level random split of one run's data, exchangeability approximately
*holds by construction*. Say this plainly at the conference — it's what an honest
evaluation looks like, and it sets up where the real problems are:

- **Conditional coverage fails.** Marginal 0.87 hides that turn-1 prefixes cover
  only **0.77–0.80** and late turns over-cover. The guarantee is *marginal* —
  averaged over everything — never per-slice. Fix implemented: **Mondrian
  conformal** = separate q̂ per depth bucket (k=1 / k=2 / k≥3): k=1 coverage
  0.860 → **0.927**.
- **Sharpness fails on SWE-bench.** Naive coverage 0.99–1.0 with intervals 2–3.3×
  the data's own spread. Coverage without usefulness.
- **And deployment breaks exchangeability entirely** → Part 5.

> ### 🤔 Check yourself
> **Q9.** "Your guarantee is marginal" — a reviewer says this like an accusation.
> What does it mean, what's the evidence in our own figures, and what's our answer?
> **Q10.** Why does CQR beat absres on width? Give the mechanism.

---

## Part 5 — Online conformal: the heart of the paper

**The deployment problem.** You calibrate the guard on logged runs of model A on
task X. Then someone swaps in model B, or points the agent at task Y. The new
residuals are *not* exchangeable with calibration — the guarantee is void.
Measured (SWE-bench, calibrate on claude-opus-4.7): frozen split-CQR covers
**0.61 / 0.51 / 0.76 / 0.38** on sonnet-4.6 / gemini-3.1 / gpt-5.2 / qwen3-235B.
Cross-task is worse: sokoban→swebench frozen coverage **0.12**. Silent failure —
the intervals look confident and are wrong.

**The saving grace:** labels keep arriving. Each finished run reveals its y. So
adapt online:

- **ACI** — a thermostat on the miscoverage level. Maintain a working level αₜ;
  after each prediction: αₜ₊₁ = αₜ + γ(α − errₜ), errₜ∈{0,1}. Missing too often
  → αₜ falls → wider intervals. Long-run coverage → α regardless of drift.
  Subtlety you must know: when αₜ sinks low enough, the finite-sample quantile
  demands an **unbounded interval** — that's not a bug, it's what carries the
  guarantee. (Our first implementation capped it; a synthetic-shift unit test
  caught coverage collapsing to 0.01, and fixing it changed the results. Great
  Q&A story about testing statistical code.) Cost, measured: under model swap ACI
  restores ~0.90 *but* 13–50% of its intervals are unbounded — "recovery by
  surrender."
- **SPCI (our windowed variant — say "windowed variant" in the paper)** — keep a
  sliding window of the most recent scores (warm-started from calibration); read
  q̂ off the window. The score distribution itself tracks the new regime.
  Measured: 0.906–0.925 under model swap with **zero** unbounded intervals —
  recovery by adaptation. The contrast with ACI is a finding, not a footnote.
  One real design rule discovered: the window must be ≪ the deployment stream
  (sokoban→searchr1: stream of 87 < window of 100 → stale scores never flush →
  0.71; window 25 → **0.931**).
- **DtACI** — runs several ACI copies with different γ's and lets an
  expert-aggregation scheme weight them online. No tuning knob at all. It's our
  best headline method: **0.936±0.011 (Sokoban), 0.950±0.015 (SWE-bench)**,
  narrowest widths, lowest seed variance. Exists to kill the "you tuned γ"
  objection before it's raised (our tuned-γ ACI kept hitting the grid ceiling —
  visible in our own tables, which is exactly why DtACI is in the repo).

**Breadth:** across all 19 runs (7 Sokoban, 7 Search-R1, 5 SWE-bench; Claude,
GPT, Gemini, Qwen, Codex): **SPCI ≥ 0.85 coverage on 19/19**, DtACI 18/19,
frozen split-CQR only 14/19. Online adaptation is what makes the guard reliable,
not the base model.

**The zero-training punchline (P3):** take the agent's OWN interval midpoint —
no features, no LightGBM — and just conformalize it. Coverage goes 0.51/0.23/0.35
→ **0.93/0.90/0.97**. The agent's self-knowledge isn't wrong; it's uncalibrated.
The fitted guard then buys ~40% narrower intervals on top. (Ablation, honest:
adding the agent's estimate as a *feature* to the fitted guard adds ~nothing.)

> ### 🤔 Check yourself
> **Q11.** Explain ACI's update rule as a thermostat, then explain why refusing
> to ever emit an unbounded interval silently destroys its guarantee.
> **Q12.** ACI and SPCI both "recover coverage" under model swap. A reviewer asks:
> "so they're equivalent?" What's the one-sentence rebuttal with numbers?
> **Q13.** Why is the label-efficiency result (5–8 logged runs suffice; at 2 runs
> the guard outputs unbounded intervals) an *answer to the PI's cold-start
> question* rather than a weakness?
> **Q14.** What exactly did the conformalized-agent experiment hold constant, and
> why does that make "calibration, not knowledge, is the bottleneck" defensible?

---

## Part 6 — C2: one interval per resource is not enough

Warehouse runs consume three budgets at once: **time (weeks), storage
(item-weeks), cost (USD)**. An operator needs all three simultaneously: "will
this run fit in budget?" is a *joint* event.

The trap: three independent 90% intervals cover jointly ~0.9³ ≈ 73% at best —
less if errors correlate. Measured: independent margins → joint **0.80**. The
agent's own joint coverage: **0.42** over all its samples — and **0.36** when
recomputed like-for-like on the exact feasible test rows the guard is scored on
(the fair version; the gap *widens*).

Fixes, both implemented:
- **Bonferroni:** run each margin at α/3. Union bound ⇒ joint ≥ 90%,
  assumption-free. Measured joint: **0.95** — valid but conservative (margins at
  0.97–1.00).
- **Copula (empirical):** find the *smallest shared rank level* u\* such that on
  calibration, all three scores fall inside their u\*-quantiles ≥ 90% of the
  time. Adapts to the actual dependence between resources. Measured joint:
  **0.885** with visibly tighter margins — sits between independent and
  Bonferroni, exactly as theory says.

Data note that becomes Part 8: exactly half the Warehouse samples (640/1280) have
**no remaining-resource labels** — the run can't finish within budget, so
"remaining until completion" is undefined. Keep that in mind.

> ### 🤔 Check yourself
> **Q15.** Why is per-resource 90% coverage not 90% joint coverage? Give the
> back-of-envelope number.
> **Q16.** Bonferroni "always works." Why would you still want the copula method?

---

## Part 7 — C3 + C4: turning intervals into money

**C3, the stopping rule.** Fit a classifier for P(run can finish | prefix
features). Abort a run the first time its score drops below τ. The subtle part is
calibrating τ: the rule looks at *every* prefix, so a per-prefix guarantee
doesn't control the per-run false-abort rate. Trick: a run is aborted iff its
**minimum** score over prefixes < τ — so calibrate τ as the δ-quantile of
*per-rollout minimum scores* among feasible calibration runs. That gives a clean
guarantee: P(falsely abort a feasible run) ≤ δ. (This min-score reduction is
ours; remember it.)

**Where it wins and loses — know this cold:**
- **Warehouse (the headline):** at δ=0.10, the guard saves **86.3% of doomed-run
  dollars with 0% false aborts**; hard caps on dollars or weeks are dominated
  everywhere (best cap: ≤15% saved while falsely killing 3–62% of good runs).
  Honest caveat: Warehouse doom is largely decidable from the initial
  budget/target configuration — information the guard reads and a cap can't.
  That's the point of a learned guard, but say it out loud.
- **Sokoban:** guard modestly dominates the cap; total savings small because runs
  are short — little left to save by the time doom is visible.
- **SWE-bench:** the hard cap WINS (40% saved at 0 false aborts). Why: there,
  infeasibility is *defined* as exceeding the 7060-token context cap, so "did you
  cross the cap" is an oracle. When doom IS the cap, use the cap. Presenting
  this negative result honestly is worth more credibility than hiding it.
  (We also tried an interval-driven trigger — abort when tokens_so_far +
  conformal-lower-bound > budget; it's calibration-starved at 64–123 rollouts
  per run and only fires on cap-style doom. Kept in the repo, documented.)

**C4, cost-of-pass** = total spend / number of *correct* runs — the economics
endpoint (concept from Erol et al., arXiv:2504.13359; we extend it from single
responses to whole trajectories). Both effects priced in: aborting a doomed run
saves its tail; falsely aborting a good run forfeits its pass. Measured:
SWE-bench 21,254 → 17,134 tokens per pass (**−19.4%**, keeping 94% of passes);
Warehouse **$1.61M → $0.87M per pass (−46%) at 100% of passes retained**.
Policy *rankings* are price-invariant (cost scales linearly); the Warehouse
numbers are native dollars, no price assumption at all.

> ### 🤔 Check yourself
> **Q17.** Why does calibrating τ on per-prefix scores under-control the per-run
> false-abort rate, and how does the min-score trick fix it exactly?
> **Q18.** A reviewer: "a one-line token cap beats your learned guard on
> SWE-bench." Give the full honest answer, including when the cap must lose.
> **Q19.** In cost-of-pass, what are the two opposing forces, and why does a
> tiny false-abort rate sometimes cost more than it saves?

---

## Part 8 — Censored conformal: the candidate methods contribution

**The problem the data forced on us.** Those 640 label-less Warehouse samples are
not "missing at random" — they're **censored**: the run couldn't finish within
budget, so its remaining-cost-to-completion exceeds the budget it had left
(b = budget − spent), and that's *all* you know. Censored runs have
systematically LARGE y, so they break the **upper** interval endpoint: calibrate
on uncensored data only and hi = pred + q̂ under-covers exactly the doomed runs a
budget guard exists to catch.

**Why Warehouse is the perfect testbed:** BAGEN nulls the remaining fields but
keeps the realized totals, so true y is *recoverable*. We can mask labels (treat
them exactly as deployment would), calibrate each method, then grade against
truth. "Mask-and-measure" — most censored-inference papers can't do this on real
data.

**Four calibrations of the upper bound, measured (α=0.1, 50% censoring):**

| calibration | coverage (censored pop.) | q̂ |
|---|---|---|
| drop censored (naive) | **0.786** — under-covers, as predicted | 66k |
| censored → +∞ | 1.000 | **∞** — valid but useless once censoring > α |
| censored → known bound (b − pred) | **0.998** | 385k — valid AND finite |
| IPCW (survival-analysis standard) | **0.777** — fails | 65k |

**Rung-1 findings:**
1. **IPCW fails on real agent data.** IPCW reweights uncensored samples by
   1/P(uncensored|x) — it requires *positivity*: censored-like x's must sometimes
   be uncensored. Here censoring is nearly deterministic in the features (doom
   decidable from the config), so there is nothing to upweight. A textbook
   assumption, empirically broken in the wild.
2. **Censoring is cross-resource.** The bound "y_cost > cost-budget-left" holds
   on only **42%** of censored rows — because the run often died on *time*, not
   cost.

**Rung 2 — resource attribution (`resource_bound`), and a self-correction you
must know.** A censored run informs resource r only when r was the *operative*
(binding) constraint — the budget that actually got hit (time binds 30% of
censored runs, warehouse 34%, cost 42%; a run can bind several). Once you
attribute correctly, rung 1's "bound" method is exposed: **its 0.998 coverage was
an artifact** — it borrowed large *false* bounds from runs that died on a
different resource (they spent little cost, so their cost-headroom was huge and
inflated q̂ to 385k). With attribution: on **time** (where spend is measured
exactly) `resource_bound` is the clean winner — nominal **0.90** in every stratum
where the alternatives over-cover at 1.00 with q̂ up to ~50,000× larger. On
**cost**, it exposes a hard limit: doomed-on-cost runs overshoot far beyond their
remaining headroom, so no tight valid bound exists from censored data alone.

**The KM check (a second self-correction).** A Kaplan–Meier survival estimator —
the statistically proper way to use right-censored scores — gives the best
non-gated coverage on doomed-on-cost runs (**0.58** vs drop 0.50) with a finite
~91k bound. So the honest statement is not "unboundable" but: *a finite bound
exists, a VALID (0.90) one does not — even the proper survival method reaches
only 0.58.* That quantified failure is the motivation for rung 3.

**Rung 3 — feasibility-gated (selective) intervals: the resolution.** If the
operative resource can't be validly bounded from censored data, don't bound it:
**gate** on the feasibility classifier (abort predicted-doomed runs — that's C3)
and emit a calibrated interval only for the kept population, where censoring is
filtered out and exchangeability ~holds. Measured: on cost, coverage of the
doomed goes 0.46 un-gated → **0.92 on the kept population with a tight 70k
bound**, catching 72% of doomed runs at a δ-controlled false-abort rate. The
selective frontier (`run_gated.py`) stays above nominal across kept∈[0.5, 0.9].

**The completed methods narrative** (this is the paper's methods section):
censoring in multi-resource agent budgets is *resource-specific*; correct
attribution fixes what's fixable (exact-spend resources), a KM diagnostic proves
the operative resource cannot be validly covered from censored data, and so the
guard **abstains there and guarantees coverage on the rest** — a
selective-conformal division of labor between classification and intervals.
Still PI-gated: which guarantee to *claim* (selective-on-kept vs marginal) and
the proposed next increment (gated-IPCW / positivity restoration).

> ### 🤔 Check yourself
> **Q20.** Why does censoring break the upper endpoint rather than the lower one?
> **Q21.** Explain IPCW's positivity assumption and why our data violates it —
> then explain why that failure is *publishable* rather than embarrassing.
> **Q21b.** Rung 1 concluded "bound-informed calibration is valid and finite";
> rung 2 partially retracted that. What exactly was wrong, and why does the
> correction *strengthen* the paper?

---

## Part 9 — The weaknesses (know them better than the audience)

1. **Methods novelty now has a real core, but it's narrow.** C1–C4 apply known
   techniques carefully. The original pieces: censored rungs 1–3 (resource
   attribution → KM diagnostic → gated/selective intervals), the
   rollout-min-score calibration for stopping, and the mask-and-measure
   evaluation design. The guarantee framing is PI-gated — don't over-claim
   before that conversation.
2. **The 0.51-vs-0.92 headline is apples-to-oranges.** Zero-shot prompted agent
   vs supervised model fit on in-distribution logs. The *fair* claims:
   conformalized-agent (same information, add only calibration),
   like-for-like C2 (agent 0.36 on the same rows), and guard-under-shift.
   Frame it that way before a reviewer does.
3. **Everything is off-policy — and we measured what that costs.** Aborting in
   deployment changes the future data the guard calibrates on. A toy
   closed-loop pilot quantifies it: true coverage drifts 0.92 → 0.83 once the
   guard's own actions filter the stream (an oracle-fed guard holds 0.90, and
   the guard can't see its own miscalibration — it reads 0.91). State it as a
   limitation with a number, propose deployment simulation as future work.
3b. **The external-corpus check is honest but weak.** On a non-BAGEN corpus the
   unmodified guard covers ~0.90 — but a trivial baseline nearly matches there,
   so it demonstrates portability, not superiority. Don't oversell it.
4. **Small samples in places.** Search-R1 test sets ~23 samples; CIs like
   [0.84, 0.98]. We report rollout-level bootstrap CIs (resample runs, not
   prefixes — prefixes within a run are correlated, per-sample CIs are too
   tight); still, don't hang claims on Search-R1.
5. **Interval-driven stopping didn't work** at current data sizes. Documented,
   kept, honest.
6. **Novelty vs literature unverified** — the lit-review team owns this
   (`notes/references.md` §unresolved: MiCP, CCPO, 2025–26 conformal×agents).

## Mock hostile Q&A (rehearse these out loud)

- *"Split conformal works under exchangeability — what's new here?"* → Within-run,
  correct, and our own gap figure says so. The paper is about where it breaks:
  conditional coverage at k=1 (0.77→0.93 via Mondrian), sharpness, and above all
  deployment shift (0.12 frozen → 0.90+ online), plus the economics layer.
- *"Why LightGBM?"* → Any regressor works; validity never depends on it (the
  constant-quantile row proves coverage survives even no model). LightGBM =
  strong tabular default, quantile objective for CQR, handles NaNs, CPU-fast.
  It's deliberately not the point.
- *"Your gamma is tuned."* → Tuned only on calibration, but better: DtACI
  aggregates over γ's with no tuning and is our best method anyway.
- *"Prefixes are correlated — your CIs are wrong."* → Rollout-level cluster
  bootstrap, in every table.
- *"Aborting changes the distribution."* → Yes, and we measured the effect in a
  toy closed loop: true coverage 0.92 → 0.83 once the guard's actions filter the
  stream, and the guard can't detect it from inside. Logged evaluation is the
  stated scope; the pilot turns the limitation into a research direction.
- *"Is 90% marginal coverage even useful for an operator?"* → Alone, no —
  which is why C3 converts intervals into a decision rule with a per-run
  false-abort guarantee, and C4 prices the outcome. The guarantee an operator
  actually consumes is "≤ δ of good runs killed."

---

## Glossary (one-liners)

**rollout** one recorded agent run · **prefix** first k turns of it · **x_t**
features at turn k · **y_t** true remaining tokens after turn k · **coverage**
fraction of intervals containing truth · **nominal / α** the promise (90% ⇔
α=0.1) · **marginal vs conditional** averaged-over-everything vs per-slice ·
**exchangeability** any ordering equally likely; conformal's only assumption ·
**split conformal** calibrate a residual quantile on held-out data ·
**q̂** the calibrated padding · **CQR** conformalized quantile regression ·
**pinball loss** what quantile regressors minimize · **ACI** online α-thermostat ·
**SPCI** sliding-window score recalibration · **DtACI** expert-weighted ACI, no
tuning · **Mondrian** separate calibration per group (we group by depth) ·
**Bonferroni** α/K per margin ⇒ joint valid · **copula method** shared empirical
rank level across resources · **censoring** label known only as a bound ·
**IPCW** inverse-probability-of-censoring weighting · **positivity** IPCW's
requirement that censoring isn't deterministic in x · **feasible / can_finish**
run succeeds within budget · **false abort** killing a feasible run ·
**cost-of-pass** spend ÷ correct answers · **leak** feature unknowable mid-run ·
**group split** train/cal/test by rollout · **mask-and-measure** hide recoverable
labels, calibrate as if censored, grade against truth.

---

## Answer key

**A1.** Agents burn real money on doomed runs; BAGEN showed stopping doomed runs
early recovers 28–64% of failed-run spend. The blocker is that the agent's own
budget estimates cover the truth only ~27–47% of the time, so no one can act on
them.
**A2.** Training-free means it wraps *any* agent (closed models included), costs
no GPU, can't degrade the agent's task skill, and carries a distribution-free
guarantee fine-tuning can't offer. BAGEN's own SFT+RL attempt stayed
miscalibrated — evidence the problem isn't model capacity.
**A3.** Live, the target depends on the agent's own future behavior (verbosity
now predicts spend later — the distribution is created by the policy). A log
freezes that future, so y is deterministic subtraction per prefix: ordinary
supervised data.
**A4.** `y = total_rollout_tokens − tokens_so_far`. Give the model
`total_rollout_tokens` and it can compute the answer exactly — perfect test
scores, zero deployment value, because at deployment the run isn't finished and
the field doesn't exist yet.
**A5.** They share the entire trajectory and its total. They are correlated, and
any prefix reveals its siblings' label almost completely — so statistical units
are rollouts, not rows: split by rollout, bootstrap by rollout.
**A6.** Conformal never trusts the model; it measures the model's own errors on
held-out data and pads by the 90th-percentile error. The new point's error is
exchangeable with the measured ones, so it exceeds that percentile ~10% of the
time — regardless of the model. A bad model shows up as wide intervals, never as
broken coverage.
**A7.** When it comes with useless width — unbounded intervals (ACI under shift:
13–50% infinite), or SWE-bench naive intervals 2–3× the data's own spread, or
the interval [0, ∞). Always report coverage *and* width.
**A8.** Calibration would contain prefixes of the same runs as test; since
siblings share the total, calibration has effectively seen test answers.
Coverage would look *great* — which is worse than an error because nothing
crashes; you'd ship fake validity.
**A9.** Marginal = averaged over all test prefixes; it permits systematic
failure on slices. Our own evidence: 0.87 marginal with 0.77 at k=1. Answer:
we measure conditional coverage explicitly and fix depth-conditioning with
Mondrian (k=1: 0.860→0.927); full conditional validity is provably impossible
distribution-free, so bucketed validity is the honest attainable target.
**A10.** Absres pads a symmetric constant everywhere, sized by the hardest
cases. CQR learns where y is uncertain (quantile band varies with x) and
conformal only pads the band's *escapes* — width goes where the data needs it.
**A11.** Thermostat: err too often → αₜ drops → wider intervals; cover too often
→ αₜ rises → tighter. Long-run average miscoverage is forced to α. If you cap
the interval at the largest calibration score, then under a hard shift every
point misses, αₜ sinks, but the interval can't grow past the cap — errors stay
1 forever and coverage never recovers (our unit test measured 0.01). The
unbounded fallback IS the guarantee's escape valve.
**A12.** No — ACI recovers 0.90 while emitting 13–50% unbounded intervals
(surrender); SPCI reaches 0.906–0.925 with 0% unbounded and moderate widths
(adaptation). Same coverage, completely different usefulness.
**A13.** "No labels on a new task" is really cold start, because every completed
run labels itself. The curve quantifies the cost: ~5–8 logged runs to reach
~0.9, and below that the finite-sample correction forces unbounded intervals —
the guard fails *safe*, never silently overconfident.
**A14.** It holds the information source constant: the agent's own per-turn
estimate, produced from the same prefix the agent saw. We add only a
calibration layer — no features, no training — and coverage goes 0.23–0.51 →
0.90–0.97. Whatever was missing, it wasn't knowledge; it was calibration.
**A15.** Independent 90% margins: P(all three) ≈ 0.9³ ≈ 0.73, and correlated
errors can push lower; measured joint was 0.80 vs target 0.90.
**A16.** Bonferroni buys validity with worst-case width (margins at 97–100%).
The copula level adapts to how the three errors actually co-move — tighter
margins at joint ≈ nominal. Valid-but-unusable vs slightly-riskier-but-sharp is
an operator choice; we provide both.
**A17.** The rule tests every prefix, so per-run false-abort probability
compounds across looks. But "aborted ⇔ min prefix score < τ" — one number per
run — so calibrating τ on the δ-quantile of feasible runs' *minimum* scores
controls the per-run rate at δ exactly, finite-sample corrected.
**A18.** On SWE-bench doom is *defined* as crossing the 7060-token cap, so the
cap is an oracle there — we say so and show it. Where doom comes from the task
(Sokoban: failure; Warehouse: infeasible configs), caps are dominated badly —
86% of doomed dollars saved at 0% false aborts vs ≤15% at 3–62%. Moral, stated
plainly: when doom is the cap, use the cap; anywhere else you need a guard.
**A19.** Savings (killing doomed runs early) vs forfeited passes (killing good
runs). Cost-of-pass divides by passes, so losing even a few successes raises
the denominator's price sharply — at Sokoban's short horizons the forfeits beat
the tiny savings and the guard rightly declines to help.
**A20.** Censored ⇒ the run overran ⇒ its true remaining-to-completion is
LARGE (larger than budget-left). Lower bounds get *easier* to satisfy on such
points; it's hi = pred + q̂ that gets violated — and calibrating q̂ without
those large-y points systematically under-covers exactly them.
**A21.** IPCW reweights observed (uncensored) samples by 1/P(uncensored|x) to
stand in for censored ones — which requires censored-like x's to be uncensored
*sometimes* (positivity). In our data feasibility is nearly a function of the
initial config, so P≈0 regions have no observed samples to upweight: weighting
cannot manufacture the missing tail. Publishable because it's a clean,
real-data counterexample to the default tool's core assumption — and it's what
motivates the gated (selective) design that replaces weighting entirely.
**A21b.** Rung 1's "bound" method achieved 0.998 coverage by pooling censored
bounds from ALL censored runs — including runs that died on a *different*
resource, whose cost-headroom bounds were large and false; the inflation was
borrowed, not earned. Resource attribution (rung 2) removed it, revealing time
as cleanly fixable (0.90 exact) and cost as unboundable-at-validity even by KM
(0.58) — which *forces* the gated design (rung 3, 0.92 on kept). It strengthens
the paper because the correction chain is visible, measured, and ends in a
method whose necessity is now proven rather than asserted.

---

*End of guide. If you can answer all 22 without looking, you're ready for the
conference room. Regenerate any number: `python -m budget_guard.run_coverage`,
`run_allruns`, `run_transfer`, `run_transfer_env`, `run_label_efficiency`,
`run_gap`, `run_multiresource`, `run_economic`, `run_economic_warehouse`,
`run_costofpass`, `run_censored`, `run_gated`, `run_final`. Wrapper demo:
`python examples/quickstart.py`. Current status + what's blocked:
`notes/current_state.md`.*
