"""budget_guard/run_label_efficiency.py — how much logging before the guard is trustworthy?

The PI question, quantified: y_t labels are self-supervised (every completed run
reveals its own), so "no labels on a new task" = cold start. This measures coverage
of split-CQR as a function of the number of *calibration rollouts*, holding the
underlying quantile model and the test set fixed. For each budget m we pool S fixed
seeds x R calibration-subset redraws and report the mean and the 10-90% band.

Usage: python -m budget_guard.run_label_efficiency [env]   (default: sokoban)
Writes figures/label_efficiency_<env>.png and tables/label_efficiency_<env>.csv.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, _cqr_scores, _finite_sample_quantile, _fit_cqr
from .data import load_env
from .features import build_xy
from .plotting import nominal_line
from .split import group_split

BLUE, GRAY = "#2a78d6", "#8B93A1"


def run(env: str = "sokoban", seeds: tuple[int, ...] = (0, 1, 2, 3, 4),
        alpha: float = DEFAULT_ALPHA, redraws: int = 30):
    df, _ = load_env(env)
    X, y, groups = build_xy(df)
    budget_grid = (2, 3, 5, 8, 12, 16, 24, 32)

    samples: dict[int, list[float]] = {}
    inf_fracs: dict[int, list[float]] = {}
    for seed in seeds:
        masks = group_split(df, fracs=(0.5, 0.25, 0.25), seed=seed)
        tr, ca, te = masks["train"], masks["cal"], masks["test"]
        mlo, mhi = _fit_cqr(X[tr], y[tr], alpha)
        qlo_te, qhi_te = mlo.predict(X[te]), mhi.predict(X[te])
        yte = y[te]
        cal_scores = _cqr_scores(mlo.predict(X[ca]), mhi.predict(X[ca]), y[ca])
        cal_rollouts = groups[ca]
        pool = np.unique(cal_rollouts)
        rng = np.random.default_rng(seed)
        for m in budget_grid:
            if m > len(pool):
                continue
            for _ in range(redraws):
                chosen = rng.choice(pool, size=m, replace=False)
                scores = cal_scores[np.isin(cal_rollouts, chosen)]
                qhat = _finite_sample_quantile(scores, alpha)
                lo = np.maximum(qlo_te - qhat, 0.0)
                hi = qhi_te + qhat
                samples.setdefault(m, []).append(float(np.mean((lo <= yte) & (yte <= hi))))
                # At tiny m the finite-sample level exceeds 1 and qhat = inf: the
                # curve's "fail-safe ~1.0" points are unbounded intervals counted
                # as covered. Record the fraction so the table/figure disclose it.
                inf_fracs.setdefault(m, []).append(float(not np.isfinite(qhat)))

    budgets = sorted(samples)
    table = pd.DataFrame([
        {"env": env, "n_cal_rollouts": m,
         "coverage_mean": float(np.mean(samples[m])),
         "coverage_p10": float(np.quantile(samples[m], 0.10)),
         "coverage_p90": float(np.quantile(samples[m], 0.90)),
         "frac_draws_unbounded": float(np.mean(inf_fracs[m])),
         "n_draws": len(samples[m])}
        for m in budgets
    ])

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    table.to_csv(f"tables/label_efficiency_{env}.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 4.2), constrained_layout=True)
    ax.fill_between(table["n_cal_rollouts"], table["coverage_p10"], table["coverage_p90"],
                    color=BLUE, alpha=0.18, lw=0, label="10-90% over seeds x redraws")
    ax.plot(table["n_cal_rollouts"], table["coverage_mean"], marker="o", ms=5, lw=2,
            color=BLUE, label="mean coverage")
    nominal_line(ax, alpha, color=GRAY)
    ax.set_xscale("log")
    ax.set_xticks(budgets)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _pos: f"{int(v)}"))
    ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.set_xlabel("calibration rollouts (completed runs logged)")
    ax.set_ylabel("test coverage")
    ax.set_ylim(0.6, 1.02)
    ax.set_title(f"{env}: label efficiency of the guard (split-CQR, alpha={alpha}, "
                 f"{len(seeds)} seeds x {redraws} redraws)")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.savefig(f"figures/label_efficiency_{env}.png", dpi=200)

    print(table.to_string(index=False))
    print(f"\nwrote figures/label_efficiency_{env}.png, tables/label_efficiency_{env}.csv")
    return table


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "sokoban")
