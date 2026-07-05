"""budget_guard/metrics.py — interval quality metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd


def marginal_coverage(y, lo, hi) -> float:
    """Fraction of samples whose interval contains the truth."""
    y, lo, hi = map(np.asarray, (y, lo, hi))
    return float(np.mean((lo <= y) & (y <= hi)))


def mean_width(lo, hi) -> float:
    return float(np.mean(np.asarray(hi) - np.asarray(lo)))


def median_width(lo, hi) -> float:
    """Robust to the occasional unbounded interval proper ACI can emit."""
    return float(np.median(np.asarray(hi) - np.asarray(lo)))


def frac_unbounded(hi) -> float:
    return float(np.mean(~np.isfinite(np.asarray(hi))))


def rollout_bootstrap_ci(y, lo, hi, groups, B: int = 500, level: float = 0.9, seed: int = 0):
    """Coverage CI that respects within-rollout correlation: resample ROLLOUTS with
    replacement, not prefix samples. Per-sample binomial CIs are too tight here."""
    y, lo, hi = map(np.asarray, (y, lo, hi))
    covered = ((lo <= y) & (y <= hi)).astype(float)
    uniq, inv = np.unique(np.asarray(groups), return_inverse=True)
    cov_sum = np.bincount(inv, weights=covered)
    counts = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(uniq), size=(B, len(uniq)))
    stats = cov_sum[idx].sum(axis=1) / counts[idx].sum(axis=1)
    tail = (1 - level) / 2
    return float(np.quantile(stats, tail)), float(np.quantile(stats, 1 - tail))


def normalized_width(y, lo, hi, agg: str = "mean") -> float:
    """Width relative to y's central 80% range — comparable across envs whose
    token scales differ by orders of magnitude. agg='median' is robust to
    unbounded intervals."""
    y = np.asarray(y)
    spread = float(np.quantile(y, 0.9) - np.quantile(y, 0.1))
    if spread <= 0:
        return float("nan")
    width = median_width(lo, hi) if agg == "median" else mean_width(lo, hi)
    return width / spread
