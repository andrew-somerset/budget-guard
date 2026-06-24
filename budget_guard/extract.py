"""budget_guard/extract.py — standalone offline extractor for BAGEN token-budget rollouts.

Faithful port of the prefix -> (x_t, y_t) logic in
``ragen/env/token_estimation/env.py`` (``_flatten_rollouts``). NO ``ragen``/``verl`` import,
so it runs on plain CPU Python (Windows / Mac / Colab). Validate once against the official
harness on Colab (see ``docs/bagen_week1_walkthrough.md`` §6); the diff catches any
token-bookkeeping edge cases.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Optional

DEFAULT_MAX_CTX = 2500


def load_rollouts(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [payload] if isinstance(payload, dict) else payload


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def resolve_turn_total(turn: dict) -> Optional[int]:
    """Total tokens for one turn. Mirrors env.py ``_resolve_turn_total_tokens`` order."""
    for key in ("api_total_tokens", "total_tokens"):
        value = _safe_int(turn.get(key))
        if value is not None:
            return value
    inp = _safe_int(turn.get("api_input_tokens")) or _safe_int(turn.get("input_tokens"))
    out = _safe_int(turn.get("api_output_tokens")) or _safe_int(turn.get("output_tokens"))
    if inp is not None or out is not None:
        return int(inp or 0) + int(out or 0)
    return _safe_int(turn.get("actual_token"))


def _assistant_content(turn: dict) -> str:
    for key in ("parsed_response", "raw_response", "raw_generation"):
        text = str(turn.get(key) or "").strip()
        if text:
            return text
    return ""


def _is_truncated(turn: dict, max_ctx: int) -> bool:
    if bool(turn.get("context_token_truncated")):
        return True
    info = turn.get("info")
    if isinstance(info, dict) and bool(info.get("context_token_truncated")):
        return True
    total = resolve_turn_total(turn)  # implicit truncation: over budget, not successful,
    if total is None or total <= max_ctx:  # has content, and no executed actions
        return False
    if bool(turn.get("success")) or not _assistant_content(turn):
        return False
    actions = turn.get("actions")
    return (len(actions) == 0) if isinstance(actions, list) else actions in (None, "")


@dataclass
class PrefixSample:
    rollout_index: int
    sample_id: str
    k: int  # completed_turns (prefix length)
    N: int  # total usable turns  -- LEAK, do not use as a feature
    tokens_so_far: int  # cumulative tokens through turn k  (feature)
    total_rollout_tokens: int  # LEAK, never a feature
    y: int  # remaining tokens from turn k+1 onward  (TARGET)
    can_finish: bool  # feasibility label
    rollout_success: bool  # LEAK
    per_turn_total: list[int]  # totals for turns 1..k  (feature source)


def flatten_to_samples(rollouts: list[dict], max_ctx: int = DEFAULT_MAX_CTX) -> list[PrefixSample]:
    out: list[PrefixSample] = []
    for rollout_index, rollout in enumerate(rollouts):
        turns = sorted(rollout.get("turns") or [], key=lambda t: int(t.get("turn_idx", 0) or 0))
        kept: list[dict] = []
        for turn in turns:
            if _is_truncated(turn, max_ctx):
                break
            kept.append(turn)
        kept = [turn for turn in kept if _assistant_content(turn)]
        if len(kept) < 2:
            continue
        totals = [int(resolve_turn_total(turn) or 0) for turn in kept]
        cumulative, running = [], 0
        for value in totals:
            running += value
            cumulative.append(running)
        total_rollout_tokens = cumulative[-1]
        success = bool(rollout.get("rollout_success")) or any(bool(t.get("success")) for t in kept)
        n_turns = len(kept)
        for k in range(1, n_turns):
            out.append(
                PrefixSample(
                    rollout_index=rollout_index,
                    sample_id=f"rollout-{rollout_index}-turn-{k}",
                    k=k,
                    N=n_turns,
                    tokens_so_far=cumulative[k - 1],
                    total_rollout_tokens=total_rollout_tokens,
                    y=max(0, total_rollout_tokens - cumulative[k - 1]),
                    can_finish=success and total_rollout_tokens <= max_ctx,
                    rollout_success=success,
                    per_turn_total=totals[:k],
                )
            )
    return out


def samples_to_dataframe(samples: list[PrefixSample]):
    import pandas as pd

    return pd.DataFrame([asdict(s) for s in samples])


def _default_smoke_path() -> str:
    bagen_dir = os.environ.get("BAGEN_DIR") or os.path.join(
        os.path.dirname(__file__), "..", "..", "BAGEN"
    )
    return os.path.join(bagen_dir, "_smoke", "sokoban_dialogues.json")


def _self_check(df) -> None:
    expected = (df["total_rollout_tokens"] - df["tokens_so_far"]).clip(lower=0)
    assert (df["y"] == expected).all(), "y must equal max(0, total_rollout_tokens - tokens_so_far)"
    for rollout_index, group in df.groupby("rollout_index"):
        ys = group.sort_values("k")["y"].tolist()
        assert ys == sorted(ys, reverse=True), f"y not non-increasing in rollout {rollout_index}"


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else _default_smoke_path()
    df = samples_to_dataframe(flatten_to_samples(load_rollouts(path), max_ctx=DEFAULT_MAX_CTX))
    print(df.drop(columns=["per_turn_total"]).to_string(index=False))
    _self_check(df)
    print(f"\nOK: {len(df)} prefix samples from {df['rollout_index'].nunique()} rollouts.")
