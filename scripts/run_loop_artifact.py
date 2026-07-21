"""Regenerate generic loop-engineering evidence and write an auditable manifest.

Usage:
  python scripts/run_loop_artifact.py --quick   # one seed / two orderings
  python scripts/run_loop_artifact.py --full    # five seeds / full 200-run stress grid
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from budget_guard.run_loop_closed_loop import main as run_closed_loop  # noqa: E402
from budget_guard.run_loop_stress import main as run_stress  # noqa: E402
from budget_guard.run_loop_validation import main as run_validation  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--quick", action="store_true")
    mode.add_argument("--full", action="store_true")
    args = parser.parse_args()

    seeds = (0,) if args.quick else (0, 1, 2, 3, 4)
    windows = (10,) if args.quick else (5, 10, 20, 40)
    order_seeds = (0, 1) if args.quick else tuple(range(10))
    started = perf_counter()

    # Fresh tables: resume behavior is useful for interactive chunks, but an artifact
    # build must be self-contained and not inherit stale rows.
    run_validation(seeds=seeds, window_rollouts=10, resume=False)
    run_stress(windows=windows, order_seeds=order_seeds, resume=False)
    run_closed_loop(seeds=seeds, window_rollouts=10)

    outputs = [
        ROOT / "tables" / "loop_validation.csv",
        ROOT / "tables" / "loop_validation_per_seed.csv",
        ROOT / "tables" / "loop_stress.csv",
        ROOT / "tables" / "loop_stress_raw.csv",
        ROOT / "tables" / "loop_closed_loop.csv",
        ROOT / "tables" / "loop_closed_loop_per_seed.csv",
    ]
    manifest = {
        "mode": "quick" if args.quick else "full",
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "seeds": list(seeds),
        "windows": list(windows),
        "order_seeds": list(order_seeds),
        "runtime_seconds": perf_counter() - started,
        "outputs": {
            str(path.relative_to(ROOT)): {"sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in outputs
        },
    }
    destination = ROOT / "tables" / "loop_artifact_manifest.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
