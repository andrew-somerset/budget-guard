"""budget_guard/run_conditional.py — item 2: conditional (per-depth) coverage.

Marginal coverage can sit near nominal while coverage at a specific turn depth k
collapses — and k is exactly where the abort decision gets made. This regenerates the
by-depth breakdown for split-CQR (one global qhat) vs Mondrian-CQR (one qhat per depth
bucket), per env, over 5 seeds, with rollout cluster-bootstrap CIs and a worst-slice
column. Extends the single-env Week-2 diagnostic in run_gap.py.

Usage: python -m budget_guard.run_conditional
Writes figures/conditional_coverage.png and tables/conditional_coverage.csv.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, cqr_split, mondrian_cqr
from .data import ENVS, load_env
from .features import build_xy
from .metrics import marginal_coverage, pooled_bootstrap_ci, rollout_bootstrap_draws
from .split import group_split

BUCKET_EDGES = (2, 3)              # k=1 / k=2 / k>=3  (matches conformal.mondrian_cqr)
BUCKETS = {0: "k=1", 1: "k=2", 2: "k>=3"}
AQUA, VIOLET, GRAY = "#1baf7a", "#4a3aa7", "#8B93A1"


def _slices(k_te: np.ndarray):
    b = np.digitize(k_te, BUCKET_EDGES)
    yield "marginal", np.ones(len(k_te), dtype=bool)
    for code, name in BUCKETS.items():
        yield name, (b == code)


def run_env(env: str, seed: int, alpha: float = DEFAULT_ALPHA) -> list[dict]:
    df, _ = load_env(env)
    X, y, groups = build_xy(df)
    m = group_split(df, seed=seed)
    tr, ca, te = m["train"], m["cal"], m["test"]
    k_ca, k_te = df.loc[ca, "k"].to_numpy(), df.loc[te, "k"].to_numpy()
    yte, gte = y[te], groups[te]

    methods = {
        "split-CQR": cqr_split(X[tr], y[tr], X[ca], y[ca], X[te], alpha=alpha)[:2],
        "Mondrian-CQR": mondrian_cqr(
            X[tr], y[tr], X[ca], y[ca], k_ca, X[te], k_te, alpha=alpha
        )[:2],
    }
    rows = []
    for name, (lo, hi) in methods.items():
        for slice_name, sel in _slices(k_te):
            if sel.sum() < 5:
                continue
            draws = rollout_bootstrap_draws(yte[sel], lo[sel], hi[sel], gte[sel], seed=seed)
            rows.append({
                "env": env, "seed": seed, "method": name, "slice": slice_name,
                "coverage": marginal_coverage(yte[sel], lo[sel], hi[sel]),
                # per-seed 90% cluster-bootstrap CI (quantiles of this seed's draws)
                "ci_lo": float(np.quantile(draws, 0.05)),
                "ci_hi": float(np.quantile(draws, 0.95)),
                "n": int(sel.sum()),
                "_draws": draws,
            })
    return rows


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4), alpha: float = DEFAULT_ALPHA):
    rows = []
    for seed in seeds:
        for env in ENVS:
            rows += run_env(env, seed, alpha)
    per = pd.DataFrame(rows)
    agg = (per.groupby(["env", "method", "slice"], sort=False)
           .agg(coverage=("coverage", "mean"), cov_std=("coverage", "std"),
                n=("n", "mean")).reset_index())
    # Aggregate band: pooled seed×rollout bootstrap quantiles, NOT a mean of
    # per-seed CI endpoints (which is not a CI; see metrics.rollout_bootstrap_mean_draws).
    pooled = per.groupby(["env", "method", "slice"], sort=False)["_draws"].apply(
        lambda s: pooled_bootstrap_ci(list(s))
    )
    assert len(pooled) == len(agg)
    agg["ci_lo"] = [c[0] for c in pooled]
    agg["ci_hi"] = [c[1] for c in pooled]

    # worst-slice: min coverage over the k-buckets (not marginal), per env×method×seed,
    # then averaged over seeds — the number a reviewer worried about conditional coverage
    # actually cares about.
    buckets = per[per["slice"] != "marginal"]
    worst = (buckets.groupby(["env", "method", "seed"])["coverage"].min()
             .groupby(level=[0, 1]).mean().reset_index(name="worst_slice_cov"))

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    agg.to_csv("tables/conditional_coverage.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = ["k=1", "k=2", "k>=3"]
    envs = list(ENVS)

    # Floor the y-axis below the lowest CI actually drawn. With a fixed 0.5 floor the
    # searchr1 k=2 interval (ci_lo 0.43) ran off the bottom of the panel with no cue
    # that it had been cut.
    drawn = agg[agg["slice"].isin(order)]
    ylo = float(min(0.5, drawn["ci_lo"].min() - 0.03)) if not drawn.empty else 0.5

    fig, axes = plt.subplots(1, len(envs), figsize=(3.6 * len(envs), 4.0),
                             constrained_layout=True, sharey=True)
    axes = np.atleast_1d(axes)
    for ax, env in zip(axes, envs):
        for method, color in [("split-CQR", AQUA), ("Mondrian-CQR", VIOLET)]:
            # Reindex WITHOUT dropping: every panel keeps the same three x slots, so a
            # depth means the same position in all of them. Dropping first put
            # searchr1's k=2 at the far-right slot, aligning it with sokoban's k>=3.
            sub = (agg[(agg["env"] == env) & (agg["method"] == method)]
                   .set_index("slice").reindex(order))
            have = sub["coverage"].notna().to_numpy()
            if not have.any():
                continue
            xs = np.arange(len(order))[have]
            cov = sub["coverage"].to_numpy()[have]
            yerr = np.vstack([cov - sub["ci_lo"].to_numpy()[have],
                              sub["ci_hi"].to_numpy()[have] - cov])
            ax.errorbar(xs, cov, yerr=yerr, marker="o", ms=5, lw=2,
                        capsize=3, color=color, label=method)
        ax.set_xticks(np.arange(len(order)), order)
        # Padding keeps the outer ticks off the panel edges; without it the last tick of
        # one panel and the first of the next collided across the gap ("k>=3 k=1").
        ax.set_xlim(-0.5, len(order) - 0.5)
        ax.axhline(1 - alpha, color=GRAY, lw=1.2, ls="--")
        ax.set_title(env)
        ax.set_ylim(ylo, 1.05)
        ax.grid(alpha=0.25)
        ax.set_axisbelow(True)
    # Short label: the long form overflowed the 4-inch axis and was clipped at both
    # ends. What the bars mean belongs in the caption, per NeurIPS convention.
    axes[0].set_ylabel("coverage")
    axes[-1].legend(frameon=False, fontsize=9)
    fig.suptitle(f"Conditional coverage by turn depth: split-CQR vs Mondrian-CQR "
                 f"(nominal {1 - alpha:.2f})")
    fig.savefig("figures/conditional_coverage.png", dpi=200, bbox_inches="tight")

    print(agg.to_string(index=False))
    print("\nworst-slice coverage (min over k-buckets, mean over seeds):")
    print(worst.to_string(index=False))
    print("\nwrote figures/conditional_coverage.png, tables/conditional_coverage.csv")
    return agg, worst


if __name__ == "__main__":
    main()
