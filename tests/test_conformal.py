import numpy as np
import pandas as pd
import pytest

from budget_guard.conformal import (
    aci_cqr,
    cqr_split,
    spci,
    split_conformal_absres,
)
from budget_guard.features import LEAK_COLUMNS, build_xy
from budget_guard.metrics import marginal_coverage, mean_width
from budget_guard.split import group_split


def _synthetic(n=2000, seed=0):
    """Exchangeable regression data where split conformal must hit ~0.90."""
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n)})
    y = 3 * X["a"].to_numpy() - 2 * X["b"].to_numpy() + rng.normal(scale=1.0, size=n)
    y = y - y.min()  # nonneg, like remaining tokens
    idx = np.arange(n)
    return X.iloc[idx[:1000]], y[:1000], X.iloc[idx[1000:1500]], y[1000:1500], X.iloc[idx[1500:]], y[1500:]


@pytest.mark.parametrize("method", ["absres", "cqr"])
def test_split_conformal_coverage_on_exchangeable_data(method):
    Xtr, ytr, Xca, yca, Xte, yte = _synthetic()
    if method == "absres":
        lo, hi, _ = split_conformal_absres(Xtr, ytr, Xca, yca, Xte)
    else:
        lo, hi, _ = cqr_split(Xtr, ytr, Xca, yca, Xte)
    cov = marginal_coverage(yte, lo, hi)
    assert 0.85 <= cov <= 0.96, f"{method} coverage {cov}"
    assert mean_width(lo, hi) > 0


@pytest.mark.parametrize("online", [aci_cqr, spci])
def test_online_methods_recover_under_shift(online):
    """Shift the test distribution; online methods must stay near nominal anyway."""
    Xtr, ytr, Xca, yca, Xte, yte = _synthetic()
    yte_shifted = yte * 1.8 + 5.0  # deployment drift
    lo, hi, _ = online(Xtr, ytr, Xca, yca, Xte, yte_shifted)
    cov = marginal_coverage(yte_shifted, lo, hi)
    assert cov >= 0.80, f"online coverage under shift {cov}"


class _ConstModel:
    """Deterministic stand-in for a fitted quantile model."""

    def __init__(self, value: float):
        self._value = value

    def predict(self, X):
        return np.full(len(X), self._value, dtype=float)


@pytest.mark.parametrize("method", ["aci", "spci", "dtaci"])
def test_rollout_safe_revelation_freezes_within_rollout(method, monkeypatch):
    """With ``groups``, predictions inside a rollout are invariant to that rollout's
    own labels — remaining-to-completion labels do not exist until the rollout ends.
    Per-step revelation (groups=None) is NOT invariant, which is exactly the leak
    the rollout-safe schedule closes; asserting both proves the test can see it."""
    import budget_guard.conformal as conformal_mod

    monkeypatch.setattr(
        conformal_mod, "_fit_cqr", lambda X, y, alpha: (_ConstModel(40.0), _ConstModel(60.0))
    )
    fn = {
        "aci": lambda *a, **k: conformal_mod.aci_cqr(*a, gamma=0.05, **k),
        "spci": conformal_mod.spci,
        "dtaci": conformal_mod.dtaci,
    }[method]

    X_cal = pd.DataFrame({"a": np.zeros(10)})
    y_cal = np.linspace(30.0, 70.0, 10)
    n_test = 12
    X_test = pd.DataFrame({"a": np.zeros(n_test)})
    groups = np.repeat([0, 1], 6)
    y_plain = np.full(n_test, 50.0)  # every label comfortably covered
    y_leaky = y_plain.copy()
    y_leaky[1:5] = 1e6  # rollout 0's later labels explode

    lo_a, hi_a, _ = fn(X_cal, y_cal, X_cal, y_cal, X_test, y_plain, alpha=0.1, groups=groups)
    lo_b, hi_b, _ = fn(X_cal, y_cal, X_cal, y_cal, X_test, y_leaky, alpha=0.1, groups=groups)
    # rollout 0 (rows 0-5): its own labels are unobservable mid-rollout -> identical
    assert np.array_equal(lo_a[:6], lo_b[:6]) and np.array_equal(hi_a[:6], hi_b[:6])
    # rollout 1 (rows 6-11): rollout 0 finished, labels legitimately revealed -> reacts
    assert not np.array_equal(hi_a[6:], hi_b[6:])

    # positive control: per-step revelation leaks same-rollout labels into rows 2-5
    _, hi_c, _ = fn(X_cal, y_cal, X_cal, y_cal, X_test, y_plain, alpha=0.1)
    _, hi_d, _ = fn(X_cal, y_cal, X_cal, y_cal, X_test, y_leaky, alpha=0.1)
    assert not np.array_equal(hi_c[2:6], hi_d[2:6])


def test_group_split_partitions_by_rollout():
    df = pd.DataFrame({"rollout_index": np.repeat(np.arange(40), 5)})
    masks = group_split(df, seed=1)
    total = sum(m.astype(int) for m in masks.values())
    assert (total == 1).all()
    for name, mask in masks.items():
        rollouts = set(df.loc[mask, "rollout_index"])
        for other, omask in masks.items():
            if other != name:
                assert rollouts.isdisjoint(set(df.loc[omask, "rollout_index"]))


def test_features_are_leak_free_and_finite():
    df = pd.DataFrame(
        {
            "rollout_index": [0, 0, 1],
            "k": [1, 2, 1],
            "N": [3, 3, 2],
            "tokens_so_far": [100, 260, 80],
            "total_rollout_tokens": [400, 400, 200],
            "y": [300, 140, 120],
            "can_finish": [True, True, False],
            "rollout_success": [True, True, False],
            "sample_id": ["r0t1", "r0t2", "r1t1"],
            "per_turn_total": [[100], [100, 160], [80]],
        }
    )
    X, y, groups = build_xy(df)
    assert not (set(X.columns) & set(LEAK_COLUMNS))
    assert np.isfinite(X.to_numpy()).all()
    assert (y == df["y"].to_numpy()).all()
    assert (groups == df["rollout_index"].to_numpy()).all()
