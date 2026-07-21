import numpy as np
import pandas as pd
import pytest
import json

from budget_guard.loop_features import build_loop_dataset
from budget_guard.loop_guard import LoopBudgetGuard, _ordered_predictions
from budget_guard.loop_policy import LoopAction
from budget_guard.loop_schema import (
    ResourceLedger,
    ResourceSpec,
    RunFinish,
    RunStart,
    StepUsage,
)


TEMPLATES = (
    ("tokens", "tokens"),
    ("usd", "USD"),
    ("seconds", "s"),
)


def _specs(token_budget=1400, usd_budget=8, seconds_budget=300):
    return (
        ResourceSpec("tokens", "tokens", token_budget),
        ResourceSpec("usd", "USD", usd_budget),
        ResourceSpec("seconds", "s", seconds_budget),
    )


def _synthetic_traces(n=80, seed=0):
    rng = np.random.default_rng(seed)
    traces = []
    for i in range(n):
        success = i % 4 != 0
        specs = _specs(
            token_budget=float(rng.integers(1100, 1600)),
            usd_budget=float(rng.uniform(6, 10)),
            seconds_budget=float(rng.integers(240, 360)),
        )
        ledger = ResourceLedger(
            RunStart(f"run-{i}", specs, {"difficulty": float(i % 3)})
        )
        n_steps = 5
        for step in range(n_steps):
            multiplier = 1.7 if not success else 1.0
            ledger.record(
                StepUsage(
                    str(step + 1),
                    {
                        "tokens": float(rng.normal(170 * multiplier, 12)),
                        "usd": float(rng.normal(0.8 * multiplier, 0.05)),
                        "seconds": float(rng.normal(32 * multiplier, 2)),
                    },
                    {"progress": float((step + 1) * (2 if success else 0.4))},
                )
            )
        traces.append(ledger.finish(RunFinish(success)))
    return traces


def _guard(seed=0):
    return LoopBudgetGuard.from_traces(
        _synthetic_traces(),
        seed=seed,
        context_keys=("difficulty",),
        progress_keys=("progress",),
        window_rollouts=20,
        min_evidence_runs=5,
    )


def test_stateful_guard_predicts_all_resources_and_updates_after_finish_only():
    guard = _guard()
    before = guard.evidence_runs
    gate_before = guard.gate_evidence_runs
    specs = _specs()
    guard.start("live", specs, {"difficulty": 1})
    for i in range(4):
        decision = guard.after_step(
            {"tokens": 150, "usd": 0.7, "seconds": 30},
            {"progress": (i + 1) * 2},
        )
        assert set(decision.intervals) == {"tokens", "usd", "seconds"}
        assert guard.evidence_runs == before
        assert decision.finish_probability is not None
    guard.after_step(
        {"tokens": 150, "usd": 0.7, "seconds": 30}, {"progress": 10}
    )
    guard.finish(True)
    assert guard.evidence_runs == min(before + 1, guard.window_rollouts)
    assert guard.gate_evidence_runs == min(gate_before + 1, guard.window_rollouts)


def test_aborted_run_never_fabricates_completion_scores():
    guard = _guard()
    before = guard.evidence_runs
    gate_before = guard.gate_evidence_runs
    guard.start("aborted", _specs(), {"difficulty": 2})
    guard.after_step({"tokens": 500, "usd": 2, "seconds": 80}, {"progress": 0})
    trace = guard.abort("operator stopped")
    assert trace.totals is None
    assert guard.evidence_runs == before
    assert guard.gate_evidence_runs == gate_before


def test_live_features_match_offline_features_exactly():
    traces = _synthetic_traces()
    guard = LoopBudgetGuard.from_traces(
        traces,
        context_keys=("difficulty",),
        progress_keys=("progress",),
    )
    trace = traces[1]
    guard.start(trace.start.run_id, trace.start.resources, trace.start.context)
    guard.after_step(trace.steps[0])
    live = guard._live_features(guard._require_active())
    offline = build_loop_dataset(
        [trace], context_keys=("difficulty",), progress_keys=("progress",)
    ).X.iloc[[0]].reindex(columns=live.columns)
    pd.testing.assert_frame_equal(live.reset_index(drop=True), offline.reset_index(drop=True))
    guard.abort("test cleanup")


