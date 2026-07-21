import numpy as np

from budget_guard.loop_features import build_loop_dataset, prefix_feature_row
from budget_guard.loop_schema import (
    ResourceLedger,
    ResourceSpec,
    RunAbort,
    RunFinish,
    RunStart,
    StepUsage,
)


def _trace(run_id="ok", success=True, budget=1000):
    start = RunStart(
        run_id,
        (ResourceSpec("tokens", "tokens", budget), ResourceSpec("usd", "USD", 5)),
        {"difficulty": 2},
    )
    ledger = ResourceLedger(start)
    ledger.record(StepUsage("1", {"tokens": 100, "usd": 0.5}, {"progress": 1}))
    ledger.record(StepUsage("2", {"tokens": 200, "usd": 0.7}, {"progress": 3}))
    ledger.record(StepUsage("3", {"tokens": 150, "usd": 0.6}, {"progress": 6}))
    return ledger.finish(RunFinish(success))


def test_prefix_features_are_generic_and_prefix_only():
    trace = _trace()
    row = prefix_feature_row(
        trace.start,
        trace.steps[:2],
        context_keys=("difficulty",),
        progress_keys=("progress",),
    )
    assert row["tokens__spent"] == 300
    assert row["tokens__budget_left"] == 700
    assert row["tokens__last"] == 200
    assert row["usd__spent_fraction"] == 1.2 / 5
    assert row["context__difficulty"] == 2
    assert row["progress__progress"] == 3
    assert row["progress__progress__delta"] == 2
    assert not any("total" in key or "success" in key for key in row)


def test_dataset_defines_targets_only_for_successful_finished_runs():
    good = _trace("good", True)
    failed = _trace("failed", False)
    start = RunStart("aborted", (ResourceSpec("tokens", "tokens", 1000), ResourceSpec("usd", "USD", 5)))
    ledger = ResourceLedger(start)
    ledger.record(StepUsage("1", {"tokens": 50, "usd": 0.1}))
    ledger.record(StepUsage("2", {"tokens": 50, "usd": 0.1}))
    aborted = ledger.abort(RunAbort("operator stopped"))

    data = build_loop_dataset([good, failed, aborted])
    assert len(data.X) == 2 + 2 + 1
    assert data.resource_names == ("tokens", "usd")
    good_rows = data.groups == "good"
    failed_rows = data.groups == "failed"
    abort_rows = data.groups == "aborted"
    assert data.y.loc[good_rows, "tokens"].tolist() == [350, 150]
    assert data.y.loc[failed_rows].isna().all().all()
    assert data.y.loc[abort_rows].isna().all().all()
    assert np.all(data.feasible[good_rows] == 1)
    assert np.all(data.feasible[failed_rows] == 0)
    assert np.isnan(data.feasible[abort_rows]).all()
    assert not data.feasibility_observed[abort_rows].any()


def test_schema_mismatch_fails_loudly():
    good = _trace("good")
    other_start = RunStart("other", (ResourceSpec("seconds", "s", 10),))
    ledger = ResourceLedger(other_start)
    ledger.record(StepUsage("1", {"seconds": 1}))
    ledger.record(StepUsage("2", {"seconds": 1}))
    other = ledger.finish(RunFinish(True))
    try:
        build_loop_dataset([good, other])
    except ValueError as exc:
        assert "same ordered resource" in str(exc)
    else:
        raise AssertionError("schema mismatch should fail")
