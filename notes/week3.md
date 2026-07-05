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
