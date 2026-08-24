"""scripts/make_pipeline_figure.py — Figure 1: the Budget Guard pipeline.

A methods schematic, not a results plot. The top band is the four-stage pipeline an
unmodified agent run passes through; the bottom band zooms into the two stages that do
the work — the four prefix-feature families and the conformal layer — so a reader can
see what the guard consumes and what it emits without reading §3 first.

Sized for a full-text-width figure (6.9 in wide), so it is placed at 1:1 and the labels
stay legible in print; earlier versions were drawn 10 in wide and scaled down to 4.5 in,
which shrank the body text below 4 pt. Colors match the results figures (see
budget_guard/run_*.py palettes) so the paper reads as one system.

Usage: python scripts/make_pipeline_figure.py
Writes figures/final/pipeline.png (400 dpi) and figures/final/pipeline.pdf.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon

AQUA, VIOLET, GREEN, GRAY, ORANGE = "#1baf7a", "#4a3aa7", "#008300", "#8B93A1", "#eb6834"
INK = "#2b3240"
MUTED = "#5b6473"

# Drawn at final print size, so these point sizes are the ones the reader sees.
FIG_W, FIG_H = 6.5, 3.98
FS_STAGE, FS_STAGE_SUB = 8.0, 6.4
FS_PANEL, FS_HEAD, FS_BODY, FS_NOTE = 7.6, 6.8, 6.3, 5.9

OUT = os.path.join(os.path.dirname(__file__), "..", "figures", "final")


def rbox(ax, x, y, w, h, color, *, fill_alpha=0.06, lw=1.1, ls="solid", z=2):
    """Rounded outline over a faint fill — the shared box style for the whole figure."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.004,rounding_size=0.010",
            linewidth=0, facecolor=color, alpha=fill_alpha, zorder=z - 1,
        )
    )
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.004,rounding_size=0.010",
            linewidth=lw, edgecolor=color, facecolor="none", linestyle=ls, zorder=z,
        )
    )


def stage(ax, n, x, y, w, h, color, title, subtitle):
    """One numbered box in the top band. The badge fixes the reading order."""
    rbox(ax, x, y, w, h, color)
    r = 0.0125
    ax.add_patch(Circle((x + 0.019, y + h - 0.031), r, facecolor=color,
                        edgecolor="none", zorder=4))
    ax.text(x + 0.019, y + h - 0.0325, str(n), ha="center", va="center",
            fontsize=6.0, fontweight="bold", color="white", zorder=5)
    ax.text(x + w / 2 + 0.012, y + h - 0.031, title, ha="center", va="center",
            fontsize=FS_STAGE, fontweight="bold", color=color, zorder=4)
    ax.text(x + w / 2, y + h - 0.070, subtitle, ha="center", va="top",
            fontsize=FS_STAGE_SUB, color=INK, linespacing=1.45, zorder=4)


def arrow(ax, x0, y0, x1, y1, color=INK, lw=1.3):
    ax.add_patch(
        FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=9,
                        linewidth=lw, color=color, zorder=3)
    )


def zoom_wedge(ax, x0, x1, ytop, xa, xb, ybot, color):
    """Dashed wedge tying a top-band stage to the panel that expands it."""
    ax.add_patch(Polygon([(x0, ytop), (x1, ytop), (xb, ybot), (xa, ybot)], closed=True,
                         facecolor=color, alpha=0.045, edgecolor="none", zorder=0))
    for (px, py_), (qx, qy) in (((x0, ytop), (xa, ybot)), ((x1, ytop), (xb, ybot))):
        ax.plot([px, qx], [py_, qy], color=color, lw=0.7, ls=(0, (3, 3)),
                alpha=0.5, zorder=0)


def card(ax, x, y, w, h, color, head, body):
    rbox(ax, x, y, w, h, color, fill_alpha=0.045, lw=0.9)
    ax.text(x + 0.012, y + h - 0.028, head, ha="left", va="center",
            fontsize=FS_HEAD, fontweight="bold", color=color)
    ax.text(x + 0.012, y + h - 0.052, body, ha="left", va="top",
            fontsize=FS_BODY, color=INK, linespacing=1.5)


