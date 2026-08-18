"""scripts/make_pipeline_figure.py — Figure 1: the Budget Guard pipeline.

A methods schematic (not a results plot): agent run -> prefix features ->
conformal layer -> decisions, with the rollout-end label feedback that makes the
online methods deployment-faithful. Colors match the results figures (see
budget_guard/run_*.py palettes) so the paper reads as one system.

Usage: python scripts/make_pipeline_figure.py
Writes figures/final/pipeline.png (300 dpi) and figures/final/pipeline.pdf.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

AQUA, VIOLET, GREEN, GRAY, ORANGE = "#1baf7a", "#4a3aa7", "#008300", "#8B93A1", "#eb6834"
INK = "#2b3240"

OUT = os.path.join(os.path.dirname(__file__), "..", "figures", "final")


def box(ax, x, y, w, h, color, title, lines, title_size=8.6, line_size=7.6):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.006,rounding_size=0.012",
            linewidth=1.3, edgecolor=color, facecolor=color, alpha=1.0,
            fill=False, zorder=2,
        )
    )
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.006,rounding_size=0.012",
            linewidth=0, facecolor=color, alpha=0.06, zorder=1,
        )
    )
    ax.text(x + w / 2, y + h - 0.055, title, ha="center", va="top",
            fontsize=title_size, fontweight="bold", color=color)
    body = "\n".join(lines)
    ax.text(x + w / 2, y + h - 0.135, body, ha="center", va="top",
            fontsize=line_size, color=INK, linespacing=1.45)


def arrow(ax, x0, y0, x1, y1, color=INK, style="-|>", rad=0.0, lw=1.4):
    ax.add_patch(
        FancyArrowPatch(
            (x0, y0), (x1, y1),
            arrowstyle=style, mutation_scale=11, linewidth=lw,
            color=color, connectionstyle=f"arc3,rad={rad}", zorder=3,
        )
    )


def main() -> None:
    fig, ax = plt.subplots(figsize=(10.0, 2.85))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    top, height = 0.34, 0.52

    box(ax, 0.015, top, 0.185, height, GRAY, "Agent run",
        ["any LLM agent, unmodified",
         "per-turn usage at turn $k$:",
         "tokens / dollars / time",
         "optional self-estimate"])

    box(ax, 0.255, top, 0.185, height, AQUA, "Prefix features",
        ["progress ($k$)",
         "consumption + burn rate",
         "recent-usage statistics",
         "agent estimate (if any)"])

    box(ax, 0.495, top, 0.24, height, VIOLET, "Conformal layer",
        ["CQR, split by rollout",
         "online: windowed-CQR / ACI / DtACI",
         "by depth: Mondrian buckets",
         "joint resources: Bonferroni $\\alpha/3$",
         "censoring-aware bounds + gate"], line_size=7.2)

    box(ax, 0.79, top, 0.195, height, GREEN, "Per-turn output",
        ["calibrated interval on",
         "remaining budget",
         "abort if feasibility $< \\tau$",
         "(false aborts $\\leq \\delta$ per run)"])

    mid = top + height / 2
    arrow(ax, 0.202, mid, 0.253, mid)
    arrow(ax, 0.442, mid, 0.493, mid)
    arrow(ax, 0.737, mid, 0.788, mid)

    # Rollout-end label feedback: completed rollouts reveal labels; never mid-run.
    yfb = 0.175
    ax.plot([0.107, 0.107], [top, yfb], color=ORANGE, lw=1.5)
    ax.plot([0.107, 0.615], [yfb, yfb], color=ORANGE, lw=1.5)
    arrow(ax, 0.615, yfb, 0.615, top - 0.01, color=ORANGE, lw=1.5)
    ax.text(0.362, yfb - 0.045,
            "completed rollouts reveal their labels at rollout end (never mid-run);"
            " online methods recalibrate from these alone",
            ha="center", va="top", fontsize=7.4, color=ORANGE, linespacing=1.4)

    ax.text(0.015, 0.985, "training-free  •  model-agnostic  •  CPU-only",
            ha="left", va="top", fontsize=7.8, color=GRAY)

    os.makedirs(OUT, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"pipeline.{ext}"), dpi=300,
                    bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}/pipeline.png and .pdf")


if __name__ == "__main__":
    main()
