"""budget_guard/data.py — registry of env runs (raw dialogues + official records).

All three runs use the same agent model (claude-opus-4.7) so cross-env differences
are env effects, not model effects. ``max_ctx`` mirrors each run's official
``max_context_window_tokens``; ``official`` points at the estimation record whose
summary carries the agent-self-report baseline coverage.
"""
from __future__ import annotations

import json
import os

from .extract import flatten_to_samples, load_rollouts, samples_to_dataframe

_DATA = os.path.join(os.path.dirname(__file__), "..", "data", "bagen_hf")

ENVS = {
    "sokoban": {
        "raw": f"{_DATA}/origin/sokoban-origin-claude-opus-4.7-low-thinking-128-main/sokoban_api_eval_estimation_eval_estimation_dialogues.json",
        "official": f"{_DATA}/estimation/sokoban-origin-claude-opus-4.7-low-thinking-128-main_origin-claude-opus-4.7-low-thinking-token-estimation-main/sokoban-origin-claude-opus-4.7-low-thinking-128-main_origin-claude-opus-4.7-low-thinking-token-estimation-main.json",
        "max_ctx": 2500,
    },
    "searchr1": {
        "raw": f"{_DATA}/origin/searchr1-origin-Claude-Opus-4.7-low-thinking-128-main/search_r1_api_eval_estimation_eval_estimation_dialogues.json",
        "official": f"{_DATA}/estimation/searchr1-origin-Claude-Opus-4.7-low-thinking-128-main_Claude-Opus-4.7-low-thinking-128-token-estimation-main/searchr1-origin-Claude-Opus-4.7-low-thinking-128-main_Claude-Opus-4.7-low-thinking-128-token-estimation-main.json",
        "max_ctx": 3500,
    },
    "swebench": {
        "raw": f"{_DATA}/estimation/swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main/swebench-origin-claude-opus4.7_eval_estimation_dialogues.json",
        "official": f"{_DATA}/estimation/swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main/swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main.json",
        "max_ctx": 7060,
    },
}


def load_agent_estimates(name: str):
    """Per-sample agent self-estimates from the official estimation record:
    sample_id -> (agent_lo, agent_hi). Produced at turn k from prefix-only context,
    so they are legal features. Returns None if the record is missing."""
    import pandas as pd

    spec = ENVS[name]
    if not os.path.exists(spec["official"]):
        return None
    with open(spec["official"], "r", encoding="utf-8") as handle:
        results = json.load(handle)["results"]
    rows = []
    for r in results:
        interval = (r.get("prediction") or {}).get("remaining_token_interval")
        if isinstance(interval, (list, tuple)) and len(interval) == 2 and all(
            v is not None for v in interval
        ):
            rows.append({"sample_id": r["sample_id"],
                         "agent_lo": float(interval[0]), "agent_hi": float(interval[1])})
    return pd.DataFrame(rows) if rows else None


def load_env(name: str):
    """(df, agent_baseline_coverage) for one env run."""
    spec = ENVS[name]
    df = samples_to_dataframe(
        flatten_to_samples(load_rollouts(spec["raw"]), max_ctx=spec["max_ctx"])
    )
    baseline = None
    if os.path.exists(spec["official"]):
        with open(spec["official"], "r", encoding="utf-8") as handle:
            summary = json.load(handle).get("summary", {})
        baseline = summary.get("remaining_token_interval_coverage_rate")
    return df, baseline
