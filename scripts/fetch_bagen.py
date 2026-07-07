"""scripts/fetch_bagen.py — fetch the minimal BAGEN files the offline harness needs.

The full ``MLL-Lab/BAGEN`` dataset is ~3.8 GB (the swebench *origin* trajectories
dominate, some single files >180 MB). The runners only read a handful of estimation
records + small dialogue dumps, so this downloads just those (~105 MB) into
``data/bagen_hf/`` (gitignored), preserving the repo-relative layout ``data.py`` and
``run_multiresource.py`` expect.

    python scripts/fetch_bagen.py

Extend ``FILES`` to pull more model/env records (see ``budget_guard/data.py`` and
``run_multiresource.py`` for the exact path each experiment consumes).
"""
from __future__ import annotations

import os
import shutil

from huggingface_hub import hf_hub_download

REPO_ID = "MLL-Lab/BAGEN"
DEST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "bagen_hf"))
# Short staging root: HF writes temp files under ``<local_dir>/.cache/.../<hash>.incomplete``,
# and BAGEN's 63-char estimation dir names blow past Windows' 260-char MAX_PATH when the
# repo lives under a deep path. Staging in a short dir keeps temp paths legal; the final
# moved-into-place paths fit comfortably.
STAGE = os.path.join(os.path.expanduser("~"), "_bgstage")

# Exact files each experiment group reads, kept explicit so the footprint stays
# small instead of pulling the multi-GB swebench origin trajectories.
FILES = [
    # sokoban — coverage / gap / economic / cost-of-pass
    "origin/sokoban-origin-claude-opus-4.7-low-thinking-128-main/sokoban_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/sokoban-origin-claude-opus-4.7-low-thinking-128-main_origin-claude-opus-4.7-low-thinking-token-estimation-main/sokoban-origin-claude-opus-4.7-low-thinking-128-main_origin-claude-opus-4.7-low-thinking-token-estimation-main.json",
    # searchr1 — coverage breadth
    "origin/searchr1-origin-Claude-Opus-4.7-low-thinking-128-main/search_r1_api_eval_estimation_eval_estimation_dialogues.json",
    "estimation/searchr1-origin-Claude-Opus-4.7-low-thinking-128-main_Claude-Opus-4.7-low-thinking-128-token-estimation-main/searchr1-origin-Claude-Opus-4.7-low-thinking-128-main_Claude-Opus-4.7-low-thinking-128-token-estimation-main.json",
    # swebench — coverage / transfer / economic / cost-of-pass (estimation dumps only)
    "estimation/swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main/swebench-origin-claude-opus4.7_eval_estimation_dialogues.json",
    "estimation/swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main/swebench-origin-claude-opus4.7_claude-opus-4.7-low-thinking-512-main.json",
    # warehouse — C2 joint / C3 economics / censored conformal
    "estimation/newwarehouse-opus4.7-low-thinking-main/newwarehouse-opus4.7-low-thinking-main.json",
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
            src = hf_hub_download(REPO_ID, rel, repo_type="dataset", local_dir=STAGE)
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
