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

## Status / blockers
-
