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
