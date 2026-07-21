from budget_guard.loop_evaluation import replay_traces, summarize_replay
from budget_guard.loop_guard import LoopBudgetGuard
from budget_guard.loop_policy import LoopAction, LoopDecision
from budget_guard.loop_schema import ResourceLedger, ResourceSpec, RunFinish, RunStart, StepUsage


class AlwaysAbortPolicy:
    def decide(self, inputs):
        projected_lo = {
            name: inputs.spent[name] + interval.lo for name, interval in inputs.intervals.items()
        }
        projected_hi = {
            name: inputs.spent[name] + interval.hi for name, interval in inputs.intervals.items()
        }
        return LoopDecision(
            LoopAction.ABORT,
            inputs.intervals,
            inputs.finish_probability,
            ("test_policy",),
            inputs.state,
            inputs.evidence_runs,
            projected_lo,
            projected_hi,
        )


class AbortAtTerminalPolicy(AlwaysAbortPolicy):
    def decide(self, inputs):
        decision = super().decide(inputs)
        if inputs.spent["tokens"] < 400:
            return LoopDecision(
                LoopAction.CONTINUE,
                inputs.intervals,
                inputs.finish_probability,
                ("not_terminal",),
                inputs.state,
                inputs.evidence_runs,
                decision.projected_total_lo,
                decision.projected_total_hi,
            )
        return decision


def _traces(n, prefix):
    traces = []
    for i in range(n):
        success = i % 4 != 0
        spec = (ResourceSpec("tokens", "tokens", 1000),)
        ledger = ResourceLedger(RunStart(f"{prefix}-{i}", spec))
        multiplier = 2 if not success else 1
        for step in range(4):
            ledger.record(StepUsage(str(step), {"tokens": 100 * multiplier}))
        traces.append(ledger.finish(RunFinish(success)))
    return traces


def test_oracle_and_closed_loop_have_different_label_feedback():
    history = _traces(40, "history")
    targets = _traces(8, "target")
    oracle = LoopBudgetGuard.from_traces(
        history, window_rollouts=100, policy=AlwaysAbortPolicy()
    )
    closed = LoopBudgetGuard.from_traces(
        history, window_rollouts=100, policy=AlwaysAbortPolicy()
    )
    before = oracle.evidence_runs
    oracle_records = replay_traces(oracle, targets, obey_stop_recommendations=False)
    closed_records = replay_traces(closed, targets, obey_stop_recommendations=True)

    assert oracle.evidence_runs > before
    assert closed.evidence_runs == before
    assert not oracle_records["stopped"].any()
    assert closed_records["stopped"].any()
    summary = summarize_replay(oracle_records)
    assert "joint_prefix_coverage" in summary
    assert summary["false_stop_rate"] == 1.0
    # Mandated rollout-cluster bootstrap CI must accompany the point coverage.
    assert "joint_prefix_coverage_ci_lo" in summary
    assert "joint_prefix_coverage_ci_hi" in summary
    assert summary["joint_prefix_coverage_ci_lo"] <= summary["joint_prefix_coverage_ci_hi"]
    assert "operative_level" in summary


def test_terminal_step_stop_cannot_censor_an_already_finished_run():
    history = _traces(40, "history")
    target = [_traces(2, "target")[1]]  # successful, four 100-token steps
    guard = LoopBudgetGuard.from_traces(
        history, window_rollouts=100, policy=AbortAtTerminalPolicy()
    )
    before = guard.evidence_runs
    records = replay_traces(guard, target, obey_stop_recommendations=True)
    assert not records["stopped"].any()
    assert guard.evidence_runs == before + 1
