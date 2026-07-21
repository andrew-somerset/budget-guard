"""Framework-neutral replay and closed-loop evaluation for ``LoopBudgetGuard``."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from .loop_guard import LoopBudgetGuard
from .loop_schema import RunTrace
from .metrics import rollout_bootstrap_mean_ci


def replay_traces(
    guard: LoopBudgetGuard,
    traces: Iterable[RunTrace],
    *,
    obey_stop_recommendations: bool = False,
) -> pd.DataFrame:
    """Replay traces through the live API and return auditable per-prefix records.

    In oracle replay, recommendations are recorded but every run reaches its observed
    terminal outcome. In closed-loop replay, PAUSE/ABORT recommendations stop the run and
    therefore withhold its unobserved future completion label from online calibration.
    """
    rows = []
    for trace in traces:
        guard.start(trace.start.run_id, trace.start.resources, trace.start.context)
        totals = trace.totals
        cumulative = {name: 0.0 for name in trace.resource_names}
        stopped = False
        for index, step in enumerate(trace.steps, start=1):
            decision = guard.after_step(step)
            operative_level = guard.last_operative_level
            for name in trace.resource_names:
                cumulative[name] += float(step.usage[name])
            # The terminal step has no future target and is excluded from coverage.
            if index < len(trace.steps):
                covered_all = True
                resource_records = []
                for name in trace.resource_names:
                    truth = (
                        totals[name] - cumulative[name]
                        if trace.successful and totals is not None
                        else np.nan
                    )
                    interval = decision.intervals[name]
                    covered = (
                        bool(interval.lo <= truth <= interval.hi)
                        if np.isfinite(truth)
                        else np.nan
                    )
                    if np.isfinite(truth):
                        covered_all &= bool(covered)
                    resource_records.append(
                        {
                            "run_id": trace.start.run_id,
                            "step": index,
                            "successful": trace.successful,
                            "resource": name,
                            "truth": truth,
                            "lo": interval.lo,
                            "hi": interval.hi,
                            "covered": covered,
                            "joint_covered": np.nan,
                            "action": decision.action.value,
                            "reasons": "|".join(decision.reasons),
                            "state": decision.state.value,
                            "finish_probability": decision.finish_probability,
                            "evidence_runs": decision.evidence_runs,
                            "operative_level": operative_level,
                            "stopped": False,
                        }
                    )
                if trace.successful:
                    for record in resource_records:
                        record["joint_covered"] = covered_all
                rows.extend(resource_records)

            # A recommendation after the terminal step cannot prevent a completion
            # that has already happened. Ignoring this distinction fabricates label
            # censoring and biases closed-loop calibration.
            if (
                obey_stop_recommendations
                and decision.should_stop
                and index < len(trace.steps)
            ):
                guard.abort(decision.action.value, cumulative)
                stopped = True
                for record in rows:
                    if record["run_id"] == trace.start.run_id and record["step"] == index:
                        record["stopped"] = True
                break
        if not stopped:
            if trace.naturally_finished:
                assert totals is not None
                guard.finish(trace.successful, totals)
            else:
                guard.abort("historically_aborted")
    return pd.DataFrame(rows)


def summarize_replay(records: pd.DataFrame) -> dict[str, float]:
    if records.empty:
        return {}
    successful = records[records["successful"]]
    unique_steps = successful.drop_duplicates(["run_id", "step"]).copy()
    per_run = records.drop_duplicates("run_id")
    # Project ground rule #4: coverage numbers carry a
    # rollout-cluster bootstrap CI, never a per-prefix binomial one. Prefixes of one
    # run are correlated, and at small windows the joint qhat is the sample max, so the
    # honest spread across runs matters more than the point estimate.
    ci_lo, ci_hi = (
        rollout_bootstrap_mean_ci(
            unique_steps["joint_covered"].to_numpy(dtype=float),
            unique_steps["run_id"].to_numpy(),
        )
        if not unique_steps.empty
        else (float("nan"), float("nan"))
    )
    stop_by_run = records.groupby("run_id")["action"].apply(
        lambda values: any(value in {"pause", "abort"} for value in values)
    )
    success_by_run = records.groupby("run_id")["successful"].first()
    result = {
        "joint_prefix_coverage": float(unique_steps["joint_covered"].mean()),
        "joint_prefix_coverage_ci_lo": ci_lo,
        "joint_prefix_coverage_ci_hi": ci_hi,
        "trajectory_joint_coverage": float(
            unique_steps.groupby("run_id")["joint_covered"].all().mean()
        ),
        "operative_level": float(unique_steps["operative_level"].mean())
        if "operative_level" in unique_steps
        else float("nan"),
        "false_stop_rate": float(stop_by_run[success_by_run].mean())
        if success_by_run.any()
        else np.nan,
        "failed_run_catch_rate": float(stop_by_run[~success_by_run].mean())
        if (~success_by_run).any()
        else np.nan,
        "n_runs": float(len(per_run)),
    }
    for resource, group in successful.groupby("resource"):
        result[f"coverage__{resource}"] = float(group["covered"].mean())
        finite = np.isfinite(group["hi"])
        result[f"unbounded__{resource}"] = float((~finite).mean())
        result[f"median_width__{resource}"] = float(
            np.median((group.loc[finite, "hi"] - group.loc[finite, "lo"]))
        ) if finite.any() else np.inf
    return result
