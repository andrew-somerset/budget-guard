"""budget_guard/run_coverage.py — Week 3 headline: all methods, all envs (C1).

Within-run evaluation (split by rollout, same model claude-opus-4.7 everywhere):
split-absres, split-CQR, ACI-CQR (gamma tuned on CAL only), SPCI, plus the BAGEN
agent-self-report baseline from the official records. Online methods stream over
the test rows in trajectory order.

Usage: python -m budget_guard.run_coverage
Writes figures/coverage_main.png and tables/coverage.csv.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .conformal import (
    DEFAULT_ALPHA,
    aci_cqr,
    constant_quantile,
    cqr_split,
    dtaci,
    spci,
    split_conformal_absres,
    tune_gamma,
)
from .data import ENVS, load_env
from .features import build_xy
from .metrics import (
    frac_unbounded,
    marginal_coverage,
    median_width,
    normalized_width,
    rollout_bootstrap_ci,
)
from .split import group_split

BLUE, AQUA, YELLOW, VIOLET, GRAY = "#2a78d6", "#1baf7a", "#eda100", "#4a3aa7", "#8B93A1"
GREEN, RED = "#008300", "#e34948"
METHOD_COLORS = {
    "agent self-report": GRAY,
    "constant-quantile": RED,
    "split-absres": BLUE,
    "split-CQR": AQUA,
    "ACI-CQR": YELLOW,
    "SPCI": VIOLET,
    "DtACI": GREEN,
}


def run_env(env: str, seed: int = 0, alpha: float = DEFAULT_ALPHA) -> list[dict]:
    df, baseline = load_env(env)
    X, y, groups = build_xy(df)
    masks = group_split(df, seed=seed)
    tr, ca, te = masks["train"], masks["cal"], masks["test"]
    Xtr, ytr = X[tr], y[tr]
    Xca, yca = X[ca], y[ca]
    Xte, yte = X[te], y[te]

    gamma = tune_gamma(Xtr, ytr, Xca, yca, groups[ca], alpha=alpha, seed=seed)

    intervals = {}
    intervals["constant-quantile"] = constant_quantile(yca, len(yte), alpha=alpha)[:2]
    intervals["split-absres"] = split_conformal_absres(Xtr, ytr, Xca, yca, Xte, alpha=alpha)[:2]
    intervals["split-CQR"] = cqr_split(Xtr, ytr, Xca, yca, Xte, alpha=alpha)[:2]
    intervals["ACI-CQR"] = aci_cqr(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, gamma=gamma)[:2]
    intervals["SPCI"] = spci(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha)[:2]
    intervals["DtACI"] = dtaci(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha)[:2]

    rows = []
    if baseline is not None:
        rows.append(
            {"env": env, "method": "agent self-report", "coverage": baseline,
             "cov_ci90_lo": np.nan, "cov_ci90_hi": np.nan,
             "median_width": np.nan, "normalized_width": np.nan,
             "frac_unbounded": np.nan, "n_test": np.nan, "gamma": np.nan}
        )
    for name, (lo, hi) in intervals.items():
        ci_lo, ci_hi = rollout_bootstrap_ci(yte, lo, hi, groups[te])
        rows.append(
            {
                "env": env,
                "method": name,
                "coverage": marginal_coverage(yte, lo, hi),
                "cov_ci90_lo": ci_lo,
                "cov_ci90_hi": ci_hi,
                "median_width": median_width(lo, hi),
                "normalized_width": normalized_width(yte, lo, hi, agg="median"),
                "frac_unbounded": frac_unbounded(hi),
                "n_test": int(te.sum()),
                "gamma": gamma if name == "ACI-CQR" else np.nan,
            }
        )
    return rows


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4), alpha: float = DEFAULT_ALPHA):
    rows = []
    for seed in seeds:
        for env in ENVS:
            for row in run_env(env, seed=seed, alpha=alpha):
                rows.append({**row, "seed": seed})
    per_seed = pd.DataFrame(rows).drop_duplicates(
        subset=["env", "method", "seed"]  # baseline row repeats identically per seed
    )
    agg = (
        per_seed.groupby(["env", "method"], sort=False)
        .agg(
            coverage=("coverage", "mean"),
            coverage_std=("coverage", "std"),
            cov_ci90_lo=("cov_ci90_lo", "mean"),
            cov_ci90_hi=("cov_ci90_hi", "mean"),
            median_width=("median_width", "mean"),
            normalized_width=("normalized_width", "mean"),
            frac_unbounded=("frac_unbounded", "mean"),
            n_test=("n_test", "mean"),
        )
        .reset_index()
    )
    table = agg

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    per_seed.to_csv("tables/coverage_per_seed.csv", index=False)
    table.to_csv("tables/coverage.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    envs = list(ENVS)
    methods = list(METHOD_COLORS)
    fig, ax = plt.subplots(figsize=(10, 4.6), constrained_layout=True)
    width = 0.16
    xs = np.arange(len(envs))
    for i, method in enumerate(methods):
        vals, errs = [], []
        for env in envs:
            sel = table[(table["env"] == env) & (table["method"] == method)]
            vals.append(sel["coverage"].item() if len(sel) else np.nan)
            err = sel["coverage_std"].item() if len(sel) else np.nan
            errs.append(err if np.isfinite(err) else 0.0)
        offset = (i - (len(methods) - 1) / 2) * width
        bars = ax.bar(xs + offset, vals, width=width - 0.02,
                      color=METHOD_COLORS[method], label=method,
                      yerr=errs, error_kw={"ecolor": "#4A5361", "lw": 1, "capsize": 2})
        for bar, v, e in zip(bars, vals, errs):
            if np.isfinite(v):
                ax.text(bar.get_x() + bar.get_width() / 2, v + e + 0.014, f"{v:.2f}",
                        ha="center", fontsize=8)
    ax.axhline(1 - alpha, color="#4A5361", lw=1.2, ls="--")
    ax.text(0.995, 1 - alpha + 0.015, f"nominal {1 - alpha:.2f}", ha="right",
            transform=ax.get_yaxis_transform(), fontsize=9, color="#4A5361")
    ax.set_xticks(xs, envs)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("marginal coverage")
    ax.set_title("Remaining-budget interval coverage: BAGEN agent vs conformal guard "
                 f"(alpha={alpha}, claude-opus-4.7, mean±std over {len(seeds)} split seeds)")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, ncol=len(methods), loc="lower center",
              bbox_to_anchor=(0.5, 1.06))
    fig.savefig("figures/coverage_main.png", dpi=200)

    print(table.to_string(index=False))
    print("\nwrote figures/coverage_main.png, tables/coverage.csv")
    return table


if __name__ == "__main__":
    main()
