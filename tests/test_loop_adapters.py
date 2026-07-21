import pytest

from budget_guard.loop_adapters import (
    LangChainUsageAdapter,
    MappingUsageAdapter,
    OpenAIUsageAdapter,
    TokenPricing,
)


def test_openai_adapter_maps_tokens_cost_time_and_tools():
    response = {"usage": {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}}
    adapter = OpenAIUsageAdapter(
        TokenPricing(input_usd_per_million=2, output_usd_per_million=6),
        include_seconds=True,
        include_tool_calls=True,
    )
    step = adapter.adapt(
        response,
        step_id="1",
        elapsed_seconds=4.2,
        tool_calls=3,
        progress={"subtasks_done": 1},
    )
    assert step.usage["tokens"] == 1500
    assert step.usage["usd"] == pytest.approx(0.005)
    assert step.usage["seconds"] == 4.2
    assert step.usage["tool_calls"] == 3


def test_langchain_adapter_needs_no_langchain_dependency():
    message = {
        "usage_metadata": {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30}
    }
    step = LangChainUsageAdapter().adapt(message, step_id="x")
    assert step.usage == {"tokens": 30.0}
    assert step.metadata["adapter"] == "langchain"


def test_langchain_adapter_falls_back_to_response_metadata():
    message = {"response_metadata": {"token_usage": {"prompt_tokens": 3, "completion_tokens": 2}}}
    step = LangChainUsageAdapter().adapt(message, step_id="x")
    assert step.usage["tokens"] == 5


def test_mapping_adapter_is_framework_neutral_and_fails_on_missing_fields():
    adapter = MappingUsageAdapter({"api_calls": "calls", "seconds": "latency_s"})
    step = adapter.adapt(
        {"calls": 2, "latency_s": 1.5, "node": "search"},
        step_id="1",
        metadata_fields=("node",),
    )
    assert step.usage == {"api_calls": 2.0, "seconds": 1.5}
    assert step.metadata == {"node": "search"}
    with pytest.raises(ValueError, match="latency_s"):
        adapter.adapt({"calls": 2}, step_id="2")
