"""budget_guard/plotting.py — shared figure helpers.

Two jobs, both about not letting a figure overstate a result:

* ``mark_unbounded`` — an online method can hit nominal coverage by emitting
  ``[0, inf)`` intervals. A coverage-only bar chart then ranks that method FIRST,
  which is the opposite of the truth (ACI "recovers by surrender"; windowed-CQR recovers by
  adaptation). Bars whose intervals were unbounded on part of the stream get a hatch
  plus an ``inf:NN%`` tag so the figure cannot be read as a clean win.
* ``group_bar_width`` / ``nominal_line`` — layout guards. Bar width must shrink as
  methods are added (a fixed width silently overflows into the neighbouring group),
  and the nominal-level label belongs in the legend, where it can never collide with
  a tall bar's value label.
"""
from __future__ import annotations

import numpy as np

# Categorical palette (validated for CVD separation; see the dataviz reference).
GRAY = "#8B93A1"
BLUE = "#2a78d6"
AQUA = "#1baf7a"
YELLOW = "#eda100"
VIOLET = "#4a3aa7"
GREEN = "#008300"
RED = "#e34948"
MAGENTA = "#e87ba4"
ORANGE = "#eb6834"

UNBOUNDED_HATCH = "///"
# Mark ANY nonzero unbounded fraction. frac_unbounded is an exact measured share of
# a multi-thousand-sample stream, never a rounding artefact — an earlier 0.02
# threshold silently let up to 2% [0, inf) intervals inflate a coverage bar by up
# to 0.02 absolute (a fifth of the whole miss budget at alpha=0.1) with no visual
# disclosure, which is precisely what this module exists to prevent.


def group_bar_width(n_series: int, group_span: float = 0.82) -> float:
    """Per-bar width so ``n_series`` bars fit inside one x-group without overflow."""
    return group_span / max(n_series, 1)


def nominal_line(ax, alpha: float, color: str = "#4A5361", zorder: float = 4.0):
    """Draw the 1-alpha reference line, labelled via the legend (never on the canvas)."""
    level = 1 - alpha
    x0, x1 = ax.get_xlim()
    ax.plot([x0, x1], [level, level], color=color, lw=1.2, ls="--", zorder=zorder,
            solid_capstyle="butt", label=f"nominal {level:.2f}")


def figure_title(main: str, subtitle: str = "") -> str:
    """Two-line on-figure title for standalone PNGs (internal PDF / review).

    NeurIPS §4.3: the numbered ``\\caption{}`` lives *after* ``\\includegraphics`` in
    LaTeX (sentence case; first word and proper nouns capitalized). Do not burn figure
    numbers or section codes (C1/C2/…) into PNGs. Copy-paste caption text from
    ``scripts/figure_captions.tex``.
    """
    return main if not subtitle else f"{main}\n{subtitle}"


def mark_unbounded(ax, bars, fracs, values, fontsize: float = 6.5) -> bool:
    """Hatch bars that achieved their coverage partly with unbounded intervals.

    Returns True if any bar was marked, so the caller can add the explanatory note.
    """
    marked = False
    for bar, frac, value in zip(bars, fracs, values):
        if not np.isfinite(frac) or frac <= 0 or not np.isfinite(value):
            continue
        bar.set_hatch(UNBOUNDED_HATCH)
        bar.set_edgecolor("#1C2128")
        bar.set_linewidth(0.6)
        tag = f"∞:{frac:.0%}" if frac >= 0.005 else "∞:<1%"
        ax.text(bar.get_x() + bar.get_width() / 2, value / 2,
                tag, ha="center", va="center",
                fontsize=fontsize, color="#FFFFFF", rotation=90)
        marked = True
    return marked


UNBOUNDED_NOTE = ("hatched ∞:NN% = coverage reached with unbounded intervals on NN% of the "
                  "stream (valid but uninformative)")


def bar_value_labels(ax, bars, values, *, fmt="{:.2f}", fontsize: float = 8,
                     pad: float = 0.015, yerr_upper=None, nominal: float | None = None,
                     nominal_nudge_for: set[str] | None = None) -> None:
    """Write bar values above each bar (and above error caps when provided).

    When ``nominal`` is set with ``nominal_nudge_for``, listed labels are placed at
    least ``nominal + 0.015`` (keeps other values on the bar).
    """
    err_ups = yerr_upper if yerr_upper is not None else [0.0] * len(bars)
    for bar, value, err_up in zip(bars, values, err_ups):
        if not np.isfinite(value):
            continue
        x = bar.get_x() + bar.get_width() / 2
        top = float(value) + (float(err_up) if np.isfinite(err_up) else 0.0)
        y = top + pad
        label = fmt.format(value)
        if nominal is not None and nominal_nudge_for is not None and label in nominal_nudge_for:
            y = max(y, nominal + 0.015)
        ax.text(x, y, label,
                ha="center", va="bottom", fontsize=fontsize, zorder=6)


def annotate_param_clusters(ax, xs, ys, params, *, color: str, fmt: str = "δ={:.2f}",
                            x_tol: float = 0.03, y_tol: float = 0.04,
                            fontsize: float = 7.5, xytext=(8, 4),
                            ha: str = "left") -> None:
    """One label per cluster of nearby (x, y) points instead of stacked δ tags."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    params = np.asarray(params, dtype=float)
    clusters: list[list[int]] = []
    for i in np.argsort(params):
        placed = False
        for cluster in clusters:
            j = cluster[0]
            if abs(xs[i] - xs[j]) <= x_tol and abs(ys[i] - ys[j]) <= y_tol:
                cluster.append(int(i))
                placed = True
                break
        if not placed:
            clusters.append([int(i)])
    used: list[tuple[float, float, float]] = []
    early_slots = 0
    label_bbox = dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.92)
    for cluster in clusters:
        cx = float(np.mean(xs[cluster]))
        cy = float(np.mean(ys[cluster]))
        ps = sorted(float(params[k]) for k in cluster)
        if abs(ps[-1] - ps[0]) < 1e-9:
            label = fmt.format(ps[0])
        else:
            label = f"δ={ps[0]:.2f}–{ps[-1]:.2f}"
        if cx <= 0.065 and cy <= 0.10:
            # Origin-adjacent clusters: staggered callout box clear of the curve.
            tx = 0.05 + 0.09 * early_slots
            ty = 0.42 + 0.09 * early_slots
            rad = -0.35 if early_slots % 2 == 0 else 0.35
            early_slots += 1
            ax.annotate(
                label, (cx, cy), xytext=(tx, ty),
                xycoords="data", textcoords="data",
                fontsize=fontsize, color=color,
                ha="left", va="center", bbox=label_bbox,
                arrowprops=dict(arrowstyle="-", color=color, lw=0.8,
                                shrinkA=2, shrinkB=2,
                                connectionstyle=f"arc3,rad={rad}"),
                zorder=5,
            )
            used.append((cx, cy, 0.0))
            continue
        ox, oy = xytext
        ha_use = ha
        if abs(ox) == abs(xytext[0]):
            side = -1 if len(used) % 2 == 0 else 1
            ox = side * abs(xytext[0])
            ha_use = "right" if side < 0 else "left"
        for px, py, poy in used:
            if abs(cx - px) < max(x_tol * 3, 0.08) and abs(cy - py) < max(y_tol * 3, 0.12):
                oy = poy + 14
        ax.annotate(
            label, (cx, cy), textcoords="offset points", xytext=(ox, oy),
            fontsize=fontsize, color=color, ha=ha_use, va="center", bbox=label_bbox,
            zorder=5,
        )
        used.append((cx, cy, oy))
