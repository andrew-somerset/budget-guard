#!/usr/bin/env python3
"""Build the figure files the paper embeds, from the committed tables.

The Overleaf project ships figures/fig_coverage.png (Figure 2) and
figures/fig_transfer.png (Figure 3, two panels side by side) without diagnostic
titles. This script produces those two files with the shared legend fix
(budget_guard.plotting.method_legend) plus figures/fig_case_study.png, into
paper/figures/, so a bundle can be assembled without touching the repo's own
figures/ outputs. Numbers come from tables/*.csv and are unchanged.

Usage: python scripts/make_paper_figures.py
"""
import os
import shutil
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from budget_guard.plotting import AQUA, GREEN, VIOLET, YELLOW, method_legend  # noqa: E402
from budget_guard.run_coverage import plot_coverage  # noqa: E402
from budget_guard.run_transfer import plot_transfer_swebench  # noqa: E402
from budget_guard.run_transfer_env import plot_transfer_env  # noqa: E402

OUT = "paper/figures"
# The Overleaf layout was tuned around the team's original figure files; a taller
# replacement pushes an [H] figure to the next page and cascades the whole tail. Match
# the originals' pixel aspect ratios (coverage 2084x698, transfer 2864x654) so each
# takes the same height at \linewidth.
TARGET_ASPECT = {"fig_coverage.png": 2084 / 698, "fig_transfer.png": 2864 / 654}


def fit_aspect(name, draw, height=4.6, tol=0.03):
    """Redraw at decreasing figure heights until the saved PNG's aspect matches the original's."""
    from PIL import Image
    for _ in range(8):
        draw(height)
        w, h = Image.open(f"{OUT}/{name}").size
        a = w / h
        if abs(a - TARGET_ASPECT[name]) < tol:
            return a
        height *= a / TARGET_ASPECT[name]
    return a


def n_seeds(per_seed_csv: str) -> int:
    return int(pd.read_csv(per_seed_csv)["seed"].nunique())


def main() -> None:
    os.makedirs(OUT, exist_ok=True)

    def draw_coverage(height):
        fig, ax = plt.subplots(figsize=(13.5, height), constrained_layout=True)
        plot_coverage(pd.read_csv("tables/coverage.csv"), n_seeds("tables/coverage_per_seed.csv"),
                      ax=ax, show_title=False)
        fig.savefig(f"{OUT}/fig_coverage.png", dpi=200, bbox_inches="tight")
        plt.close(fig)

    def draw_transfer(height):
        fig, (left, right) = plt.subplots(1, 2, figsize=(15, height), constrained_layout=True,
                                          gridspec_kw={"width_ratios": [1.0, 1.4]})
        plot_transfer_env(pd.read_csv("tables/transfer_env.csv"), n_seeds("tables/transfer_env_per_seed.csv"),
                          ax=left, show_title=False, show_legend=False)
        plot_transfer_swebench(pd.read_csv("tables/transfer_swebench.csv"),
                               n_seeds("tables/transfer_swebench_per_seed.csv"), ax=right, show_title=False,
                               show_legend=False)
        # One shared legend for both panels (same four methods, same nominal line).
        methods = ["split-CQR (frozen)", "ACI-CQR", "windowed-CQR", "DtACI"]
        colors = {"split-CQR (frozen)": AQUA, "ACI-CQR": YELLOW, "windowed-CQR": VIOLET, "DtACI": GREEN}
        nominal = next(l for l in left.get_lines() if l.get_label().startswith("nominal"))
        method_legend(fig, methods, colors, True, nominal, frameon=False, fontsize=9.5, ncol=6,
                      loc="lower center", bbox_to_anchor=(0.5, -0.10))
        fig.savefig(f"{OUT}/fig_transfer.png", dpi=200, bbox_inches="tight")
        plt.close(fig)

    for name, draw in (("fig_coverage.png", draw_coverage), ("fig_transfer.png", draw_transfer)):
        a = fit_aspect(name, draw)
        print(f"{name}: aspect {a:.2f} (original {TARGET_ASPECT[name]:.2f})")

    shutil.copyfile("figures/case_study_sokoban.png", f"{OUT}/fig_case_study.png")
    print(f"wrote {OUT}/fig_coverage.png, {OUT}/fig_transfer.png, {OUT}/fig_case_study.png")


if __name__ == "__main__":
    main()
