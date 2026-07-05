"""budget_guard/conformal.py — interval predictors for remaining budget.

Offline (Week 2): ``split_conformal_absres`` and ``cqr_split`` — valid when
calibration and test scores are exchangeable.

Online (Week 3, C1): ``aci_cqr`` (Gibbs & Candès 2021) and ``spci`` (windowed
variant of Xu & Xie 2023) — track drift along the test stream by adapting the
miscoverage level / score window as true labels arrive. The stream order is the
natural trajectory order (rollout by rollout, turn by turn), which mimics
deployment: each finished turn reveals its label.

All intervals are clipped below at 0 (remaining tokens are non-negative).
"""
from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np

DEFAULT_ALPHA = 0.1

_LGBM_PARAMS = dict(
    n_estimators=200,
    learning_rate=0.05,
    num_leaves=15,
    min_child_samples=10,
    verbose=-1,
)


def _fit_point(X, y):
    from lightgbm import LGBMRegressor

    model = LGBMRegressor(objective="regression", **_LGBM_PARAMS)
    model.fit(X, y)
    return model


def _fit_quantile(X, y, q: float):
    from lightgbm import LGBMRegressor

    model = LGBMRegressor(objective="quantile", alpha=q, **_LGBM_PARAMS)
    model.fit(X, y)
    return model


def _finite_sample_quantile(scores: np.ndarray, alpha: float) -> float:
    """Conformal quantile with the (n+1) finite-sample correction.

    Returns +inf when the corrected level exceeds 1 — the guarantee then requires
    an unbounded interval. ACI relies on this: under persistent miscoverage its
    working level sinks until the interval opens up, which is what lets it
    re-achieve coverage after a hard distribution shift.
    """
    n = len(scores)
    if n == 0:
        return float("inf")
    level = np.ceil((n + 1) * (1.0 - alpha)) / n
    if level > 1.0:
        return float("inf")
    return float(np.quantile(scores, level, method="higher"))


def _clip_nonneg(lo: np.ndarray) -> np.ndarray:
    return np.maximum(lo, 0.0)


def split_conformal_absres(X_train, y_train, X_cal, y_cal, X_test, alpha=DEFAULT_ALPHA):
    """Symmetric intervals: point prediction ± calibrated |residual| quantile."""
    model = _fit_point(X_train, y_train)
    qhat = _finite_sample_quantile(np.abs(y_cal - model.predict(X_cal)), alpha)
    pred = model.predict(X_test)
    return _clip_nonneg(pred - qhat), pred + qhat, {"qhat": qhat}


def _cqr_scores(qlo_pred, qhi_pred, y):
    """CQR conformity score: how far y falls outside the quantile band."""
    return np.maximum(qlo_pred - y, y - qhi_pred)


def _fit_cqr(X_train, y_train, alpha):
    return _fit_quantile(X_train, y_train, alpha / 2), _fit_quantile(X_train, y_train, 1 - alpha / 2)


def cqr_split(X_train, y_train, X_cal, y_cal, X_test, alpha=DEFAULT_ALPHA):
    """Conformalized quantile regression (Romano et al. 2019)."""
    mlo, mhi = _fit_cqr(X_train, y_train, alpha)
    qhat = _finite_sample_quantile(
        _cqr_scores(mlo.predict(X_cal), mhi.predict(X_cal), y_cal), alpha
    )
    lo = mlo.predict(X_test) - qhat
    hi = mhi.predict(X_test) + qhat
    return _clip_nonneg(lo), hi, {"qhat": qhat}