def test_guard_rejects_schema_changes_and_parallel_runs():
    guard = _guard()
    guard.start("live", _specs())
    with pytest.raises(RuntimeError, match="active run"):
        guard.start("other", _specs())
    guard.abort("cleanup")
    with pytest.raises(ValueError, match="trained schema"):
        guard.start("wrong", (ResourceSpec("tokens", "tokens", 1000),))


def test_guard_artifact_round_trip(tmp_path):
    guard = _guard()
    artifact = tmp_path / "guard.pkl"
    guard.save(artifact)
    manifest = json.loads((tmp_path / "guard.pkl.json").read_text(encoding="utf-8"))
    assert manifest["resources"][0]["name"] == "tokens"
    assert manifest["calibration_scheme"] == "joint"
    assert len(manifest["sha256"]) == 64
    restored = LoopBudgetGuard.load(artifact)
    assert restored.resource_names == guard.resource_names
    assert restored.evidence_runs == guard.evidence_runs
    restored.start("live", _specs(), {"difficulty": 1})
    decision = restored.after_step(
        {"tokens": 150, "usd": 0.7, "seconds": 30}, {"progress": 2}
    )
    assert decision.action in set(LoopAction)
    restored.abort("cleanup")


def test_guard_artifact_detects_checksum_mismatch(tmp_path):
    guard = _guard()
    artifact = tmp_path / "guard.pkl"
    guard.save(artifact)
    artifact.write_bytes(artifact.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        LoopBudgetGuard.load(artifact)


def test_crossed_quantile_predictions_are_ordered():
    class ConstantModel:
        def __init__(self, value):
            self.value = value

        def predict(self, X):
            return np.full(len(X), self.value)

    lo, hi = _ordered_predictions(
        ConstantModel(10), ConstantModel(3), pd.DataFrame({"x": [1, 2]})
    )
    assert lo.tolist() == [3, 3]
    assert hi.tolist() == [10, 10]


def test_independent_adaptive_baseline_and_scheme_validation():
    guard = LoopBudgetGuard.from_traces(
        _synthetic_traces(), calibration_scheme="independent"
    )
    assert guard.calibration_scheme == "independent"
    assert len(guard._current_qhats()) == 3
    with pytest.raises(ValueError, match="calibration_scheme"):
        LoopBudgetGuard.from_traces(_synthetic_traces(), calibration_scheme="unknown")


def test_small_window_joint_qhat_degenerates_to_sample_max_and_is_reported():
    """Honesty check: at window=10 the joint level is ~1.0 (worst-of-window), not 0.90.

    The guard must not silently present a sample-max bound as a 1-alpha interval; the
    operative level is exposed so callers/evaluation can see the conservative regime.
    """
    guard = _guard()  # default window_rollouts=10
    guard.start("live", _specs(), {"difficulty": 1})
    guard.after_step({"tokens": 150, "usd": 0.7, "seconds": 30}, {"progress": 2})
    assert guard.last_operative_level is not None
    assert guard.last_operative_level >= 0.999  # rounds up to the componentwise max
    guard.abort("cleanup")



def test_live_delayed_usage_correction_recomputes_without_new_step():
    guard = _guard()
    guard.start("live", _specs(), {"difficulty": 1})
    first = guard.after_step(
        {"tokens": 100, "usd": 0.0, "seconds": 20}, {"progress": 1}, step_id="one"
    )
    gate_count = len(guard._current_gate_probabilities)
    corrected = guard.correct_usage("one", {"usd": 0.8})
    assert guard._require_active().spent["usd"] == 0.8
    assert len(guard._require_active().steps) == 1
    assert len(guard._current_gate_probabilities) == gate_count
    assert corrected.projected_total_lo["usd"] >= 0.8
    assert corrected.projected_total_lo["usd"] != first.projected_total_lo["usd"]
    guard.abort("cleanup")
