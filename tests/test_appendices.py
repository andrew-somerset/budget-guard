"""Guards the generated appendices: the label mapping and the table's agreement
with allruns.csv.

The mapping is the drift-prone part. BAGEN spells the same model several ways
across environments, so an added run or a renamed directory silently produces a
model column that disagrees with the figures unless something checks.
"""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "bg_model_names", ROOT / "budget_guard" / "model_names.py")
_names = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_names)


# Every distinct run-label spelling currently present in the BAGEN download.
REAL_LABELS = {
    "claude-opus-4.7": "Claude Opus 4.7",
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "claude-opus4.7-claude-opus-4": "Claude Opus 4.7",
    "claude-opus-4-6": "Claude Opus 4.6",
    "claude-sonnet-4.6": "Claude Sonnet 4.6",
    "Claude-Sonnet-4.6": "Claude Sonnet 4.6",
    "claude-sonnet4.6-claude-sonn": "Claude Sonnet 4.6",
    "gpt5.2-instant": "GPT-5.2-instant",
    "gpt5.2instant-gpt5.2instant-": "GPT-5.2-instant",
    "openai-openai-5-2-codex": "GPT-5.2-Codex",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "openrouter-gemini-3-1-pro-pr": "Gemini 3.1 Pro",
    "gemini3.1-gemini3.1-pro-prev": "Gemini 3.1 Pro",
    "qwen-qwen3-235b": "Qwen3-235B",
    "qwen-qwen3-235b-a22b-2507": "Qwen3-235B",
    "qwen3-235b-qwen3-235b-512-ma": "Qwen3-235B",
}


@pytest.mark.parametrize("label,expected", sorted(REAL_LABELS.items()))
def test_display_name_maps_every_real_label(label, expected):
    assert _names.display_name(label) == expected


def test_codex_is_not_swallowed_by_the_generic_gpt_rule():
    """Rule order matters: the Codex label also contains '5-2'."""
    assert _names.display_name("openai-openai-5-2-codex") == "GPT-5.2-Codex"


def test_opus_version_precedence():
    """A 4.7 label also contains a trailing '-4' that must not read as 4.6."""
    assert _names.display_name("claude-opus4.7-claude-opus-4") == "Claude Opus 4.7"
    assert _names.display_name("claude-opus-4-6") == "Claude Opus 4.6"


def test_every_name_is_in_the_canonical_order():
    assert set(REAL_LABELS.values()) <= set(_names.ORDER)


def test_unknown_label_passes_through():
    """The generator flags this rather than inventing a name."""
    assert _names.display_name("some-new-model-2027") == "some-new-model-2027"


def test_generated_appendix_matches_allruns():
    """If both artifacts exist, the appendix table must agree with the source table."""
    table = ROOT / "tables" / "allruns.csv"
    appendix = ROOT / "paper" / "appendices.md"
    if not table.exists() or not appendix.exists():
        pytest.skip("run `make repro-all && make appendices` to generate both")

    with table.open() as fh:
        want = sorted((_names.display_name(r["model"]),
                       int(float(r["n_rollouts"])), int(float(r["n_samples"])))
                      for r in csv.DictReader(fh))
    got = []
    for line in appendix.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0] not in ("Environment", "---") and "---" not in cells[1]:
            if cells[0] == "Warehouse":
                continue
            got.append((cells[1], int(cells[2]), int(cells[3].replace(",", ""))))
    assert sorted(got) == want
