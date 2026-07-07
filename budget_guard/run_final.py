"""budget_guard/run_final.py — regenerate the headline warehouse figures into figures/final/.

Fixed seeds (0–4) for the reproducible final-figure set the write-up references:
- joint_vs_marginal.png       (C2 multi-resource, like-for-like agent baseline)
- abort_frontier_warehouse.png (C3 economic stopping, native USD)
- selective_frontier.png       (feasibility-gated intervals — the methods result)

Transfer / coverage-main figures need the full multi-model BAGEN dataset (the swebench
origin trajectories, not fetched by scripts/fetch_bagen.py) and are regenerated on a
machine with that data.

Usage: python -m budget_guard.run_final
"""
from __future__ import annotations

from . import run_economic_warehouse, run_gated, run_multiresource

OUTDIR = "figures/final"
SEEDS = (0, 1, 2, 3, 4)


def main() -> None:
    run_multiresource.main(seeds=SEEDS, outdir=OUTDIR)       # C2 joint (like-for-like)
    run_economic_warehouse.main(seeds=SEEDS, outdir=OUTDIR)  # C3 abort frontier
    run_gated.main(seeds=SEEDS, outdir=OUTDIR)               # selective frontier (methods)
    print(f"\nfinal figures written to {OUTDIR}/")


if __name__ == "__main__":
    main()
