"""budget_guard/run_transfer.py — the deployment story: guard survives model swap.

Answers the PI question "how does the wrapper generalize when ground-truth labels
are not available?" empirically. Setting: the guard is trained + calibrated on
logged claude-opus-4.7 SWE-bench runs. The deployed agent is then a *different*
model, so no labels from the new distribution exist at time zero — but every
completed run reveals its label, and the online methods consume them.

Frozen split-CQR (never updates) vs ACI-CQR, SPCI, and parameter-free DtACI
(adapt online, rollout-safe label revelation) on each target model's stream.

Usage: python -m budget_guard.run_transfer
Writes figures/transfer_swebench.png and tables/transfer_swebench.csv.
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, aci_cqr, cqr_split, dtaci, spci, tune_gamma
from .extract import flatten_to_samples, load_rollouts, samples_to_dataframe
from .features import build_xy
from .metrics import frac_unbounded, marginal_coverage, normalized_width
from .plotting import UNBOUNDED_NOTE, group_bar_width, mark_unbounded, nominal_line
from .split import group_split

_DATA = os.path.join(os.path.dirname(__file__), "..", "data", "bagen_hf", "estimation")
SOURCE = "swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main"
MAX_CTX = 7060

BLUE, AQUA, YELLOW, VIOLET, GREEN, GRAY = "#2a78d6", "#1baf7a", "#eda100", "#4a3aa7", "#008300", "#8B93A1"


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
        Xte, yte, gte = build_xy(tgt)
        for name, (lo, hi) in {
            "split-CQR (frozen)": cqr_split(Xtr, ytr, Xca, yca, Xte, alpha=alpha)[:2],
            "ACI-CQR": aci_cqr(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, gamma=gamma, groups=gte)[:2],
            "SPCI": spci(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, groups=gte)[:2],
            "DtACI": dtaci(Xtr, ytr, Xca, yca, Xte, yte, alpha=alpha, groups=gte)[:2],
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

    methods = ["split-CQR (frozen)", "ACI-CQR", "SPCI", "DtACI"]
    colors = {"split-CQR (frozen)": AQUA, "ACI-CQR": YELLOW, "SPCI": VIOLET, "DtACI": GREEN}
    models = list(dict.fromkeys(table["target_model"]))
    xs = np.arange(len(models))

    width = group_bar_width(len(methods))
    fig, ax = plt.subplots(figsize=(10, 5.0), constrained_layout=True)
    any_unbounded = False
    for i, method in enumerate(methods):
        sel = [table[(table["target_model"] == m) & (table["method"] == method)] for m in models]
        vals = [s["coverage"].item() for s in sel]
        fracs = [float(s["frac_unbounded"].item()) for s in sel]
        offset = (i - (len(methods) - 1) / 2) * width
        bars = ax.bar(xs + offset, vals, width=width * 0.86, color=colors[method], label=method)
        any_unbounded |= mark_unbounded(ax, bars, fracs, vals)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.014, f"{v:.2f}",
                    ha="center", va="bottom", fontsize=7.5)
    nominal_line(ax, alpha)
    ax.set_xticks(xs, models)
    ax.set_ylim(0, 1.16)
    ax.set_ylabel("marginal coverage on target stream")
    title = ("Model-swap transfer (SWE-bench): guard calibrated on claude-opus-4.7, "
             "deployed on other models")
    if any_unbounded:
        title += f"\n{UNBOUNDED_NOTE}"
    ax.set_title(title, fontsize=10.5)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.07))
    fig.savefig("figures/transfer_swebench.png", dpi=200, bbox_inches="tight")

    print(table.to_string(index=False))
    print("\nwrote figures/transfer_swebench.png, tables/transfer_swebench.csv")
    return table


if __name__ == "__main__":
    main()
