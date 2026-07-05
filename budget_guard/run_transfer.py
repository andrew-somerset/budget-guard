"""budget_guard/run_transfer.py — the deployment story: guard survives model swap.

Answers the PI question "how does the wrapper generalize when ground-truth labels
are not available?" empirically. Setting: the guard is trained + calibrated on
logged claude-opus-4.7 SWE-bench runs. The deployed agent is then a *different*
model, so no labels from the new distribution exist at time zero — but every
completed run reveals its label, and the online methods consume them.

Frozen split-CQR (never updates) vs ACI-CQR and SPCI (adapt online) on each
target model's rollout stream.

Usage: python -m budget_guard.run_transfer
Writes figures/transfer_swebench.png and tables/transfer_swebench.csv.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, aci_cqr, cqr_split, spci, tune_gamma
from .extract import flatten_to_samples, load_rollouts, samples_to_dataframe
from .features import build_xy
from .metrics import frac_unbounded, marginal_coverage, normalized_width
from .split import group_split

_DATA = os.path.join(os.path.dirname(__file__), "..", "data", "bagen_hf", "estimation")
SOURCE = "swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main"
MAX_CTX = 7060

BLUE, AQUA, YELLOW, VIOLET, GRAY = "#2a78d6", "#1baf7a", "#eda100", "#4a3aa7", "#8B93A1"


def _load(run_dir: str) -> pd.DataFrame:
    (path,) = glob.glob(f"{_DATA}/{run_dir}/*eval_estimation_dialogues.json")
    return samples_to_dataframe(flatten_to_samples(load_rollouts(path), max_ctx=MAX_CTX))


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


def main(seed: int = 0, alpha: float = DEFAULT_ALPHA):
    src = _load(SOURCE)
    X, y, groups = build_xy(src)
    masks = group_split(src, fracs=(0.7, 0.3, 0.0), seed=seed)
    tr, ca = masks["train"], masks["cal"]
    Xtr, ytr, Xca, yca = X[tr], y[tr], X[ca], y[ca]
    gamma = tune_gamma(Xtr, ytr, Xca, yca, groups[ca], alpha=alpha, seed=seed)

    rows = []
    for model, run_dir in target_runs().items():
        tgt = _load(run_dir)
        Xte, yte, _ = build_xy(tgt)
        for name, (lo, hi) in {
            "split-CQR (frozen)": cqr_split(Xtr, ytr, Xca, yca, Xte, alpha=alpha)[:2],
            "ACI-CQR": aci_cqr(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, gamma=gamma)[:2],
            "SPCI": spci(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha)[:2],
        }.items():
            rows.append(
                {
                    "target_model": model,
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
    table.to_csv("tables/transfer_swebench.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = ["split-CQR (frozen)", "ACI-CQR", "SPCI"]
    colors = {"split-CQR (frozen)": AQUA, "ACI-CQR": YELLOW, "SPCI": VIOLET}
    models = list(dict.fromkeys(table["target_model"]))
    xs = np.arange(len(models))
    width = 0.24

    fig, ax = plt.subplots(figsize=(9.5, 4.4), constrained_layout=True)
    for i, method in enumerate(methods):
        vals = [
            table[(table["target_model"] == m) & (table["method"] == method)]["coverage"].item()
            for m in models
        ]
        offset = (i - (len(methods) - 1) / 2) * width
        bars = ax.bar(xs + offset, vals, width=width - 0.03, color=colors[method], label=method)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.012, f"{v:.2f}",
                    ha="center", fontsize=8)
    ax.axhline(1 - alpha, color="#4A5361", lw=1.2, ls="--")
    ax.text(0.995, 1 - alpha + 0.015, f"nominal {1 - alpha:.2f}", ha="right",
            transform=ax.get_yaxis_transform(), fontsize=9, color="#4A5361")
    ax.set_xticks(xs, models)
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("marginal coverage on target stream")
    ax.set_title("Model-swap transfer (SWE-bench): guard calibrated on claude-opus-4.7, "
                 "deployed on other models")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.06))
    fig.savefig("figures/transfer_swebench.png", dpi=200)

    print(table.to_string(index=False))
    print("\nwrote figures/transfer_swebench.png, tables/transfer_swebench.csv")
    return table


if __name__ == "__main__":
    main()
