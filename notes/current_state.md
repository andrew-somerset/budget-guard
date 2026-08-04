# budget-guard — current state & next steps

_Last updated 2026-07-21 (development branch)._

> **2026-07-21 correction (read first):** the single-resource online evaluation had a
> within-rollout label-revelation leak, now fixed (rollout-safe revelation everywhere +
> regression test). Corrected headlines: cross-env SPCI 0.10 → **0.80** recovery (not
> 0.90) at 0% unbounded; model-swap SPCI **0.66–0.89** (not 0.91–0.93); within-
> distribution and all frozen numbers unchanged; multi-resource adaptive joint
> (0.86–0.88) was already rollout-safe and stands. See robustness_progress.md
> 2026-07-21. **Body updated 2026-08-01** — transfer numbers below are the corrected,
> post-fix values, checked against `tables/transfer_env.csv` and
> `tables/transfer_swebench.csv`.

## Snapshot
Training-free, distribution-free **budget guards** for long-horizon LLM agents: online
conformal prediction wraps any logged-agent budget predictor with calibrated
remaining-budget intervals + an economic abort rule. CPU-only, built on BAGEN rollouts.
**Status: research complete and robustness-hardened; entering write-up.** Target: a
NeurIPS/ICML 2026 workshop (or COPA / AISTATS 2027 for the methods angle).

## What's done
- **Core contributions (C1–C4):** calibrated intervals that survive deployment shift
  (agent self-report 47% → ~0.90–0.92; frozen conformal collapses to 0.10 under cross-env
  shift while SPCI recovers to 0.80 at 0% unbounded); multi-resource joint coverage
  (0.42 → 0.95); economic stopping (86% of doomed-$ saved @ 0% false aborts on warehouse);
  cost-of-pass (−46%).
- **Methods contribution (censored conformal, rungs 1–3):** resource-specific
  ("which-budget-was-hit") bounds; a Kaplan–Meier survival diagnostic; and
  feasibility-gated (selective) intervals that restore cost coverage 0.46 → 0.92.
- **Robustness pass (9 items, all closed):** synthetic audit tests pinning the two
  load-bearing guarantees (nominal-on-clean; frozen-degrades / online-recovers under
  drift); conditional (by-depth) coverage with Mondrian closing the sokoban k=1 hole
  (0.860 → 0.927); a transfer-led headline figure with cluster-bootstrap CIs; a non-BAGEN
  generality smoke test; a label-efficiency curve (5–8 rollouts → ~0.90, fail-safe
  below); DtACI + constant-quantile baselines on by default; the closed-loop /
  counterfactual-free limitation (stated + toy pilot); a PI-ready censored-conformal
  proposal.
- **Artifact:** pip-installable `BudgetGuard` wrapper (`pip install -e .`) + a runnable
  no-data demo (`examples/quickstart.py`). A fresh-env install caught and fixed a missing
  scikit-learn dependency.
