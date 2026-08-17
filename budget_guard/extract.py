"""budget_guard/extract.py — standalone offline extractor for BAGEN token-budget rollouts.

Faithful port of the prefix -> (x_t, y_t) logic in
``ragen/env/token_estimation/env.py`` (``_flatten_rollouts``). NO ``ragen``/``verl`` import,
so it runs on plain CPU Python (Windows / Mac / Colab). Validated once against the official
harness on Colab — 0 mismatches (Week 1); the diff catches
any token-bookkeeping edge cases.
"""
from __future__ import annotations

import json
import os
import re
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


def _first_int(turn: dict, *keys: str) -> Optional[int]:
    """First key whose value parses to an int — falling through ONLY on None.

    An ``or``-chain here would treat a legitimate 0 token count as missing and
    read the secondary key instead (e.g. api_input_tokens=0 for a fully-cached
    request falling through to a nonzero input_tokens), diverging from the BAGEN
    reference's explicit is-None checks and silently inflating turn totals.
    """
    for key in keys:
        value = _safe_int(turn.get(key))
        if value is not None:
            return value
    return None


def resolve_turn_total(turn: dict) -> Optional[int]:
    """Total tokens for one turn. Mirrors env.py ``_resolve_turn_total_tokens`` order."""
    value = _first_int(turn, "api_total_tokens", "total_tokens")
    if value is not None:
        return value
    inp = _first_int(turn, "api_input_tokens", "input_tokens")
    out = _first_int(turn, "api_output_tokens", "output_tokens")
    if inp is not None or out is not None:
        return int(inp or 0) + int(out or 0)
    return _safe_int(turn.get("actual_token"))


def _resolve_turn_input_tokens(turn: dict) -> Optional[int]:
    return _first_int(turn, "api_input_tokens", "input_tokens")


def _resolve_turn_output_tokens(turn: dict) -> Optional[int]:
    return _first_int(turn, "api_output_tokens", "output_tokens", "actual_token")


def _rough_text_token_count(text: str) -> int:
    if not text:
        return 0
    return len(re.findall(r"\w+|[^\w\s]", text, re.UNICODE))


def _resolve_turn_reasoning_tokens(turn: dict) -> Optional[int]:
    interactions = turn.get("api_interactions")
    if not isinstance(interactions, list):
        return None
    reasoning_total, found = 0, False
    for interaction in interactions:
        if not isinstance(interaction, dict):
            continue
        usage = interaction.get("usage")
        raw_usage = usage.get("raw") if isinstance(usage, dict) else None
        if not isinstance(raw_usage, dict):
            continue
        for parent_key in ("output_tokens_details", "completion_tokens_details"):
            parent = raw_usage.get(parent_key)
            if isinstance(parent, dict):
                value = _safe_int(parent.get("reasoning_tokens"))
                if value is not None:
                    reasoning_total += max(0, int(value))
                    found = True
                    break
    return reasoning_total if found else None


def _estimate_turn_visible_output_tokens(turn: dict) -> Optional[int]:
    """Output tokens that land in the visible transcript (reasoning excluded)."""
    output_tokens = _resolve_turn_output_tokens(turn)
    if output_tokens is None:
        return None
    output_tokens_int = max(0, int(output_tokens))
    reasoning_tokens = _resolve_turn_reasoning_tokens(turn)
    if reasoning_tokens is not None:
        return max(0, output_tokens_int - int(reasoning_tokens))
    raw_response = str(turn.get("raw_response") or turn.get("raw_generation") or "").strip()
    parsed_response = str(turn.get("parsed_response") or "").strip()
    if not raw_response or not parsed_response or raw_response == parsed_response:
        return output_tokens_int
    raw_estimate = _rough_text_token_count(raw_response)
    parsed_estimate = _rough_text_token_count(parsed_response)
    if raw_estimate <= 0 or parsed_estimate <= 0:
        return output_tokens_int
    visible_ratio = min(1.0, float(parsed_estimate) / float(raw_estimate))
    return max(0, int(round(float(output_tokens_int) * visible_ratio)))


def _turn_usage_detail(turn: dict) -> dict:
    """Per-request usage {input, output, total}. Mirrors ``_resolve_turn_token_usage_detail``."""
    input_tokens = _resolve_turn_input_tokens(turn)
    output_tokens = _resolve_turn_output_tokens(turn)
    total_tokens = resolve_turn_total(turn)
    if total_tokens is not None:
        if input_tokens is None and output_tokens is not None and int(output_tokens) <= int(total_tokens):
            input_tokens = int(total_tokens) - int(output_tokens)
        if output_tokens is None and input_tokens is not None and int(input_tokens) <= int(total_tokens):
            output_tokens = int(total_tokens) - int(input_tokens)
    if total_tokens is None and (input_tokens is not None or output_tokens is not None):
        total_tokens = int(input_tokens or 0) + int(output_tokens or 0)
    return {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens}


