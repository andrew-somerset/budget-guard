"""Tests for rollout-safe adaptive joint multi-resource calibration."""

import numpy as np

from budget_guard.multiresource import _joint_rank_qhats, adaptive_joint_qhats


def test_joint_rank_adapts_to_resource_dependence():
    """Opposing resource errors require a higher shared rank than either margin alone."""
    first = np.arange(100, dtype=float)
    scores = np.column_stack([first, first[::-1], np.zeros(100)])

    qhats, shared_level = _joint_rank_qhats(scores, alpha=0.1)
    joint_coverage = float(np.all(scores <= qhats, axis=1).mean())

    assert shared_level > 0.90
    assert joint_coverage >= 0.90


def test_joint_rank_fails_safe_with_too_few_scores():
    qhats, shared_level = _joint_rank_qhats(np.zeros((5, 3)), alpha=0.1)
    assert np.isinf(qhats).all()
    assert shared_level == 1.0


def test_online_update_happens_only_after_a_rollout_finishes():
    """No prefix may use another prefix's future total from the same live rollout."""
    cal_scores = np.zeros((20, 3))
    stream_scores = np.full((10, 3), 10.0)
    groups = np.repeat(["run-a", "run-b"], 5)

    qhat_path, _ = adaptive_joint_qhats(
        cal_scores, stream_scores, groups, alpha=0.1, window=20
    )

    # Every prefix of run-a uses the untouched source-calibration window.
    assert np.all(qhat_path[:5] == qhat_path[0])
    assert np.all(qhat_path[:5] == 0.0)
    # Only after run-a completes can its larger errors widen run-b's intervals.
    assert np.all(qhat_path[5:] == qhat_path[5])
    assert np.all(qhat_path[5:] == 10.0)


def test_adaptive_joint_window_recovers_after_shift():
    """A shifted stream defeats frozen qhats but is learned after one completed run."""
    cal_scores = np.zeros((20, 3))
    stream_scores = np.full((50, 3), 10.0)
    groups = np.repeat(np.arange(5), 10)

    frozen_qhats, _ = _joint_rank_qhats(cal_scores, alpha=0.1)
    frozen_covered = np.all(stream_scores <= frozen_qhats, axis=1)

    adaptive_qhats, _ = adaptive_joint_qhats(
        cal_scores, stream_scores, groups, alpha=0.1, window=20
    )
    adaptive_covered = np.all(stream_scores <= adaptive_qhats, axis=1)

    assert float(frozen_covered.mean()) == 0.0
    assert not adaptive_covered[:10].any()  # cold-start run, before any target label
    assert adaptive_covered[10:].all()      # all later runs recover after the update
    assert float(adaptive_covered.mean()) == 0.8