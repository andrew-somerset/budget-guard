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
from .metrics import frac_unbounded, marginal_coverage, normalized_width, rollout_bootstrap_ci
from .split import group_split

AQUA, YELLOW, VIOLET = "#1baf7a", "#eda100", "#4a3aa7"
SOURCE = "sokoban"


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4), alpha: float = DEFAULT_ALPHA):
    src, _ = load_env(SOURCE)
    Xs, ys, gs = build_xy(src)
    targets = [env for env in ENVS if env != SOURCE]
    tgt_data = {env: build_xy(load_env(env)[0]) for env in targets}  # stream is seed-independent

    rows = []
    for seed in seeds:
        masks = group_split(src, fracs=(0.7, 0.3, 0.0), seed=seed)
        tr, ca = masks["train"], masks["cal"]
        Xtr, ytr, Xca, yca = Xs[tr], ys[tr], Xs[ca], ys[ca]
        gamma = tune_gamma(Xtr, ytr, Xca, yca, gs[ca], alpha=alpha, seed=seed)
        for env in targets:
            Xte, yte, gte = tgt_data[env]
            for name, (lo, hi) in {
                "split-CQR (frozen)": cqr_split(Xtr, ytr, Xca, yca, Xte, alpha=alpha)[:2],
                "ACI-CQR": aci_cqr(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, gamma=gamma)[:2],
                "SPCI": spci(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha)[:2],
            }.items():
                ci = rollout_bootstrap_ci(yte, lo, hi, gte, seed=seed)
                rows.append({
                    "target_env": env, "method": name, "seed": seed,
                    "coverage": marginal_coverage(yte, lo, hi),
                    "ci_lo": ci[0], "ci_hi": ci[1],
                    "normalized_width": normalized_width(yte, lo, hi, agg="median"),
                    "frac_unbounded": frac_unbounded(hi),
                })
    table = (pd.DataFrame(rows).groupby(["target_env", "method"], sort=False)
             .agg(coverage=("coverage", "mean"), cov_std=("coverage", "std"),
                  ci_lo=("ci_lo", "mean"), ci_hi=("ci_hi", "mean"),
                  normalized_width=("normalized_width", "mean"),
                  frac_unbounded=("frac_unbounded", "mean")).reset_index())

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    table.to_csv("tables/transfer_env.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    method_order = ["split-CQR (frozen)", "ACI-CQR", "SPCI"]
    colors = {"split-CQR (frozen)": AQUA, "ACI-CQR": YELLOW, "SPCI": VIOLET}
    xs = np.arange(len(targets))
    width = 0.24

    fig, ax = plt.subplots(figsize=(8, 4.6), constrained_layout=True)
    for i, method in enumerate(method_order):
        sub = [table[(table["target_env"] == e) & (table["method"] == method)].iloc[0] for e in targets]
        vals = [float(s["coverage"]) for s in sub]
        yerr = np.clip(np.array([[v - float(s["ci_lo"]) for v, s in zip(vals, sub)],
                                 [float(s["ci_hi"]) - v for v, s in zip(vals, sub)]]), 0, None)
        offset = (i - (len(method_order) - 1) / 2) * width
        bars = ax.bar(xs + offset, vals, width=width - 0.03, color=colors[method], label=method,
                      yerr=yerr, capsize=3, error_kw={"lw": 1, "alpha": 0.7})
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, min(v + 0.03, 1.08), f"{v:.2f}",
                    ha="center", fontsize=8)
    ax.axhline(1 - alpha, color="#4A5361", lw=1.2, ls="--")
    ax.text(0.995, 1 - alpha + 0.015, f"nominal {1 - alpha:.2f}", ha="right",
            transform=ax.get_yaxis_transform(), fontsize=9, color="#4A5361")
    ax.set_xticks(xs, [f"sokoban → {e}" for e in targets])
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("marginal coverage on target stream")
    ax.set_title("Cross-env transfer (same model): frozen conformal collapses, online self-heals\n"
                 f"calibrated on sokoban, deployed on new task types ({len(seeds)} seeds, cluster-bootstrap CI)")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, ncol=1, loc="center")
    fig.savefig("figures/transfer_env.png", dpi=200)

    print(table.to_string(index=False))
    print("\nwrote figures/transfer_env.png, tables/transfer_env.csv")
    return table


if __name__ == "__main__":
    main()
