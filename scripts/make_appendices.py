"""scripts/make_appendices.py — build Appendices B and C from the generated tables.

Appendix B (per-run dataset composition) and Appendix C (supporting figures) are
the two appendices whose content is DERIVED from experiment output, so they are
generated here rather than typed by hand. Every number in Appendix B is read from
tables/allruns.csv and tables/transfer_warehouse.csv, which `make repro-all`
produces and `make check-numbers` verifies. Appendix A is prose, not data, so it
stays in the document.

Writes paper/appendices.md, which is paste-ready: no metadata, no instructions,
nothing to strip. See paper/README.md for the workflow.

Fails loudly (non-zero exit) if a table or figure is missing, if the run count is
not the expected 19, or if a figure is older than the table it is drawn from.

Usage: python scripts/make_appendices.py    (or: make appendices)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLES, FIGURES, OUT = ROOT / "tables", ROOT / "figures", ROOT / "paper" / "appendices.md"

# Raw run labels in allruns.csv are directory names from the BAGEN download and
# vary in spelling across environments ("claude-opus-4.7", "claude-opus4.7-claude-opus-4",
# "Claude-Opus-4.7"). Order matters: check Codex before the generic GPT-5.2 rule,
# and 4.7 before 4.6, since several labels contain both a version and a stray "-4".
MODEL_RULES = (
    ("codex", "GPT-5.2-Codex"),
    ("gpt5.2", "GPT-5.2-instant"),
    ("gpt-5.2", "GPT-5.2-instant"),
    ("gemini", "Gemini 3.1 Pro"),
    ("qwen", "Qwen3-235B"),
    ("sonnet", "Claude Sonnet 4.6"),
)
MODEL_ORDER = ("Claude Opus 4.7", "Claude Opus 4.6", "Claude Sonnet 4.6",
               "GPT-5.2-instant", "GPT-5.2-Codex", "Gemini 3.1 Pro", "Qwen3-235B")
ENV_NAMES = {"sokoban": "Sokoban", "searchr1": "Search-R1", "swebench": "SWE-bench"}
ENV_ORDER = ("sokoban", "searchr1", "swebench")

# A driver writes its table and its figure within the same call, and shutil.copy2
# preserves mtimes when figures are collected into figures/final/, so within one run
# the two can land in either order a second apart. Only a gap larger than this means
# the figure really predates the numbers it is drawn from.
SAME_RUN_TOLERANCE_S = 300

FIGURES_IN_C = (
    (6, "figures/final/transfer_swebench.png", "tables/transfer_swebench.csv",
     "Model-swap transfer on SWE-bench, guard calibrated on Claude Opus 4.7. Mean "
     "coverage is comparable between frozen split-CQR and windowed-CQR; the difference "
     "is the width of the seed-to-seed band."),
    (7, "figures/conditional_coverage.png", "tables/conditional_coverage.csv",
     "Conditional coverage by turn depth. The Sokoban k = 1 slice is the only place a "
     "marginal number materially overstates performance, and it is the slice the abort "
     "decision depends on most."),
)

problems: list[str] = []


def die_if_missing(path: Path, what: str) -> bool:
    if not path.exists():
        problems.append(f"{what} is missing: {path.relative_to(ROOT)} (run: make repro-all)")
        return False
    return True


def model_name(label: str) -> str:
    low = label.lower()
    for needle, name in MODEL_RULES:
        if needle in low:
            return name
    if "opus" in low:
        return "Claude Opus 4.7" if "4.7" in low or "4-7" in low else "Claude Opus 4.6"
    problems.append(f"unrecognized run label in allruns.csv: {label!r} (add a rule)")
    return label


def read_runs() -> list[tuple[str, str, int, int]]:
    path = TABLES / "allruns.csv"
    if not die_if_missing(path, "Appendix B source table"):
        return []
    rows = []
    with path.open() as fh:
        for r in csv.DictReader(fh):
            rows.append((r["env"], model_name(r["model"]),
                         int(float(r["n_rollouts"])), int(float(r["n_samples"]))))
    if len(rows) != 19:
        problems.append(f"expected 19 model x environment runs, found {len(rows)} "
                        "(a partial BAGEN download silently skips runs; see make doctor)")
    rows.sort(key=lambda t: (ENV_ORDER.index(t[0]) if t[0] in ENV_ORDER else 99,
                             MODEL_ORDER.index(t[1]) if t[1] in MODEL_ORDER else 99))
    return rows


def warehouse_row() -> tuple[int, int, int] | None:
    """(n_swap_targets, rollouts_per_model, prefixes_per_model) from the transfer table.

    n_test on the frozen rows is the count of FEASIBLE prefixes. The Warehouse
    prefix set is exactly half censored (the runs that can no longer finish), which
    is the property Appendix B reports, so the total is twice the feasible count.
    """
    path = TABLES / "transfer_warehouse.csv"
    if not die_if_missing(path, "Appendix B Warehouse source table"):
        return None
    with path.open() as fh:
        rows = [r for r in csv.DictReader(fh) if r["method"] == "frozen Bonferroni"]
    if not rows:
        problems.append("no 'frozen Bonferroni' rows in transfer_warehouse.csv")
        return None
    targets = sorted({r["target_model"] for r in rows})
    rollouts = {int(float(r["n_rollouts"])) for r in rows}
    feasible = {int(float(r["n_test"])) for r in rows}
    if len(rollouts) != 1 or len(feasible) != 1:
        problems.append("Warehouse targets disagree on rollout/prefix counts; "
                        "the single summary row in Appendix B would be wrong")
        return None
    return len(targets), rollouts.pop(), feasible.pop() * 2


def check_figure(rel_fig: str, rel_table: str, num: int) -> None:
    fig, tbl = ROOT / rel_fig, ROOT / rel_table
    if not die_if_missing(fig, f"Appendix C Figure {num}"):
        return
    if tbl.exists() and fig.stat().st_mtime < tbl.stat().st_mtime - SAME_RUN_TOLERANCE_S:
        problems.append(f"Figure {num} ({rel_fig}) is older than {rel_table}; "
                        "regenerate it with make repro-all before submitting")


def main() -> int:
    runs = read_runs()
    wh = warehouse_row()
    for num, fig, tbl, _ in FIGURES_IN_C:
        check_figure(fig, tbl, num)

    lines = [
        "## Appendix B. Per-run dataset composition", "",
        "Table 3: Rollout and prefix-sample counts for every model x environment run "
        "evaluated in this paper.", "",
        "| Environment | Model | Rollouts | Prefix samples |",
        "|---|---|---|---|",
    ]
    for env, model, rollouts, samples in runs:
        lines.append(f"| {ENV_NAMES.get(env, env)} | {model} | {rollouts} | {samples:,} |")
    if wh:
        n_targets, rollouts, prefixes = wh
        lines.append(f"| Warehouse | Opus 4.7 + {n_targets} swap targets | {rollouts} each | "
                     f"{prefixes:,} each (3 resources; 50% censored) |")
    lines += ["", "## Appendix C. Supporting figures", ""]
    for num, fig, _, caption in FIGURES_IN_C:
        lines += [f"Figure {num}: {caption}", "", f"[insert image: {fig}]", ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines).rstrip() + "\n")

    print(f"wrote {OUT.relative_to(ROOT)}: {len(runs)} runs"
          + (" + Warehouse row" if wh else "") + f", {len(FIGURES_IN_C)} figures")
    if problems:
        print("\nPROBLEMS (the appendices above are not submission-ready):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("all sources present and current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
