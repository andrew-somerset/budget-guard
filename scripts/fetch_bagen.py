"""scripts/fetch_bagen.py — fetch the BAGEN files the offline harness needs.

The full ``MLL-Lab/BAGEN`` dataset is ~3.8 GB (the swebench *origin* trajectories
dominate, some single files >180 MB — thousands of tiny per-GitHub-issue trajectory
files that no ``run_*.py`` in this repo actually reads). ``FILES`` below now covers:
the single-model minimum (~105 MB) PLUS the other 6 sokoban / 6 searchr1 / 4 swebench
model runs needed to unblock ``run_allruns.py``'s all-19-runs breadth table and
``run_transfer.py``'s model-swap transfer bars (~670 MB total) — downloaded 2026-07-20.
Everything lands in ``data/bagen_hf/`` (gitignored), preserving the repo-relative
layout ``data.py`` and ``run_multiresource.py`` expect.

    python scripts/fetch_bagen.py

Extend ``FILES`` to pull more model/env records (see ``budget_guard/data.py`` and
``run_multiresource.py`` for the exact path each experiment consumes).
"""
from __future__ import annotations

import os
import shutil

from huggingface_hub import hf_hub_download

REPO_ID = "MLL-Lab/BAGEN"
# Pinned to the exact commit every number in notes/week*.md was derived from. The
# upstream dataset is a live HF repo and can change; without pinning, re-running
# this script later could silently fetch different bytes than the paper used.
# Re-verified reachable 2026-07-20 (last_modified 2026-05-28).
REVISION = "58189576e54b675fdd0e1d6c1c9f189c2992732f"
DEST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "bagen_hf"))
# Short staging root: HF writes temp files under ``<local_dir>/.cache/.../<hash>.incomplete``,
# and BAGEN's 63-char estimation dir names blow past Windows' 260-char MAX_PATH when the
# repo lives under a deep path. Staging in a short dir keeps temp paths legal; the final
# moved-into-place paths fit comfortably.
STAGE = os.path.join(os.path.expanduser("~"), "_bgstage")

