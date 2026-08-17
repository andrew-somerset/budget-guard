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

With --full, additionally regenerates every remaining reported table: external-budget
transfer, censored rungs, conditional coverage, per-env economics / cost-of-pass /
gap / label-efficiency, and the three loop-layer drivers. Split out because the loop
stress sweep alone is 4 windows x 10 order seeds and dominates the runtime — the
default set is what the write-up's figures come from.

Usage: python -m budget_guard.run_final [--full]
"""
from __future__ import annotations

import os
import shutil

from . import (
    run_allruns,
    run_censored,
    run_conditional,
    run_costofpass,
    run_coverage,
    run_economic,
    run_economic_warehouse,
    run_gap,
    run_gated,
    run_label_efficiency,
    run_loop_closed_loop,
    run_loop_stress,
    run_loop_validation,
    run_multiresource,
    run_transfer,
    run_transfer_env,
    run_transfer_warehouse,
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


def _require_data() -> None:
    """Fail early and actionably when the BAGEN subset has not been fetched.

    Without this, the first driver dies on a raw FileNotFoundError naming a path deep
    inside data/bagen_hf/, which reads like a bug rather than a missing download step —
    and `make repro` is a plausible first command for someone who has just built the
    image.
    """
    data = os.path.join(os.path.dirname(__file__), "..", "data", "bagen_hf")
    if os.path.isdir(data) and os.listdir(data):
        return
    raise SystemExit(
        "No BAGEN data found at data/bagen_hf/.\n\n"
        "The experiment drivers read logged rollouts that are not part of the repo\n"
        "(licence + size); fetch the revision-pinned subset first:\n\n"
        "    make fetch          # or: python scripts/fetch_bagen.py\n\n"
        "Nothing else is needed — the fetch is pinned to a fixed BAGEN revision, so it\n"
        "produces the same bytes every reported number was computed from.\n\n"
        "To check the committed results without regenerating them, run:\n"
        "    make check-numbers"
    )


def _has_multimodel_data() -> bool:
    """True when other models' swebench trajectories are on disk (model-swap + breadth)."""
    try:
        return len(run_transfer.target_runs()) >= 2 and len(run_allruns.discover_runs()) >= 10
    except (OSError, KeyError):
        return False


def _remaining_tables() -> None:
    """Every reported table not covered by the headline set above.

    Kept behind --full: these back claims in the methods section but do not
    produce write-up figures, and the loop stress sweep dominates total runtime.
    """
    print("\n--- external-budget transfer + methods tables ---")
    run_transfer_warehouse.main(seeds=SEEDS)     # transfer_warehouse{,_per_seed}
    run_censored.main(seeds=SEEDS)               # censored_upper
    run_conditional.main(seeds=SEEDS)            # conditional_coverage

    print("\n--- per-env economics / diagnostics ---")
    for env in ("sokoban", "swebench"):
        run_economic.run(env, seeds=SEEDS)       # abort_frontier_<env>
        run_costofpass.run(env, seeds=SEEDS)     # cost_of_pass_<env>
    for env in ("sokoban", "searchr1", "swebench"):
        run_gap.run(env)                         # gap_<env> (single-seed diagnostic)
    run_label_efficiency.run("sokoban", seeds=SEEDS)  # label_efficiency_sokoban

    print("\n--- loop layer ---")
    run_loop_validation.main(resume=True)        # loop_validation{,_per_seed}
    run_loop_stress.main(resume=True)            # loop_stress{,_raw}
    run_loop_closed_loop.main(seeds=SEEDS)       # loop_closed_loop{,_per_seed}


def main(full: bool = False) -> None:
    _require_data()
    run_multiresource.main(seeds=SEEDS, outdir=OUTDIR)       # C2 joint (like-for-like)
    run_economic_warehouse.main(seeds=SEEDS, outdir=OUTDIR)  # C3 abort frontier
    run_gated.main(seeds=SEEDS, outdir=OUTDIR)               # selective frontier (methods)

    run_coverage.main(seeds=SEEDS)                           # C1 coverage
    run_transfer_env.main(seeds=SEEDS)                       # cross-env transfer
    _collect("coverage_main.png", "transfer_env.png")

    if _has_multimodel_data():
        run_transfer.main(seeds=SEEDS)                       # model-swap transfer
        run_allruns.main()                                    # breadth, all runs
        _collect("transfer_swebench.png", "allruns.png")
    else:
        print("\nSKIPPED transfer_swebench.png + allruns.png — the full multi-model BAGEN "
              "set is not on this machine (see scripts/fetch_bagen.py).")

    if full:
        _remaining_tables()

    print(f"\nfinal figures written to {OUTDIR}/")


if __name__ == "__main__":
    import sys

    main(full="--full" in sys.argv[1:])
