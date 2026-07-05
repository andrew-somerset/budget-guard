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
