"""budget_guard/run_transfer.py — the deployment story: guard survives model swap.

Answers the PI question "how does the wrapper generalize when ground-truth labels
are not available?" empirically. Setting: the guard is trained + calibrated on
logged claude-opus-4.7 SWE-bench runs. The deployed agent is then a *different*
model, so no labels from the new distribution exist at time zero — but every
completed run reveals its label, and the online methods consume them.

Frozen split-CQR (never updates) vs ACI-CQR, windowed-CQR, and parameter-free DtACI
(adapt online, rollout-safe label revelation) on each target model's stream.

Five seeds with rollout cluster-bootstrap CIs, matching run_transfer_env and the
project's >=5-seed rule for headline tables (this script was single-seed until
2026-08-01, the only headline transfer figure without a variability estimate).

Usage: python -m budget_guard.run_transfer
Writes figures/transfer_swebench.png, tables/transfer_swebench.csv and
tables/transfer_swebench_per_seed.csv.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, aci_cqr, cqr_split, dtaci, windowed_cqr, tune_gamma
from .extract import flatten_to_samples, load_rollouts, samples_to_dataframe
from .features import build_xy
from .metrics import (
    frac_unbounded,
    marginal_coverage,
    normalized_width,
    pooled_bootstrap_ci,
    rollout_bootstrap_draws,
)
from .plotting import UNBOUNDED_NOTE, apply_figure_title, figure_title, group_bar_width, mark_unbounded, nominal_line
from .split import group_split

_DATA = os.path.join(os.path.dirname(__file__), "..", "data", "bagen_hf", "estimation")
SOURCE = "swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main"
# Fallback only (= the opus source record's official value). Each run's actual
# context window comes from its own estimation record: the five swebench runs use
# 7060 / 6772 / 10472 / 8265 / 21711 — one constant corrupts can_finish vs the
# official ground truth on up to 19% of a target's samples.
MAX_CTX = 7060

BLUE, AQUA, YELLOW, VIOLET, GREEN, GRAY = "#2a78d6", "#1baf7a", "#eda100", "#4a3aa7", "#008300", "#8B93A1"


def _official_max_ctx(run_dir: str) -> int:
    """The run's own recorded max_context_window_tokens, else the MAX_CTX fallback."""
    for path in glob.glob(f"{_DATA}/{run_dir}/*.json"):
        if "dialogues" in path or path.endswith("_pairs.json"):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                ctx = (json.load(handle).get("config") or {}).get("max_context_window_tokens")
        except (json.JSONDecodeError, OSError):
            continue
        if ctx:
            return int(ctx)
    return MAX_CTX


def _load(run_dir: str) -> pd.DataFrame:
    (path,) = glob.glob(f"{_DATA}/{run_dir}/*eval_estimation_dialogues.json")
    return samples_to_dataframe(
        flatten_to_samples(load_rollouts(path), max_ctx=_official_max_ctx(run_dir))
    )


