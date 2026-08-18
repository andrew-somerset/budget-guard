"""Assemble budget-guard-results.pdf from regenerated figures.

Page headers are draft labels for the internal results PDF only. NeurIPS §4.3 puts
the numbered caption *after* the figure in LaTeX (sentence case); use
``scripts/figure_captions.tex`` for Overleaf ``\\caption{}`` text.

Usage: python scripts/make_results_pdf.py [output.pdf]
"""
from __future__ import annotations

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.image import imread

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(
    os.path.dirname(HERE), "budget-guard-supporting-documents", "budget-guard-results.pdf"
)

# (page header = main title only, relative path under repo root)
PAGES: list[tuple[str, str]] = [
    ("Within-run interval coverage", "figures/coverage_main.png"),
    ("Gap vs agent self-report — Sokoban", "figures/gap_sokoban.png"),
    ("Gap vs agent self-report — SearchR1", "figures/gap_searchr1.png"),
    ("Gap vs agent self-report — SWE-bench", "figures/gap_swebench.png"),
    ("Label efficiency — Sokoban", "figures/label_efficiency_sokoban.png"),
    ("Cross-environment transfer", "figures/transfer_env.png"),
    ("Model-swap transfer — SWE-bench", "figures/transfer_swebench.png"),
    ("Coverage across all runs", "figures/allruns.png"),
    ("Conditional coverage by turn depth", "figures/conditional_coverage.png"),
    ("Per-resource and joint coverage — Warehouse", "figures/final/joint_vs_marginal.png"),
    ("Warehouse model-swap transfer", "figures/transfer_warehouse.png"),
    ("Abort frontier — Warehouse", "figures/final/abort_frontier_warehouse.png"),
    ("Abort frontier — Sokoban", "figures/abort_frontier_sokoban.png"),
    ("Abort frontier — SWE-bench", "figures/abort_frontier_swebench.png"),
    ("Cost of pass — Warehouse", "figures/final/cost_of_pass_warehouse.png"),
    ("Cost of pass — Sokoban", "figures/cost_of_pass_sokoban.png"),
    ("Cost of pass — SWE-bench", "figures/cost_of_pass_swebench.png"),
    ("Feasibility-gated selective frontier", "figures/final/selective_frontier.png"),
    ("Budget Guard pipeline", "figures/final/pipeline.png"),
]


def main(out_path: str = DEFAULT_OUT) -> None:
    root = HERE
    with PdfPages(out_path) as pdf:
        for title, rel in PAGES:
            path = os.path.join(root, rel)
            if not os.path.isfile(path):
                raise FileNotFoundError(f"missing figure for PDF: {path}")
            img = imread(path)
            h, w = img.shape[:2]
            fig_w, fig_h = 11.0, 11.0 * h / w
            if fig_h > 8.2:
                fig_h, fig_w = 8.2, 8.2 * w / h
            fig, ax = plt.subplots(figsize=(fig_w, fig_h + 0.4))
            ax.imshow(img)
            ax.axis("off")
            fig.suptitle(title, fontsize=11, y=0.98)
            fig.tight_layout(rect=(0, 0, 1, 0.96))
            pdf.savefig(fig, dpi=150)
            plt.close(fig)
    print(f"wrote {out_path} ({len(PAGES)} pages)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT)
