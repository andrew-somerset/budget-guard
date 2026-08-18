"""budget_guard/run_costofpass.py — cost of pass: dollars per correct answer, whole trajectories.

Cost-of-pass = total spend / number of passing runs, over test rollouts, for three
policies: the agent alone (rides every run to the end), the guard (feasibility
stopping rule at tolerance delta), and hard token caps. Aborting a doomed run saves
its remaining spend; aborting a feasible run forfeits that run's pass — both effects
are priced in, which is what makes this an economics metric rather than a coverage one.

Prices are an explicit assumption (per-token blended rate); policy *rankings* are
price-invariant since cost scales linearly.

Usage: python -m budget_guard.run_costofpass [env]   (default: sokoban)
Writes figures/cost_of_pass_<env>.png and tables/cost_of_pass_<env>.csv.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

from .data import load_env
from .economic import calibrate_threshold, fit_feasibility
from .features import build_xy
from .plotting import figure_title, apply_figure_title
from .split import group_split

USD_PER_MTOK = 15.0  # blended $/1M tokens assumption; change freely, rankings unaffected
BLUE, YELLOW, GRAY = "#2a78d6", "#eda100", "#8B93A1"
DELTAS = (0.02, 0.05, 0.10, 0.15, 0.20, 0.30)
# Per-env δ label placement when default offset sits on the guard curve.
_GUARD_LABEL_OFFSET: dict[str, dict[float, tuple[int, int]]] = {
    "sokoban": {0.15: (-38, -10)},  # down-left in points, no leader line
}
_LABEL_BBOX = dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.92)


def _annotate_swebench_guard(ax, guard: pd.DataFrame) -> None:
    """Place each δ next to its marker. 0.02 and 0.05 share the x=1 star; 0.10 is just below."""
    pts = {round(float(r["param"]), 2):
           (float(r["pass_rate_retained"]), float(r["cost_of_pass_tokens"]))
           for _, r in guard.iterrows()}
    # (key, label, xytext, ha, va) — all in the open gap beside the marker, no leaders
    placements = (
        (0.30, "δ=0.30", (0.785, 20580), "right", "center"),
        (0.20, "δ=0.20", (0.958, 16980), "left", "top"),
        (0.15, "δ=0.15", (0.958, 18550), "left", "bottom"),
        (0.10, "δ=0.10", (1.028, 20805), "left", "center"),
        (0.02, "δ=0.02, 0.05", (1.028, 21254), "left", "center"),
    )
    for key, label, xytext, ha, va in placements:
        ax.annotate(label, pts[key], xytext=xytext, textcoords="data",
                    fontsize=7.5, color=BLUE, ha=ha, va=va,
                    bbox=_LABEL_BBOX, zorder=5)


def _annotate_guard_labels(ax, guard: pd.DataFrame, env: str) -> None:
    if env == "swebench":
        _annotate_swebench_guard(ax, guard)
        return
    pt_overrides = _GUARD_LABEL_OFFSET.get(env, {})
    for _, r in guard.iterrows():
        p = float(r["param"])
        key = round(p, 2)
        xy = (r["pass_rate_retained"], r["cost_of_pass_tokens"])
        label = f"δ={p:.2f}"
        if key in pt_overrides:
            ox, oy = pt_overrides[key]
            ax.annotate(label, xy, textcoords="offset points", xytext=(ox, oy),
                        fontsize=7.5, color=BLUE, ha="right" if ox < 0 else "left",
                        va="top" if oy < 0 else "bottom",
                        bbox=_LABEL_BBOX, zorder=5)
        else:
            ax.annotate(label, xy, textcoords="offset points", xytext=(5, 4),
                        fontsize=7.5, color=BLUE, zorder=5)


def _policy_outcomes(df_test: pd.DataFrame, abort_mask: pd.Series) -> dict:
    """Spend + passes when each rollout is aborted at its first flagged prefix."""
    tmp = df_test[["rollout_index", "k", "can_finish", "tokens_so_far", "total_rollout_tokens"]].copy()
    tmp["abort"] = abort_mask.to_numpy() if hasattr(abort_mask, "to_numpy") else abort_mask
    spend = passes = 0.0
    n = 0
    for _, g in tmp.sort_values("k").groupby("rollout_index"):
        n += 1
        flagged = g[g["abort"]]
        if len(flagged):
            spend += float(flagged["tokens_so_far"].iloc[0])
        else:
            spend += float(g["total_rollout_tokens"].iloc[0])
            passes += float(bool(g["can_finish"].iloc[0]))
    return {"tokens_spent": spend, "passes": passes, "n_rollouts": n}


def _cop(out: dict) -> float:
    return out["tokens_spent"] / max(out["passes"], 1.0)


def run(env: str = "sokoban", seeds: tuple[int, ...] = (0, 1, 2, 3, 4)):
    df, _ = load_env(env)
    X, y, groups = build_xy(df)
    cap_grid = np.quantile(df["total_rollout_tokens"].unique(), [0.35, 0.5, 0.65, 0.8])

    rows = []
    for seed in seeds:
        masks = group_split(df, seed=seed)
        tr, ca, te = masks["train"], masks["cal"], masks["test"]
        dft = df[te]
        model = fit_feasibility(X[tr], df.loc[tr, "can_finish"])
        s_cal = model.predict_proba(X[ca])[:, 1]
        s_te = pd.Series(model.predict_proba(X[te])[:, 1], index=dft.index)

        rows.append({"seed": seed, "policy": "agent alone", "param": np.nan,
                     **_policy_outcomes(dft, pd.Series(False, index=dft.index))})
        for delta in DELTAS:
            tau = calibrate_threshold(df[ca], s_cal, delta)
            rows.append({"seed": seed, "policy": "guard", "param": delta,
                         **_policy_outcomes(dft, s_te < tau)})
        for cap in cap_grid:
            rows.append({"seed": seed, "policy": "hard cap", "param": float(cap),
                         **_policy_outcomes(dft, dft["tokens_so_far"] > cap)})

    per = pd.DataFrame(rows)
    per["cost_of_pass_tokens"] = per["tokens_spent"] / per["passes"].clip(lower=1)
    agg = (per.groupby(["policy", "param"], dropna=False, sort=False)
           .agg(cost_of_pass_tokens=("cost_of_pass_tokens", "mean"),
                passes=("passes", "mean"), tokens_spent=("tokens_spent", "mean"))
           .reset_index())
    agg["cost_of_pass_usd"] = agg["cost_of_pass_tokens"] / 1e6 * USD_PER_MTOK
    agg["pass_rate_retained"] = agg["passes"] / agg.loc[agg["policy"] == "agent alone", "passes"].iloc[0]

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    agg.to_csv(f"tables/cost_of_pass_{env}.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.6), constrained_layout=True)
    agent = agg[agg["policy"] == "agent alone"].iloc[0]
    guard = agg[agg["policy"] == "guard"]
    caps = agg[agg["policy"] == "hard cap"]
    ax.scatter([1.0], [agent["cost_of_pass_tokens"]], s=70, color=GRAY, marker="*",
               zorder=4, label="agent alone")
    ax.plot(guard["pass_rate_retained"], guard["cost_of_pass_tokens"], marker="o", ms=5,
            lw=2, color=BLUE, label="guard (sweep delta)")
    _annotate_guard_labels(ax, guard, env)
    ax.plot(caps["pass_rate_retained"], caps["cost_of_pass_tokens"], marker="s", ms=5,
            lw=1.6, ls=":", color=YELLOW, label="hard cap (sweep cap)")
    ax.set_xlabel("fraction of passes retained (vs agent alone)")
    ax.set_ylabel("cost of pass (tokens per correct answer)")
    apply_figure_title(ax, figure_title(
        f"Cost of pass — {env}",
        f"Mean over {len(seeds)} seeds; ${USD_PER_MTOK}/Mtok assumed for $ column",
    ))
    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9)
    if env == "swebench":
        ax.set_xlim(0.68, 1.12)
    fig.savefig(f"figures/cost_of_pass_{env}.png", dpi=200)

    print(agg.to_string(index=False))
    print(f"\nwrote figures/cost_of_pass_{env}.png, tables/cost_of_pass_{env}.csv")
    return agg


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "sokoban")
