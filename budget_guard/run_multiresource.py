"""budget_guard/run_multiresource.py — C2 headline: joint multi-resource coverage.

Warehouse env, claude-opus-4.7 run. Compares the BAGEN agent's own joint coverage
against the guard with independent margins (each at alpha) and with the Bonferroni
correction (each at alpha/3), mean over 5 split seeds.

Usage: python -m budget_guard.run_multiresource
Writes figures/joint_vs_marginal.png and tables/multiresource.csv.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA
from .multiresource import (
    RESOURCES,
    agent_joint_baseline,
    joint_coverage,
    joint_intervals,
    load_warehouse,
)
from .split import group_split

PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "bagen_hf", "estimation",
    "newwarehouse-opus4.7-low-thinking-main", "newwarehouse-opus4.7-low-thinking-main.json",
)
BLUE, AQUA, YELLOW, GRAY = "#2a78d6", "#1baf7a", "#eda100", "#8B93A1"


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4), alpha: float = DEFAULT_ALPHA):
    df = load_warehouse(PATH)
    baseline = agent_joint_baseline(PATH)
    print(f"{len(df)} prefix samples, {df['rollout_index'].nunique()} rollouts; "
          f"agent joint baseline = {baseline['joint']:.3f}")

    rows = []
    for seed in seeds:
        masks = group_split(df, seed=seed)
        for scheme in ("independent", "bonferroni", "copula"):
            result = joint_intervals(df, masks, alpha=alpha, scheme=scheme)
            cov = joint_coverage(df, masks["test"], result["intervals"])
            rows.append({"scheme": scheme, "seed": seed, **cov})
    per_seed = pd.DataFrame(rows)
    agg = per_seed.groupby("scheme", sort=False).agg(
        **{c: (c, "mean") for c in list(RESOURCES) + ["joint"]},
        joint_std=("joint", "std"),
    ).reset_index()

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    baseline_row = {"scheme": "agent self-report", **baseline, "joint_std": np.nan}
    table = pd.concat([pd.DataFrame([baseline_row]), agg], ignore_index=True)
    table.to_csv("tables/multiresource.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["agent self-report", "independent", "bonferroni", "copula"]
    colors = {"agent self-report": GRAY, "independent": AQUA, "bonferroni": YELLOW,
              "copula": BLUE}
    cats = list(RESOURCES) + ["joint"]
    xs = np.arange(len(cats))
    width = 0.21

    fig, ax = plt.subplots(figsize=(9, 4.4), constrained_layout=True)
    for i, scheme in enumerate(labels):
        sel = table[table["scheme"] == scheme].iloc[0]
        vals = [sel[c] for c in cats]
        offset = (i - (len(labels) - 1) / 2) * width
        bars = ax.bar(xs + offset, vals, width=width - 0.03, color=colors[scheme], label=scheme)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.012, f"{v:.2f}",
                    ha="center", fontsize=8)
    ax.axhline(1 - alpha, color="#4A5361", lw=1.2, ls="--")
    ax.text(0.995, 1 - alpha + 0.015, f"nominal {1 - alpha:.2f}", ha="right",
            transform=ax.get_yaxis_transform(), fontsize=9, color="#4A5361")
    ax.set_xticks(xs, ["time", "warehouse", "cost", "JOINT (all 3)"])
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("coverage")
    ax.set_title(f"C2 multi-resource (Warehouse, opus-4.7): per-resource and joint coverage, "
                 f"mean over {len(seeds)} seeds")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.06))
    fig.savefig("figures/joint_vs_marginal.png", dpi=200)

    print(table.to_string(index=False))
    print("\nwrote figures/joint_vs_marginal.png, tables/multiresource.csv")
    return table


if __name__ == "__main__":
    main()
