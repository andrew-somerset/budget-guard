"""budget_guard/run_transfer_warehouse.py — model-swap transfer for the EXTERNAL budget.

Closes a gap flagged in the robustness pass: ``run_transfer.py`` / ``run_transfer_env.py``
only ever test transfer on INTERNAL (token) budgets (sokoban/searchr1/swebench).
Warehouse (the multi-resource EXTERNAL budget env) had never been a transfer source or
target — it was only ever evaluated in one fixed condition (claude-opus-4.7, no shift).

Setting: fit on logged claude-opus-4.7 Warehouse runs, then deploy on four other models.
Compares the agent's own intervals, frozen Bonferroni CQR, a frozen empirical-copula
baseline, and a new rollout-safe adaptive joint copula. The adaptive method predicts
every prefix of a rollout first, then updates its recent joint-error window only after
that rollout finishes — no within-rollout future leak.

This is the "better" multi-resource version: it updates both each resource margin and
the shared rank that combines all three resources. It still uses frozen CQR prediction
models; only the calibration layer self-corrects from newly completed target rollouts.

Usage: python -m budget_guard.run_transfer_warehouse
Writes figures/transfer_warehouse.png and tables/transfer_warehouse.csv.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, cqr_split
from .metrics import (
    frac_unbounded,
    normalized_width,
    pooled_bootstrap_ci,
    rollout_bootstrap_draws,
    rollout_bootstrap_mean_draws,
)
from .multiresource import (
    RESOURCES,
    adaptive_joint_intervals,
    build_features,
    load_warehouse,
)
from .plotting import bar_value_labels, nominal_line
from .split import group_split

_DATA = os.path.join(os.path.dirname(__file__), "..", "data", "bagen_hf", "estimation")
SOURCE_PATH = f"{_DATA}/newwarehouse-opus4.7-low-thinking-main/newwarehouse-opus4.7-low-thinking-main.json"
TARGETS = {
    "gemini3.1": f"{_DATA}/newwarehouse-gemini3.1-low-thinking-main/newwarehouse-gemini3.1-low-thinking-main.json",
    "gpt5.2": f"{_DATA}/newwarehouse-gpt5.2-main/newwarehouse-gpt5.2-main.json",
    "qwen3-235b": f"{_DATA}/newwarehouse-qwen3-235b-main/newwarehouse-qwen3-235b-main.json",
    "sonnet4.6": f"{_DATA}/newwarehouse-sonnet4.6-low-thinking-main/newwarehouse-sonnet4.6-low-thinking-main.json",
}

METHOD_COLORS = {
    "agent self-report": "#8B93A1",
    "frozen Bonferroni": "#1baf7a",
    "frozen joint copula": "#eda100",
    "adaptive joint copula": "#4a3aa7",
}


def _late_mask(df: pd.DataFrame) -> np.ndarray:
    rollout_order = list(dict.fromkeys(df["rollout_index"].tolist()))
    late_rollouts = set(rollout_order[len(rollout_order) // 2 :])
    return df["rollout_index"].isin(late_rollouts).to_numpy()


def _interval_rows(
    model: str,
    method: str,
    seed: int,
    target: pd.DataFrame,
    intervals: dict,
    final_shared_level: float = np.nan,
) -> list[dict]:
    groups = target["rollout_index"].to_numpy()
    late = _late_mask(target)
    covered_all = np.ones(len(target), dtype=bool)
    unbounded_any = np.zeros(len(target), dtype=bool)
    rows = []
    for res in RESOURCES:
        y = target[f"y_{res}"].to_numpy(dtype=float)
        lo, hi = intervals[res]
        covered = (lo <= y) & (y <= hi)
        covered_all &= covered
        unbounded_any |= ~np.isfinite(hi)
        draws = rollout_bootstrap_draws(y, lo, hi, groups, seed=seed)
        late_draws = rollout_bootstrap_draws(
            y[late], lo[late], hi[late], groups[late], seed=seed
        )
        rows.append(
            {
                "target_model": model,
                "method": method,
                "resource": res,
                "seed": seed,
                "coverage": float(covered.mean()),
                # per-seed 90% cluster-bootstrap CIs (quantiles of this seed's draws)
                "ci_lo": float(np.quantile(draws, 0.05)),
                "ci_hi": float(np.quantile(draws, 0.95)),
                "late_coverage": float(covered[late].mean()),
                "late_ci_lo": float(np.quantile(late_draws, 0.05)),
                "late_ci_hi": float(np.quantile(late_draws, 0.95)),
                "_draws": draws,
                "_late_draws": late_draws,
                "normalized_width": normalized_width(y, lo, hi, agg="median"),
                "frac_unbounded": frac_unbounded(hi),
                "n_test": len(target),
                "n_rollouts": target["rollout_index"].nunique(),
                "final_shared_level": final_shared_level,
            }
        )
    draws = rollout_bootstrap_mean_draws(covered_all, groups, seed=seed)
    late_draws = rollout_bootstrap_mean_draws(
        covered_all[late], groups[late], seed=seed
    )
    rows.append(
        {
            "target_model": model,
            "method": method,
            "resource": "ALL (joint)",
            "seed": seed,
            "coverage": float(covered_all.mean()),
            "ci_lo": float(np.quantile(draws, 0.05)),
            "ci_hi": float(np.quantile(draws, 0.95)),
            "late_coverage": float(covered_all[late].mean()),
            "late_ci_lo": float(np.quantile(late_draws, 0.05)),
            "late_ci_hi": float(np.quantile(late_draws, 0.95)),
            "_draws": draws,
            "_late_draws": late_draws,
            "normalized_width": np.nan,
            "frac_unbounded": float(unbounded_any.mean()),
            "n_test": len(target),
            "n_rollouts": target["rollout_index"].nunique(),
            "final_shared_level": final_shared_level,
        }
    )
    return rows


def _agent_rows(model: str, seed: int, target: pd.DataFrame) -> list[dict]:
    groups = target["rollout_index"].to_numpy()
    late = _late_mask(target)
    covered_all = np.ones(len(target), dtype=bool)
    rows = []
    # None flags = the agent declared the run impossible and gave no interval;
    # BAGEN's coverage convention excludes them. A bool cast would count NaN as
    # covered (truthy) — mask to defined rows instead.
    defined_all = target[[f"agent_cov_{r}" for r in RESOURCES]].notna().all(axis=1).to_numpy()
    for res in RESOURCES:
        flags = target[f"agent_cov_{res}"]
        defined = flags.notna().to_numpy()
        covered = flags.fillna(False).astype(bool).to_numpy()
        covered_all &= covered
        d_res, d_late = defined, defined & late
        draws = rollout_bootstrap_mean_draws(covered[d_res], groups[d_res], seed=seed)
        late_draws = rollout_bootstrap_mean_draws(covered[d_late], groups[d_late], seed=seed)
        rows.append(
            {
                "target_model": model,
                "method": "agent self-report",
                "resource": res,
                "seed": seed,
                "coverage": float(covered[d_res].mean()) if d_res.any() else float("nan"),
                "ci_lo": float(np.quantile(draws, 0.05)),
                "ci_hi": float(np.quantile(draws, 0.95)),
                "late_coverage": float(covered[d_late].mean()) if d_late.any() else float("nan"),
                "late_ci_lo": float(np.quantile(late_draws, 0.05)),
                "late_ci_hi": float(np.quantile(late_draws, 0.95)),
                "_draws": draws,
                "_late_draws": late_draws,
                "normalized_width": np.nan,
                "frac_unbounded": np.nan,
                "n_test": int(d_res.sum()),
                "n_rollouts": target["rollout_index"].nunique(),
                "final_shared_level": np.nan,
            }
        )
    d_all, d_all_late = defined_all, defined_all & late
    draws = rollout_bootstrap_mean_draws(covered_all[d_all], groups[d_all], seed=seed)
    late_draws = rollout_bootstrap_mean_draws(
        covered_all[d_all_late], groups[d_all_late], seed=seed
    )
    rows.append(
        {
            "target_model": model,
            "method": "agent self-report",
            "resource": "ALL (joint)",
            "seed": seed,
            "coverage": float(covered_all[d_all].mean()) if d_all.any() else float("nan"),
            "ci_lo": float(np.quantile(draws, 0.05)),
            "ci_hi": float(np.quantile(draws, 0.95)),
            "late_coverage": float(covered_all[d_all_late].mean()) if d_all_late.any() else float("nan"),
            "late_ci_lo": float(np.quantile(late_draws, 0.05)),
            "late_ci_hi": float(np.quantile(late_draws, 0.95)),
            "_draws": draws,
            "_late_draws": late_draws,
            "normalized_width": np.nan,
            "frac_unbounded": np.nan,
            "n_test": int(d_all.sum()),
            "n_rollouts": target["rollout_index"].nunique(),
            "final_shared_level": np.nan,
        }
    )
    return rows


def _bonferroni_intervals(
    source: pd.DataFrame,
    masks: dict[str, np.ndarray],
    target: pd.DataFrame,
    alpha: float,
) -> dict:
    X_source, X_target = build_features(source), build_features(target)
    tr, ca = masks["train"], masks["cal"]
    intervals = {}
    for res in RESOURCES:
        y_source = source[f"y_{res}"].to_numpy(dtype=float)
        intervals[res] = cqr_split(
            X_source[tr],
            y_source[tr],
            X_source[ca],
            y_source[ca],
            X_target,
            alpha=alpha / len(RESOURCES),
        )[:2]
    return intervals


def main(
    seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
    alpha: float = DEFAULT_ALPHA,
    window: int = 100,
):
    source = load_warehouse(SOURCE_PATH)
    targets = {
        model: load_warehouse(path)
        .sort_values(["rollout_index", "completed_turns"])
        .reset_index(drop=True)
        for model, path in TARGETS.items()
    }

    rows = []
    for seed in seeds:
        masks = group_split(source, fracs=(0.7, 0.3, 0.0), seed=seed)
        for model, target in targets.items():
            rows.extend(_agent_rows(model, seed, target))
            bonferroni = _bonferroni_intervals(source, masks, target, alpha)
            rows.extend(
                _interval_rows(model, "frozen Bonferroni", seed, target, bonferroni)
            )
            adaptive = adaptive_joint_intervals(
                source, masks, target, alpha=alpha, window=window
            )
            rows.extend(
                _interval_rows(
                    model,
                    "frozen joint copula",
                    seed,
                    target,
                    adaptive["frozen_intervals"],
                    final_shared_level=adaptive["frozen_shared_level"],
                )
            )
            rows.extend(
                _interval_rows(
                    model,
                    "adaptive joint copula",
                    seed,
                    target,
                    adaptive["intervals"],
                    final_shared_level=float(adaptive["shared_level_path"][-1]),
                )
            )

    per_seed = pd.DataFrame(rows)
    keys = ["target_model", "method", "resource"]
    table = (
        per_seed.groupby(keys, sort=False)
        .agg(
            coverage=("coverage", "mean"),
            coverage_std=("coverage", "std"),
            late_coverage=("late_coverage", "mean"),
            normalized_width=("normalized_width", "mean"),
            frac_unbounded=("frac_unbounded", "mean"),
            n_test=("n_test", "first"),
            n_rollouts=("n_rollouts", "first"),
            final_shared_level=("final_shared_level", "mean"),
        )
        .reset_index()
    )
    # Aggregate bands: pooled seed×rollout bootstrap quantiles, NOT means of
    # per-seed CI endpoints (which is not a CI at any level; see
    # metrics.rollout_bootstrap_mean_draws).
    pooled = per_seed.groupby(keys, sort=False)["_draws"].apply(
        lambda s: pooled_bootstrap_ci(list(s))
    )
    pooled_late = per_seed.groupby(keys, sort=False)["_late_draws"].apply(
        lambda s: pooled_bootstrap_ci(list(s))
    )
    assert len(pooled) == len(table) == len(pooled_late)
    table.insert(5, "ci_lo", [c[0] for c in pooled])
    table.insert(6, "ci_hi", [c[1] for c in pooled])
    table.insert(8, "late_ci_lo", [c[0] for c in pooled_late])
    table.insert(9, "late_ci_hi", [c[1] for c in pooled_late])
    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    per_seed.drop(columns=["_draws", "_late_draws"]).to_csv(
        "tables/transfer_warehouse_per_seed.csv", index=False
    )
    table.to_csv("tables/transfer_warehouse.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = list(TARGETS)
    methods = list(METHOD_COLORS)
    xs = np.arange(len(models))
    width = 0.2

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True, constrained_layout=True)
    for ax, metric, lo_col, hi_col, subtitle in [
        (axes[0], "coverage", "ci_lo", "ci_hi", "all target rollouts"),
        (axes[1], "late_coverage", "late_ci_lo", "late_ci_hi", "late half (after adapting)"),
    ]:
        bar_groups: list[tuple] = []
        for i, method in enumerate(methods):
            sub = [
                table[
                    (table["target_model"] == model)
                    & (table["method"] == method)
                    & (table["resource"] == "ALL (joint)")
                ].iloc[0]
                for model in models
            ]
            vals = np.array([float(row[metric]) for row in sub])
            yerr = np.clip(
                np.array(
                    [
                        [v - float(row[lo_col]) for v, row in zip(vals, sub)],
                        [float(row[hi_col]) - v for v, row in zip(vals, sub)],
                    ]
                ),
                0,
                None,
            )
            offset = (i - (len(methods) - 1) / 2) * width
            bars = ax.bar(
                xs + offset,
                vals,
                width=width - 0.02,
                color=METHOD_COLORS[method],
                label=method,
                yerr=yerr,
                capsize=2,
                error_kw={"lw": 0.8, "alpha": 0.7},
                zorder=1,
            )
            for patch in bars:
                patch.set_zorder(1)
            bar_groups.append((bars, vals, yerr[1]))
        ax.set_xticks(xs, models)
        ax.set_ylim(0, 1.15)
        ax.set_title(subtitle)
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)
        nominal_line(ax, alpha, zorder=4)
        for bars, vals, err_up in bar_groups:
            bar_value_labels(ax, bars, vals, fmt="{:.2f}", fontsize=7,
                             yerr_upper=err_up, nominal=1 - alpha,
                             nominal_nudge_for={"0.79"})
    axes[0].set_ylabel("joint coverage (all 3 Warehouse resources)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=8, ncol=4,
               loc="upper center", bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(
        "Warehouse model-swap: rollout-safe joint adaptation\n"
        f"calibrated on claude-opus-4.7 ({len(seeds)} seeds, rollout-cluster 90% CI; window={window})"
    )
    fig.savefig("figures/transfer_warehouse.png", dpi=200, bbox_inches="tight")

    joint = table[table["resource"] == "ALL (joint)"]
    print(joint.to_string(index=False))
    print(
        "\nwrote figures/transfer_warehouse.png, tables/transfer_warehouse.csv, "
        "tables/transfer_warehouse_per_seed.csv"
    )
    return table


if __name__ == "__main__":
    main()
