"""budget_guard/run_final.py — regenerate the headline figures into figures/final/.

Fixed seeds (0–4) for the reproducible final-figure set the write-up references.

Always regenerated (needs only the minimal `scripts/fetch_bagen.py` subset):
- joint_vs_marginal.png        (C2 multi-resource, like-for-like agent baseline)
- abort_frontier_warehouse.png (C3 economic stopping, native USD)
- selective_frontier.png       (feasibility-gated intervals — the methods result)
- coverage_main.png            (C1 within-run coverage, all methods)
- transfer_env.png             (cross-env transfer — the transfer-led headline)

Regenerated only where the FULL multi-model BAGEN set is present (other models'
swebench origin trajectories); skipped with a printed notice otherwise:
- transfer_swebench.png        (model-swap transfer)
- allruns.png                  (breadth across every model x env run)

Usage: python -m budget_guard.run_final
"""
from __future__ import annotations

import os
import shutil

from . import (
    run_allruns,
    run_coverage,
    run_economic_warehouse,
    run_gated,
    run_multiresource,
    run_transfer,
    run_transfer_env,
)

OUTDIR = "figures/final"
SEEDS = (0, 1, 2, 3, 4)


def _collect(*names: str) -> None:
    """Copy figures written to figures/ into the fixed-seed final set."""
    os.makedirs(OUTDIR, exist_ok=True)
    for name in names:
        src = os.path.join("figures", name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(OUTDIR, name))
            print(f"  collected {name}")
        else:
            print(f"  MISSING {name} (driver did not write it)")


def _has_multimodel_data() -> bool:
    """True when other models' swebench trajectories are on disk (model-swap + breadth)."""
    try:
        return len(run_transfer.target_runs()) >= 2 and len(run_allruns.discover_runs()) >= 10
    except (OSError, KeyError):
        return False


def main() -> None:
    run_multiresource.main(seeds=SEEDS, outdir=OUTDIR)       # C2 joint (like-for-like)
    run_economic_warehouse.main(seeds=SEEDS, outdir=OUTDIR)  # C3 abort frontier
    run_gated.main(seeds=SEEDS, outdir=OUTDIR)               # selective frontier (methods)

    run_coverage.main(seeds=SEEDS)                           # C1 coverage
    run_transfer_env.main(seeds=SEEDS)                       # cross-env transfer
    _collect("coverage_main.png", "transfer_env.png")

    if _has_multimodel_data():
        run_transfer.main()                                  # model-swap transfer
        run_allruns.main()                                    # breadth, all runs
        _collect("transfer_swebench.png", "allruns.png")
    else:
        print("\nSKIPPED transfer_swebench.png + allruns.png — the full multi-model BAGEN "
              "set is not on this machine (see scripts/fetch_bagen.py).")

    print(f"\nfinal figures written to {OUTDIR}/")


if __name__ == "__main__":
    main()
