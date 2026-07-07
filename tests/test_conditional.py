"""Item-2 audit: Mondrian-by-depth restores conditional coverage where a global
split-CQR qhat has a depth hole. Synthetic (no BAGEN data)."""
import numpy as np
import pandas as pd

from budget_guard.conformal import cqr_split, mondrian_cqr
from budget_guard.metrics import marginal_coverage
from budget_guard.split import group_split


def test_mondrian_closes_a_depth_coverage_hole():
    """k=1 is high-variance and depth is NOT a feature, so a single global qhat
    (split-CQR) under-covers k=1; a per-depth qhat (Mondrian) restores it."""
    rng = np.random.default_rng(0)
    n_roll = 300
    ks = np.tile([1, 2, 3], n_roll)                 # three depths, equal mass
    groups = np.repeat(np.arange(n_roll), 3)
    x = rng.normal(size=len(ks))
    noise = np.where(ks == 1, 6.0, 1.0)             # the k=1 hole
    y = 2 * x + rng.normal(size=len(ks)) * noise
    y = y - y.min()
    X = pd.DataFrame({"x": x})                       # no depth feature -> can't adapt

    m = group_split(pd.DataFrame({"rollout_index": groups}), seed=0)
    tr, ca, te = m["train"], m["cal"], m["test"]
    k_te = ks[te]

    lo, hi, _ = cqr_split(X[tr], y[tr], X[ca], y[ca], X[te], alpha=0.1)
    cov_k1_marginal = marginal_coverage(y[te][k_te == 1], lo[k_te == 1], hi[k_te == 1])

    lo_m, hi_m, _ = mondrian_cqr(X[tr], y[tr], X[ca], y[ca], ks[ca], X[te], k_te, alpha=0.1)
    cov_k1_mondrian = marginal_coverage(y[te][k_te == 1], lo_m[k_te == 1], hi_m[k_te == 1])

    assert cov_k1_marginal < 0.85, f"expected a k=1 hole, got {cov_k1_marginal:.3f}"
    assert cov_k1_mondrian >= cov_k1_marginal + 0.05, (
        f"Mondrian should lift k=1 ({cov_k1_mondrian:.3f} vs {cov_k1_marginal:.3f})"
    )
