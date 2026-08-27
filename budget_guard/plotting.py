"""budget_guard/plotting.py — shared figure helpers.

Two jobs, both about not letting a figure overstate a result:

* ``mark_unbounded`` — an online method can hit nominal coverage by emitting
  ``[0, inf)`` intervals. A coverage-only bar chart then ranks that method FIRST,
  which is the opposite of the truth (ACI "recovers by surrender"; SPCI recovers by
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


def nominal_line(ax, alpha: float, color: str = "#4A5361"):
    """Draw the 1-alpha reference line, labelled via the legend (never on the canvas)."""
    return ax.axhline(1 - alpha, color=color, lw=1.2, ls="--",
                      label=f"nominal {1 - alpha:.2f}")


def mark_unbounded(ax, bars, fracs, values, fontsize: float = 6.5) -> bool:
    """Hatch bars that achieved their coverage partly with unbounded intervals.

    The tag sits mid-bar on a white plate in dark ink. It used to be white text
    rotated 90 degrees directly on the hatching, which is the least legible
    combination available and was illegible at column width, even though this tag
    carries the paper's honesty mechanism: coverage bought with infinite intervals.
    Rotation is now used only when the bar is too narrow to fit the tag flat.

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
        # Bar width in pixels decides orientation: a flat tag needs roughly
        # 0.62 * fontsize px per character plus padding.
        x0 = ax.transData.transform((bar.get_x(), 0.0))[0]
        x1 = ax.transData.transform((bar.get_x() + bar.get_width(), 0.0))[0]
        flat = (x1 - x0) >= 0.62 * fontsize * len(tag) + 6.0
        ax.text(bar.get_x() + bar.get_width() / 2, value / 2,
                tag, ha="center", va="center",
                fontsize=fontsize, color="#1C2128",
                rotation=0 if flat else 90,
                bbox=dict(boxstyle="round,pad=0.18", facecolor="#FFFFFF",
                          edgecolor="none", alpha=0.88))
        marked = True
    return marked


UNBOUNDED_NOTE = ("hatched ∞:NN% = coverage reached with unbounded intervals on NN% of the "
                  "stream (valid but uninformative)")
UNBOUNDED_LEGEND = "hatched, ∞:NN% = unbounded intervals on NN% of the stream"


def method_legend(ax, methods, colors, any_unbounded: bool, nominal=None, **legend_kw):
    """Legend with SOLID method swatches plus one standalone hatched entry.

    matplotlib draws a bar series' legend swatch from that series' first bar. Hatching
    is a per-bar flag (see ``mark_unbounded``), so a method whose first bar happened
    to be hatched got a hatched swatch and one whose first bar was solid got a solid
    swatch, which told readers hatching was a method property and made a legitimately
    hatched bar elsewhere look like a rendering error. Explicit handles fix both.
    """
    from matplotlib.patches import Patch

    handles = [nominal] if nominal is not None else []
    handles += [Patch(facecolor=colors[m], label=m) for m in methods]
    if any_unbounded:
        handles.append(Patch(facecolor="#FFFFFF", edgecolor="#1C2128", linewidth=0.6,
                             hatch=UNBOUNDED_HATCH, label=UNBOUNDED_LEGEND))
    return ax.legend(handles=handles, **legend_kw)
