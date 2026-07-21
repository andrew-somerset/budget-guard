"""Task-neutral lifecycle and resource schema for long-horizon agent loops.

The statistical core should not know whether a run is coding, browsing, or managing a
warehouse. It only needs four observable events:

- :class:`RunStart`: run id, cumulative resource budgets, optional task context.
- :class:`StepUsage`: one step's resource deltas and optional numeric progress signals.
- :class:`UsageCorrection`: replace a recorded step's resource deltas when delayed
    provider/tool accounting arrives (never silently double-count late telemetry).
- :class:`RunFinish`: naturally finished outcome and final resource totals.
- :class:`RunAbort`: stopped run with only the lower bounds actually observed.

``ResourceLedger`` validates and accumulates those events. The same events serialize to
portable JSONL so framework adapters remain thin translation layers rather than places
where prediction logic quietly forks.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = 1
_RESOURCE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


def _finite_nonnegative(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} must be finite and non-negative")
    return number


def _numeric_mapping(values: Mapping[str, Any], label: str) -> dict[str, float]:
    return {str(key): _finite_nonnegative(value, f"{label}.{key}") for key, value in values.items()}


@dataclass(frozen=True)
class ResourceSpec:
    """One cumulative resource monitored by the loop guard.

    Version 1 intentionally supports additive resources only: tokens, dollars, elapsed
    seconds, API/tool calls, retries, energy, and item-time occupancy all add over a run.
    Peak-memory or replenishable-stock constraints need different target semantics and
    must not be silently treated as additive.
    """

    name: str
    unit: str
    budget: float
    aggregation: str = "sum"

    def __post_init__(self) -> None:
        if not _RESOURCE_NAME.match(self.name):
            raise ValueError(f"invalid resource name: {self.name!r}")
        if not self.unit.strip():
            raise ValueError("resource unit must be non-empty")
        object.__setattr__(self, "budget", _finite_nonnegative(self.budget, f"{self.name}.budget"))
        if self.budget <= 0:
            raise ValueError(f"{self.name}.budget must be positive")
        if self.aggregation != "sum":
            raise ValueError("schema v1 supports aggregation='sum' only")


@dataclass(frozen=True)
class RunStart:
    run_id: str
    resources: tuple[ResourceSpec, ...]
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.run_id).strip():
            raise ValueError("run_id must be non-empty")
        if not self.resources:
            raise ValueError("at least one resource is required")
        names = [resource.name for resource in self.resources]
        if len(names) != len(set(names)):
            raise ValueError("resource names must be unique")


@dataclass(frozen=True)
class StepUsage:
    step_id: str
    usage: Mapping[str, float]
    progress: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.step_id).strip():
            raise ValueError("step_id must be non-empty")
        object.__setattr__(self, "usage", _numeric_mapping(self.usage, "usage"))
        # Progress signals may be signed (for example profit delta), but must be numeric/finite.
        clean_progress: dict[str, float] = {}
        for key, value in self.progress.items():
            try:
                number = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"progress.{key} must be numeric") from exc
            if not math.isfinite(number):
                raise ValueError(f"progress.{key} must be finite")
            clean_progress[str(key)] = number
        object.__setattr__(self, "progress", clean_progress)


@dataclass(frozen=True)
class UsageCorrection:
    """Replace selected resource deltas for one already-recorded step."""

    step_id: str
    usage: Mapping[str, float]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.step_id).strip():
            raise ValueError("step_id must be non-empty")
        if not self.usage:
            raise ValueError("a correction must contain at least one resource")
        object.__setattr__(self, "usage", _numeric_mapping(self.usage, "usage"))


@dataclass(frozen=True)
class RunFinish:
    success: bool
    totals: Mapping[str, float] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.totals is not None:
            object.__setattr__(self, "totals", _numeric_mapping(self.totals, "totals"))


@dataclass(frozen=True)
class RunAbort:
    reason: str
    observed_lower_bounds: Mapping[str, float] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("abort reason must be non-empty")
        object.__setattr__(
            self,
            "observed_lower_bounds",
            _numeric_mapping(self.observed_lower_bounds, "observed_lower_bounds"),
        )


TerminalEvent = RunFinish | RunAbort
LoopEvent = RunStart | StepUsage | UsageCorrection | RunFinish | RunAbort


@dataclass(frozen=True)
class RunTrace:
    """A validated run history consumed by generic feature and model code."""

    start: RunStart
    steps: tuple[StepUsage, ...]
    outcome: TerminalEvent

    @property
    def resource_names(self) -> tuple[str, ...]:
        return tuple(resource.name for resource in self.start.resources)

    @property
    def naturally_finished(self) -> bool:
        return isinstance(self.outcome, RunFinish)

    @property
    def successful(self) -> bool:
        return isinstance(self.outcome, RunFinish) and self.outcome.success

    @property
    def totals(self) -> dict[str, float] | None:
        if not isinstance(self.outcome, RunFinish):
            return None
        if self.outcome.totals is not None:
            return dict(self.outcome.totals)
        totals = {name: 0.0 for name in self.resource_names}
        for step in self.steps:
            for name in self.resource_names:
                totals[name] += float(step.usage[name])
        return totals


@dataclass(frozen=True)
class LedgerSnapshot:
    run_id: str
    step_count: int
    spent: Mapping[str, float]
    budget_left: Mapping[str, float]
    latest_progress: Mapping[str, float]
    closed: bool


class ResourceLedger:
    """Validate and accumulate one live run without any task-specific assumptions.

    ``allow_partial_usage`` is a deliberate foot-gun: a resource omitted from a step is
    treated as **zero usage this step**, which *under-counts* cumulative spend and biases a
    budget guard toward *not* aborting (optimistic, unsafe). Enable it only when a missing
    resource genuinely had zero usage that step — never to paper over telemetry you simply
    have not collected yet. For late-arriving authoritative usage, record it and later
    :meth:`correct` the step instead of leaving it out.
    """

    def __init__(self, start: RunStart, *, allow_partial_usage: bool = False):
        self.start_event = start
        self.allow_partial_usage = allow_partial_usage
        self._resource_names = tuple(resource.name for resource in start.resources)
        self._budgets = {resource.name: resource.budget for resource in start.resources}
        self._steps: list[StepUsage] = []
        self._step_ids: set[str] = set()
        self._spent = {name: 0.0 for name in self._resource_names}
        self._outcome: TerminalEvent | None = None

    @property
    def closed(self) -> bool:
        return self._outcome is not None

    @property
    def steps(self) -> tuple[StepUsage, ...]:
        return tuple(self._steps)

    @property
    def spent(self) -> dict[str, float]:
        return dict(self._spent)

    def record(self, step: StepUsage) -> LedgerSnapshot:
        if self.closed:
            raise RuntimeError("cannot record usage after a run is closed")
        step_id = str(step.step_id)
        if step_id in self._step_ids:
            raise ValueError(f"duplicate step_id: {step_id}")
        unknown = set(step.usage) - set(self._resource_names)
        if unknown:
            raise ValueError(f"unknown resources in step: {sorted(unknown)}")
        missing = set(self._resource_names) - set(step.usage)
        if missing and not self.allow_partial_usage:
            raise ValueError(f"missing resources in step: {sorted(missing)}")

        normalized_usage = {
            name: float(step.usage.get(name, 0.0)) for name in self._resource_names
        }
        normalized = StepUsage(
            step_id=step_id,
            usage=normalized_usage,
            progress=step.progress,
            metadata=step.metadata,
        )
        self._steps.append(normalized)
        self._step_ids.add(step_id)
        for name, value in normalized_usage.items():
            self._spent[name] += value
        return self.snapshot()

    def correct(self, event: UsageCorrection) -> LedgerSnapshot:
        """Apply delayed authoritative usage by replacing—not adding—step values."""
        if self.closed:
            raise RuntimeError("cannot correct usage after a run is closed")
        unknown = set(event.usage) - set(self._resource_names)
        if unknown:
            raise ValueError(f"unknown resources in correction: {sorted(unknown)}")
        try:
            index = next(
                i for i, step in enumerate(self._steps) if str(step.step_id) == str(event.step_id)
            )
        except StopIteration as exc:
            raise ValueError(f"cannot correct unknown step_id: {event.step_id}") from exc
        old = self._steps[index]
        corrected_usage = dict(old.usage)
        corrected_usage.update({name: float(value) for name, value in event.usage.items()})
        for name in event.usage:
            self._spent[name] += corrected_usage[name] - float(old.usage[name])
        metadata = {**dict(old.metadata), **dict(event.metadata), "usage_corrected": True}
        self._steps[index] = StepUsage(
            old.step_id, corrected_usage, old.progress, metadata
        )
        return self.snapshot()

    def finish(self, event: RunFinish) -> RunTrace:
        if self.closed:
            raise RuntimeError("run is already closed")
        if not self._steps:
            raise ValueError("cannot finish a run with no steps")
        totals = dict(event.totals) if event.totals is not None else dict(self._spent)
        if set(totals) != set(self._resource_names):
            raise ValueError("finish totals must contain exactly the configured resources")
        for name in self._resource_names:
            if totals[name] + 1e-12 < self._spent[name]:
                raise ValueError(f"{name} total cannot be below observed spend")
        self._outcome = RunFinish(event.success, totals, event.metadata)
        return self.trace()

    def abort(self, event: RunAbort) -> RunTrace:
        if self.closed:
            raise RuntimeError("run is already closed")
        unknown = set(event.observed_lower_bounds) - set(self._resource_names)
        if unknown:
            raise ValueError(f"unknown resources in abort bounds: {sorted(unknown)}")
        self._outcome = event
        return self.trace()

    def snapshot(self) -> LedgerSnapshot:
        latest_progress = self._steps[-1].progress if self._steps else {}
        return LedgerSnapshot(
            run_id=self.start_event.run_id,
            step_count=len(self._steps),
            spent=dict(self._spent),
            budget_left={
                name: self._budgets[name] - self._spent[name] for name in self._resource_names
            },
            latest_progress=dict(latest_progress),
            closed=self.closed,
        )

    def trace(self) -> RunTrace:
        if self._outcome is None:
            raise RuntimeError("run has not finished or aborted")
        return RunTrace(self.start_event, tuple(self._steps), self._outcome)


def event_to_dict(event: LoopEvent) -> dict[str, Any]:
    """Serialize one event to a stable, framework-neutral dictionary."""
    if isinstance(event, RunStart):
        return {
            "schema_version": SCHEMA_VERSION,
            "event": "run_start",
            "run_id": event.run_id,
            "resources": [asdict(resource) for resource in event.resources],
            "context": dict(event.context),
        }
    if isinstance(event, StepUsage):
        return {
            "schema_version": SCHEMA_VERSION,
            "event": "step_usage",
            "step_id": event.step_id,
            "usage": dict(event.usage),
            "progress": dict(event.progress),
            "metadata": dict(event.metadata),
        }
    if isinstance(event, UsageCorrection):
        return {
            "schema_version": SCHEMA_VERSION,
            "event": "usage_correction",
            "step_id": event.step_id,
            "usage": dict(event.usage),
            "metadata": dict(event.metadata),
        }
    if isinstance(event, RunFinish):
        return {
            "schema_version": SCHEMA_VERSION,
            "event": "run_finish",
            "success": event.success,
            "totals": None if event.totals is None else dict(event.totals),
            "metadata": dict(event.metadata),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "event": "run_abort",
        "reason": event.reason,
        "observed_lower_bounds": dict(event.observed_lower_bounds),
        "metadata": dict(event.metadata),
    }


def event_from_dict(payload: Mapping[str, Any]) -> LoopEvent:
    version = payload.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {version}")
    kind = payload.get("event")
    if kind == "run_start":
        return RunStart(
            run_id=str(payload["run_id"]),
            resources=tuple(ResourceSpec(**item) for item in payload["resources"]),
            context=dict(payload.get("context") or {}),
        )
    if kind == "step_usage":
        return StepUsage(
            step_id=str(payload["step_id"]),
            usage=dict(payload.get("usage") or {}),
            progress=dict(payload.get("progress") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )
    if kind == "usage_correction":
        return UsageCorrection(
            step_id=str(payload["step_id"]),
            usage=dict(payload.get("usage") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )
    if kind == "run_finish":
        totals = payload.get("totals")
        return RunFinish(
            success=bool(payload["success"]),
            totals=None if totals is None else dict(totals),
            metadata=dict(payload.get("metadata") or {}),
        )
    if kind == "run_abort":
        return RunAbort(
            reason=str(payload["reason"]),
            observed_lower_bounds=dict(payload.get("observed_lower_bounds") or {}),
            metadata=dict(payload.get("metadata") or {}),
        )
    raise ValueError(f"unknown event type: {kind!r}")


def write_jsonl(path: str | Path, events: Iterable[LoopEvent]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(json.dumps(event_to_dict(event), sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> list[LoopEvent]:
    with Path(path).open(encoding="utf-8") as handle:
        return [event_from_dict(json.loads(line)) for line in handle if line.strip()]


def traces_from_events(events: Sequence[LoopEvent]) -> list[RunTrace]:
    """Reconstruct traces from an ordered event stream containing one run at a time."""
    traces: list[RunTrace] = []
    ledger: ResourceLedger | None = None
    for event in events:
        if isinstance(event, RunStart):
            if ledger is not None and not ledger.closed:
                raise ValueError("new run started before the previous run closed")
            ledger = ResourceLedger(event)
        elif ledger is None:
            raise ValueError("event stream must begin with RunStart")
        elif isinstance(event, StepUsage):
            ledger.record(event)
        elif isinstance(event, UsageCorrection):
            ledger.correct(event)
        elif isinstance(event, RunFinish):
            traces.append(ledger.finish(event))
        else:
            traces.append(ledger.abort(event))
    if ledger is not None and not ledger.closed:
        raise ValueError("event stream ended with an open run")
    return traces
