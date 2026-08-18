"""Item-1 audit: coverage on analytically-known data + injected-drift direction.

Synthetic only (no BAGEN data). Two guarantees the whole project rests on:
(1) the conformal machinery hits nominal on exchangeable data, with nominal inside a
    rollout cluster-bootstrap CI (not a per-sample binomial one);
(2) under an injected distribution shift, FROZEN split conformal degrades while ONLINE
    windowed-CQR recovers — the direction the theory predicts. If this direction ever flips,
    the transfer story (the paper's lead) is wrong.
"""
import numpy as np
import pandas as pd

from budget_guard.conformal import cqr_split, spci, split_conformal_absres
from budget_guard.metrics import marginal_coverage, rollout_bootstrap_ci
from budget_guard.split import group_split


def _grouped(n_rollouts=300, per=6, seed=0, shift=0.0, scale=1.0):
    """Exchangeable regression with a rollout structure; shift/scale simulate drift."""
    rng = np.random.default_rng(seed)
    n = n_rollouts * per
    X = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n)})
    base = 3 * X["a"].to_numpy() - 2 * X["b"].to_numpy() + rng.normal(scale=1.0, size=n)
    y = (base - base.min()) * scale + shift
    return X, y, np.repeat(np.arange(n_rollouts), per)


def test_clean_data_hits_nominal_within_cluster_ci():
    """i.i.d. exchangeable: split-CQR must contain nominal 0.90 in its rollout CI."""
    X, y, g = _grouped(seed=0)
    m = group_split(pd.DataFrame({"rollout_index": g}), seed=0)
    tr, ca, te = m["train"], m["cal"], m["test"]
    lo, hi, _ = cqr_split(X[tr], y[tr], X[ca], y[ca], X[te], alpha=0.1)
    cov = marginal_coverage(y[te], lo, hi)
    ci = rollout_bootstrap_ci(y[te], lo, hi, g[te])
    assert ci[0] <= 0.90 <= ci[1], f"nominal outside cluster CI {ci} (cov={cov:.3f})"


def test_clean_data_absres_hits_nominal():
    X, y, g = _grouped(seed=3)
    m = group_split(pd.DataFrame({"rollout_index": g}), seed=3)
    tr, ca, te = m["train"], m["cal"], m["test"]
    lo, hi, _ = split_conformal_absres(X[tr], y[tr], X[ca], y[ca], X[te], alpha=0.1)
    assert 0.86 <= marginal_coverage(y[te], lo, hi) <= 0.94


def test_injected_drift_frozen_degrades_online_recovers():
    """Calibrate on clean data, deploy on a shifted stream: frozen split-CQR must
    under-cover; windowed-CQR must recover meaningfully toward nominal."""
    Xc, yc, gc = _grouped(n_rollouts=300, seed=1)
    m = group_split(pd.DataFrame({"rollout_index": gc}), fracs=(0.6, 0.4, 0.0), seed=1)
    tr, ca = m["train"], m["cal"]
    Xs, ys, gs = _grouped(n_rollouts=400, seed=2, shift=6.0, scale=1.6)  # deployment drift

    lo_f, hi_f, _ = cqr_split(Xc[tr], yc[tr], Xc[ca], yc[ca], Xs, alpha=0.1)
    cov_frozen = marginal_coverage(ys, lo_f, hi_f)
    # rollout-safe revelation: online must recover using only completed-rollout labels
    lo_o, hi_o, _ = spci(Xc[tr], yc[tr], Xc[ca], yc[ca], Xs, ys, alpha=0.1, groups=gs)
    cov_online = marginal_coverage(ys, lo_o, hi_o)

    assert cov_frozen < 0.75, f"frozen should degrade under shift, got {cov_frozen:.3f}"
    assert cov_online >= cov_frozen + 0.10, f"online should recover ({cov_online:.3f} vs {cov_frozen:.3f})"
    assert cov_online >= 0.80, f"online should be near nominal, got {cov_online:.3f}"
