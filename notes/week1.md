# Week 1 — notes & deliverables

## Self-check answers (write 1–2 sentences each)
1. Why is `y_t` online / partly self-induced, and why do logged rollouts make it tractable?
   -
2. Why does plain split-conformal under-cover here?
   -
3. Why split by rollout, never by prefix?
   -

## Reproduced BAGEN number (from Colab DRY_RUN / API eval)
- env: sokoban
- metric:
- value:
- date:

## Colab fidelity check
- extractor `y_t` vs official `actual_remaining_total_tokens`: mismatches = ___ (target 0)

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
- [todo — you] Readings + 3 self-check answers; Colab fidelity check (extractor `y_t` vs official); 1 reproduced BAGEN number.
- [note] `extract.py` uses raw per-turn totals; if the Colab diff shows mismatches on real data, port `_convert_request_usage_to_turn_usage` (history-excluded usage).
