"""Task-neutral intervention policy for agent-loop resource decisions.

The estimator answers what is likely; this module decides what to recommend given
budgets and risk tolerance. Keeping those concerns separate lets two teams use the same
calibrated estimator with different operational policies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Mapping, Protocol, Sequence

from .loop_schema import ResourceSpec


class LoopAction(str, Enum):
    CONTINUE = "continue"
    REPLAN = "replan"
    REDUCE_SCOPE = "reduce_scope"
    SWITCH_MODEL = "switch_model"
    SWITCH_TOOL = "switch_tool"
    ASK_HUMAN = "ask_human"
    CHECKPOINT = "checkpoint"
    PAUSE = "pause"
    ABORT = "abort"


class GuardState(str, Enum):
    WARMING_UP = "warming_up"
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAIL_SAFE = "fail_safe"


@dataclass(frozen=True)
class ResourceInterval:
    lo: float
    hi: float

    def __post_init__(self) -> None:
        if self.lo < 0 or math.isnan(self.lo):
            raise ValueError("interval lower bound must be non-negative")
        if self.hi < self.lo or math.isnan(self.hi):
            raise ValueError("interval upper bound must be >= lower bound")


@dataclass(frozen=True)
class PolicyInput:
    resources: tuple[ResourceSpec, ...]
    spent: Mapping[str, float]
    intervals: Mapping[str, ResourceInterval]
    finish_probability: float | None
    gate_threshold: float | None
    state: GuardState
    evidence_runs: int
    progress: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class LoopDecision:
    """A recommendation, not an enforced side effect."""

    action: LoopAction
    intervals: Mapping[str, ResourceInterval]
    finish_probability: float | None
    reasons: tuple[str, ...]
    state: GuardState
    evidence_runs: int
    projected_total_lo: Mapping[str, float]
    projected_total_hi: Mapping[str, float]

    @property
    def should_stop(self) -> bool:
        return self.action in {LoopAction.PAUSE, LoopAction.ABORT}


class InterventionPolicy(Protocol):
    def decide(self, inputs: PolicyInput) -> LoopDecision: ...


@dataclass(frozen=True)
class DefaultInterventionPolicy:
    """Conservative default recommendations for cumulative-resource loops.

    Rules are deliberately simple and auditable. Teams can replace this policy without
    retraining the estimator.
    """

    risk_action: LoopAction = LoopAction.REPLAN
    high_spend_action: LoopAction = LoopAction.REDUCE_SCOPE
    # A model probability can drift across tasks/providers. Escalate by default;
    # deployments that have validated their gate can opt into automatic abort.
    infeasible_action: LoopAction = LoopAction.ASK_HUMAN
    fail_safe_action: LoopAction = LoopAction.PAUSE
    high_spend_fraction: float = 0.8

    def __post_init__(self) -> None:
        if not 0 < self.high_spend_fraction <= 1:
            raise ValueError("high_spend_fraction must be in (0, 1]")

    def decide(self, inputs: PolicyInput) -> LoopDecision:
        resource_by_name = {resource.name: resource for resource in inputs.resources}
        projected_lo = {
            name: float(inputs.spent[name]) + interval.lo
            for name, interval in inputs.intervals.items()
        }
        projected_hi = {
            name: float(inputs.spent[name]) + interval.hi
            for name, interval in inputs.intervals.items()
        }
        reasons: list[str] = []

        already_over = [
            name for name, resource in resource_by_name.items()
            if float(inputs.spent[name]) > resource.budget
        ]
        optimistic_over = [
            name for name, resource in resource_by_name.items()
            if projected_lo[name] > resource.budget
        ]
        upper_at_risk = [
            name for name, resource in resource_by_name.items()
            if projected_hi[name] > resource.budget
        ]
        high_spend = [
            name for name, resource in resource_by_name.items()
            if float(inputs.spent[name]) / resource.budget >= self.high_spend_fraction
        ]

        if already_over:
            action = LoopAction.ABORT
            reasons.append("budget_already_exceeded:" + ",".join(already_over))
        elif optimistic_over:
            action = LoopAction.ABORT
            reasons.append("optimistic_projection_exceeds_budget:" + ",".join(optimistic_over))
        elif (
            inputs.finish_probability is not None
            and inputs.gate_threshold is not None
            and inputs.finish_probability < inputs.gate_threshold
        ):
            action = self.infeasible_action
            reasons.append("finish_probability_below_gate")
        elif inputs.state == GuardState.FAIL_SAFE:
            action = self.fail_safe_action
            reasons.append("insufficient_evidence_for_finite_interval")
        elif upper_at_risk and high_spend:
            action = self.high_spend_action
            reasons.append("upper_projection_at_risk:" + ",".join(upper_at_risk))
            reasons.append("high_budget_fraction:" + ",".join(high_spend))
        elif upper_at_risk:
            action = self.risk_action
            reasons.append("upper_projection_at_risk:" + ",".join(upper_at_risk))
        else:
            action = LoopAction.CONTINUE
            reasons.append("within_projected_budgets")

        if inputs.state == GuardState.WARMING_UP:
            reasons.append("limited_completed_run_history")
        elif inputs.state == GuardState.DEGRADED:
            reasons.append("some_guard_capabilities_unavailable")

        return LoopDecision(
            action=action,
            intervals=dict(inputs.intervals),
            finish_probability=inputs.finish_probability,
            reasons=tuple(reasons),
            state=inputs.state,
            evidence_runs=inputs.evidence_runs,
            projected_total_lo=projected_lo,
            projected_total_hi=projected_hi,
        )