# Exact files each experiment group reads, kept explicit so the footprint stays
# small instead of pulling the multi-GB swebench origin trajectories.
FILES = [
    # sokoban — coverage / gap / economic / cost-of-pass (opus4.7 = primary env-effect run)
    "origin/sokoban-origin-claude-opus-4.7-low-thinking-128-main/sokoban_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/sokoban-origin-claude-opus-4.7-low-thinking-128-main_origin-claude-opus-4.7-low-thinking-token-estimation-main/sokoban-origin-claude-opus-4.7-low-thinking-128-main_origin-claude-opus-4.7-low-thinking-token-estimation-main.json",
    # sokoban — other 6 models (7 total), for run_allruns.py's all-19-runs breadth table
    "origin/sokoban-origin-claude-opus-4-6-low-thinking-128-main/sokoban_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/sokoban-origin-claude-opus-4-6-low-thinking-128-main_claude-opus-4-6-low-thinking-128-main/sokoban-origin-claude-opus-4-6-low-thinking-128-main_claude-opus-4-6-low-thinking-128-main.json",
    "origin/sokoban-origin-claude-sonnet-4.6-low-thinking-128-main/sokoban_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/sokoban-origin-claude-sonnet-4.6-low-thinking-128-main_origin-claude-sonnet-4.6-low-thinking-token-estimation-main/sokoban-origin-claude-sonnet-4.6-low-thinking-128-main_origin-claude-sonnet-4.6-low-thinking-token-estimation-main.json",
    "origin/sokoban-origin-gemini-3.1-pro-preview-128-main/sokoban_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/sokoban-origin-gemini-3.1-pro-preview-128-main_gemini-3.1-pro-preview-token-estimation-main/sokoban-origin-gemini-3.1-pro-preview-128-main_gemini-3.1-pro-preview-token-estimation-main.json",
    "origin/sokoban-origin-gpt5.2-instant-128-main/sokoban_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/sokoban-origin-gpt5.2-instant-128-main_gpt5.2-instant-128-token-estimation-main/sokoban-origin-gpt5.2-instant-128-main_gpt5.2-instant-128-token-estimation-main.json",
    "origin/sokoban-origin-openai-openai-5-2-codex-low-thinking-128-main/sokoban_api_eval_estimation_eval_estimation_dialogues.json",
    "origin/sokoban-origin-qwen-qwen3-235b-128-main/sokoban_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/sokoban-origin-qwen-qwen3-235b-128-main_origin-qwen-qwen3-235b-128-main-token-estimation-main/sokoban-origin-qwen-qwen3-235b-128-main_origin-qwen-qwen3-235b-128-main-token-estimation-main.json",
    # searchr1 — coverage breadth (opus4.7 = primary env-effect run)
    "origin/searchr1-origin-Claude-Opus-4.7-low-thinking-128-main/search_r1_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/searchr1-origin-Claude-Opus-4.7-low-thinking-128-main_Claude-Opus-4.7-low-thinking-128-token-estimation-main/searchr1-origin-Claude-Opus-4.7-low-thinking-128-main_Claude-Opus-4.7-low-thinking-128-token-estimation-main.json",
    # searchr1 — other 6 models (7 total), for run_allruns.py's all-19-runs breadth table
    "origin/searchr1-origin-Claude-Sonnet-4.6-low-thinking-128-main/search_r1_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/searchr1-origin-Claude-Sonnet-4.6-low-thinking-128-main_Claude-Sonnet-4.6-low-thinking-128-token-estimation-main/searchr1-origin-Claude-Sonnet-4.6-low-thinking-128-main_Claude-Sonnet-4.6-low-thinking-128-token-estimation-main.json",
    "origin/searchr1-origin-claude-opus-4-6-low-thinking-128-main/search_r1_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/searchr1-origin-claude-opus-4-6-low-thinking-128-main_claude-opus-4-6-low-thinking-main/searchr1-origin-claude-opus-4-6-low-thinking-128-main_claude-opus-4-6-low-thinking-main.json",
    "origin/searchr1-origin-gpt5.2-instant-128-main/search_r1_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/searchr1-origin-gpt5.2-instant-128-main_gpt5.2-instant-token-estimation-main/searchr1-origin-gpt5.2-instant-128-main_gpt5.2-instant-token-estimation-main.json",
    "origin/searchr1-origin-openai-openai-5-2-codex-low-thinking-128-main/search_r1_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/searchr1-origin-openai-5-2-codex-low-thinking-128-main_openai-5-2-codex-low-thinking-512-main/searchr1-origin-openai-5-2-codex-low-thinking-128-main_openai-5-2-codex-low-thinking-512-main.json",
    "origin/searchr1-origin-openrouter-gemini-3-1-pro-preview-128-main/search_r1_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/searchr1-origin-openrouter-gemini-3-1-pro-preview-128-main_openrouter-gemini-3-1-pro-preview-main/searchr1-origin-openrouter-gemini-3-1-pro-preview-128-main_openrouter-gemini-3-1-pro-preview-main.json",
    "origin/searchr1-origin-qwen-qwen3-235b-a22b-2507-128-main/search_r1_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/searchr1-origin-qwen-qwen3-235b-a22b-2507-128-main_qwen-qwen3-235b-a22b-2507-main/searchr1-origin-qwen-qwen3-235b-a22b-2507-128-main_qwen-qwen3-235b-a22b-2507-main.json",
    # swebench — coverage / transfer / economic / cost-of-pass (estimation dumps only; the
    # `origin/` tree for swebench is thousands of tiny per-GitHub-issue trajectory files
    # that no run_*.py reads — skip it to keep the footprint small)
    "estimation/swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main/swebench-origin-claude-opus4.7_eval_estimation_dialogues.json",
    "estimation/swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main/swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main.json",
    # swebench — other 4 models (5 total), for run_allruns.py breadth + run_transfer.py's
    # model-swap transfer bars (the other data-blocked headline item)
    "estimation/swebench-origin-claude-sonnet4.6_claude-sonnet-4.6-512-main/swebench-origin-claude-sonnet4.6_eval_estimation_dialogues.json",
    "estimation/swebench-origin-claude-sonnet4.6_claude-sonnet-4.6-512-main/swebench-origin-claude-sonnet4.6_claude-sonnet-4.6-512-main.json",
    "estimation/swebench-origin-gemini3.1_gemini3.1-pro-preview-512-main/swebench-origin-gemini3.1_eval_estimation_dialogues.json",
    "estimation/swebench-origin-gemini3.1_gemini3.1-pro-preview-512-main/swebench-origin-gemini3.1_gemini3.1-pro-preview-512-main.json",
    "estimation/swebench-origin-gpt5.2instant_gpt5.2instant-512-main/swebench-origin-gpt5.2instant_eval_estimation_dialogues.json",
    "estimation/swebench-origin-gpt5.2instant_gpt5.2instant-512-main/swebench-origin-gpt5.2instant_gpt5.2instant-512-main.json",
    "estimation/swebench-origin-qwen3-235b_qwen3-235b-512-main/swebench-origin-qwen3-235b_eval_estimation_dialogues.json",
    "estimation/swebench-origin-qwen3-235b_qwen3-235b-512-main/swebench-origin-qwen3-235b_qwen3-235b-512-main.json",
    # warehouse — C2 joint / C3 economics / censored conformal
    "estimation/newwarehouse-opus4.7-low-thinking-main/newwarehouse-opus4.7-low-thinking-main.json",
    # warehouse — other 4 models, for run_transfer_warehouse.py's model-swap transfer
    # (closes the internal-vs-external transfer gap: run_transfer/run_transfer_env only
    # ever covered token-budget envs, never Warehouse)
    "estimation/newwarehouse-gemini3.1-low-thinking-main/newwarehouse-gemini3.1-low-thinking-main.json",
    "estimation/newwarehouse-gpt5.2-main/newwarehouse-gpt5.2-main.json",
    "estimation/newwarehouse-qwen3-235b-main/newwarehouse-qwen3-235b-main.json",
    "estimation/newwarehouse-sonnet4.6-low-thinking-main/newwarehouse-sonnet4.6-low-thinking-main.json",
]


