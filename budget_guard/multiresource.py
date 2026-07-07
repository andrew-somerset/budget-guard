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

# Per-sample agent interval-coverage flags in the record's ``metrics`` (BAGEN's own
# per-resource "did the agent's interval contain the truth" indicators). Averaging
# these over the guard's feasible test rows gives a like-for-like agent baseline.
_AGENT_COV_KEY = {
    "time_weeks": "time_interval_contains_actual",
    "warehouse_item_weeks": "warehouse_interval_contains_actual",
    "cost_usd": "cost_interval_contains_actual",
}

_FEATURES = (
    "completed_turns",
    "completed_weeks",
    "current_cash_usd",
    "target_cash_usd",
    "budget_time_weeks",
    "budget_warehouse_item_weeks",
    "budget_cost_usd",
)


def load_warehouse(path: str, keep_censored: bool = False) -> pd.DataFrame:
    """One row per prefix sample: legal features + the three targets.

    Samples with ``can_finish=False`` carry no remaining-resource labels (the run
    cannot complete within budget, so "remaining to completion" is undefined by
    BAGEN's convention) — but their realized totals ARE recorded, so with
    ``keep_censored=True`` the rows come back flagged ``censored`` with
    ``y_*`` recovered from ``actual_total_* − spent_so_far``. That recoverability
    is what makes Warehouse the mask-and-measure testbed for censored conformal.

    Spend-so-far: exact for time (= completed_weeks); cost/warehouse are
    interpolated as completed_weeks/total_weeks × total (stated approximation).
    """
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = []
    for record in payload["results"]:
        gt = record["ground_truth"]
        is_censored = gt.get(f"actual_remaining_{RESOURCES[0]}") is None
        if is_censored and not keep_censored:
            continue
        row = {
            "rollout_index": record["rollout_index"],
            "sample_id": record["sample_id"],
            "censored": is_censored,
            "can_finish": bool(gt.get("actual_can_finish")),
        }
        for feat in _FEATURES:
            row[feat] = gt[feat]
        total_weeks = gt.get("actual_total_time_weeks")
        frac = (gt["completed_weeks"] / total_weeks) if total_weeks else np.nan
        for res in RESOURCES:
            total = gt.get(f"actual_total_{res}")
            if res == "time_weeks":
                spent = gt["completed_weeks"]
            else:
                spent = frac * total if total is not None else np.nan
            row[f"total_{res}"] = total
            row[f"spent_{res}"] = spent
            remaining = gt.get(f"actual_remaining_{res}")
            if remaining is None and total is not None and np.isfinite(spent):
                remaining = max(0.0, total - spent)  # recovered truth for censored rows
            row[f"y_{res}"] = remaining
        metrics = record.get("metrics") or {}
        for res in RESOURCES:
            row[f"agent_cov_{res}"] = bool(metrics.get(_AGENT_COV_KEY[res]))
        rows.append(row)
    df = pd.DataFrame(rows)
    if not keep_censored:
        assert df[[f"y_{r}" for r in RESOURCES]].notna().all().all()
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

    - ``independent``: each margin conformalized at alpha (joint under-covers).
    - ``bonferroni``: each margin at alpha/3 (union bound; conservative).
    - ``copula``: one shared rank level u*, the smallest for which the CAL samples'
      *joint* event {all three scores within their u-quantiles} holds with frequency
      >= 1-alpha (+1 corrected). Adapts to the actual dependence between resources,
      so it sits between independent and Bonferroni in width while keeping >= 1-alpha
      joint coverage on CAL.

    Returns {resource: (lo, hi)} on the test rows plus the per-margin level used.
    """
    from .conformal import _cqr_scores, _fit_cqr

    X = build_features(df)
    tr, ca, te = masks["train"], masks["cal"], masks["test"]

    if scheme in ("independent", "bonferroni"):
        per_margin_alpha = alpha / len(RESOURCES) if scheme == "bonferroni" else alpha
        out = {}
        for res in RESOURCES:
            y = df[f"y_{res}"].to_numpy(dtype=float)
            lo, hi, _ = cqr_split(X[tr], y[tr], X[ca], y[ca], X[te], alpha=per_margin_alpha)
            out[res] = (lo, hi)
        return {"intervals": out, "per_margin_level": 1 - per_margin_alpha}

    assert scheme == "copula", scheme
    cal_scores, test_preds = {}, {}
    for res in RESOURCES:
        y = df[f"y_{res}"].to_numpy(dtype=float)
        mlo, mhi = _fit_cqr(X[tr], y[tr], alpha)
        cal_scores[res] = _cqr_scores(mlo.predict(X[ca]), mhi.predict(X[ca]), y[ca])
        test_preds[res] = (mlo.predict(X[te]), mhi.predict(X[te]))

    n = int(ca.sum())
    score_mat = np.column_stack([cal_scores[res] for res in RESOURCES])
    # smallest shared level u whose per-margin u-quantiles jointly cover >= 1-alpha on CAL
    u_star = 1.0
    for u in np.linspace(0.90, 1.0, 101):
        qhats = np.quantile(score_mat, u, axis=0, method="higher")
        joint_ok = (score_mat <= qhats).all(axis=1).sum()
        if (joint_ok + 1) / (n + 1) >= 1 - alpha:
            u_star = float(u)
            break
    qhats = np.quantile(score_mat, u_star, axis=0, method="higher")
    out = {
        res: (np.maximum(test_preds[res][0] - qhats[i], 0.0), test_preds[res][1] + qhats[i])
        for i, res in enumerate(RESOURCES)
    }
    return {"intervals": out, "per_margin_level": u_star}


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