def main() -> None:
    fig = plt.figure(figsize=(FIG_W, FIG_H))
    # Axes fills the canvas: normalized x = 1.0 is exactly FIG_W inches, so the
    # point sizes above are the sizes the reader sees at 1:1 placement.
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ----------------------------------------------------------- top band
    ty, th = 0.740, 0.180
    sw, gap = 0.224, 0.028
    xs = [0.011 + i * (sw + gap) for i in range(4)]

    stage(ax, 1, xs[0], ty, sw, th, GRAY, "Agent run",
          "any LLM agent, unmodified;\nper-turn spend at turn $k$\n(tokens / dollars / time)")
    stage(ax, 2, xs[1], ty, sw, th, AQUA, "Prefix features",
          "four families, all readable\nfrom the turns so far\n(no future information)")
    stage(ax, 3, xs[2], ty, sw, th, VIOLET, "Conformal layer",
          "turns a point estimate into\nan interval carrying a\ncoverage guarantee")
    stage(ax, 4, xs[3], ty, sw, th, GREEN, "Per-turn decision",
          "calibrated interval on the\nremaining budget, plus a\ncontinue-or-abort call")

    mid = ty + th / 2
    for i in range(3):
        arrow(ax, xs[i] + sw + 0.005, mid, xs[i + 1] - 0.005, mid)

    ax.text(0.011, 0.998, "training-free   •   model-agnostic   •   no logits, no GPU",
            ha="left", va="top", fontsize=FS_NOTE, color=MUTED)

    # Only a finished rollout may update the online calibration. Routed above the
    # band so it cannot collide with the zoom wedges below.
    yfb = 0.966
    x_from, x_to = xs[3] + sw / 2, xs[2] + sw / 2
    ax.plot([x_from, x_from], [ty + th + 0.004, yfb], color=ORANGE, lw=1.2)
    ax.plot([x_from, x_to], [yfb, yfb], color=ORANGE, lw=1.2)
    arrow(ax, x_to, yfb, x_to, ty + th + 0.006, color=ORANGE, lw=1.2)
    ax.text((x_from + x_to) / 2, yfb + 0.012,
            "labels feed back only once a rollout finishes (never mid-run)",
            ha="center", va="bottom", fontsize=FS_NOTE, color=ORANGE)

    # ------------------------------------------------------ detail panels
    py, ph = 0.028, 0.578
    p2x, p2w = 0.011, 0.543
    p3x, p3w = 0.586, 0.403
    ywedge = ty - 0.030

    zoom_wedge(ax, xs[1], xs[1] + sw, ywedge, p2x, p2x + p2w, py + ph, AQUA)
    zoom_wedge(ax, xs[2], xs[2] + sw, ywedge, p3x, p3x + p3w, py + ph, VIOLET)

    rbox(ax, p2x, py, p2w, ph, AQUA, fill_alpha=0.02, lw=1.0, ls=(0, (5, 3)))
    rbox(ax, p3x, py, p3w, ph, VIOLET, fill_alpha=0.02, lw=1.0, ls=(0, (5, 3)))

    ax.text(p2x + 0.016, py + ph - 0.030, "2   The four prefix-feature families",
            ha="left", va="center", fontsize=FS_PANEL, fontweight="bold", color=AQUA)
    ax.text(p3x + 0.016, py + ph - 0.030, "3   Inside the conformal layer",
            ha="left", va="center", fontsize=FS_PANEL, fontweight="bold", color=VIOLET)

    # --- the four feature families, 2 x 2
    cw, ch = 0.252, 0.170
    gx0, gx1 = p2x + 0.016, p2x + 0.016 + cw + 0.012
    gy0, gy1 = py + ph - 0.240, py + ph - 0.428

    card(ax, gx0, gy0, cw, ch, AQUA, "1.  Progress",
         "turn index $k$")
    card(ax, gx1, gy0, cw, ch, AQUA, "2.  Cumulative consumption",
         "spend so far;\nburn rate (spend / $k$)")
    card(ax, gx0, gy1, cw, ch, AQUA, "3.  Recent usage",
         "last / mean / sd / min / max\nper-turn spend; last-3 mean;\nlast $-$ mean")
    card(ax, gx1, gy1, cw, ch, AQUA, "4.  Agent self-estimate",
         "optional; the agent's own\ninterval: endpoints,\nmidpoint, width")

    ax.text(p2x + p2w / 2, py + 0.068,
            "Excluded by construction: final totals, success, feasibility — anything\n"
            "known only at rollout end; absence is asserted in code, not assumed.",
            ha="center", va="center", fontsize=FS_NOTE, color=MUTED, linespacing=1.6)

    # --- what the conformal layer contains, one row per job it does
    rows = [
        ("offline default", "split-CQR, calibrated by rollout"),
        ("per turn depth", "Mondrian buckets: $k{=}1$, $k{=}2$, $k{\\geq}3$"),
        ("under deployment shift", "online windowed-CQR / ACI / DtACI"),
        ("several budgets at once", "Bonferroni margins at $\\alpha/3$"),
        ("runs that cannot finish", "censoring-aware bounds + feasibility gate"),
    ]
    ry = py + ph - 0.110
    for label, detail in rows:
        ax.plot([p3x + 0.024], [ry + 0.001], marker="o", ms=2.2, color=VIOLET, zorder=3)
        ax.text(p3x + 0.038, ry, label, ha="left", va="center",
                fontsize=FS_HEAD, fontweight="bold", color=VIOLET)
        ax.text(p3x + 0.038, ry - 0.032, detail, ha="left", va="center",
                fontsize=FS_BODY, color=INK)
        ry -= 0.074

    ax.text(p3x + p3w / 2, py + 0.068,
            "Emits $[\\,$lo, hi$\\,]$ at nominal $1-\\alpha$ coverage, and\n"
            "aborts when the feasibility score drops below\n"
            "$\\tau$ (false aborts $\\leq\\delta$ per run).",
            ha="center", va="center", fontsize=FS_NOTE, color=MUTED, linespacing=1.6)

    os.makedirs(OUT, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"pipeline.{ext}"), dpi=400, facecolor="white")
    print(f"wrote {OUT}/pipeline.png and .pdf")


if __name__ == "__main__":
    main()
