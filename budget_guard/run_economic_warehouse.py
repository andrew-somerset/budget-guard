"""budget_guard/run_economic_warehouse.py — C3+C4 on the env they were designed for.

Warehouse: long runs, failure-driven doom (target cash unreachable in budget), and
native DOLLARS — no per-token price assumption. Guard = feasibility rule with
rollout-level false-abort calibration; baselines = hard caps on dollars spent and
on weeks elapsed (both must be beaten). Also reports cost-of-pass in USD.

Usage: python -m budget_guard.run_economic_warehouse
Writes figures/abort_frontier_warehouse.png and tables/abort_frontier_warehouse.csv
(+ cost_of_pass_warehouse.csv).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .economic import _run_rule, calibrate_threshold, evaluate_stopping, fit_feasibility
from .multiresource import build_features, load_warehouse
from .run_multiresource import PATH
from .split import group_split

BLUE, YELLOW, ORANGE, GRAY = "#2a78d6", "#eda100", "#eb6834", "#8B93A1"
DELTAS = (0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)
COLS = dict(spent_col="spent_cost_usd", total_col="total_cost_usd", order_col="completed_turns")


def _cost_of_pass(df_test: pd.DataFrame, trigger: np.ndarray) -> dict:
    tmp = df_test[["rollout_index", "completed_turns", "can_finish",
                   "spent_cost_usd", "total_cost_usd"]].copy()
    tmp["trigger"] = np.asarray(trigger)
    spend = passes = 0.0
    for _, g in tmp.sort_values("completed_turns").groupby("rollout_index"):
        flagged = g[g["trigger"]]
        if len(flagged):
            spend += float(flagged["spent_cost_usd"].iloc[0])
        else:
            spend += float(g["total_cost_usd"].iloc[0])
            passes += float(bool(g["can_finish"].iloc[0]))
    return {"usd_spent": spend, "passes": passes,
            "cost_of_pass_usd": spend / max(passes, 1.0)}


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4)):
    df = load_warehouse(PATH, keep_censored=True)
    X = build_features(df)
    print(f"{len(df)} samples, {df['rollout_index'].nunique()} rollouts, "
          f"feasible={df.groupby('rollout_index')['can_finish'].first().mean():.0%}")
    cash_caps = np.quantile(df["total_cost_usd"].unique(), [0.2, 0.35, 0.5, 0.65, 0.8])
    week_caps = np.quantile(df["budget_time_weeks"].unique(), [0.25, 0.5, 0.75]) * np.array([0.5, 0.75, 1.0])

    rows, cop_rows = [], []
    for seed in seeds:
        masks = group_split(df, seed=seed)
        tr, ca, te = masks["train"], masks["cal"], masks["test"]
        dft = df[te]
        model = fit_feasibility(X[tr], df.loc[tr, "can_finish"])
        s_cal = model.predict_proba(X[ca])[:, 1]
        s_te = model.predict_proba(X[te])[:, 1]

        cop_rows.append({"seed": seed, "policy": "agent alone", "param": np.nan,
                         **_cost_of_pass(dft, np.zeros(len(dft), dtype=bool))})
        for delta in DELTAS:
            tau = calibrate_threshold(df[ca], s_cal, delta)
            rows.append({"seed": seed, "rule": "guard", "param": delta,
                         **evaluate_stopping(dft, s_te, tau, **COLS)})
            cop_rows.append({"seed": seed, "policy": "guard", "param": delta,
                             **_cost_of_pass(dft, s_te < tau)})
        for cap in cash_caps:
            trig = dft["spent_cost_usd"].to_numpy(dtype=float) > cap
            rows.append({"seed": seed, "rule": "hard cap ($ spent)", "param": float(cap),
                         **_run_rule(dft, trig, **COLS)})
            cop_rows.append({"seed": seed, "policy": "hard cap ($)", "param": float(cap),
                             **_cost_of_pass(dft, trig)})
        for cap in week_caps:
            trig = dft["completed_weeks"].to_numpy(dtype=float) > cap
            rows.append({"seed": seed, "rule": "hard cap (weeks)", "param": float(cap),
                         **_run_rule(dft, trig, **COLS)})

    frontier = (pd.DataFrame(rows).groupby(["rule", "param"], sort=True)
                .agg(false_abort_rate=("false_abort_rate", "mean"),
                     doomed_savings_frac=("doomed_savings_frac", "mean")).reset_index())
    cop = (pd.DataFrame(cop_rows).groupby(["policy", "param"], dropna=False, sort=False)
           .agg(cost_of_pass_usd=("cost_of_pass_usd", "mean"),
                passes=("passes", "mean")).reset_index())
    cop["pass_rate_retained"] = cop["passes"] / cop.loc[cop["policy"] == "agent alone", "passes"].iloc[0]

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    frontier.to_csv("tables/abort_frontier_warehouse.csv", index=False)
    cop.to_csv("tables/cost_of_pass_warehouse.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.6), constrained_layout=True)
    styles = {"guard": (BLUE, "o", "-"), "hard cap ($ spent)": (YELLOW, "s", ":"),
              "hard cap (weeks)": (ORANGE, "^", ":")}
    for rule, (color, marker, ls) in styles.items():
        sel = frontier[frontier["rule"] == rule].sort_values("false_abort_rate")
        ax.plot(sel["false_abort_rate"], sel["doomed_savings_frac"], marker=marker,
                ms=5, lw=2 if rule == "guard" else 1.6, ls=ls, color=color, label=rule)
    ax.set_xlabel("false-abort rate on feasible runs (test)")
    ax.set_ylabel("fraction of doomed-run $ saved")
    ax.set_title(f"C3 abort frontier — Warehouse, native USD (mean over {len(seeds)} seeds)")
    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.savefig("figures/abort_frontier_warehouse.png", dpi=200)

    print(frontier.to_string(index=False))
    print("\ncost of pass (USD):\n" + cop.to_string(index=False))
    print("\nwrote figures/abort_frontier_warehouse.png + 2 tables")
    return frontier, cop


if __name__ == "__main__":
    main()
