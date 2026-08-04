"""Staleness guard for resumable driver checkpoints.

A resume path that trusts any existing per-seed CSV is a silent poisoning
mechanism: after a code or label-definition change, a complete stale checkpoint
suppresses the entire recomputation while rewriting the tables with fresh
mtimes — they LOOK regenerated. This actually happened on 2026-08-02: after the
warehouse-label fix in loop_datasets, `python -m budget_guard.run_loop_validation`
(whose __main__ passes resume=True) skipped all five seeds and re-serialized the
pre-fix rows; the audit caught it because the "regenerated" tables were
byte-identical to a round-trip of the old checkpoint.

The guard: every checkpoint gets a sidecar recording a hash of all budget_guard/
source files. Resume is honored only when the recorded hash matches the current
source — any code change since the checkpoint was written forces a recompute.
Conservative on purpose: a changed comment also invalidates, which costs one
recompute and can never poison a table.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os


def source_fingerprint() -> str:
    """Hash of every budget_guard/*.py file, in sorted order."""
    digest = hashlib.sha256()
    root = os.path.dirname(__file__)
    for path in sorted(glob.glob(os.path.join(root, "*.py"))):
        with open(path, "rb") as handle:
            digest.update(handle.read())
    return digest.hexdigest()


def _sidecar(checkpoint_path: str) -> str:
    return f"{checkpoint_path}.fingerprint.json"


def resume_allowed(checkpoint_path: str) -> bool:
    """True only when the checkpoint exists AND was written by the current source."""
    checkpoint_path = str(checkpoint_path)
    if not os.path.exists(checkpoint_path):
        return False
    try:
        with open(_sidecar(checkpoint_path), encoding="utf-8") as handle:
            recorded = json.load(handle).get("source_fingerprint")
    except (json.JSONDecodeError, OSError):
        recorded = None
    if recorded != source_fingerprint():
        print(
            f"NOTE: ignoring checkpoint {checkpoint_path} — budget_guard/ source "
            "changed since it was written (or no fingerprint recorded); "
            "recomputing from scratch."
        )
        return False
    return True


def write_fingerprint(checkpoint_path: str) -> None:
    with open(_sidecar(str(checkpoint_path)), "w", encoding="utf-8") as handle:
        json.dump({"source_fingerprint": source_fingerprint()}, handle)