def target_runs() -> dict[str, str]:
    """Other-model SWE-bench runs that ship raw dialogues."""
    out = {}
    for path in sorted(glob.glob(f"{_DATA}/swebench-*/*eval_estimation_dialogues.json")):
        run_dir = os.path.basename(os.path.dirname(path))
        if run_dir == SOURCE:
            continue
        model = run_dir.split("-origin-")[1].split("_")[0]
        out[model] = run_dir
    return out


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4), alpha: float = DEFAULT_ALPHA):
    src = _load(SOURCE)
    X, y, groups = build_xy(src)
    # Target streams do not depend on the seed (only the source train/cal split does),
    # so load and featurize each one once rather than per seed.
    tgt_data = {model: build_xy(_load(run_dir)) for model, run_dir in target_runs().items()}

    rows = []
    for seed in seeds:
        masks = group_split(src, fracs=(0.7, 0.3, 0.0), seed=seed)
        tr, ca = masks["train"], masks["cal"]
        Xtr, ytr, Xca, yca = X[tr], y[tr], X[ca], y[ca]
        gamma = tune_gamma(Xtr, ytr, Xca, yca, groups[ca], alpha=alpha, seed=seed)

        for model, (Xte, yte, gte) in tgt_data.items():
            for name, (lo, hi) in {
                "split-CQR (frozen)": cqr_split(Xtr, ytr, Xca, yca, Xte, alpha=alpha)[:2],
                "ACI-CQR": aci_cqr(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, gamma=gamma, groups=gte)[:2],
                "windowed-CQR": windowed_cqr(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, groups=gte)[:2],
                "DtACI": dtaci(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, groups=gte)[:2],
            }.items():
                draws = rollout_bootstrap_draws(yte, lo, hi, gte, seed=seed)
                rows.append(
                    {
                        "target_model": model,
                        "method": name,
                        "seed": seed,
                        "coverage": marginal_coverage(yte, lo, hi),
                        # per-seed 90% cluster-bootstrap CI (quantiles of this
                        # seed's draws — identical to rollout_bootstrap_ci)
                        "ci_lo": float(np.quantile(draws, 0.05)),
                        "ci_hi": float(np.quantile(draws, 0.95)),
                        "normalized_width": normalized_width(yte, lo, hi, agg="median"),
                        "frac_unbounded": frac_unbounded(hi),
                        "n_test": len(yte),
                        "gamma": gamma if name == "ACI-CQR" else np.nan,
                        "_draws": draws,  # pooled across seeds for the aggregate band
                    }
                )
    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)

    per_seed = pd.DataFrame(rows)
    per_seed.drop(columns=["_draws"]).to_csv(
        "tables/transfer_swebench_per_seed.csv", index=False
    )
    # gamma is deliberately NOT mean-aggregated: tune_gamma picks from a discrete
    # grid (0.05 or 0.005 across these seeds), so a mean (0.023) is a value no run
    # ever used. The per-seed CSV carries the real selections.
    table = (
        per_seed.groupby(["target_model", "method"], sort=False)
        .agg(
            coverage=("coverage", "mean"),
            cov_std=("coverage", "std"),
            normalized_width=("normalized_width", "mean"),
            frac_unbounded=("frac_unbounded", "mean"),
            n_test=("n_test", "first"),
        )
        .reset_index()
    )
    # Aggregate band: POOL the per-seed bootstrap draws, then take quantiles —
    # carries both within-seed (rollout resampling) and between-seed (calibration
    # split) variance. Averaging per-seed CI endpoints (the pre-2026-08-01
    # behavior) understated the band by up to 10x when some seeds sat at 1.0.
    pooled = per_seed.groupby(["target_model", "method"], sort=False)["_draws"].apply(
        lambda s: pooled_bootstrap_ci(list(s))
    )
    assert len(pooled) == len(table)
    table["ci_lo"] = [c[0] for c in pooled]
    table["ci_hi"] = [c[1] for c in pooled]

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    table.to_csv("tables/transfer_swebench.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = ["split-CQR (frozen)", "ACI-CQR", "windowed-CQR", "DtACI"]
    colors = {"split-CQR (frozen)": AQUA, "ACI-CQR": YELLOW, "windowed-CQR": VIOLET, "DtACI": GREEN}
    models = list(dict.fromkeys(table["target_model"]))
    xs = np.arange(len(models))

    width = group_bar_width(len(methods))
    fig, ax = plt.subplots(figsize=(10, 5.0), constrained_layout=True)
    any_unbounded = False
    for i, method in enumerate(methods):
        sel = [table[(table["target_model"] == m) & (table["method"] == method)].iloc[0] for m in models]
        vals = [float(s["coverage"]) for s in sel]
        fracs = [float(s["frac_unbounded"]) for s in sel]
        yerr = np.clip(np.array([[v - float(s["ci_lo"]) for v, s in zip(vals, sel)],
                                 [float(s["ci_hi"]) - v for v, s in zip(vals, sel)]]), 0, None)
        offset = (i - (len(methods) - 1) / 2) * width
        bars = ax.bar(xs + offset, vals, width=width * 0.86, color=colors[method], label=method,
                      yerr=yerr, capsize=3, error_kw={"lw": 1, "alpha": 0.7})
        any_unbounded |= mark_unbounded(ax, bars, fracs, vals)
        for bar, v, s in zip(bars, vals, sel):
            ax.text(bar.get_x() + bar.get_width() / 2, float(s["ci_hi"]) + 0.02, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=7.5)
    nominal_line(ax, alpha)
    ax.set_xticks(xs, models)
    ax.set_ylim(0, 1.16)
    ax.set_ylabel("marginal coverage on target stream")
    title = figure_title(
        "Model-swap transfer (SWE-bench): guard calibrated on claude-opus-4.7, deployed on other models",
        f"{len(seeds)} seeds; band = 90% pooled seed×rollout cluster bootstrap",
    )
    if any_unbounded:
        title += f"\n{UNBOUNDED_NOTE}"
    apply_figure_title(ax, title, fontsize=10.5)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.07))
    fig.savefig("figures/transfer_swebench.png", dpi=200, bbox_inches="tight")

    print(table.to_string(index=False))
    print("\nwrote figures/transfer_swebench.png, tables/transfer_swebench.csv, "
          "tables/transfer_swebench_per_seed.csv")
    return table


if __name__ == "__main__":
    main()