def aci_cqr(
    X_train, y_train, X_cal, y_cal, X_test, y_test,
    alpha=DEFAULT_ALPHA, gamma: float = 0.01,
):
    """Adaptive Conformal Inference on top of CQR.

    Streams over the test rows in order. After each prediction the true label is
    revealed (a finished turn's cost is observable), and the working miscoverage
    level moves by ``gamma`` toward the target: alpha_t+1 = alpha_t + gamma*(alpha - err_t).
    """
    mlo, mhi = _fit_cqr(X_train, y_train, alpha)
    cal_scores = np.sort(_cqr_scores(mlo.predict(X_cal), mhi.predict(X_cal), y_cal))
    qlo_test, qhi_test = mlo.predict(X_test), mhi.predict(X_test)

    alpha_t = alpha
    lo = np.empty(len(y_test))
    hi = np.empty(len(y_test))
    alphas = np.empty(len(y_test))
    for t in range(len(y_test)):
        if alpha_t <= 0:
            qhat = float("inf")  # the level demands an unbounded interval
        else:
            qhat = _finite_sample_quantile(cal_scores, min(alpha_t, 0.999))
        lo[t] = qlo_test[t] - qhat if np.isfinite(qhat) else 0.0
        hi[t] = qhi_test[t] + qhat
        err = float(not (lo[t] <= y_test[t] <= hi[t]))
        alphas[t] = alpha_t
        alpha_t = alpha_t + gamma * (alpha - err)
    frac_inf = float(np.mean(~np.isfinite(hi)))
    return _clip_nonneg(lo), hi, {"gamma": gamma, "alpha_path": alphas, "frac_inf": frac_inf}


def spci(
    X_train, y_train, X_cal, y_cal, X_test, y_test,
    alpha=DEFAULT_ALPHA, window: int = 100,
):
    """Windowed sequential conformal (SPCI-style).

    Keeps the most recent ``window`` conformity scores — warm-started from CAL —
    and reads the interval half-width off that window's empirical quantile, so the
    score distribution itself tracks drift (unlike ACI, which reweights a frozen
    CAL distribution). Simplification vs. full SPCI: empirical window quantiles in
    place of a quantile regression on the residual series.
    """
    mlo, mhi = _fit_cqr(X_train, y_train, alpha)
    recent = deque(
        _cqr_scores(mlo.predict(X_cal), mhi.predict(X_cal), y_cal).tolist(),
        maxlen=window,
    )
    qlo_test, qhi_test = mlo.predict(X_test), mhi.predict(X_test)

    lo = np.empty(len(y_test))
    hi = np.empty(len(y_test))
    for t in range(len(y_test)):
        qhat = _finite_sample_quantile(np.asarray(recent), alpha)
        lo[t] = qlo_test[t] - qhat
        hi[t] = qhi_test[t] + qhat
        recent.append(float(_cqr_scores(qlo_test[t : t + 1], qhi_test[t : t + 1], y_test[t : t + 1])[0]))
    return _clip_nonneg(lo), hi, {"window": window}


def mondrian_cqr(
    X_train, y_train, X_cal, y_cal, k_cal, X_test, k_test,
    alpha=DEFAULT_ALPHA,
    bucket_edges: tuple[int, ...] = (2, 3),
    min_bucket: int = 10,
):
    """Group-conditional (Mondrian) CQR bucketed by turn depth k.

    One qhat per depth bucket (k=1 / k=2 / k>=3 by default) instead of a global one —
    the fix for early-turn under-coverage: validity holds per bucket, not just
    marginally. Buckets with fewer than ``min_bucket`` CAL scores fall back to the
    global qhat.
    """
    mlo, mhi = _fit_cqr(X_train, y_train, alpha)
    cal_scores = _cqr_scores(mlo.predict(X_cal), mhi.predict(X_cal), y_cal)
    k_cal = np.asarray(k_cal)
    k_test = np.asarray(k_test)
    cal_bucket = np.digitize(k_cal, bucket_edges)
    test_bucket = np.digitize(k_test, bucket_edges)

    global_qhat = _finite_sample_quantile(cal_scores, alpha)
    qhat_by_bucket = {}
    for b in np.unique(cal_bucket):
        scores = cal_scores[cal_bucket == b]
        qhat_by_bucket[b] = (
            _finite_sample_quantile(scores, alpha) if len(scores) >= min_bucket else global_qhat
        )

    qlo_test, qhi_test = mlo.predict(X_test), mhi.predict(X_test)
    qhats = np.array([qhat_by_bucket.get(b, global_qhat) for b in test_bucket])
    lo = qlo_test - qhats
    hi = qhi_test + qhats
    return _clip_nonneg(lo), hi, {"qhat_by_bucket": qhat_by_bucket}


