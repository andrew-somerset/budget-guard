"""budget_guard/split.py — TRAIN/CAL/TEST split by rollout, never by prefix.

Prefixes of one rollout share ``total_rollout_tokens``; splitting them apart would
leak each test rollout's answer into calibration.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def group_split(
    df: pd.DataFrame,
    fracs: tuple[float, float, float] = (0.5, 0.25, 0.25),
    seed: int = 0,
) -> dict[str, np.ndarray]:
    """Boolean masks {'train','cal','test'} over df rows, split by rollout_index."""
    assert abs(sum(fracs) - 1.0) < 1e-9, "fracs must sum to 1"
    rollouts = df["rollout_index"].unique()
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(rollouts)
    n = len(shuffled)
    n_train = int(round(fracs[0] * n))
    n_cal = int(round(fracs[1] * n))
    parts = {
        "train": set(shuffled[:n_train]),
        "cal": set(shuffled[n_train : n_train + n_cal]),
        "test": set(shuffled[n_train + n_cal :]),
    }
    masks = {
        name: df["rollout_index"].isin(members).to_numpy()
        for name, members in parts.items()
    }
    total = masks["train"].astype(int) + masks["cal"].astype(int) + masks["test"].astype(int)
    assert (total == 1).all(), "masks must partition the rows"
    return masks
