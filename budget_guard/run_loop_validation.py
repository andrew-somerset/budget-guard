"""Cross-family validation of the task-neutral ``LoopBudgetGuard``.

Uses the same live lifecycle and model code for:
1. Sokoban -> SWE-bench token-budget shift (BAGEN internal budget),
2. Opus -> four-model Warehouse shift (BAGEN external multi-resource budget),
3. a local non-BAGEN sequential-source-text pipeline smoke test.

The source-text case is not an agent benchmark; it checks software generality only.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import os

import numpy as np
import pandas as pd

from .data import ENVS, load_env
from .loop_datasets import (
    text_file_traces,
    token_traces_from_dataframe,
    warehouse_traces_from_dataframe,
)
from .loop_evaluation import replay_traces, summarize_replay
from .loop_guard import LoopBudgetGuard
from .multiresource import load_warehouse
from .run_transfer_warehouse import SOURCE_PATH, TARGETS

METHODS = {
    # Labels are explicit about the windowing so this rollout-max online method is not
    # conflated with the per-prefix multiresource.adaptive_joint_qhats of the same idea.
    "frozen joint (rollout-max)": {"online": False, "calibration_scheme": "joint"},
    "online per-resource (rollout-max)": {"online": True, "calibration_scheme": "independent"},
    "online joint (rollout-max)": {"online": True, "calibration_scheme": "joint"},
}
WAREHOUSE_PROGRESS = ("current_cash_usd", "target_cash_usd", "cash_gap_usd")


def _fit_methods(
    source,
    *,
    seed: int,
    progress_keys=(),
    window_rollouts: int = 10,
) -> dict[str, LoopBudgetGuard]:
    return {
        method: LoopBudgetGuard.from_traces(
            source,
            seed=seed,
            progress_keys=progress_keys,
            window_rollouts=window_rollouts,
            **options,
        )
        for method, options in METHODS.items()
    }


def _evaluate_fitted(
    guards: dict[str, LoopBudgetGuard],
    target,
    *,
    scenario: str,
    seed: int,
):
    rows = []
    for method, initial_guard in guards.items():
        # Replay mutates online windows, so every target starts from an identical
        # source-calibrated state rather than inheriting another target's labels.
        guard = deepcopy(initial_guard)
        records = replay_traces(guard, target, obey_stop_recommendations=False)
        rows.append({"scenario": scenario, "method": method, "seed": seed, **summarize_replay(records)})
    return rows


def _write_tables(rows: list[dict]) -> pd.DataFrame:
    per_seed = pd.DataFrame(rows)
    numeric = [
        column for column in per_seed.columns
        if column not in {"scenario", "method", "seed"}
    ]
    table = (
        per_seed.groupby(["scenario", "method"], sort=False)[numeric]
        .mean(numeric_only=True)
        .reset_index()
    )
    os.makedirs("tables", exist_ok=True)
    per_seed.to_csv("tables/loop_validation_per_seed.csv", index=False)
    table.to_csv("tables/loop_validation.csv", index=False)
    return table


def _text_paths(seed: int = 0, max_paths: int = 900) -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    paths = sorted(
        set((root / "budget_guard").glob("*.py"))
        | set((root / "notes").glob("*.md"))
        | set((root / ".venv" / "Lib" / "site-packages").glob("**/*.py"))
    )
    rng = np.random.default_rng(seed)
    if len(paths) > max_paths:
        indices = rng.choice(len(paths), size=max_paths, replace=False)
        paths = [paths[index] for index in sorted(indices)]
    return paths


def main(
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
    window_rollouts: int = 10,
    resume: bool = False,
):
    sokoban_df, _ = load_env("sokoban")
    swebench_df, _ = load_env("swebench")
    token_source = token_traces_from_dataframe(
        sokoban_df,
        budget=ENVS["sokoban"]["max_ctx"],
        run_prefix="sokoban",
    )
    token_target = token_traces_from_dataframe(
        swebench_df,
        budget=ENVS["swebench"]["max_ctx"],
        run_prefix="swebench",
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

    text_traces = text_file_traces(_text_paths(), run_prefix="source-text")
    if len(text_traces) < 20:
        raise RuntimeError("not enough source-text traces for validation")

    checkpoint = Path("tables/loop_validation_per_seed.csv")
    rows: list[dict] = []
    completed_seeds: set[int] = set()
    if resume and checkpoint.exists():
        prior = pd.read_csv(checkpoint)
        rows = prior.to_dict("records")
        completed_seeds = {int(seed) for seed in prior["seed"].unique()}
    for seed in seeds:
        if seed in completed_seeds:
            continue
        token_guards = _fit_methods(
            token_source, seed=seed, window_rollouts=window_rollouts
        )
        rows.extend(
            _evaluate_fitted(
                token_guards,
                token_target,
                scenario="tokens:sokoban->swebench",
                seed=seed,
            )
        )
        warehouse_guards = _fit_methods(
            warehouse_source,
            seed=seed,
            progress_keys=WAREHOUSE_PROGRESS,
            window_rollouts=window_rollouts,
        )
        for model, target in warehouse_targets.items():
            rows.extend(
                _evaluate_fitted(
                    warehouse_guards,
                    target,
                    scenario=f"warehouse:opus->{model}",
                    seed=seed,
                )
            )
        rng = np.random.default_rng(seed)
        order = rng.permutation(len(text_traces))
        cut = int(0.7 * len(order))
        source = [text_traces[index] for index in order[:cut]]
        target = [text_traces[index] for index in order[cut:]]
        text_guards = _fit_methods(
            source, seed=seed, window_rollouts=window_rollouts
        )
        rows.extend(
            _evaluate_fitted(
                text_guards,
                target,
                scenario="non-agent:source-text",
                seed=seed,
            )
        )
        # Make long validation resumable/auditable: an interruption after any seed
        # still leaves a valid partial table whose seed column states what completed.
        _write_tables(rows)

    table = _write_tables(rows)
    display = [
        "scenario",
        "method",
        "joint_prefix_coverage",
        "joint_prefix_coverage_ci_lo",
        "joint_prefix_coverage_ci_hi",
        "operative_level",
        "trajectory_joint_coverage",
        "false_stop_rate",
        "failed_run_catch_rate",
        "n_runs",
    ]
    print(table[[column for column in display if column in table]].to_string(index=False))
    print("\nwrote tables/loop_validation.csv, tables/loop_validation_per_seed.csv")
    return table


if __name__ == "__main__":
    main(resume=True)
