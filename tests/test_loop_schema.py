import pytest

from budget_guard.loop_schema import (
    ResourceLedger,
    ResourceSpec,
    RunAbort,
    RunFinish,
    RunStart,
    StepUsage,
    UsageCorrection,
    read_jsonl,
    traces_from_events,
    write_jsonl,
)


def _start():
    return RunStart(
        "run-1",
        (
            ResourceSpec("tokens", "tokens", 1000),
            ResourceSpec("usd", "USD", 2.0),
        ),
        {"task_type": "coding"},
    )


def test_ledger_accumulates_and_finishes():
    ledger = ResourceLedger(_start())
    snapshot = ledger.record(
        StepUsage("1", {"tokens": 100, "usd": 0.2}, {"tests_passing": 3})
    )
    assert snapshot.spent == {"tokens": 100.0, "usd": 0.2}
    assert snapshot.budget_left == {"tokens": 900.0, "usd": 1.8}
    ledger.record(StepUsage("2", {"tokens": 150, "usd": 0.3}))
    trace = ledger.finish(RunFinish(True))
    assert trace.successful
    assert trace.totals == {"tokens": 250.0, "usd": 0.5}


def test_ledger_rejects_bad_or_ambiguous_usage():
    ledger = ResourceLedger(_start())
    with pytest.raises(ValueError, match="missing resources"):
        ledger.record(StepUsage("1", {"tokens": 100}))
    with pytest.raises(ValueError, match="unknown resources"):
        ledger.record(StepUsage("1", {"tokens": 100, "usd": 0.1, "gpu": 1}))
    ledger.record(StepUsage("1", {"tokens": 100, "usd": 0.1}))
    with pytest.raises(ValueError, match="duplicate step_id"):
        ledger.record(StepUsage("1", {"tokens": 10, "usd": 0.01}))
    with pytest.raises(RuntimeError, match="not finished or aborted"):
        ledger.trace()


def test_abort_preserves_only_observed_information():
    ledger = ResourceLedger(_start())
    ledger.record(StepUsage("1", {"tokens": 100, "usd": 0.1}))
    trace = ledger.abort(RunAbort("budget risk", {"tokens": 100, "usd": 0.1}))
    assert not trace.naturally_finished
    assert trace.totals is None
    with pytest.raises(RuntimeError, match="closed"):
        ledger.record(StepUsage("2", {"tokens": 1, "usd": 0.01}))


def test_jsonl_round_trip(tmp_path):
    events = [
        _start(),
        StepUsage("1", {"tokens": 100, "usd": 0.2}, {"tests_passing": 3}),
        StepUsage("2", {"tokens": 150, "usd": 0.3}, {"tests_passing": 8}),
        RunFinish(True),
    ]
    path = tmp_path / "events.jsonl"
    write_jsonl(path, events)
    restored = read_jsonl(path)
    traces = traces_from_events(restored)
    assert len(traces) == 1
    assert traces[0].start.run_id == "run-1"
    assert traces[0].totals == {"tokens": 250.0, "usd": 0.5}


def test_schema_rejects_nonadditive_resource_for_now():
    with pytest.raises(ValueError, match="aggregation='sum'"):
        ResourceSpec("peak_memory", "GB", 16, aggregation="max")


def test_delayed_usage_correction_replaces_instead_of_double_counting(tmp_path):
    events = [
        _start(),
        StepUsage("1", {"tokens": 100, "usd": 0.0}),
        UsageCorrection("1", {"usd": 0.25}, {"source": "provider_bill"}),
        StepUsage("2", {"tokens": 50, "usd": 0.1}),
        RunFinish(True),
    ]
    path = tmp_path / "corrected.jsonl"
    write_jsonl(path, events)
    trace = traces_from_events(read_jsonl(path))[0]
    assert trace.totals == {"tokens": 150.0, "usd": 0.35}
    assert trace.steps[0].metadata["usage_corrected"] is True

    ledger = ResourceLedger(_start())
    with pytest.raises(ValueError, match="unknown step_id"):
        ledger.correct(UsageCorrection("missing", {"usd": 0.2}))
