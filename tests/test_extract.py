import json
import os

import pytest

from budget_guard.extract import (
    _default_smoke_path,
    flatten_to_samples,
    load_rollouts,
    samples_to_dataframe,
)

REPO = os.path.join(os.path.dirname(__file__), "..")
# Resolve the smoke fixture the same way extract.py's CLI does, so BAGEN_DIR works here
# too. Previously this hardcoded <repo>/../BAGEN, so the test skipped whenever BAGEN sat
# anywhere else — including inside the reproducibility container.
SMOKE = _default_smoke_path()
SOKOBAN_RAW = os.path.join(
    REPO, "data", "bagen_hf", "origin",
    "sokoban-origin-claude-opus-4.7-low-thinking-128-main",
    "sokoban_api_eval_estimation_eval_estimation_dialogues.json",
)
SOKOBAN_OFFICIAL = os.path.join(
    REPO, "data", "bagen_hf", "estimation",
    "sokoban-origin-claude-opus-4.7-low-thinking-128-main_origin-claude-opus-4.7-low-thinking-token-estimation-main",
    "sokoban-origin-claude-opus-4.7-low-thinking-128-main_origin-claude-opus-4.7-low-thinking-token-estimation-main.json",
)


def _check_invariants(df):
    expected = (df["total_rollout_tokens"] - df["tokens_so_far"]).clip(lower=0)
    assert (df["y"] == expected).all()
    for _, group in df.groupby("rollout_index"):
        ys = group.sort_values("k")["y"].tolist()
        assert ys == sorted(ys, reverse=True)


@pytest.mark.skipif(not os.path.exists(SMOKE), reason="BAGEN _smoke sample not present")
def test_smoke_sample():
    df = samples_to_dataframe(flatten_to_samples(load_rollouts(SMOKE), max_ctx=2500))
    assert len(df) == 3
    assert df["rollout_index"].nunique() == 1
    _check_invariants(df)


@pytest.mark.skipif(
    not (os.path.exists(SOKOBAN_RAW) and os.path.exists(SOKOBAN_OFFICIAL)),
    reason="sokoban HF data not downloaded",
)
def test_fidelity_vs_official_ground_truth():
    """The Week-1 acceptance criterion: y_t identical to the official harness."""
    samples = flatten_to_samples(load_rollouts(SOKOBAN_RAW), max_ctx=2500)
    mine = {s.sample_id: s.y for s in samples}
    with open(SOKOBAN_OFFICIAL, encoding="utf-8") as handle:
        official = {
            r["sample_id"]: r["ground_truth"]["actual_remaining_total_tokens"]
            for r in json.load(handle)["results"]
        }
    assert set(mine) == set(official)
    mismatches = [sid for sid in official if mine[sid] != official[sid]]
    assert mismatches == []
