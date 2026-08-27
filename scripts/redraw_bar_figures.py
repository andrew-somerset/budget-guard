#!/usr/bin/env python3
"""Redraw the three bar-chart figures from the committed tables, without recomputing.

The paper embeds figures/coverage_main.png (Figure 2), figures/transfer_env.png and
figures/transfer_swebench.png (Figure 3). Their numbers come from tables/*.csv, which
are tracked in git, so a purely cosmetic change (legend, labels) should not require
the multi-minute conformal recomputation behind `make repro`. This script calls the
same plot functions the run modules use, fed from the CSVs they wrote.

Usage: python scripts/redraw_bar_figures.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from budget_guard.run_coverage import plot_coverage  # noqa: E402
from budget_guard.run_transfer import plot_transfer_swebench  # noqa: E402
from budget_guard.run_transfer_env import plot_transfer_env  # noqa: E402


def n_seeds(per_seed_csv: str) -> int:
    return int(pd.read_csv(per_seed_csv)["seed"].nunique())


def main() -> None:
    os.makedirs("figures", exist_ok=True)
    plot_coverage(pd.read_csv("tables/coverage.csv"), n_seeds("tables/coverage_per_seed.csv"))
    plot_transfer_env(pd.read_csv("tables/transfer_env.csv"), n_seeds("tables/transfer_env_per_seed.csv"))
    plot_transfer_swebench(pd.read_csv("tables/transfer_swebench.csv"),
                           n_seeds("tables/transfer_swebench_per_seed.csv"))
    print("redrew figures/coverage_main.png, figures/transfer_env.png, figures/transfer_swebench.png")


if __name__ == "__main__":
    main()
