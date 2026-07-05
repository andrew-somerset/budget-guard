"""budget_guard/multiresource.py — C2: joint intervals over {time, warehouse, cost}.

Data comes straight from the official Warehouse estimation records: each per-prefix
``ground_truth`` carries the true remaining amount of all three resources, so no
dialogue extraction is needed. Legal features are quantities known at turn k
(progress so far + the budgets fixed at task start); ``actual_*`` totals are leaks.

Joint methods:
- ``independent``: split-CQR per resource at alpha — each margin covers ~1-alpha,
  but the *joint* event (all three covered at once) does not.
- ``bonferroni_joint``: split-CQR per resource at alpha/3 — union bound guarantees
  joint coverage ≥ 1-alpha, at the price of wider margins.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, cqr_split

RESOURCES = ("time_weeks", "warehouse_item_weeks", "cost_usd")

_FEATURES = (
    "completed_turns",
    "completed_weeks",
    "current_cash_usd",
    "target_cash_usd",
    "budget_time_weeks",
    "budget_warehouse_item_weeks",
    "budget_cost_usd",
)


def load_warehouse(path: str) -> pd.DataFrame:
    """One row per prefix sample: legal features + the three targets.

    Samples with ``can_finish=False`` carry no remaining-resource labels (the run
    cannot complete within budget, so "remaining to completion" is undefined) —
    they are censored, not missing at random. C2 regresses on the feasible half;
    the censored half is the economic-stopping (C3) signal.
    """
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = []
    censored = 0
    for record in payload["results"]:
        gt = record["ground_truth"]
        if gt.get(f"actual_remaining_{RESOURCES[0]}") is None:
            censored += 1
            continue
        row = {"rollout_index": record["rollout_index"], "sample_id": record["sample_id"]}
        for feat in _FEATURES:
            row[feat] = gt[feat]
        for res in RESOURCES:
            row[f"y_{res}"] = gt[f"actual_remaining_{res}"]
        rows.append(row)
    df = pd.DataFrame(rows)
    assert df[[f"y_{r}" for r in RESOURCES]].notna().all().all()
    df.attrs["censored_samples"] = censored
    return df


def agent_joint_baseline(path: str) -> dict:
    """The BAGEN agent's own per-resource and joint coverage, from the summary."""
    with open(path, "r", encoding="utf-8") as handle:
        summary = json.load(handle)["summary"]
    return {
        "time_weeks": summary["time_interval_coverage_rate"],
        "warehouse_item_weeks": summary["warehouse_interval_coverage_rate"],
        "cost_usd": summary["cost_interval_coverage_rate"],
        "joint": summary["all_interval_coverage_rate"],
    }


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    X = df[list(_FEATURES)].astype(float).copy()
    X["cash_gap"] = X["current_cash_usd"] - X["target_cash_usd"]
    X["weeks_left_of_budget"] = X["budget_time_weeks"] - X["completed_weeks"]
    return X


def joint_intervals(
    df: pd.DataFrame,
    masks: dict[str, np.ndarray],
    alpha: float = DEFAULT_ALPHA,
    scheme: str = "bonferroni",
) -> dict:
    """Per-resource CQR intervals under the given correction scheme.

    Returns {resource: (lo, hi)} on the test rows plus the per-margin alpha used.
    """
    per_margin_alpha = alpha / len(RESOURCES) if scheme == "bonferroni" else alpha
    X = build_features(df)
    tr, ca, te = masks["train"], masks["cal"], masks["test"]
    out = {}
    for res in RESOURCES:
        y = df[f"y_{res}"].to_numpy(dtype=float)
        lo, hi, _ = cqr_split(
            X[tr], y[tr], X[ca], y[ca], X[te], alpha=per_margin_alpha
        )
        out[res] = (lo, hi)
    return {"intervals": out, "per_margin_alpha": per_margin_alpha}


def joint_coverage(df: pd.DataFrame, test_mask: np.ndarray, intervals: dict) -> dict:
    """Per-resource and all-at-once coverage on the test rows."""
    covered_all = np.ones(int(test_mask.sum()), dtype=bool)
    out = {}
    for res, (lo, hi) in intervals.items():
        y = df.loc[test_mask, f"y_{res}"].to_numpy(dtype=float)
        covered = (lo <= y) & (y <= hi)
        out[res] = float(covered.mean())
        covered_all &= covered
    out["joint"] = float(covered_all.mean())
    return out
