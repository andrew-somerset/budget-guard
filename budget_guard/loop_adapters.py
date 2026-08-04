"""Thin, dependency-free adapters from common agent telemetry to ``StepUsage``.

Adapters translate framework events only. They contain no prediction or intervention
logic, keeping the loop guard provider- and framework-independent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .loop_schema import StepUsage


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _usage_container(payload: Any) -> Any:
    usage = _value(payload, "usage")
    if usage is not None:
        return usage
    usage = _value(payload, "usage_metadata")
    if usage is not None:
        return usage
    return payload


_TOKEN_KEYS = (
    "input_tokens", "prompt_tokens", "output_tokens", "completion_tokens", "total_tokens",
)


def _token_counts(payload: Any) -> tuple[float, float, float]:
    usage = _usage_container(payload)
    # Missing telemetry must be LOUD. Recording a zero-usage step keeps the
    # ledger's spend at 0 and the guard reporting full headroom while the run
    # spends freely — the exact "optimistic, unsafe" failure the ledger docstring
    # warns about, and here it previously needed no opt-in: a response with
    # usage=None (e.g. streaming without include_usage) silently adapted to
    # {'tokens': 0.0}. The other adapters already raise; now this one does too.
    if usage is None or all(_value(usage, key) is None for key in _TOKEN_KEYS):
        raise ValueError(
            "OpenAIUsageAdapter: no token usage found on the response (usage / "
            "usage_metadata is missing, None, or carries no token fields). "
            "Refusing to record zero spend. For streaming chat completions pass "
            "stream_options={'include_usage': True}; otherwise supply a payload "
            "with input/output token counts."
        )
    input_tokens = float(
        _value(usage, "input_tokens", _value(usage, "prompt_tokens", 0)) or 0
    )
    output_tokens = float(
        _value(usage, "output_tokens", _value(usage, "completion_tokens", 0)) or 0
    )
    total = _value(usage, "total_tokens")
    total_tokens = float(total) if total is not None else input_tokens + output_tokens
    return input_tokens, output_tokens, total_tokens


@dataclass(frozen=True)
class TokenPricing:
    """Caller-supplied prices; avoids embedding fast-changing provider prices."""

    input_usd_per_million: float
    output_usd_per_million: float

    def cost(self, input_tokens: float, output_tokens: float) -> float:
        return (
            input_tokens * self.input_usd_per_million
            + output_tokens * self.output_usd_per_million
        ) / 1_000_000


@dataclass(frozen=True)
class OpenAIUsageAdapter:
    """Adapt an OpenAI-SDK-style response or equivalent dictionary."""

    pricing: TokenPricing | None = None
    include_seconds: bool = False
    include_tool_calls: bool = False

    def adapt(
        self,
        response: Any,
        *,
        step_id: str,
        elapsed_seconds: float | None = None,
        tool_calls: int | None = None,
        progress: Mapping[str, float] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> StepUsage:
        input_tokens, output_tokens, total_tokens = _token_counts(response)
        usage = {"tokens": total_tokens}
        if self.pricing is not None:
            usage["usd"] = self.pricing.cost(input_tokens, output_tokens)
        if self.include_seconds:
            if elapsed_seconds is None:
                raise ValueError("elapsed_seconds is required by this adapter")
            usage["seconds"] = float(elapsed_seconds)
        if self.include_tool_calls:
            if tool_calls is None:
                raise ValueError("tool_calls is required by this adapter")
            usage["tool_calls"] = float(tool_calls)
        details = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            **dict(metadata or {}),
        }
        return StepUsage(step_id, usage, dict(progress or {}), details)


@dataclass(frozen=True)
class LangChainUsageAdapter:
    """Adapt a LangChain AIMessage's ``usage_metadata`` without importing LangChain."""

    pricing: TokenPricing | None = None
    include_seconds: bool = False
    include_tool_calls: bool = False

    def adapt(
        self,
        message: Any,
        *,
        step_id: str,
        elapsed_seconds: float | None = None,
        tool_calls: int | None = None,
        progress: Mapping[str, float] | None = None,
    ) -> StepUsage:
        usage_metadata = _value(message, "usage_metadata")
        if usage_metadata is None:
            response_metadata = _value(message, "response_metadata", {}) or {}
            usage_metadata = _value(response_metadata, "token_usage")
        if usage_metadata is None:
            raise ValueError("message has no usage_metadata or response token_usage")
        adapter = OpenAIUsageAdapter(
            pricing=self.pricing,
            include_seconds=self.include_seconds,
            include_tool_calls=self.include_tool_calls,
        )
        return adapter.adapt(
            usage_metadata,
            step_id=step_id,
            elapsed_seconds=elapsed_seconds,
            tool_calls=tool_calls,
            progress=progress,
            metadata={"adapter": "langchain"},
        )


@dataclass(frozen=True)
class MappingUsageAdapter:
    """Map arbitrary flat telemetry fields to guard resource names."""

    field_map: Mapping[str, str]
    defaults: Mapping[str, float] = field(default_factory=dict)

    def adapt(
        self,
        payload: Mapping[str, Any],
        *,
        step_id: str,
        progress: Mapping[str, float] | None = None,
        metadata_fields: Sequence[str] = (),
    ) -> StepUsage:
        usage: dict[str, float] = {}
        for resource, field_name in self.field_map.items():
            if field_name in payload:
                usage[resource] = float(payload[field_name])
            elif resource in self.defaults:
                usage[resource] = float(self.defaults[resource])
            else:
                raise ValueError(f"missing telemetry field: {field_name}")
        metadata = {name: payload[name] for name in metadata_fields if name in payload}
        return StepUsage(step_id, usage, dict(progress or {}), metadata)
