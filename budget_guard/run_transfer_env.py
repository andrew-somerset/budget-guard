"""budget_guard/run_transfer_env.py — cross-ENV transfer: the hardest cold start.

Guard trained + calibrated on sokoban (short puzzle runs, ~2.5k-token budgets),
then deployed on searchr1 and swebench streams (different task type, budgets up to
~7k ctx and vastly longer trajectories) with the same agent model. Token scales and
trajectory shapes shift together — frozen conformal should break badly; the online
methods see labels as runs complete and must re-find coverage.

Usage: python -m budget_guard.run_transfer_env
Writes figures/transfer_env.png, tables/transfer_env.csv and
tables/transfer_env_per_seed.csv.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, aci_cqr, cqr_split, dtaci, windowed_cqr, tune_gamma
from .data import ENVS, load_env
from .features import build_xy
from .metrics import (
    frac_unbounded,
    marginal_coverage,
    normalized_width,
    pooled_bootstrap_ci,
    rollout_bootstrap_draws,
)
from .plotting import UNBOUNDED_NOTE, group_bar_width, mark_unbounded, nominal_line
from .split import group_split

AQUA, YELLOW, VIOLET, GREEN = "#1baf7a", "#eda100", "#4a3aa7", "#008300"
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
                "ACI-CQR": aci_cqr(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, gamma=gamma, groups=gte)[:2],
                "windowed-CQR": windowed_cqr(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, groups=gte)[:2],
                "DtACI": dtaci(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, groups=gte)[:2],
            }.items():
                draws = rollout_bootstrap_draws(yte, lo, hi, gte, seed=seed)
                rows.append({
                    "target_env": env, "method": name, "seed": seed,
                    "coverage": marginal_coverage(yte, lo, hi),
                    # per-seed 90% cluster-bootstrap CI (quantiles of this seed's draws)
                    "ci_lo": float(np.quantile(draws, 0.05)),
                    "ci_hi": float(np.quantile(draws, 0.95)),
                    "normalized_width": normalized_width(yte, lo, hi, agg="median"),
                    "frac_unbounded": frac_unbounded(hi),
                    "_draws": draws,  # pooled across seeds for the aggregate band
                })
    per_seed = pd.DataFrame(rows)
    table = (per_seed.groupby(["target_env", "method"], sort=False)
             .agg(coverage=("coverage", "mean"), cov_std=("coverage", "std"),
                  normalized_width=("normalized_width", "mean"),
                  frac_unbounded=("frac_unbounded", "mean")).reset_index())
    # Aggregate band: pooled seed×rollout bootstrap quantiles, NOT a mean of
    # per-seed CI endpoints (which is not a CI and hides seed-to-seed spread —
    # see metrics.rollout_bootstrap_mean_draws).
    pooled = per_seed.groupby(["target_env", "method"], sort=False)["_draws"].apply(
        lambda s: pooled_bootstrap_ci(list(s))
    )
    assert len(pooled) == len(table)
    table["ci_lo"] = [c[0] for c in pooled]
    table["ci_hi"] = [c[1] for c in pooled]

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    per_seed.drop(columns=["_draws"]).to_csv(
        "tables/transfer_env_per_seed.csv", index=False
    )
    table.to_csv("tables/transfer_env.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    method_order = ["split-CQR (frozen)", "ACI-CQR", "windowed-CQR", "DtACI"]
    colors = {"split-CQR (frozen)": AQUA, "ACI-CQR": YELLOW, "windowed-CQR": VIOLET, "DtACI": GREEN}
    xs = np.arange(len(targets))
    width = group_bar_width(len(method_order))
    fig, ax = plt.subplots(figsize=(9, 5.0), constrained_layout=True)
    any_unbounded = False
    for i, method in enumerate(method_order):
        sub = [table[(table["target_env"] == e) & (table["method"] == method)].iloc[0] for e in targets]
        vals = [float(s["coverage"]) for s in sub]
        fracs = [float(s.get("frac_unbounded", np.nan)) for s in sub]
        yerr = np.clip(np.array([[v - float(s["ci_lo"]) for v, s in zip(vals, sub)],
                                 [float(s["ci_hi"]) - v for v, s in zip(vals, sub)]]), 0, None)
        offset = (i - (len(method_order) - 1) / 2) * width
        bars = ax.bar(xs + offset, vals, width=width * 0.86, color=colors[method], label=method,
                      yerr=yerr, capsize=3, error_kw={"lw": 1, "alpha": 0.7})
        any_unbounded |= mark_unbounded(ax, bars, fracs, vals)
        for bar, v, s in zip(bars, vals, sub):
            ax.text(bar.get_x() + bar.get_width() / 2, float(s["ci_hi"]) + 0.02, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=7.5)
    nominal_line(ax, alpha)
    ax.set_xticks(xs, [f"sokoban → {e}" for e in targets])
    ax.set_ylim(0, 1.16)
    ax.set_ylabel("marginal coverage on target stream")
    title = ("Cross-env transfer (same model): frozen conformal collapses, online self-heals\n"
             f"calibrated on sokoban, deployed on new task types ({len(seeds)} seeds; "
             "band = 90% pooled seed×rollout cluster bootstrap)")
    if any_unbounded:
        title += f"\n{UNBOUNDED_NOTE}"
    ax.set_title(title, fontsize=10.5)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    # Legend below the axes: loc="center" put it on top of the bars.
    ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.07))
    fig.savefig("figures/transfer_env.png", dpi=200, bbox_inches="tight")

    print(table.to_string(index=False))
    print("\nwrote figures/transfer_env.png, tables/transfer_env.csv, "
          "tables/transfer_env_per_seed.csv")
    return table


if __name__ == "__main__":
    main()
