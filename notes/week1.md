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
