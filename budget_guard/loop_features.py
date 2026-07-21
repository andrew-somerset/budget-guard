"""Generic, prefix-only features for task-independent agent-loop monitoring."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .loop_schema import ResourceSpec, RunFinish, RunStart, RunTrace, StepUsage


@dataclass(frozen=True)
class LoopDataset:
    """One row per non-terminal prefix across validated run traces."""

    X: pd.DataFrame
    y: pd.DataFrame
    groups: np.ndarray
    feasible: np.ndarray
    feasibility_observed: np.ndarray
    run_ids: np.ndarray
    step_counts: np.ndarray
    resource_names: tuple[str, ...]
    context_keys: tuple[str, ...]
    progress_keys: tuple[str, ...]


def _schema_signature(resources: Sequence[ResourceSpec]) -> tuple[tuple[str, str, str], ...]:
    return tuple((resource.name, resource.unit, resource.aggregation) for resource in resources)


def validate_trace_schemas(traces: Sequence[RunTrace]) -> tuple[str, ...]:
    if not traces:
        raise ValueError("at least one trace is required")
    expected = _schema_signature(traces[0].start.resources)
    for trace in traces[1:]:
        actual = _schema_signature(trace.start.resources)
        if actual != expected:
            raise ValueError(
                "all traces must use the same ordered resource names, units, and aggregation"
            )
    return tuple(item[0] for item in expected)


def prefix_feature_row(
    start: RunStart,
    steps: Sequence[StepUsage],
    *,
    context_keys: Sequence[str] = (),
    progress_keys: Sequence[str] = (),
) -> dict[str, float]:
    """Build features available at the current prefix—never terminal/future fields."""
    if not steps:
        raise ValueError("at least one completed step is required")
    row: dict[str, float] = {"step_count": float(len(steps))}
    for resource in start.resources:
        values = np.asarray([step.usage[resource.name] for step in steps], dtype=float)
        spent = float(values.sum())
        mean = float(values.mean())
        row[f"{resource.name}__budget"] = resource.budget
        row[f"{resource.name}__spent"] = spent
        row[f"{resource.name}__budget_left"] = resource.budget - spent
        row[f"{resource.name}__spent_fraction"] = spent / resource.budget
        row[f"{resource.name}__last"] = float(values[-1])
        row[f"{resource.name}__mean"] = mean
        row[f"{resource.name}__std"] = float(values.std()) if len(values) > 1 else 0.0
        row[f"{resource.name}__min"] = float(values.min())
        row[f"{resource.name}__max"] = float(values.max())
        row[f"{resource.name}__last3_mean"] = float(values[-3:].mean())
        row[f"{resource.name}__trend"] = float(values[-1] - mean)

    for key in context_keys:
        value = start.context.get(key, np.nan)
        row[f"context__{key}"] = float(value) if value is not None else np.nan
    for key in progress_keys:
        history = np.asarray(
            [step.progress.get(key, np.nan) for step in steps], dtype=float
        )
        finite = history[np.isfinite(history)]
        latest = float(finite[-1]) if len(finite) else np.nan
        first = float(finite[0]) if len(finite) else np.nan
        row[f"progress__{key}"] = latest
        row[f"progress__{key}__delta"] = latest - first if len(finite) else np.nan
        row[f"progress__{key}__rate"] = (
            (latest - first) / max(len(finite) - 1, 1) if len(finite) else np.nan
        )
    return row


def _trace_feasibility(trace: RunTrace) -> tuple[float, bool]:
    if not isinstance(trace.outcome, RunFinish):
        return np.nan, False
    totals = trace.totals
    assert totals is not None
    inside_budgets = all(
        totals[resource.name] <= resource.budget for resource in trace.start.resources
    )
    return float(trace.outcome.success and inside_budgets), True


def build_loop_dataset(
    traces: Iterable[RunTrace],
    *,
    context_keys: Sequence[str] = (),
    progress_keys: Sequence[str] = (),
) -> LoopDataset:
    """Convert traces to leak-free prefix features, targets, and rollout groups.

    Remaining-resource targets are defined only for successful, in-budget natural
    completions. Failed or aborted traces still produce feature rows for live replay and
    feasibility work, but their interval targets remain NaN rather than inventing the
    counterfactual resources needed for success.
    """
    traces = list(traces)
    resource_names = validate_trace_schemas(traces)
    rows: list[dict[str, float]] = []
    targets: list[dict[str, float]] = []
    groups: list[str] = []
    feasible: list[float] = []
    observed: list[bool] = []
    run_ids: list[str] = []
    step_counts: list[int] = []

    for trace in traces:
        feasibility, is_observed = _trace_feasibility(trace)
        totals = trace.totals if feasibility == 1.0 else None
        cumulative = {name: 0.0 for name in resource_names}
        # The terminal step has no future left to predict, matching the old extractors.
        for index, step in enumerate(trace.steps[:-1], start=1):
            for name in resource_names:
                cumulative[name] += float(step.usage[name])
            rows.append(
                prefix_feature_row(
                    trace.start,
                    trace.steps[:index],
                    context_keys=context_keys,
                    progress_keys=progress_keys,
                )
            )
            targets.append(
                {
                    name: totals[name] - cumulative[name] if totals is not None else np.nan
                    for name in resource_names
                }
            )
            groups.append(trace.start.run_id)
            feasible.append(feasibility)
            observed.append(is_observed)
            run_ids.append(trace.start.run_id)
            step_counts.append(index)

    if not rows:
        raise ValueError("traces must contain at least one run with two steps")
    X = pd.DataFrame(rows)
    y = pd.DataFrame(targets, columns=list(resource_names))
    return LoopDataset(
        X=X,
        y=y,
        groups=np.asarray(groups, dtype=object),
        feasible=np.asarray(feasible, dtype=float),
        feasibility_observed=np.asarray(observed, dtype=bool),
        run_ids=np.asarray(run_ids, dtype=object),
        step_counts=np.asarray(step_counts, dtype=int),
        resource_names=resource_names,
        context_keys=tuple(context_keys),
        progress_keys=tuple(progress_keys),
    )
