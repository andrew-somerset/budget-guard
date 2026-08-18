"""budget_guard/model_names.py — raw BAGEN run labels to the paper's model names.

Run labels are directory names from the BAGEN download and spell the same model
several ways ("claude-opus-4.7", "claude-opus4.7-claude-opus-4", "Claude-Opus-4.7").
Figures and the generated appendix table both need the paper's spelling, so the
mapping lives here rather than in either one. Standard library only: the appendix
generator loads this module directly, without importing the package.
"""
from __future__ import annotations

# Order matters: Codex before the generic GPT-5.2 rule, and 4.7 before 4.6, because
# several labels contain both a version number and a stray trailing "-4".
_RULES = (
    ("codex", "GPT-5.2-Codex"),
    ("gpt5.2", "GPT-5.2-instant"),
    ("gpt-5.2", "GPT-5.2-instant"),
    ("gemini", "Gemini 3.1 Pro"),
    ("qwen", "Qwen3-235B"),
    ("sonnet", "Claude Sonnet 4.6"),
)

ORDER = ("Claude Opus 4.7", "Claude Opus 4.6", "Claude Sonnet 4.6",
         "GPT-5.2-instant", "GPT-5.2-Codex", "Gemini 3.1 Pro", "Qwen3-235B")


def display_name(label: str) -> str:
    """The paper's name for a run label, or the label itself if unrecognized."""
    low = label.lower()
    for needle, name in _RULES:
        if needle in low:
            return name
    if "opus" in low:
        return "Claude Opus 4.7" if ("4.7" in low or "4-7" in low) else "Claude Opus 4.6"
    return label
