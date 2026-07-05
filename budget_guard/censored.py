"""budget_guard/censored.py — conformal upper bounds when doomed runs censor the label.

Setting: remaining-cost y is observed only for feasible runs; infeasible runs are
censored — we know only that y exceeded the remaining budget b = budget − spent
(else the run would have finished inside it). Censoring bites the UPPER endpoint:
censored y's are systematically LARGE, so calibrating hi = pred + qhat on
uncensored data alone under-covers the very runs a budget guard most needs to flag.

Four calibrations of the one-sided upper bound, P(y <= hi) >= 1 − alpha:
- ``drop``      : uncensored scores only (the naive thing; expected to under-cover).
- ``infinity``  : censored scores treated as +inf — always valid, but qhat = inf
                  whenever the censored fraction exceeds alpha (useless at 50%).
- ``bound``     : censored scores replaced by their known lower bound b − pred —
                  informed middle ground; validity depends on how tight b is.
- ``ipcw``      : inverse-probability-of-censoring-weighted quantile of uncensored
                  scores, p̂(uncensored | x) from the feasibility classifier —
                  approximately valid, informative (the survival-analysis route).

Warehouse validation: censored rows secretly retain their totals, so true y is
recoverable — mask it, calibrate as if censored, then measure real coverage.
"""
from __future__ import annotations

import numpy as np


def _weighted_quantile(scores: np.ndarray, weights: np.ndarray, level: float) -> float:
    order = np.argsort(scores)
    scores, weights = scores[order], weights[order]
    cdf = np.cumsum(weights) / np.sum(weights)
    idx = int(np.searchsorted(cdf, level, side="left"))
    return float(scores[min(idx, len(scores) - 1)])


def upper_qhat(
    scores_uncensored: np.ndarray,
    censored_lower_bounds: np.ndarray,
    alpha: float,
    method: str,
    p_uncensored: np.ndarray | None = None,
) -> float:
    """qhat for hi = pred + qhat under the four censoring treatments.

    ``censored_lower_bounds``: per censored CAL sample, the known lower bound on its
    score (b_i − pred_i). ``p_uncensored``: P(uncensored | x_i) for the UNCENSORED
    cal samples (ipcw only).
    """
    s_unc = np.asarray(scores_uncensored, dtype=float)
    s_cens = np.asarray(censored_lower_bounds, dtype=float)
    n = len(s_unc) + len(s_cens)
    level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / max(n, 1))

    if method == "drop":
        n_u = len(s_unc)
        lvl = min(1.0, np.ceil((n_u + 1) * (1 - alpha)) / max(n_u, 1))
        return float(np.quantile(s_unc, lvl, method="higher"))
    if method == "infinity":
        pooled = np.concatenate([s_unc, np.full(len(s_cens), np.inf)])
        return float(np.quantile(pooled, level, method="higher"))
    if method == "bound":
        pooled = np.concatenate([s_unc, s_cens])
        return float(np.quantile(pooled, level, method="higher"))
    if method == "ipcw":
        assert p_uncensored is not None
        w = 1.0 / np.clip(np.asarray(p_uncensored, dtype=float), 0.05, 1.0)
        return _weighted_quantile(s_unc, w, 1 - alpha)
    raise ValueError(method)
