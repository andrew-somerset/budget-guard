"""budget_guard/run_gap.py — Week 2: does naive conformal keep its promise here?

Fits split-conformal (abs-residual) and split-CQR at alpha=0.1 on one env run and
reports marginal coverage plus coverage conditional on turn index k. The marginal
number can look fine while per-depth coverage collapses — that conditional failure
is what motivates the online methods (Week 3).

Usage: python -m budget_guard.run_gap [env]      (default: sokoban)
Writes figures/gap_<env>.png and tables/gap_<env>.csv.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, cqr_split, mondrian_cqr, split_conformal_absres
from .data import load_env
from .features import build_xy
from .metrics import marginal_coverage, mean_width, normalized_width
from .plotting import apply_figure_suptitle, bar_value_labels, figure_title, nominal_line
from .split import group_split

# dataviz-validated categorical palette (light surface)
BLUE, AQUA, YELLOW, VIOLET, GRAY = "#2a78d6", "#1baf7a", "#eda100", "#4a3aa7", "#8B93A1"


def run(env: str = "sokoban", seed: int = 0, alpha: float = DEFAULT_ALPHA):
    df, _ = load_env(env)
    X, y, groups = build_xy(df)
    masks = group_split(df, seed=seed)
    tr, ca, te = masks["train"], masks["cal"], masks["test"]

    results = {}
    for name, fn in [("split-absres", split_conformal_absres), ("split-CQR", cqr_split)]:
        lo, hi, _ = fn(X[tr], y[tr], X[ca], y[ca], X[te], alpha=alpha)
        results[name] = {"lo": lo, "hi": hi}
    lo, hi, _ = mondrian_cqr(
        X[tr], y[tr], X[ca], y[ca], df.loc[ca, "k"].to_numpy(),
        X[te], df.loc[te, "k"].to_numpy(), alpha=alpha,
    )
    results["Mondrian-CQR"] = {"lo": lo, "hi": hi}

    rows = []
    k_test = df.loc[te, "k"].to_numpy()
    for name, r in results.items():
        rows.append(
            {
                "env": env,
                "method": name,
                "coverage": marginal_coverage(y[te], r["lo"], r["hi"]),
                "mean_width": mean_width(r["lo"], r["hi"]),
                "normalized_width": normalized_width(y[te], r["lo"], r["hi"]),
                "n_test": int(te.sum()),
            }
        )
    table = pd.DataFrame(rows)

    # coverage conditional on turn depth (bucketed so each bucket has mass)
    max_k_plot = int(np.quantile(k_test, 0.95))
    ks = np.arange(1, max_k_plot + 1)
    by_k = {}
    for name, r in results.items():
        covered = (r["lo"] <= y[te]) & (y[te] <= r["hi"])
        by_k[name] = [
            covered[k_test == k].mean() if (k_test == k).sum() >= 5 else np.nan for k in ks
        ]

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    table.to_csv(f"tables/gap_{env}.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    colors = {"split-absres": BLUE, "split-CQR": AQUA, "Mondrian-CQR": VIOLET}

    ax = axes[0]
    names = list(results)
    covs = [table.loc[table["method"] == m, "coverage"].item() for m in names]
    bars = ax.bar(names, covs, width=0.5, color=[colors[m] for m in names], zorder=1)
    for patch in bars:
        patch.set_zorder(1)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("marginal coverage")
    ax.set_title(f"{env}: Marginal coverage (test, split by rollout)")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    nominal_line(ax, alpha, color=GRAY, zorder=4)
    bar_value_labels(ax, bars, covs, fmt="{:.3f}", fontsize=9, nominal=1 - alpha)

    ax = axes[1]
    markers = {"split-absres": "o", "split-CQR": "s", "Mondrian-CQR": "D"}
    for name in names:
        ax.plot(ks, by_k[name], marker=markers[name], ms=5, lw=2, color=colors[name],
                label=name)
    ax.axhline(1 - alpha, color=GRAY, lw=1.2, ls="--")
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("turn index k")
    ax.set_ylabel("coverage at depth k")
    ax.set_title("Coverage conditional on trajectory depth")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, loc="lower right")

    title = figure_title(
        f"Gap vs agent self-report — {env}",
        f"Test coverage split by rollout; α={alpha}",
    )
    top = apply_figure_suptitle(fig, title)
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(f"figures/gap_{env}.png", dpi=200)
    print(table.to_string(index=False))
    print(f"\nwrote figures/gap_{env}.png, tables/gap_{env}.csv")
    return table


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "sokoban")
