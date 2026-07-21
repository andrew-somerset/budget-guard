"""scripts/run_overhead.py — the overhead row: per-step guard latency on CPU.

Measures the live-path cost of the shipped wrapper: ``BudgetGuard.step()`` per agent
turn (featurize + two LGBM quantile predicts + one window quantile), ``observe()``
per finished run, and the one-time ``from_logs()`` fit/calibration. Synthetic logs
only — overhead does not depend on BAGEN data. Writes tables/overhead.csv.

Usage: python scripts/run_overhead.py
"""
from __future__ import annotations

import os
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from budget_guard.guard import BudgetGuard


def synthetic_logs(n_runs: int = 120, seed: int = 0) -> pd.DataFrame:
    """Completed runs as an extractor-schema table (same shape as examples/quickstart)."""
    rng = np.random.default_rng(seed)
    rows = []
    for r in range(n_runs):
        per = rng.integers(80, 220, size=int(rng.integers(4, 9))).astype(float)
        total = float(per.sum())
        for k in range(1, len(per)):
            rows.append({
                "rollout_index": r, "sample_id": f"{r}_{k}", "k": k, "N": len(per),
                "tokens_so_far": float(per[:k].sum()), "total_rollout_tokens": total,
                "y": total - float(per[:k].sum()), "can_finish": True,
                "rollout_success": True, "per_turn_total": list(per[:k]),
            })
    return pd.DataFrame(rows)


def main(n_live_runs: int = 200, seed: int = 7) -> pd.DataFrame:
    t0 = time.perf_counter()
    guard = BudgetGuard.from_logs(synthetic_logs(), budget=1e9)  # budget high: never abort
    fit_seconds = time.perf_counter() - t0

    rng = np.random.default_rng(seed)
    step_ns: list[int] = []
    observe_ns: list[int] = []
    for _ in range(n_live_runs):
        guard.reset()
        for turn_tokens in rng.integers(80, 220, size=int(rng.integers(4, 9))).astype(float):
            t = time.perf_counter_ns()
            guard.step(turn_tokens)
            step_ns.append(time.perf_counter_ns() - t)
        t = time.perf_counter_ns()
        guard.observe()
        observe_ns.append(time.perf_counter_ns() - t)

    steps_us = np.asarray(step_ns, dtype=float) / 1e3
    observe_ms = np.asarray(observe_ns, dtype=float) / 1e6
    row = {
        "n_steps": len(steps_us),
        "step_us_median": float(np.median(steps_us)),
        "step_us_mean": float(steps_us.mean()),
        "step_us_p95": float(np.percentile(steps_us, 95)),
        "observe_ms_per_run_median": float(np.median(observe_ms)),
        "fit_seconds": fit_seconds,
        "python": platform.python_version(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
    }
    table = pd.DataFrame([row])
    os.makedirs("tables", exist_ok=True)
    table.to_csv("tables/overhead.csv", index=False)
    print(table.to_string(index=False))
    print(f"\nper-turn guard overhead: median {row['step_us_median']:.0f} us "
          f"(p95 {row['step_us_p95']:.0f} us) on CPU; "
          f"observe() {row['observe_ms_per_run_median']:.1f} ms per finished run; "
          f"one-time fit {fit_seconds:.1f} s")
    print("wrote tables/overhead.csv")
    return table


if __name__ == "__main__":
    main()
