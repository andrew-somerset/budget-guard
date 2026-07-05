"""budget_guard/features.py — leak-free feature matrix from the extractor table.

``build_xy`` consumes the DataFrame produced by ``extract.samples_to_dataframe`` and
returns (X, y, groups). Every feature is computable at turn k mid-run; the LEAK set
(anything that peeks at the rollout's future) is asserted out.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Known at the end of the run only — never features (see data_dictionary.md).
LEAK_COLUMNS = frozenset(
    {"N", "total_rollout_tokens", "y", "rollout_success", "can_finish", "sample_id"}
)


def build_xy(
    df: pd.DataFrame, agent_est: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Return (X, y, groups) with only turn-k-legal features.

    groups = rollout_index, for group-aware splitting (never split by prefix).
    ``agent_est`` (sample_id, agent_lo, agent_hi) adds the agent's own per-turn
    self-estimate as features; missing estimates become NaN (LGBM handles them).
    """
    per = df["per_turn_total"]
    X = pd.DataFrame(index=df.index)
    X["k"] = df["k"].astype(float)
    X["tokens_so_far"] = df["tokens_so_far"].astype(float)
    X["burn_rate"] = X["tokens_so_far"] / X["k"]
    X["last_turn_tokens"] = per.map(lambda v: float(v[-1]))
    X["mean_turn_tokens"] = per.map(lambda v: float(np.mean(v)))
    X["std_turn_tokens"] = per.map(lambda v: float(np.std(v)) if len(v) > 1 else 0.0)
    X["min_turn_tokens"] = per.map(lambda v: float(np.min(v)))
    X["max_turn_tokens"] = per.map(lambda v: float(np.max(v)))
    X["last3_mean_tokens"] = per.map(lambda v: float(np.mean(v[-3:])))
    X["turn_trend"] = X["last_turn_tokens"] - X["mean_turn_tokens"]

    if agent_est is not None:
        est = df[["sample_id"]].merge(agent_est, on="sample_id", how="left")
        est.index = df.index
        X["agent_lo"] = est["agent_lo"]
        X["agent_hi"] = est["agent_hi"]
        X["agent_mid"] = (est["agent_lo"] + est["agent_hi"]) / 2
        X["agent_width"] = est["agent_hi"] - est["agent_lo"]

    leaked = set(X.columns) & LEAK_COLUMNS
    assert not leaked, f"leak features present: {leaked}"

    y = df["y"].to_numpy(dtype=float)
    groups = df["rollout_index"].to_numpy()
    return X, y, groups
