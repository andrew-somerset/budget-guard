"""budget_guard/run_transfer_env.py — cross-ENV transfer: the hardest cold start.

Guard trained + calibrated on sokoban (short puzzle runs, ~2.5k-token budgets),
then deployed on searchr1 and swebench streams (different task type, budgets up to
~7k ctx and vastly longer trajectories) with the same agent model. Token scales and
trajectory shapes shift together — frozen conformal should break badly; the online
methods see labels as runs complete and must re-find coverage.

Usage: python -m budget_guard.run_transfer_env
Writes figures/transfer_env.png and tables/transfer_env.csv.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, aci_cqr, cqr_split, spci, tune_gamma
from .data import ENVS, load_env
from .features import build_xy
from .metrics import frac_unbounded, marginal_coverage, normalized_width
from .split import group_split

AQUA, YELLOW, VIOLET = "#1baf7a", "#eda100", "#4a3aa7"
SOURCE = "sokoban"


def main(seed: int = 0, alpha: float = DEFAULT_ALPHA):
    src, _ = load_env(SOURCE)
    X, y, groups = build_xy(src)
    masks = group_split(src, fracs=(0.7, 0.3, 0.0), seed=seed)
    tr, ca = masks["train"], masks["cal"]
    Xtr, ytr, Xca, yca = X[tr], y[tr], X[ca], y[ca]
    gamma = tune_gamma(Xtr, ytr, Xca, yca, groups[ca], alpha=alpha, seed=seed)

    rows = []
    targets = [env for env in ENVS if env != SOURCE]
    for env in targets:
        tgt, _ = load_env(env)
        Xte, yte, _ = build_xy(tgt)
        for name, (lo, hi) in {
            "split-CQR (frozen)": cqr_split(Xtr, ytr, Xca, yca, Xte, alpha=alpha)[:2],
            "ACI-CQR": aci_cqr(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, gamma=gamma)[:2],
            "SPCI": spci(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha)[:2],
        }.items():
            rows.append(
                {
                    "source": SOURCE,
                    "target_env": env,
                    "method": name,
                    "coverage": marginal_coverage(yte, lo, hi),
                    "normalized_width": normalized_width(yte, lo, hi, agg="median"),
                    "frac_unbounded": frac_unbounded(hi),
                    "n_test": len(yte),
                    "gamma": gamma if name == "ACI-CQR" else np.nan,
                }
            )
    table = pd.DataFrame(rows)

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    table.to_csv("tables/transfer_env.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = ["split-CQR (frozen)", "ACI-CQR", "SPCI"]
    colors = {"split-CQR (frozen)": AQUA, "ACI-CQR": YELLOW, "SPCI": VIOLET}
    xs = np.arange(len(targets))
    width = 0.24

    fig, ax = plt.subplots(figsize=(8, 4.4), constrained_layout=True)
    for i, method in enumerate(methods):
        vals = [
            table[(table["target_env"] == e) & (table["method"] == method)]["coverage"].item()
            for e in targets
        ]
        offset = (i - (len(methods) - 1) / 2) * width
        bars = ax.bar(xs + offset, vals, width=width - 0.03, color=colors[method], label=method)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.012, f"{v:.2f}",
                    ha="center", fontsize=8)
    ax.axhline(1 - alpha, color="#4A5361", lw=1.2, ls="--")
    ax.text(0.995, 1 - alpha + 0.015, f"nominal {1 - alpha:.2f}", ha="right",
            transform=ax.get_yaxis_transform(), fontsize=9, color="#4A5361")
    ax.set_xticks(xs, [f"sokoban → {e}" for e in targets])
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("marginal coverage on target stream")
    ax.set_title("Cross-env transfer: guard calibrated on sokoban, deployed on new task types")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.06))
    fig.savefig("figures/transfer_env.png", dpi=200)

    print(table.to_string(index=False))
    print("\nwrote figures/transfer_env.png, tables/transfer_env.csv")
    return table


if __name__ == "__main__":
    main()
