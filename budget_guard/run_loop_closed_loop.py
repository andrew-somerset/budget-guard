"""Real-data oracle-vs-closed-loop replay for the generic loop guard.

Offline logs let us audit truths that a deployed guard would never observe after it
stops a run. This script reports both the audit view and the guard's self-measured view
on the self-selected runs it allowed to finish.
"""
from __future__ import annotations

from copy import deepcopy
import os

import numpy as np
import pandas as pd

from .data import ENVS, load_env
from .loop_datasets import token_traces_from_dataframe, warehouse_traces_from_dataframe
from .loop_evaluation import replay_traces, summarize_replay
from .loop_guard import LoopBudgetGuard
from .multiresource import load_warehouse
from .run_transfer_warehouse import SOURCE_PATH, TARGETS

WAREHOUSE_PROGRESS = ("current_cash_usd", "target_cash_usd", "cash_gap_usd")


def _closed_loop_metrics(records: pd.DataFrame) -> dict[str, float]:
    successful = records[records["successful"]]
    stopped_runs = set(records.loc[records["stopped"], "run_id"])
    completed = successful[~successful["run_id"].isin(stopped_runs)]
    audit_steps = successful.drop_duplicates(["run_id", "step"])
    self_steps = completed.drop_duplicates(["run_id", "step"])
    return {
        "audit_joint_coverage": float(audit_steps["joint_covered"].mean()),
        "self_measured_joint_coverage": float(self_steps["joint_covered"].mean())
        if len(self_steps)
        else np.nan,
        "successful_runs_observed_frac": float(
            successful["run_id"].nunique() - len(stopped_runs & set(successful["run_id"]))
        ) / max(successful["run_id"].nunique(), 1),
        **summarize_replay(records),
    }


def _scenario_rows(
    source,
    target,
    *,
    scenario: str,
    seed: int,
    progress_keys=(),
    window_rollouts: int = 10,
):
    initial = LoopBudgetGuard.from_traces(
        source,
        seed=seed,
        online=True,
        calibration_scheme="joint",
        window_rollouts=window_rollouts,
        progress_keys=progress_keys,
    )
    oracle = replay_traces(
        deepcopy(initial), target, obey_stop_recommendations=False
    )
    closed = replay_traces(
        deepcopy(initial), target, obey_stop_recommendations=True
    )
    return [
        {"scenario": scenario, "mode": "oracle", "seed": seed, **_closed_loop_metrics(oracle)},
        {"scenario": scenario, "mode": "closed_loop", "seed": seed, **_closed_loop_metrics(closed)},
    ]


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4), window_rollouts: int = 10):
    sokoban, _ = load_env("sokoban")
    swebench, _ = load_env("swebench")
    token_source = token_traces_from_dataframe(
        sokoban, budget=ENVS["sokoban"]["max_ctx"], run_prefix="sokoban"
    )
    token_target = token_traces_from_dataframe(
        swebench, budget=ENVS["swebench"]["max_ctx"], run_prefix="swebench"
    )
    warehouse_source = warehouse_traces_from_dataframe(
        load_warehouse(SOURCE_PATH, keep_censored=True), run_prefix="opus"
    )
    # Gemini is the hardest frozen Warehouse target in the generic validation and
    # therefore the most informative bounded closed-loop case.
    warehouse_target = warehouse_traces_from_dataframe(
        load_warehouse(TARGETS["gemini3.1"], keep_censored=True), run_prefix="gemini"
    )

    rows = []
    for seed in seeds:
        rows.extend(
            _scenario_rows(
                token_source,
                token_target,
                scenario="tokens:sokoban->swebench",
                seed=seed,
                window_rollouts=window_rollouts,
            )
        )
        rows.extend(
            _scenario_rows(
                warehouse_source,
                warehouse_target,
                scenario="warehouse:opus->gemini3.1",
                seed=seed,
                progress_keys=WAREHOUSE_PROGRESS,
                window_rollouts=window_rollouts,
            )
        )
    raw = pd.DataFrame(rows)
    numeric = [column for column in raw if column not in {"scenario", "mode", "seed"}]
    summary = raw.groupby(["scenario", "mode"], sort=False)[numeric].mean().reset_index()
    os.makedirs("tables", exist_ok=True)
    raw.to_csv("tables/loop_closed_loop_per_seed.csv", index=False)
    summary.to_csv("tables/loop_closed_loop.csv", index=False)
    display = [
        "scenario",
        "mode",
        "audit_joint_coverage",
        "self_measured_joint_coverage",
        "successful_runs_observed_frac",
        "false_stop_rate",
        "failed_run_catch_rate",
    ]
    print(summary[display].to_string(index=False))
    print("\nwrote tables/loop_closed_loop.csv, tables/loop_closed_loop_per_seed.csv")
    return summary


if __name__ == "__main__":
    main()
