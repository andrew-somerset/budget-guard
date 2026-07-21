from budget_guard.loop_policy import (
    DefaultInterventionPolicy,
    GuardState,
    LoopAction,
    PolicyInput,
    ResourceInterval,
)
from budget_guard.loop_schema import ResourceSpec


RESOURCES = (
    ResourceSpec("tokens", "tokens", 1000),
    ResourceSpec("usd", "USD", 5),
)


def _input(*, spent=None, intervals=None, probability=0.9, threshold=0.2, state=GuardState.ACTIVE):
    return PolicyInput(
        resources=RESOURCES,
        spent=spent or {"tokens": 100, "usd": 0.5},
        intervals=intervals or {
            "tokens": ResourceInterval(200, 400),
            "usd": ResourceInterval(0.5, 1.0),
        },
        finish_probability=probability,
        gate_threshold=threshold,
        state=state,
        evidence_runs=20,
    )


def test_policy_continues_when_budgets_are_safe():
    decision = DefaultInterventionPolicy().decide(_input())
    assert decision.action == LoopAction.CONTINUE
    assert decision.projected_total_hi == {"tokens": 500.0, "usd": 1.5}
    assert not decision.should_stop


def test_policy_replans_on_upper_risk_but_aborts_on_optimistic_failure():
    policy = DefaultInterventionPolicy()
    risky = policy.decide(
        _input(intervals={"tokens": ResourceInterval(400, 950), "usd": ResourceInterval(1, 2)})
    )
    assert risky.action == LoopAction.REPLAN
    doomed = policy.decide(
        _input(spent={"tokens": 800, "usd": 1}, intervals={
            "tokens": ResourceInterval(250, 300), "usd": ResourceInterval(1, 2)
        })
    )
    assert doomed.action == LoopAction.ABORT
    assert doomed.should_stop


def test_policy_uses_gate_and_fails_safe():
    policy = DefaultInterventionPolicy()
    gated = policy.decide(_input(probability=0.1, threshold=0.2))
    assert gated.action == LoopAction.ASK_HUMAN
    assert not gated.should_stop
    fail_safe = policy.decide(
        _input(
            intervals={
                "tokens": ResourceInterval(0, float("inf")),
                "usd": ResourceInterval(0, float("inf")),
            },
            probability=None,
            threshold=None,
            state=GuardState.FAIL_SAFE,
        )
    )
    assert fail_safe.action == LoopAction.PAUSE
    assert "insufficient_evidence_for_finite_interval" in fail_safe.reasons