- **Reproducibility:** Python 3.12 venv + `scripts/fetch_bagen.py` (started as a ~105 MB
  minimal subset; now **~2.7 GB on disk** after the full multi-model set was downloaded
  for the breadth/transfer experiments; BAGEN revision + exact Python
  dependencies pinned; every headline number re-derived; full suite now has **65 passed /
  0 skipped** (exit 0; verified 2026-08-01 — the 2 former data-path skips now execute
  because the fetched data is present), plus Python 3.10/3.12 CI on both demos.
- **Containerized reproduction (2026-08-01):** `Dockerfile` + `make repro`. Base image
  pinned by digest, `linux/amd64` fixed, full transitive tree hash-locked in
  `requirements.lock.txt` (38 packages, up from 9 hand-pinned direct deps), single-thread
  numeric kernels for deterministic float summation order. **Validated:** regenerating
  `transfer_env` inside the container reproduces the macOS/arm64 host run with every
  coverage, CI bound and unbounded-fraction bit-identical; one `normalized_width` differs
  by 1 ULP (2.2e-16), the cross-architecture floor. So the reported numbers are not
  environment-sensitive. CI now builds the image, runs the suite in it, and fails if
  `requirements.lock.txt` drifts from `requirements-repro.in`.
- **Headline-number audit:** `scripts/check_headline_numbers.py` (`make check-numbers`)
  machine-checks 9 numbers quoted in these notes against the generated CSVs. Added after
  four stale figures were found here on 2026-08-01 (three pre-leak-fix transfer
  coverages sitting directly under a correction banner, plus a stale test count and data
  size). Prose cannot be diffed, so it rots silently; this makes it fail loudly.
- **Full breadth + model transfer:** all 19 token-budget model×environment runs now execute;
  SWE-bench model swap (**5 seeds since 2026-08-01**, was single-seed): frozen 0.64–0.89
  vs SPCI 0.66–0.89, both at 0% unbounded — i.e. comparable MEAN coverage. The separation
  is in variance, not level: frozen cov_std ≈ 0.18 (per-model spread up to 0.44 across
  five seeds) vs SPCI ≈ 0.01. See the 2026-08-01 entry in robustness_progress.md; the
  previously quoted "frozen 0.38–0.76" was seed 0, which sat near frozen's minimum on
  all four targets.
- **External-budget transfer + adaptive joint method (development):** Opus 4.7 → four
  Warehouse models initially gives frozen Bonferroni joint coverage 0.66–0.79. A new
  rollout-safe recent-error window updates all three resource margins plus their shared
  empirical-copula rank, raising joint coverage to 0.86–0.88 overall and 0.87–0.90 in
  the late half (five seeds; every rollout-cluster 90% CI includes 0.90; 0% unbounded).
- **Generic loop-engineering wrapper (development):** task-neutral resource/event schema,
  validated ledger + JSONL, generic prefix features, stateful `LoopBudgetGuard`, feasibility
  gate, replaceable intervention policy, delayed-usage correction, artifact checksum/
  metadata, and dependency-free OpenAI/LangChain/mapping telemetry adapters. The same
  live core now replays token, Warehouse, and independent sequential-text traces.
- **Generic robustness evidence:** five-seed default-10 online-joint coverage = 0.912 on
  Sokoban→SWE-bench tokens and 0.928–0.970 across four Warehouse model swaps (corrected
  2026-08-02: exact warehouse labels + a stale-checkpoint fix — see robustness log; now with
  rollout-cluster 90% CIs), with 0–3.1% automatic false stops and 71–78% failed-run
  catches. A 200-run order/window stress grid picks window=10 for stability; 5 fails safe,
  20–40 adapt slower on token shift. **Self-audit caveat:** at window=10 the operative
  conformal level is ~1.0, i.e. the joint qhat is the componentwise sample maximum
  (worst-of-window), not a calibrated 0.90 interval; trajectory coverage is below nominal
  (0.80–0.85) under shift; the per-resource baseline is structurally +inf at that window;
  and this rollout-max online method differs from the per-prefix
  `multiresource.adaptive_joint_qhats`. Unify the two calibrators + revisit the window
  before any headline claim. Five-seed closed-loop and oracle replay match under the
  conservative default because no successful run is auto-stopped.

## What's blocked (documented, not skipped)
- **PI-blocked** — which censored-conformal guarantee to claim (selective-on-kept vs
  marginal); the next methods increment (gated-IPCW / positivity restoration — proposal
  in `notes/robustness_progress.md`); whether adaptive joint calibration should be joined
  to the feasibility gate for censored/doomed Warehouse runs; and whether the by-depth
  cut belongs on the warehouse tables.
- **Evidence-blocked** — no second independent agent benchmark and no anonymized live/
  production pilot logs are available here. The source-text path is explicitly a pipeline
  smoke test, not external agent-domain validation.

## Next steps (prioritized)
1. **PI meeting** — sign off on (a) the censored-conformal guarantee framing + the
  gated-IPCW next increment, (b) whether to connect adaptive joint calibration to the
  feasibility gate, and (c) the target venue. These gate the methods framing.
2. **Independent validation / pilot** — collect one coding or browser-agent dataset through
  the generic JSONL/adapters, then run the unchanged validation/closed-loop harness. This
  is a data/resource task; do not relabel the source-text smoke test as agent evidence.
3. **Write-up** — 4-pager led by the transfer figure; add the internal-vs-external contrast
  (token shift recovers to 0.66–0.89 cross-model and 0.80 cross-env, both at 0%
  unbounded; Warehouse joint shift to 0.86–0.88 overall) — but lead the model-swap
  result with the VARIANCE claim, not a level claim (see 2026-08-01 entry);
  methods section around censored rungs 1–3 + rollout-safe adaptive joint calibration;
  related-work table + unresolved citations.
4. **Artifact release** — replace the placeholder LICENSE holder, prepare an anonymized
  submission repository, and archive the exact release/data revision for a permanent DOI.
5. **Submit** — NeurIPS 2026 workshop (~Oct; watch the slate confirmed ~Sep 29); consider
   COPA / AISTATS 2027 for the methods angle. Submit fast — the BAGEN team targets
   NeurIPS 2026 main with public code (scoop risk).

## Where things live
- Per-item robustness log + reproduce commands: `notes/robustness_progress.md`
- Strategy + "Robustness pass — results": `notes/positioning.md`
- Weekly research log (weeks 1–6, consolidated): `notes/research_log.md`
- Wrapper + demo: `budget_guard/guard.py`, `examples/quickstart.py`, `README.md`
- Data fetch: `scripts/fetch_bagen.py`