def _request_usage_input_includes_history(
    request_details: list[dict], visible_output_tokens: list[Optional[int]]
) -> bool:
    """Majority vote: does each request's input re-count the prior transcript?"""
    comparable, history_votes = 0, 0
    prev_request_input: Optional[int] = None
    for idx, detail in enumerate(request_details):
        current_input = detail.get("input_tokens")
        if prev_request_input is not None and current_input is not None:
            comparable += 1
            baseline = int(prev_request_input)
            prev_visible = visible_output_tokens[idx - 1]
            if prev_visible is not None:
                baseline += int(prev_visible)
            if int(current_input) >= baseline:
                history_votes += 1
        if current_input is not None:
            prev_request_input = int(current_input)
    if comparable == 0:
        return False
    return history_votes * 2 >= comparable


def convert_request_usage_to_turn_usage(
    request_details: list[dict], visible_output_tokens: list[Optional[int]]
) -> list[dict]:
    """History-excluded per-turn usage. Faithful port of
    ``_convert_request_usage_to_turn_usage`` (BAGEN default ``turn_usage_mode``)."""
    visible = list(visible_output_tokens)
    visible.extend([None] * (len(request_details) - len(visible)))
    input_includes_history = _request_usage_input_includes_history(request_details, visible)

    out: list[dict] = []
    prev_request_input: Optional[int] = None
    for idx, detail in enumerate(request_details):
        request_input = detail.get("input_tokens")
        output_tokens = detail.get("output_tokens")
        request_total = detail.get("total_tokens")
        if input_includes_history and request_input is not None and prev_request_input is not None:
            baseline = int(prev_request_input)
            prev_visible = visible[idx - 1]
            if prev_visible is not None:
                baseline += int(prev_visible)
            input_tokens = max(0, int(request_input) - baseline)
        else:
            input_tokens = request_input
        if input_tokens is not None and output_tokens is not None:
            total_tokens = int(input_tokens) + int(output_tokens)
        elif not input_includes_history:
            total_tokens = request_total
        elif input_tokens is not None:
            total_tokens = int(input_tokens)
        else:
            total_tokens = None
        out.append({"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": total_tokens})
        if request_input is not None:
            prev_request_input = int(request_input)
    return out


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
    if isinstance(actions, list):
        return len(actions) == 0
    if actions in (None, ""):
        # Mirror the reference (env.py _turn_has_no_executed_actions): a missing
        # actions field falls back to action_names; only an explicitly EMPTY list
        # means "no executed actions". Returning True here unconditionally would
        # declare implicit truncation and drop the rest of the rollout — silently
        # rewriting y for every earlier prefix.
        action_names = turn.get("action_names")
        return len(action_names) == 0 if isinstance(action_names, list) else False
    return False


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
        request_details = [_turn_usage_detail(turn) for turn in kept]
        visible_output = [_estimate_turn_visible_output_tokens(turn) for turn in kept]
        turn_details = convert_request_usage_to_turn_usage(request_details, visible_output)
        if any(detail["total_tokens"] is None for detail in turn_details):
            # Mirror the reference: a turn with no usable usage voids the whole
            # rollout's labels (env.py propagates None into
            # actual_remaining_total_tokens). Substituting 0 would fabricate
            # understated tokens_so_far and y for every prefix of the rollout.
            continue
        totals = [int(detail["total_tokens"]) for detail in turn_details]
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
    """Locate the sokoban smoke sample.

    A real BAGEN checkout always wins ($BAGEN_DIR, then a sibling ../BAGEN). The vendored
    copy under tests/fixtures/ is the last resort, so that a fresh clone with no BAGEN
    alongside it can still run the extractor invariant tests instead of skipping them.
    """
    candidates = []
    if os.environ.get("BAGEN_DIR"):
        candidates.append(
            os.path.join(os.environ["BAGEN_DIR"], "_smoke", "sokoban_dialogues.json")
        )
    here = os.path.dirname(__file__)
    candidates.append(
        os.path.join(here, "..", "..", "BAGEN", "_smoke", "sokoban_dialogues.json")
    )
    vendored = os.path.join(
        here, "..", "tests", "fixtures", "bagen_smoke_sokoban_dialogues.json"
    )
    candidates.append(vendored)

    for path in candidates:
        if os.path.exists(path):
            return path
    # Nothing found: return the first candidate so the caller's error names the location
    # the user most likely intended.
    return candidates[0]


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
