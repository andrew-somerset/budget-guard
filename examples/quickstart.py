"""examples/quickstart.py — a runnable, no-data BudgetGuard demo.

Builds a handful of synthetic "completed runs" (per-turn token counts), calibrates the
guard, then streams a fresh live run turn-by-turn. Needs only numpy/pandas/lightgbm —
no BAGEN data, no GPU, no API. Run:  python examples/quickstart.py
"""
import numpy as np
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from budget_guard.guard import BudgetGuard


def synthetic_logs(n_runs: int = 120, seed: int = 0) -> pd.DataFrame:
    """Completed runs as an extractor-schema table: one row per prefix (k=1..N-1)."""
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


def main() -> None:
    guard = BudgetGuard.from_logs(synthetic_logs(), budget=900.0)
    print("Calibrated a training-free BudgetGuard on 120 synthetic runs (budget=900).\n")

    rng = np.random.default_rng(7)
    live_run = rng.integers(120, 260, size=6).astype(float)  # a heavy live run
    guard.reset()
    for turn_tokens in live_run:
        step = guard.step(turn_tokens)
        flag = "   <-- ABORT: projected spend exceeds budget" if step.abort else ""
        print(f"turn {step.k}: spent {step.spent:6.0f} | remaining in "
              f"[{step.lo:6.0f}, {step.hi:6.0f}]{flag}")
        if step.abort:
            break
    else:
        guard.observe()
        print("\nrun finished within budget; folded its labels back into calibration.")


if __name__ == "__main__":
    main()
