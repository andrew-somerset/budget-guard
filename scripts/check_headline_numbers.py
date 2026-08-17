"""Verify that the project's headline numbers still match the generated tables.

The claims below are the ones quoted in the paper (and originally in the internal
research notes, now archived on the internal-notes branch). Each entry records its
provenance so a failure points at the claim to fix, not just the table.

Motivation: on 2026-08-01 four separate stale figures were found in a hand-written summary to
be stale — three transfer coverages left over from before the rollout-safe revelation fix
(which had a correction banner directly above them that the body never absorbed), plus a
test count and a data size. Nothing was wrong with the code; a hand-written summary had
drifted from the artifacts it summarized. Prose cannot be diffed, so it silently rots.

This script makes each headline claim machine-checkable: a claim names a table, a row
selector, a column, and the value the notes assert. If a re-run moves a number, this fails
and tells you which sentence to go edit.

Run:  make check-numbers      (or: python scripts/check_headline_numbers.py)
Exits 0 if every claim holds, 1 otherwise. Exits 0 with a notice if tables/ is absent,
so it is harmless in environments without the generated artifacts (e.g. CI).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

TABLES = Path(__file__).resolve().parent.parent / "tables"

# Absolute tolerance for a point claim quoted to 4 decimals. Loose enough to survive
# last-bit cross-platform noise (the container-vs-host comparison differed by 1 ULP,
# ~2e-16), tight enough that a real methodological change cannot slip through.
TOL = 5e-4

# Range claims are quoted in prose rounded to 2 decimals ("SPCI 0.66-0.89"), so a value
# is consistent with the claim if it rounds to it: half of the last quoted digit.
# Without this the check fails on correct prose, which would train you to ignore it.
RANGE_TOL = 5e-3

# Each claim: where it is asserted in prose, which table cell backs it, and what it says.
#   kind="approx" -> the single selected row's column must equal `value` within TOL
#   kind="range"  -> every selected row's column must fall within [lo, hi]
CLAIMS = [
    {
        "quoted_in": "current_state.md — 'frozen conformal collapses to 0.10 under cross-env shift'",
        "table": "transfer_env.csv",
        "where": {"target_env": "swebench", "method": "split-CQR (frozen)"},
        "column": "coverage",
        "kind": "approx",
        "value": 0.1031,
    },
    {
        "quoted_in": "current_state.md — 'SPCI recovers to 0.80 at 0% unbounded'",
        "table": "transfer_env.csv",
        "where": {"target_env": "swebench", "method": "windowed-CQR"},
        "column": "coverage",
        "kind": "approx",
        "value": 0.7983,
    },
    {
        "quoted_in": "current_state.md — '...at 0% unbounded' (the operational half of the claim)",
        "table": "transfer_env.csv",
        "where": {"target_env": "swebench", "method": "windowed-CQR"},
        "column": "frac_unbounded",
        "kind": "approx",
        "value": 0.0,
    },
    {
        "quoted_in": "robustness_progress.md 2026-07-21 — 'searchr1: SPCI 0.726 -> 0.710'",
        "table": "transfer_env.csv",
        "where": {"target_env": "searchr1", "method": "windowed-CQR"},
        "column": "coverage",
        "kind": "approx",
        "value": 0.7103,
    },
    {
        "quoted_in": "current_state.md — 'model swap ... SPCI 0.66-0.89'",
        "table": "transfer_swebench.csv",
        "where": {"method": "windowed-CQR"},
        "column": "coverage",
        "kind": "range",
        "lo": 0.66,
        "hi": 0.89,
    },
    {
        "quoted_in": "current_state.md — 'model swap: frozen 0.64-0.89 (5-seed mean)'",
        "table": "transfer_swebench.csv",
        "where": {"method": "split-CQR (frozen)"},
        "column": "coverage",
        "kind": "range",
        "lo": 0.64,
        "hi": 0.89,
    },
    {
        # The load-bearing claim for model-swap transfer after the 2026-08-01 five-seed
        # hardening: frozen and SPCI have comparable MEAN coverage, but frozen's is a
        # lottery on the calibration split while SPCI's is stable. Guards the variance
        # gap, which is what the claim now rests on.
        "quoted_in": "current_state.md — 'frozen cov_std ~0.18 vs SPCI ~0.01 on model swap'",
        "table": "transfer_swebench.csv",
        "where": {"method": "windowed-CQR"},
        "column": "cov_std",
        "kind": "within",
        "lo": 0.0,
        "hi": 0.02,
    },
    {
        "quoted_in": "current_state.md — 'frozen cov_std ~0.18 vs SPCI ~0.01 on model swap'",
        "table": "transfer_swebench.csv",
        "where": {"method": "split-CQR (frozen)"},
        "column": "cov_std",
        "kind": "within",
        "lo": 0.10,
        "hi": 0.25,
    },
    {
        "quoted_in": "robustness_progress.md 2026-07-21 — 'sokoban ~unchanged (SPCI 0.916)'",
        "table": "coverage.csv",
        "where": {"env": "sokoban", "method": "windowed-CQR"},
        "column": "coverage",
        "kind": "approx",
        "value": 0.9155,
    },
    {
        "quoted_in": "current_state.md — 'Warehouse joint shift to 0.86-0.88 overall'",
        "table": "transfer_warehouse.csv",
        "where": {"method": "adaptive joint copula", "resource": "ALL (joint)"},
        "column": "coverage",
        "kind": "range",
        "lo": 0.86,
        "hi": 0.88,
    },
    {
        "quoted_in": "current_state.md — '0.87-0.90 in the late half'",
        "table": "transfer_warehouse.csv",
        "where": {"method": "adaptive joint copula", "resource": "ALL (joint)"},
        "column": "late_coverage",
        "kind": "range",
        "lo": 0.87,
        "hi": 0.90,
    },
]


def _select(df: pd.DataFrame, where: dict) -> pd.DataFrame:
    for col, val in where.items():
        if col not in df.columns:
            raise KeyError(f"column {col!r} not in table (columns: {list(df.columns)})")
        df = df[df[col] == val]
    return df


def check(claim: dict) -> tuple[bool, str]:
    path = TABLES / claim["table"]
    if not path.exists():
        return True, f"SKIP  {claim['table']} not present"

    rows = _select(pd.read_csv(path), claim["where"])
    if rows.empty:
        return False, f"FAIL  no rows matched {claim['where']} in {claim['table']}"

    values = rows[claim["column"]].to_numpy()

    if claim["kind"] == "approx":
        if len(values) != 1:
            return False, (
                f"FAIL  selector matched {len(values)} rows, expected exactly 1 "
                f"({claim['table']} {claim['where']})"
            )
        actual, expected = float(values[0]), claim["value"]
        ok = abs(actual - expected) <= TOL
        return ok, (
            f"{'PASS' if ok else 'FAIL'}  {claim['table']}[{claim['column']}] "
            f"= {actual:.4f}, notes say {expected:.4f}"
        )

    lo, hi = claim["lo"], claim["hi"]
    actual_lo, actual_hi = float(values.min()), float(values.max())
    if claim["kind"] == "within":
        # Bound-style claim ("cov_std ~0.01", encoded as a permissive interval):
        # every value must lie inside; the span need not touch the endpoints.
        ok = actual_lo >= lo - RANGE_TOL and actual_hi <= hi + RANGE_TOL
    else:
        # Span-style claim (prose quotes the range itself, e.g. "SPCI 0.66-0.89"):
        # two-sided — the ENDPOINTS must match. Containment-only checking passes
        # when a regenerated table's spread collapses (actual 0.70-0.71 against a
        # claimed 0.66-0.89), leaving prose that overstates the variability.
        ok = abs(actual_lo - lo) <= RANGE_TOL and abs(actual_hi - hi) <= RANGE_TOL
    return ok, (
        f"{'PASS' if ok else 'FAIL'}  {claim['table']}[{claim['column']}] "
        f"spans {actual_lo:.4f}-{actual_hi:.4f}, notes claim {lo:.2f}-{hi:.2f}"
    )


def main() -> int:
    if not TABLES.exists():
        print(f"tables/ not found at {TABLES} — nothing to check.")
        return 0

    failures = 0
    for claim in CLAIMS:
        ok, message = check(claim)
        if not ok:
            failures += 1
        print(message)
        print(f"      quoted in: {claim['quoted_in']}")

    print()
    if failures:
        print(
            f"{failures} of {len(CLAIMS)} headline claims no longer match the tables.\n"
            "Either the tables were regenerated with a real change (update the prose), "
            "or a regression crept in (fix the code). Do not update the claim without "
            "knowing which."
        )
        return 1

    print(f"All {len(CLAIMS)} headline claims match the generated tables.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