def constant_quantile(y_cal, n_test: int, alpha=DEFAULT_ALPHA):
    """No-model baseline: the same empirical [alpha/2, 1-alpha/2] interval of the
    calibration y's for every test point. If the guard barely beats this, the
    features/model add nothing — reviewers will ask."""
    y_cal = np.asarray(y_cal, dtype=float)
    lo = float(np.quantile(y_cal, alpha / 2))
    hi = float(np.quantile(y_cal, 1 - alpha / 2))
    return np.full(n_test, max(lo, 0.0)), np.full(n_test, hi), {}


def dtaci(
    X_train, y_train, X_cal, y_cal, X_test, y_test,
    alpha=DEFAULT_ALPHA,
    gammas: tuple[float, ...] = (0.005, 0.01, 0.02, 0.05, 0.1, 0.2),
    eta: float = 2.0,
    sigma: float = 0.01,
):
    """DtACI (Gibbs & Candès 2022, simplified constants): expert aggregation over
    ACI copies with different gammas — no gamma tuning step at all.

    Each expert k tracks its own alpha_t^k; the working level is the weight-averaged
    alpha_t. After each label, beta_t (the largest level that would still have
    covered) scores every expert via pinball loss; weights update exponentially with
    a small uniform mixing sigma to keep experts alive.
    """
    mlo, mhi = _fit_cqr(X_train, y_train, alpha)
    cal_scores = np.sort(_cqr_scores(mlo.predict(X_cal), mhi.predict(X_cal), y_cal))
    qlo_test, qhi_test = mlo.predict(X_test), mhi.predict(X_test)
    n_cal = len(cal_scores)

    K = len(gammas)
    expert_alpha = np.full(K, alpha)
    weights = np.full(K, 1.0 / K)

    lo = np.empty(len(y_test))
    hi = np.empty(len(y_test))
    for t in range(len(y_test)):
        alpha_t = float(np.clip(np.dot(weights, expert_alpha), 0.0, 0.999))
        qhat = float("inf") if alpha_t <= 0 else _finite_sample_quantile(cal_scores, alpha_t)
        lo[t] = qlo_test[t] - qhat if np.isfinite(qhat) else 0.0
        hi[t] = qhi_test[t] + qhat

        score_t = float(_cqr_scores(qlo_test[t : t + 1], qhi_test[t : t + 1], y_test[t : t + 1])[0])
        # beta_t: largest alpha whose (finite-sample) quantile still covers score_t
        beta_t = float(np.sum(cal_scores >= score_t) + 1) / (n_cal + 1)
        # pinball loss of each expert's level against beta_t
        u = beta_t - expert_alpha
        losses = u * (alpha - (u < 0).astype(float))
        weights = weights * np.exp(-eta * losses)
        weights = (1 - sigma) * weights / weights.sum() + sigma / K
        # each expert runs its own ACI update
        expert_err = (expert_alpha > beta_t).astype(float)
        expert_alpha = expert_alpha + np.asarray(gammas) * (alpha - expert_err)

    frac_inf = float(np.mean(~np.isfinite(hi)))
    return _clip_nonneg(lo), hi, {"frac_inf": frac_inf, "final_weights": weights}


def tune_gamma(
    X_train, y_train, X_cal, y_cal, cal_groups,
    alpha=DEFAULT_ALPHA,
    gammas: tuple[float, ...] = (0.005, 0.01, 0.02, 0.05),
    seed: int = 0,
) -> float:
    """Pick gamma on CAL only: split CAL's rollouts in half, calibrate on one half,
    stream ACI over the other, keep the gamma whose coverage lands closest to 1-alpha."""
    rng = np.random.default_rng(seed)
    rollouts = rng.permutation(np.unique(cal_groups))
    half = set(rollouts[: len(rollouts) // 2])
    in_a = np.isin(cal_groups, list(half))
    Xa, ya = X_cal[in_a], y_cal[in_a]
    Xb, yb = X_cal[~in_a], y_cal[~in_a]

    best_gamma, best_dist = gammas[0], float("inf")
    for gamma in gammas:
        lo, hi, _ = aci_cqr(X_train, y_train, Xa, ya, Xb, yb, alpha=alpha, gamma=gamma)
        coverage = float(np.mean((lo <= yb) & (yb <= hi)))
        dist = abs(coverage - (1 - alpha))
        if dist < best_dist:
            best_gamma, best_dist = gamma, dist
    return best_gamma
