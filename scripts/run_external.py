"""scripts/run_external.py — item 5: the UNMODIFIED guard on a non-BAGEN corpus.

Cheapest viable external check without API keys or human-provided data: a large, real,
LOCAL corpus of source files (this repo + venv site-packages). Each file is a "session",
blank-line-separated blocks are "turns", and per-turn "tokens" are counted by the repo's
OWN word tokenizer (extract._rough_text_token_count) — real measured counts, no
fabrication, no new dependency. The guard predicts remaining tokens-to-end-of-file from
prefix-only features via the SAME build_xy + conformal code path as BAGEN (no
per-dataset special casing).

This is a PIPELINE-GENERALITY smoke test on sequential text, NOT agent-deployment
transfer: the domain is source code, sessions are short, there is no agent. Stronger
external validation (real logged agent runs / AssetOpsBench / GM cost units) needs API
keys / a benchmark harness / data access and is tracked as Blocked in the progress log.

Usage: python scripts/run_external.py     (writes tables/external_coverage.csv)
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from budget_guard.conformal import (  # noqa: E402  — unmodified guard (offline)
    DEFAULT_ALPHA, constant_quantile, cqr_split, split_conformal_absres,
)
from budget_guard.extract import _rough_text_token_count  # noqa: E402  — repo tokenizer
from budget_guard.features import build_xy  # noqa: E402
from budget_guard.metrics import (  # noqa: E402
    marginal_coverage, median_width, normalized_width,
    pooled_bootstrap_ci, rollout_bootstrap_draws,
)
from budget_guard.split import group_split  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MIN_TURNS, MAX_TURNS = 4, 40
MIN_TOTAL, MAX_TOTAL = 50, 4000


def _collect_files(n_sample: int = 1200, seed: int = 0) -> list[str]:
    # Both venv layouts (Windows Lib/, POSIX lib/pythonX.Y/) plus the running
    # interpreter's site-packages as a fallback — the original Windows-only glob
    # collapsed the corpus to ~44 repo files everywhere else.
    import sysconfig

    pats = [
        os.path.join(REPO, ".venv", "Lib", "site-packages", "**", "*.py"),
        os.path.join(REPO, ".venv", "lib", "python*", "site-packages", "**", "*.py"),
        os.path.join(REPO, "budget_guard", "*.py"),
        os.path.join(REPO, "notes", "*.md"),
    ]
    if not glob.glob(pats[0]) and not glob.glob(pats[1], recursive=True):
        pats.append(os.path.join(sysconfig.get_paths()["purelib"], "**", "*.py"))
    files = sorted({f for p in pats for f in glob.glob(p, recursive=True)})
    rng = np.random.default_rng(seed)
    if len(files) > n_sample:
        files = list(rng.choice(files, size=n_sample, replace=False))
    return files


def _sessions() -> tuple[pd.DataFrame, int]:
    rows, r = [], 0
    for path in _collect_files():
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        per = [_rough_text_token_count(b) for b in re.split(r"\n\s*\n", text) if b.strip()]
        per = [t for t in per if t > 0]
        N, total = len(per), int(sum(per))
        if not (MIN_TURNS <= N <= MAX_TURNS and MIN_TOTAL <= total <= MAX_TOTAL):
            continue
        for k in range(1, N):  # prefixes k = 1..N-1, same convention as the extractor
            cum = int(sum(per[:k]))
            rows.append({
                "rollout_index": r, "sample_id": f"{r}_{k}", "k": k, "N": N,
                "tokens_so_far": cum, "total_rollout_tokens": total,
                "y": total - cum, "can_finish": True, "rollout_success": True,
                "per_turn_total": list(per[:k]),
            })
        r += 1
    return pd.DataFrame(rows), r


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4), alpha: float = DEFAULT_ALPHA):
    df, n_sessions = _sessions()
    med = df.groupby("rollout_index")["total_rollout_tokens"].first().median()
    print(f"external corpus: {n_sessions} sessions (files), {len(df)} prefix samples, "
          f"median tokens/session={med:.0f}")
    X, y, groups = build_xy(df)

    rows = []
    for seed in seeds:
        m = group_split(df, seed=seed)
        tr, ca, te = m["train"], m["cal"], m["test"]
        methods = {
            "constant-quantile": constant_quantile(y[ca], int(te.sum()), alpha=alpha)[:2],
            "split-absres": split_conformal_absres(X[tr], y[tr], X[ca], y[ca], X[te], alpha=alpha)[:2],
            "split-CQR": cqr_split(X[tr], y[tr], X[ca], y[ca], X[te], alpha=alpha)[:2],
        }
        yte, gte = y[te], groups[te]
        for name, (lo, hi) in methods.items():
            draws = rollout_bootstrap_draws(yte, lo, hi, gte, seed=seed)
            rows.append({
                "method": name, "seed": seed,
                "coverage": marginal_coverage(yte, lo, hi),
                "ci_lo": float(np.quantile(draws, 0.05)),
                "ci_hi": float(np.quantile(draws, 0.95)),
                "median_width": median_width(lo, hi),
                "normalized_width": normalized_width(yte, lo, hi, agg="median"),
                "_draws": draws,
            })
    per_seed = pd.DataFrame(rows)
    agg = (per_seed.groupby("method", sort=False)
           .agg(coverage=("coverage", "mean"), cov_std=("coverage", "std"),
                median_width=("median_width", "mean"),
                normalized_width=("normalized_width", "mean")).reset_index())
    # Pooled seed x rollout bootstrap band, not a mean of per-seed CI endpoints
    # (which is not a CI at any level — 2026-08-01 audit).
    pooled = per_seed.groupby("method", sort=False)["_draws"].apply(
        lambda group: pooled_bootstrap_ci(list(group))
    )
    agg["ci_lo"] = [c[0] for c in pooled]
    agg["ci_hi"] = [c[1] for c in pooled]
    os.makedirs(os.path.join(REPO, "tables"), exist_ok=True)
    agg.to_csv(os.path.join(REPO, "tables", "external_coverage.csv"), index=False)
    print(agg.to_string(index=False))
    print("\nwrote tables/external_coverage.csv")
    return agg


if __name__ == "__main__":
    main()
