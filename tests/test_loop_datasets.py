import pandas as pd

from budget_guard.loop_datasets import (
    text_file_traces,
    token_traces_from_dataframe,
    warehouse_traces_from_dataframe,
)
from budget_guard.multiresource import RESOURCES


def test_token_prefix_table_reconstructs_complete_trace():
    df = pd.DataFrame(
        {
            "rollout_index": [0, 0],
            "k": [1, 2],
            "per_turn_total": [[100], [100, 200]],
            "y": [500, 300],
            "total_rollout_tokens": [600, 600],
            "can_finish": [True, True],
        }
    )
    trace = token_traces_from_dataframe(df, budget=800)[0]
    assert [step.usage["tokens"] for step in trace.steps] == [100, 200, 300]
    assert trace.totals == {"tokens": 600}
    assert trace.successful


def _warehouse_df(censored=False):
    rows = []
    for turn, spent_time, spent_warehouse, spent_cost, cash in [
        (1, 2, 100, 1000, 10_000),
        (2, 4, 300, 2500, 12_000),
    ]:
        row = {
            "rollout_index": 7,
            "completed_turns": turn,
            "current_cash_usd": cash,
            "target_cash_usd": 20_000,
            "censored": censored,
            "can_finish": not censored,
        }
        budgets = {"time_weeks": 10, "warehouse_item_weeks": 2000, "cost_usd": 10_000}
        totals = {"time_weeks": 6, "warehouse_item_weeks": 500, "cost_usd": 4000}
        spent = {
            "time_weeks": spent_time,
            "warehouse_item_weeks": spent_warehouse,
            "cost_usd": spent_cost,
        }
        for resource in RESOURCES:
            row[f"budget_{resource}"] = budgets[resource]
            row[f"total_{resource}"] = totals[resource]
            row[f"spent_{resource}"] = spent[resource]
        rows.append(row)
    return pd.DataFrame(rows)


def test_warehouse_table_uses_same_generic_trace_contract():
    trace = warehouse_traces_from_dataframe(_warehouse_df())[0]
    assert len(trace.steps) == 3
    assert trace.successful
    assert trace.totals == {
        "time_weeks": 6,
        "warehouse_item_weeks": 500,
        "cost_usd": 4000,
    }
    for resource, total in trace.totals.items():
        assert sum(step.usage[resource] for step in trace.steps) == total
    assert trace.steps[1].progress["cash_gap_usd"] == -8000


def test_censored_warehouse_trace_is_a_failed_natural_outcome():
    trace = warehouse_traces_from_dataframe(_warehouse_df(censored=True))[0]
    assert trace.naturally_finished
    assert not trace.successful
    assert trace.totals is not None


def test_text_file_converter_is_an_independent_generic_smoke_path(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text("\n\n".join(["word " * 20] * 5), encoding="utf-8")
    traces = text_file_traces([path], budget=1000)
    assert len(traces) == 1
    assert traces[0].resource_names == ("tokens",)
    assert len(traces[0].steps) == 5
    assert traces[0].successful