def _ext(path: str) -> str:
    """Windows extended-length form (``\\\\?\\``) so >260-char paths are usable."""
    path = os.path.abspath(path)
    if os.name == "nt" and not path.startswith("\\\\?\\"):
        return "\\\\?\\" + path
    return path


def main() -> None:
    os.makedirs(DEST, exist_ok=True)
    shutil.rmtree(_ext(os.path.join(DEST, ".cache")), ignore_errors=True)  # stale temp
    placed, skipped = [], []
    for rel in FILES:
        dst = os.path.join(DEST, rel.replace("/", os.sep))
        try:
            src = hf_hub_download(REPO_ID, rel, repo_type="dataset", revision=REVISION, local_dir=STAGE)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(_ext(dst)):
                os.remove(_ext(dst))
            shutil.move(_ext(src), _ext(dst))
            size = os.path.getsize(_ext(dst))
            placed.append(rel)
            print(f"  ok    {round(size / 1e6, 2):>7} MB  {rel}")
        except OSError as exc:
            skipped.append(rel)
            print(f"  SKIP  (path too long / IO)  {rel}")
    shutil.rmtree(_ext(STAGE), ignore_errors=True)
    print(f"\nPlaced {len(placed)}/{len(FILES)} files into {DEST}")
    if skipped:
        print(
            "Skipped (Windows MAX_PATH: these BAGEN dir names + this repo's depth\n"
            "exceed 260 chars). They only feed agent-baseline display / self-estimate\n"
            "features; core coverage + warehouse economics run without them. To get\n"
            "them, clone the repo to a short path (e.g. C:\\bg) or enable Win long paths:"
        )
        for rel in skipped:
            print("  -", rel)


if __name__ == "__main__":
    main()
