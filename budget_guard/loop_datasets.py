"""Adapters from existing research tables into the generic loop event schema."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping

import pandas as pd

from .extract import _rough_text_token_count
from .loop_schema import ResourceLedger, ResourceSpec, RunFinish, RunStart, RunTrace, StepUsage
from .multiresource import RESOURCES


def token_traces_from_dataframe(
    df: pd.DataFrame,
    *,
    budget: float,
    run_prefix: str = "tokens",
    context: Mapping[str, Any] | None = None,
) -> list[RunTrace]:
    """Reconstruct complete one-resource traces from an extractor prefix table."""
    traces: list[RunTrace] = []
    for rollout, group in df.sort_values(["rollout_index", "k"]).groupby("rollout_index"):
        last = group.iloc[-1]
        per = [float(value) for value in last["per_turn_total"]]
        # Extractor rows stop at k=N-1; the final remaining target is the final turn.
        final_turn = float(last["y"])
        per.append(final_turn)
        start = RunStart(
            f"{run_prefix}-{rollout}",
            (ResourceSpec("tokens", "tokens", budget),),
            dict(context or {}),
        )
        ledger = ResourceLedger(start)
        for index, value in enumerate(per, start=1):
            ledger.record(StepUsage(str(index), {"tokens": value}))
        total = float(last["total_rollout_tokens"])
        traces.append(
            ledger.finish(
                RunFinish(bool(last["can_finish"]), {"tokens": total})
            )
        )
    return traces


def warehouse_traces_from_dataframe(
    df: pd.DataFrame,
    *,
    run_prefix: str = "warehouse",
) -> list[RunTrace]:
    """Convert ``load_warehouse(..., keep_censored=True)`` output to generic traces.

    Time spend is exact. Warehouse and cost spend are the same week-proportional
    interpolation already documented by ``load_warehouse``; this converter does not add
    a new approximation. A final terminal step bridges the last replayed prefix to each
    recorded realized total.
    """
    traces: list[RunTrace] = []
    order_cols = ["rollout_index", "completed_turns"]
    for rollout, group in df.sort_values(order_cols).groupby("rollout_index"):
        group = group.reset_index(drop=True)
        first = group.iloc[0]
        specs = tuple(
            ResourceSpec(resource, resource, float(first[f"budget_{resource}"]))
            for resource in RESOURCES
        )
        start = RunStart(f"{run_prefix}-{rollout}", specs, {"task_family": "warehouse"})
        ledger = ResourceLedger(start)
        previous = {resource: 0.0 for resource in RESOURCES}
        for _, row in group.iterrows():
            usage = {}
            for resource in RESOURCES:
                spent = float(row[f"spent_{resource}"])
                delta = spent - previous[resource]
                if delta < -1e-8:
                    raise ValueError(f"{resource} cumulative spend decreased")
                usage[resource] = max(delta, 0.0)
                previous[resource] = spent
            ledger.record(
                StepUsage(
                    str(int(row["completed_turns"])),
                    usage,
                    {
                        "current_cash_usd": float(row["current_cash_usd"]),
                        "target_cash_usd": float(row["target_cash_usd"]),
                        "cash_gap_usd": float(row["current_cash_usd"] - row["target_cash_usd"]),
                    },
                )
            )
        totals = {resource: float(group.iloc[-1][f"total_{resource}"]) for resource in RESOURCES}
        terminal_usage = {
            resource: max(totals[resource] - previous[resource], 0.0)
            for resource in RESOURCES
        }
        last_progress = dict(ledger.steps[-1].progress)
        ledger.record(StepUsage("terminal", terminal_usage, last_progress))
        success = bool(first["can_finish"]) and not bool(first["censored"])
        traces.append(ledger.finish(RunFinish(success, totals)))
    return traces


def text_file_traces(
    paths: list[str | Path],
    *,
    budget: float = 4000,
    min_steps: int = 4,
    max_steps: int = 40,
    min_total: int = 50,
    max_total: int = 4000,
    run_prefix: str = "text",
) -> list[RunTrace]:
    """Treat blank-line-delimited files as real measured sequential-text sessions.

    This is an independent pipeline smoke test, not an agent-deployment benchmark.
    """
    traces = []
    for path in paths:
        source = Path(path)
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        per = [
            _rough_text_token_count(block)
            for block in re.split(r"\n\s*\n", text)
            if block.strip()
        ]
        per = [value for value in per if value > 0]
        total = int(sum(per))
        if not (min_steps <= len(per) <= max_steps and min_total <= total <= max_total):
            continue
        ledger = ResourceLedger(
            RunStart(
                f"{run_prefix}-{len(traces)}",
                (ResourceSpec("tokens", "tokens", budget),),
                {"source_suffix": source.suffix},
            )
        )
        for index, value in enumerate(per, start=1):
            ledger.record(StepUsage(str(index), {"tokens": float(value)}))
        traces.append(ledger.finish(RunFinish(total <= budget, {"tokens": float(total)})))
    return traces
