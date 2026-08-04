"""Order/window sensitivity for the generic adaptive joint loop guard.

Uses one fixed source split and repeatedly permutes deployment rollout order. This tests
whether recovery is a convenient-order artifact rather than a stable property.
"""
from __future__ import annotations

from copy import deepcopy
import os

import numpy as np
import pandas as pd

from .data import ENVS, load_env
from ._checkpoint import resume_allowed, write_fingerprint
from .loop_datasets import token_traces_from_dataframe, warehouse_traces_from_dataframe
from .loop_evaluation import replay_traces, summarize_replay
from .loop_guard import LoopBudgetGuard
from .multiresource import load_warehouse
from .run_transfer_warehouse import SOURCE_PATH, TARGETS

WINDOWS = (5, 10, 20, 40)
ORDER_SEEDS = tuple(range(10))
WAREHOUSE_PROGRESS = ("current_cash_usd", "target_cash_usd", "cash_gap_usd")


def _permuted(traces, seed: int):
    order = np.random.default_rng(seed).permutation(len(traces))
    return [traces[index] for index in order]


def _run_scenario(
    source,
    target,
    *,
    scenario: str,
    windows=WINDOWS,
    order_seeds=ORDER_SEEDS,
    progress_keys=(),
):
    rows = []
    for window in windows:
        initial = LoopBudgetGuard.from_traces(
            source,
            seed=0,
            online=True,
            calibration_scheme="joint",
            window_rollouts=window,
            progress_keys=progress_keys,
        )
        for order_seed in order_seeds:
            guard = deepcopy(initial)
            records = replay_traces(
                guard, _permuted(target, order_seed), obey_stop_recommendations=False
            )
            rows.append(
                {
                    "scenario": scenario,
                    "window_rollouts": window,
                    "order_seed": order_seed,
                    **summarize_replay(records),
                }
            )
    return rows


def main(
    windows: tuple[int, ...] = WINDOWS,
    order_seeds: tuple[int, ...] = ORDER_SEEDS,
    resume: bool = False,
):
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
    warehouse_targets = {
        model: warehouse_traces_from_dataframe(
            load_warehouse(path, keep_censored=True), run_prefix=model
        )
        for model, path in TARGETS.items()
    }

    rows = _run_scenario(
        token_source,
        token_target,
        scenario="tokens:sokoban->swebench",
        windows=windows,
        order_seeds=order_seeds,
    )
    for model, target in warehouse_targets.items():
        rows.extend(
            _run_scenario(
                warehouse_source,
                target,
                scenario=f"warehouse:opus->{model}",
                windows=windows,
                order_seeds=order_seeds,
                progress_keys=WAREHOUSE_PROGRESS,
            )
        )

    raw = pd.DataFrame(rows)
    checkpoint = "tables/loop_stress_raw.csv"
    # keep="last" below means freshly computed rows always win, but prior rows for
    # (scenario, window, seed) combos NOT recomputed this run would survive a code
    # change untouched — so stale-source checkpoints are refused outright.
    if resume and resume_allowed(checkpoint):
        prior = pd.read_csv(checkpoint)
        raw = pd.concat([prior, raw], ignore_index=True).drop_duplicates(
            ["scenario", "window_rollouts", "order_seed"], keep="last"
        )
    metrics = [
        "joint_prefix_coverage",
        "trajectory_joint_coverage",
        "false_stop_rate",
        "failed_run_catch_rate",
    ]
    summary = raw.groupby(["scenario", "window_rollouts"], sort=False).agg(
        **{f"{metric}_mean": (metric, "mean") for metric in metrics},
        **{f"{metric}_min": (metric, "min") for metric in metrics},
        **{f"{metric}_max": (metric, "max") for metric in metrics},
    ).reset_index()
    os.makedirs("tables", exist_ok=True)
    raw.to_csv("tables/loop_stress_raw.csv", index=False)
    write_fingerprint("tables/loop_stress_raw.csv")
    summary.to_csv("tables/loop_stress.csv", index=False)
    print(summary.to_string(index=False))
    print("\nwrote tables/loop_stress.csv, tables/loop_stress_raw.csv")
    return summary


if __name__ == "__main__":
    main(resume=True)
