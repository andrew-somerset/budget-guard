"""budget_guard/run_allruns.py — the breadth table: every model x env run on disk.

For each run with raw dialogues (7 sokoban, 7 searchr1, 5 swebench = 19 runs),
split by rollout (seed 0), fit the guard, report coverage of split-CQR (offline),
SPCI and DtACI (online) alongside the agent-self-report baseline when the matching
estimation record exists. One seed: this table is about breadth, not variance —
the headline table (run_coverage) carries the multi-seed error bars.

Usage: python -m budget_guard.run_allruns
Writes figures/allruns.png and tables/allruns.csv.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd

from .conformal import DEFAULT_ALPHA, cqr_split, dtaci, spci
from .extract import flatten_to_samples, load_rollouts, samples_to_dataframe
from .features import build_xy
from .metrics import marginal_coverage
from .split import group_split

_DATA = os.path.join(os.path.dirname(__file__), "..", "data", "bagen_hf")
ENV_MAX_CTX = {"sokoban": 2500, "searchr1": 3500, "swebench": 7060}
AQUA, VIOLET, GREEN, GRAY = "#1baf7a", "#4a3aa7", "#008300", "#8B93A1"


def _env_of(run_dir: str) -> str:
    for env in ENV_MAX_CTX:
        if run_dir.lower().startswith(env):
            return env
    return "other"


def _model_of(run_dir: str) -> str:
    tail = run_dir.split("-origin-", 1)[-1]
    return tail.replace("-low-thinking", "").replace("-128-main", "").replace("_", "-")[:28]


def discover_runs() -> list[dict]:
    runs = []
    for path in sorted(glob.glob(f"{_DATA}/origin/*/*dialogues*.json")) + sorted(
        glob.glob(f"{_DATA}/estimation/*/*eval_estimation_dialogues.json")
    ):
        run_dir = os.path.basename(os.path.dirname(path))
        env = _env_of(run_dir)
        if env == "other":
            continue
        runs.append({"env": env, "model": _model_of(run_dir), "raw": path, "run_dir": run_dir})
    return runs


def _norm_tokens(name: str) -> str:
    """Collapse immediately-repeated '-' tokens and case-fold, so origin and
    estimation directory names that normalize the model differently still match
    (e.g. origin 'searchr1-origin-openai-openai-5-2-codex-...' vs estimation
    'searchr1-origin-openai-5-2-codex-...')."""
    out: list[str] = []
    for tok in name.lower().split("-"):
        if not out or out[-1] != tok:
            out.append(tok)
    return "-".join(out)


def _baseline_for(run_dir: str) -> float | None:
    prefix = run_dir.split("-main")[0]
    candidates = glob.glob(f"{_DATA}/estimation/{prefix}*/*.json")
    if not candidates:
        # Exact-prefix miss: retry with normalized names. Without this fallback the
        # searchr1 codex run's estimation record (which exists, coverage 0.2023)
        # was silently dropped and the figure showed no agent baseline for it.
        want = _norm_tokens(prefix)
        for est_dir in sorted(glob.glob(f"{_DATA}/estimation/*")):
            if _norm_tokens(os.path.basename(est_dir)).startswith(want):
                candidates = glob.glob(f"{est_dir}/*.json")
                break
    for est in candidates:
        if est.endswith("_pairs.json") or "dialogues" in est:
            continue
        try:
            with open(est, encoding="utf-8") as handle:
                summary = json.load(handle).get("summary", {})
        except (json.JSONDecodeError, OSError):
            continue
        cov = summary.get("remaining_token_interval_coverage_rate")
        if cov is not None:
            return float(cov)
    return None


def main(seed: int = 0, alpha: float = DEFAULT_ALPHA):
    rows = []
    for run in discover_runs():
        df = samples_to_dataframe(
            flatten_to_samples(load_rollouts(run["raw"]), max_ctx=ENV_MAX_CTX[run["env"]])
        )
        if df.empty or df["rollout_index"].nunique() < 12:
            continue
        X, y, groups = build_xy(df)
        masks = group_split(df, seed=seed)
        tr, ca, te = masks["train"], masks["cal"], masks["test"]
        if te.sum() < 10:
            continue
        gte = groups[te]  # rollout-safe revelation for the online methods
        covs = {
            "split-CQR": marginal_coverage(y[te], *cqr_split(X[tr], y[tr], X[ca], y[ca], X[te], alpha=alpha)[:2]),
            "SPCI": marginal_coverage(y[te], *spci(X[tr], y[tr], X[ca], y[ca], X[te], y[te], alpha=alpha, groups=gte)[:2]),
            "DtACI": marginal_coverage(y[te], *dtaci(X[tr], y[tr], X[ca], y[ca], X[te], y[te], alpha=alpha, groups=gte)[:2]),
        }
        baseline = _baseline_for(run["run_dir"])
        if baseline is None:
            # Loud, not silent: an absent baseline should be a known data gap,
            # never an unnoticed matching failure.
            print(f"NOTE: no agent-self-report estimation record found for {run['run_dir']}")
        rows.append(
            {
                "env": run["env"], "model": run["model"],
                "n_rollouts": df["rollout_index"].nunique(), "n_samples": len(df),
                "n_test": int(te.sum()),
                "agent": baseline,
                **covs,
            }
        )
    table = pd.DataFrame(rows).sort_values(["env", "model"]).reset_index(drop=True)

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    table.to_csv("tables/allruns.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 0.42 * len(table) + 1.6), constrained_layout=True)
    labels = [f"{r.env} · {r.model}" for r in table.itertuples()]
    ys = np.arange(len(table))[::-1]
    for col, color, marker in [("agent", GRAY, "x"), ("split-CQR", AQUA, "o"),
                               ("SPCI", VIOLET, "o"), ("DtACI", GREEN, "o")]:
        vals = table[col].to_numpy(dtype=float)
        ax.scatter(vals, ys, s=34, color=color, marker=marker, label=col, zorder=3)
    ax.axvline(1 - alpha, color="#4A5361", lw=1.2, ls="--", zorder=1)
    ax.set_yticks(ys, labels, fontsize=8)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("marginal coverage (test, seed 0)")
    ax.set_title(f"Guard coverage across all {len(table)} runs vs agent self-report (x)")
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    # Legend below the axes: loc="lower left" sat on top of the last run's markers.
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center",
              bbox_to_anchor=(0.5, -0.02))
    fig.savefig("figures/allruns.png", dpi=200, bbox_inches="tight")

    print(table.to_string(index=False))
    ok = table[["split-CQR", "SPCI", "DtACI"]].ge(0.85).mean()
    print(f"\nfraction of runs with coverage >= 0.85: {ok.to_dict()}")
    print("wrote figures/allruns.png, tables/allruns.csv")
    return table


if __name__ == "__main__":
    main()
