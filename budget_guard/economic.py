"""budget_guard/economic.py — C3: calibrated feasibility + economic stopping rule.

The guard watches a run and may abort it. Two error costs: aborting a run that
would have finished (lose its value) vs. riding a doomed run to the end (burn its
remaining tokens). The rule: abort at the first turn whose feasibility score drops
below tau.

Calibration is at ROLLOUT level, matching the sequential decision: the rule aborts
a rollout iff its minimum prefix score < tau, so tau is set to the delta-quantile
(finite-sample corrected) of feasible CAL rollouts' minimum scores. That bounds
P(falsely abort a feasible run) <= delta — a per-run guarantee, not per-prefix.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_LGBM_PARAMS = dict(
    n_estimators=200,
    learning_rate=0.05,
    num_leaves=15,
    min_child_samples=10,
    verbose=-1,
)


def fit_feasibility(X_train, feasible_train):
    from lightgbm import LGBMClassifier

    model = LGBMClassifier(**_LGBM_PARAMS)
    model.fit(X_train, feasible_train.astype(int))
    return model


def _rollout_min_scores(df: pd.DataFrame, scores: np.ndarray) -> pd.DataFrame:
    """Per rollout: min feasibility score over its prefixes + labels/costs."""
    tmp = df[["rollout_index", "can_finish", "tokens_so_far", "total_rollout_tokens", "k"]].copy()
    tmp["score"] = scores
    return tmp.groupby("rollout_index").agg(
        min_score=("score", "min"),
        feasible=("can_finish", "first"),
        total_tokens=("total_rollout_tokens", "first"),
    )


def calibrate_threshold(df_cal: pd.DataFrame, scores_cal: np.ndarray, delta: float) -> float:
    """tau s.t. P(min prefix score of a feasible run < tau) <= delta on CAL."""
    per = _rollout_min_scores(df_cal, scores_cal)
    feas = np.sort(per.loc[per["feasible"], "min_score"].to_numpy())
    n = len(feas)
    if n == 0:
        return -np.inf
    # finite-sample: rank floor((n+1)*delta); 0 -> abort nothing
    rank = int(np.floor((n + 1) * delta))
    if rank < 1:
        return -np.inf
    return float(feas[min(rank, n) - 1])


def evaluate_stopping(df_test: pd.DataFrame, scores_test: np.ndarray, tau: float) -> dict:
    """Apply 'abort at first prefix with score < tau' to each test rollout."""
    tmp = df_test[["rollout_index", "k", "can_finish", "tokens_so_far", "total_rollout_tokens"]].copy()
    tmp["score"] = scores_test

    n_feasible = n_doomed = false_aborts = 0
    doomed_total = doomed_saved = 0.0
    for _, g in tmp.sort_values("k").groupby("rollout_index"):
        feasible = bool(g["can_finish"].iloc[0])
        total = float(g["total_rollout_tokens"].iloc[0])
        below = g[g["score"] < tau]
        aborted = len(below) > 0
        if feasible:
            n_feasible += 1
            false_aborts += int(aborted)
        else:
            n_doomed += 1
            doomed_total += total
            if aborted:
                doomed_saved += total - float(below["tokens_so_far"].iloc[0])
    return {
        "tau": tau,
        "false_abort_rate": false_aborts / n_feasible if n_feasible else np.nan,
        "doomed_savings_frac": doomed_saved / doomed_total if doomed_total else np.nan,
        "n_feasible": n_feasible,
        "n_doomed": n_doomed,
    }


def fit_remaining_regressor(X_train, y_train):
    from lightgbm import LGBMRegressor

    model = LGBMRegressor(objective="regression", **_LGBM_PARAMS)
    model.fit(X_train, y_train)
    return model


def calibrate_lower_bound(df_cal: pd.DataFrame, pred_cal: np.ndarray, delta: float) -> float:
    """qhat s.t. lo_t = pred_t - qhat under-shoots y_t at EVERY prefix of a feasible
    run, except with prob <= delta. Score = pred - y; rollout-level max over feasible
    CAL rollouts; qhat = (1-delta)-quantile with the (n+1) correction.

    For a feasible run total <= budget, so tokens_so_far + lo_t > budget implies
    lo_t > y_t — controlling the invalid-lower-bound event controls false aborts.
    """
    tmp = df_cal[["rollout_index", "can_finish"]].copy()
    tmp["score"] = pred_cal - df_cal["y"].to_numpy(dtype=float)
    per = tmp.groupby("rollout_index").agg(
        max_score=("score", "max"), feasible=("can_finish", "first")
    )
    scores = np.sort(per.loc[per["feasible"], "max_score"].to_numpy())
    n = len(scores)
    if n == 0:
        return float("inf")
    rank = int(np.ceil((n + 1) * (1 - delta)))
    if rank > n:
        return float("inf")
    return float(scores[rank - 1])


def evaluate_interval_stopping(
    df_test: pd.DataFrame,
    pred_test: np.ndarray,
    qhat: float,
    budget: float,
    scores_test: Optional[np.ndarray] = None,
    tau: float = -np.inf,
) -> dict:
    """Abort at the first prefix where tokens_so_far + (pred - qhat) > budget,
    OR (if a feasibility score is supplied) where score < tau — the combined rule.
    """
    tmp = df_test[["rollout_index", "k", "can_finish", "tokens_so_far", "total_rollout_tokens"]].copy()
    tmp["lo_total"] = df_test["tokens_so_far"].to_numpy(dtype=float) + (pred_test - qhat)
    tmp["feas_score"] = scores_test if scores_test is not None else np.inf

    n_feasible = n_doomed = false_aborts = 0
    doomed_total = doomed_saved = 0.0
    for _, g in tmp.sort_values("k").groupby("rollout_index"):
        feasible = bool(g["can_finish"].iloc[0])
        total = float(g["total_rollout_tokens"].iloc[0])
        trigger = g[(g["lo_total"] > budget) | (g["feas_score"] < tau)]
        aborted = len(trigger) > 0
        if feasible:
            n_feasible += 1
            false_aborts += int(aborted)
        else:
            n_doomed += 1
            doomed_total += total
            if aborted:
                doomed_saved += total - float(trigger["tokens_so_far"].iloc[0])
    return {
        "false_abort_rate": false_aborts / n_feasible if n_feasible else np.nan,
        "doomed_savings_frac": doomed_saved / doomed_total if doomed_total else np.nan,
        "n_feasible": n_feasible,
        "n_doomed": n_doomed,
    }


def hard_cap_baseline(df_test: pd.DataFrame, cap_tokens: float) -> dict:
    """Heuristic: abort when tokens_so_far exceeds a fixed cap."""
    tmp = df_test[["rollout_index", "k", "can_finish", "tokens_so_far", "total_rollout_tokens"]]
    n_feasible = n_doomed = false_aborts = 0
    doomed_total = doomed_saved = 0.0
    for _, g in tmp.sort_values("k").groupby("rollout_index"):
        feasible = bool(g["can_finish"].iloc[0])
        total = float(g["total_rollout_tokens"].iloc[0])
        over = g[g["tokens_so_far"] > cap_tokens]
        aborted = len(over) > 0
        if feasible:
            n_feasible += 1
            false_aborts += int(aborted)
        else:
            n_doomed += 1
            doomed_total += total
            if aborted:
                doomed_saved += total - float(over["tokens_so_far"].iloc[0])
    return {
        "cap_tokens": cap_tokens,
        "false_abort_rate": false_aborts / n_feasible if n_feasible else np.nan,
        "doomed_savings_frac": doomed_saved / doomed_total if doomed_total else np.nan,
    }
