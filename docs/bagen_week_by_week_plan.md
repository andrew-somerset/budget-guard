# Budget-Guard Project — Week-by-Week Plan (your setup)

> Personal planning doc. Edit freely; check boxes as you go.

---

## 0. The project in plain English (read this first)

**The finding (BAGEN, arXiv:2606.00198).** Frontier LLM agents are bad at knowing how much
*budget* they have left mid-task — tokens, money, time, storage. BAGEN showed three things:
1. Agents can't reliably estimate their own remaining budget partway through a task.
2. Knowing it is *actionable*: stopping doomed runs early saves 28–64% on failed runs.
3. The blocker is **calibration** — even after SFT+RL training, the agent's predicted
   budget interval contains the true value only **47%** of the time (you'd want ~90%).

**Your idea (the budget guard).** Wrap *any* agent loop with a lightweight monitor that, at
each step, outputs a **calibrated interval** on remaining budget — *without fine-tuning the
LLM* — using **online conformal prediction** (a statistical method that gives coverage
guarantees even when the data drifts over time). Then add an **economic stopping rule** and a
**cost-per-correct-answer** evaluation.

**Conformal prediction in one sentence.** A wrapper that turns any point prediction into an
*interval with a guaranteed hit-rate*, by calibrating on held-out residuals. "Online" conformal
(ACI/SPCI) keeps that guarantee even when the target drifts along a trajectory.

**The four contributions.**
- **C1 — AdaptiveBudgetCP:** training-free calibrated remaining-budget intervals (raise 47% → 80–90%).
- **C2 — Multi-resource:** joint intervals over {tokens, $, time} on the Warehouse env (the hard-to-scoop part).
- **C3 — Economic stopping:** a formal expected-cost "abort or continue?" rule.
- **C4 — Cost-of-Pass for agents:** dollars-per-correct-answer over whole trajectories.

**What you actually work on.** *Logged* agent trajectories. At each prefix (partial trajectory)
you have features `x_t` (cost so far, etc.) and the true remaining budget `y_t` (known because
the run is logged). You fit interval predictors and check whether they cover the truth at the
promised rate. **This is all CPU Python — no GPU, no `verl`, no Unix needed.**

**Understanding self-check (you "get it" when you can answer):**
- Why is `y_t` "online and partly self-induced," and why does using *logged* rollouts dodge that?
- Why does plain split-conformal under-cover here? (temporal drift → exchangeability breaks)
- Why must you split calibration/test **by rollout**, never by prefix?

---

## 1. Your three compute contexts

| Tag | Machine | Best for |
| --- | --- | --- |
| **[W]** | Windows (work, downtime chunks) | Reading + CPU Python: the offline harness, conformal lib, experiments, figures, writing. The bulk of the work. |
| **[M]** | Mac (personal, evenings/weekends) | Same CPU work + "home base" for the git repo + the only place to *try* the official `verl` harness import + driving Colab. |
| **[C]** | Google Colab (free, on-demand) | The `verl`/CUDA appliance. One-time official reproduction + validation; GPU training in Weeks 7–8. Visited, not lived in. |
| **[Any]** | — | Reading / writing / thinking. |

**The glue = Git.** A private `budget-guard` repo. Push from Windows, pull on Mac, and have
Colab `git pull` it for the fidelity check. Your code lives in `budget_guard/`, cleanly
separable from BAGEN.

---

## 2. Six-week plan — exact tasks

All new code lives in a `budget_guard/` package:
`extract.py · features.py · split.py · conformal.py · metrics.py · multiresource.py ·
economic.py · costofpass.py` + `run_*.py` drivers that write to `figures/` and `tables/`.
Tags: [W]=Windows work-downtime · [M]=Mac · [C]=Colab · [Any].

### Week 1 — Understand + env + extractor + data dictionary
**Done when:** a `(x_t, y_t)` table you trust, matching official `y_t` with 0 mismatches.
- [ ] [Any] Read BAGEN (2606.00198) intro + the results table showing 47% coverage; read Angelopoulos–Bates "Gentle Introduction to Conformal Prediction" §1–4; write the 3 self-check answers from §0.
- [ ] [W] Install Miniconda → `conda create -n budget python=3.12` → `pip install` the CPU stack.
- [ ] [M] Create the private `budget-guard` repo; clone; branch `main`.
- [ ] [W] Write `budget_guard/extract.py` (NO `ragen` import). One row per prefix: `rollout_index, k, N, tokens_so_far, total_rollout_tokens, y, can_finish, rollout_success`.
- [ ] [W] Run on `_smoke/sokoban_dialogues.json`; assert `y == max(0, total_rollout_tokens − tokens_so_far)` and `y` non-increasing in `k`; write `data_dictionary.md`.
- [ ] [C] Run the official `DRY_RUN` smoke + 1 tiny API eval; diff `actual_remaining_total_tokens` vs your extractor on ≥20 prefixes.
- **Deliverable:** `extract.py` + `data_dictionary.md`; **0 mismatches**; 1 reproduced BAGEN number in `notes/week1.md`.

### Week 2 — Features + harness + the gap figure
**Done when:** a figure proving naive conformal under-covers (<0.80 at nominal 0.90).
- [ ] [W] `features.py:build_xy(df) -> (X, y, groups)` (legal features only; assert no leaks).
- [ ] [W] `split.py:group_split(df, fracs=(.5,.25,.25), seed=0)` by `rollout_index`; disjoint.
- [ ] [W] `conformal.py`: `split_conformal_absres(...)` + `cqr_split(...)`, both `alpha=0.1`.
- [ ] [W] `metrics.py`: `marginal_coverage`, `mean_width`, `normalized_width`.
- [ ] [W] `run_gap.py` on Sokoban → `figures/gap_sokoban.png` (0.90 line vs naive vs CQR).
- **Deliverable:** `figures/gap_sokoban.png` with naive coverage **<0.80** + a paragraph in `notes/week2.md`.

### Week 3 — Online conformal (C1) + KILL CHECK
**Done when:** ACI-CQR ≈ nominal on ≥1 env and beats split-CQR — else reposition.
- [ ] [W] `conformal.py` add `aci_cqr(..., gamma)` + `spci(..., window=100)`.
- [ ] [W] Tune `gamma ∈ {.005, .01, .02, .05}` on CAL trajectories only.
- [ ] [W] `run_coverage.py` over **Sokoban, SWE-bench, Search-R1** → `figures/coverage_main.png` + `tables/coverage.csv`.
- [ ] [W] `notes/positioning.md`: how you differ from BAGEN / MiCP / CCPO.
- **GO / NO-GO:** within **±0.03 of 0.90** AND beating split-CQR on ≥1 env, with **≥0.65** somewhere. Else escalate.

### Week 4 — C2 multi-resource + C3 economic stop
- [ ] [W] Extend `extract.py` for **Warehouse** → per-prefix `y` for {tokens, money, time}.
- [ ] [W] `multiresource.py`: `bonferroni_joint(...)` + `copula_conformal(...)` → `figures/joint_vs_marginal.png`.
- [ ] [W] `economic.py`: `calibrate_feasibility`, `stopping_rule`, `frontier` → `figures/abort_frontier.png`.
- **Deliverable:** both figures; abort frontier dominates BAGEN's threshold point.

### Week 5 — C4 cost-of-pass + ablations
- [ ] [W] `costofpass.py:trajectory_cost_of_pass` for {agent, agent+guard, hard cap} → `figures/cost_of_pass.png`.
- [ ] [W] `run_ablations.py` → `tables/ablations.csv`.
- **Deliverable:** cost-of-pass frontier + full ablation table.

### Week 6 — Freeze + write-up + submit
- [ ] [W] Re-run with fixed seeds → `figures/final/`. Headlines: `coverage_main`, `abort_frontier`, `cost_of_pass`.
- [ ] [W/M] Draft the 4-pager + related-work table.
- [ ] [M] `README.md` + pinned `requirements.txt` + `pytest` on `extract.py`.
- [ ] [Any] Mentor review → submit to a NeurIPS 2026 workshop; tag `v1-submission`.

---

## 3. The data dictionary (faithful, from `ragen/env/token_estimation/env.py`)
- **Unit = a "prefix sample."** Rollout with `N` usable turns → `N−1` samples, `k = 1…N−1`.
- **Target `y_t`** = `max(0, total_rollout_tokens − cum_tokens_through_k)`.
- **Feasibility** = `rollout_success AND total_rollout_tokens ≤ max_context_window_tokens`.
- **Legal features** = `k`, `tokens_so_far`, per-turn usage 1…k → rolling stats. Optional self-estimate.
- **LEAK** = `total_turns`, `relative_progress` (k/N), `y`, `total_rollout_tokens`, `rollout_success`.
- **Split** = by rollout, never by prefix.

---

## 4. Honest risks
- **Scoop risk:** BAGEN team targets NeurIPS 2026 with public code. Moat is C2+C3+C4, not C1 alone.
- **Kill criterion (Week 3):** if no method clears ~65% coverage at reasonable sharpness, reposition early.
- **Your setup's one gap:** the official `verl` harness needs Colab/a teammate — a one-time check, not a blocker.

## 5. Definition of done
Three figures hold up: coverage beats the 47% line, a savings/false-abort frontier that
dominates the heuristic, and a cost-of-pass frontier — written up and submitted to a workshop.
