"""Regenerate the Warehouse cost-of-pass frontier figure from tables/cost_of_pass_warehouse.csv.

Committed so the figure is covered by `make repro` like every other artifact — the
previous version was drawn outside the pipeline and went stale when the tables were
regenerated (hard-cap points moved by up to 8 points of retained passes).

Usage: python scripts/make_costofpass_figure.py
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "tables", "cost_of_pass_warehouse.csv")
OUT = os.path.join(HERE, "figures", "final", "cost_of_pass_warehouse")

# Validated categorical palette (scripts/validate_palette.js, light surface: all checks pass).
BLUE, ORANGE, GREEN = "#2E6FD0", "#C1741A", "#00916E"
INK, MUTED, GRID = "#1a1a1a", "#5c5c5c", "#d8d8d8"


def load():
    guard, caps, agent = [], [], None
    with open(SRC) as fh:
        for r in csv.DictReader(fh):
            x = float(r["pass_rate_retained"])
            y = float(r["cost_of_pass_usd"]) / 1e6
            if r["policy"] == "agent alone":
                agent = (x, y)
            elif r["policy"] == "guard":
                guard.append((float(r["param"]), x, y))
            else:
                caps.append((float(r["param"]), x, y))
    guard.sort(key=lambda t: t[0])
    caps.sort(key=lambda t: t[1])
    return agent, guard, caps


def main():
    agent, guard, caps = load()

    fig, ax = plt.subplots(figsize=(7.4, 4.6), dpi=200)
    ax.set_facecolor("white")

    # hard-cap frontier
    ax.plot([c[1] for c in caps], [c[2] for c in caps], ls=":", lw=2, color=ORANGE,
            marker="s", ms=8, mec="white", mew=1.2, label="hard cap on $ spent (sweep cap)",
            zorder=2)
    # guard frontier
    ax.plot([g[1] for g in guard], [g[2] for g in guard], ls="-", lw=2, color=BLUE,
            marker="o", ms=8, mec="white", mew=1.2, label="Budget Guard (sweep δ)", zorder=3)
    # agent alone
    ax.plot([agent[0]], [agent[1]], marker="*", ms=18, color=GREEN, mec="white", mew=1.2,
            ls="none", label="agent alone (no stopping)", zorder=4)

    # sparse direct labels, all placed in the empty right margin; interpretation
    # lives in the caption, not the plot
    ax.annotate("δ ≤ 0.05 (aborts nothing)", xy=(1.0, 1.6096), xytext=(12, 0),
                textcoords="offset points", ha="left", va="center", fontsize=9, color=BLUE)
    ax.annotate("δ = 0.10–0.20", xy=(1.0, 0.871), xytext=(12, 0),
                textcoords="offset points", ha="left", va="center", fontsize=9, color=BLUE)
    ax.annotate("δ = 0.30–0.40", xy=(0.9487, 0.8617), xytext=(-8, -16),
                textcoords="offset points", ha="right", va="top", fontsize=9, color=BLUE)
    ax.annotate("agent alone", xy=(1.0, 1.6096), xytext=(12, 14),
                textcoords="offset points", ha="left", va="center", fontsize=9, color=GREEN)
    ax.annotate("tightest cap that\nkeeps every success", xy=(caps[-1][1], caps[-1][2]),
                xytext=(0, -12), textcoords="offset points", ha="center", va="top",
                fontsize=9, color=ORANGE)

    ax.set_xlabel("fraction of successful runs retained (vs agent alone)", fontsize=10, color=INK)
    ax.set_ylabel("cost of pass ($M per success)", fontsize=10, color=INK)
    ax.set_title("Warehouse: cost of pass against successes retained\n"
                 "the cap frontier buys savings with lost successes; the guard does not",
                 fontsize=11, color=INK, pad=10)

    ax.set_xticks([0.4,0.5,0.6,0.7,0.8,0.9,1.0])
    ax.grid(True, color=GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_xlim(0.38, 1.30)
    ax.set_ylim(0.55, 3.45)

    leg = ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3,
                    frameon=False, fontsize=9)
    for t in leg.get_texts():
        t.set_color(INK)

    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{OUT}.{ext}", bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}.png / .pdf")


if __name__ == "__main__":
    main()
