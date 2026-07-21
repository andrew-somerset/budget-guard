"""Task-neutral loop guard demo: tokens + dollars + elapsed seconds, no BAGEN data."""
from __future__ import annotations

import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from budget_guard import (
    LoopBudgetGuard,
    ResourceLedger,
    ResourceSpec,
    RunFinish,
    RunStart,
    StepUsage,
)

RESOURCES = (
    ResourceSpec("tokens", "tokens", 1200),
    ResourceSpec("usd", "USD", 5),
    ResourceSpec("seconds", "seconds", 240),
)


def synthetic_history(n_runs: int = 80, seed: int = 0):
    """Three-resource completed histories; replace with your own event logs."""
    rng = np.random.default_rng(seed)
    traces = []
    for run in range(n_runs):
        success = run % 5 != 0
        ledger = ResourceLedger(
            RunStart(f"history-{run}", RESOURCES, {"difficulty": float(run % 3)})
        )
        for step in range(5):
            scale = 1.6 if not success else 1.0
            ledger.record(
                StepUsage(
                    str(step + 1),
                    {
                        "tokens": max(float(rng.normal(170 * scale, 12)), 0),
                        "usd": max(float(rng.normal(0.65 * scale, 0.04)), 0),
                        "seconds": max(float(rng.normal(30 * scale, 2)), 0),
                    },
                    {"subtasks_done": float(step + 1 if success else step // 2)},
                )
            )
        traces.append(ledger.finish(RunFinish(success)))
    return traces


def main() -> None:
    guard = LoopBudgetGuard.from_traces(
        synthetic_history(),
        context_keys=("difficulty",),
        progress_keys=("subtasks_done",),
        window_rollouts=10,
    )
    guard.start("live-task", RESOURCES, {"difficulty": 1.0})
    print("Monitoring one agent loop across tokens, USD, and elapsed seconds:\n")
    live_usage = [
        {"tokens": 180, "usd": 0.7, "seconds": 28},
        {"tokens": 220, "usd": 0.8, "seconds": 35},
        {"tokens": 310, "usd": 1.1, "seconds": 52},
        {"tokens": 340, "usd": 1.3, "seconds": 60},
    ]
    for index, usage in enumerate(live_usage, start=1):
        decision = guard.after_step(
            usage,
            {"subtasks_done": float(index)},
            step_id=str(index),
        )
        ranges = ", ".join(
            f"{name}=[{interval.lo:.1f}, {interval.hi:.1f}]"
            for name, interval in decision.intervals.items()
        )
        print(
            f"step {index}: {decision.action.value:12s} | {ranges} | "
            f"state={decision.state.value} | reasons={'; '.join(decision.reasons)}"
        )
        if decision.should_stop:
            guard.abort(decision.action.value)
            break
    else:
        guard.finish(True)
        print("\nRun finished naturally; its observed errors updated the calibration window.")


if __name__ == "__main__":
    main()
