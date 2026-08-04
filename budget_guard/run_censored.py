"""budget_guard/run_censored.py — mask-and-measure validation of censored conformal.

Warehouse, all three resources. Rows with can_finish=False are treated as a
deployment would see them (label masked; only the bound b = budget − spent and the
observed *which-budget-was-hit* signal are known); recovered labels are used ONLY
to measure coverage afterwards. That recovery is exact for time_weeks but carries
load_warehouse's interpolation error for cost/warehouse (median 12-27% on
comparable rows) — censored-stratum coverage for those resources is against an
approximate label. See censored.py's module docstring.

Compares five calibrations of the one-sided upper bound (see ``censored.upper_qhat``),
including ``resource_bound`` — the multi-resource fix that bounds resource r only on
the runs where r is the operative (binding) constraint.

Usage: python -m budget_guard.run_censored
Writes tables/censored_upper.csv.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .censored import upper_qhat
from .economic import fit_feasibility, fit_remaining_regressor
from .multiresource import RESOURCES, build_features, load_warehouse
from .run_multiresource import PATH
from .split import group_split

ALPHA = 0.1
METHODS = ("drop", "infinity", "bound", "ipcw", "resource_bound", "km")


def _stratified_cov(y: np.ndarray, hi: np.ndarray, te: np.ndarray, mask: np.ndarray) -> float:
    """Mean coverage y <= hi over the test rows in ``mask`` (hi is indexed over test)."""
    m = mask & te
    if not m.any():
        return float("nan")
    return float(np.mean(y[m] <= hi[m[te]]))


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4)):
    df = load_warehouse(PATH, keep_censored=True)
    X = build_features(df)
    cens = df["censored"].to_numpy(dtype=bool)
    print(f"{len(df)} prefix samples, {df['rollout_index'].nunique()} rollouts; "
          f"censored = {cens.mean():.0%}")

    rows = []
    for res in RESOURCES:
        y = df[f"y_{res}"].to_numpy(dtype=float)
        budget = df[f"budget_{res}"].to_numpy(dtype=float)
        spent = df[f"spent_{res}"].to_numpy(dtype=float)
        total = df[f"total_{res}"].to_numpy(dtype=float)
        bound = budget - spent
        obs = np.isfinite(y)  # unrecoverable censored totals -> exclude from scoring
        # r is the OPERATIVE (binding) constraint for a censored run when its full
        # requirement for r exceeds r's budget. In deployment this is the observed
        # "which budget was hit" event; here it is derived from the recovered total.
        binding = cens & np.isfinite(total) & (total > budget)
        frac_bind = float(binding[cens].mean()) if cens.any() else float("nan")

        for seed in seeds:
            masks = group_split(df, seed=seed)
            tr, ca, te = masks["train"], masks["cal"], masks["test"]
            reg = fit_remaining_regressor(X[tr & ~cens], y[tr & ~cens])
            clf = fit_feasibility(X[tr], ~cens[tr])  # P(uncensored | x)

            ca_unc = ca & ~cens
            ca_cen = ca & cens & np.isfinite(bound)
            s_unc = y[ca_unc] - reg.predict(X[ca_unc])
            s_cens_lb = bound[ca_cen] - reg.predict(X[ca_cen])
            binding_cen = binding[ca_cen]
            p_unc = clf.predict_proba(X[ca_unc])[:, 1]
            pred_te = reg.predict(X[te])

            for method in METHODS:
                qhat = upper_qhat(
                    s_unc, s_cens_lb, ALPHA, method,
                    p_uncensored=p_unc if method == "ipcw" else None,
                    censored_binding=binding_cen if method in ("resource_bound", "km") else None,
                )
                hi = pred_te + qhat
                rows.append({
                    "resource": res, "seed": seed, "method": method, "qhat": qhat,
                    "cov_feasible": _stratified_cov(y, hi, te, obs & ~cens),
                    "cov_cens_binding": _stratified_cov(y, hi, te, obs & binding),
                    "cov_cens_nonbinding": _stratified_cov(y, hi, te, obs & cens & ~binding),
                    "frac_binding_of_censored": frac_bind,
                })

    table = (pd.DataFrame(rows).groupby(["resource", "method"], sort=False)
             .agg(cov_feasible=("cov_feasible", "mean"),
                  cov_cens_binding=("cov_cens_binding", "mean"),
                  cov_cens_nonbinding=("cov_cens_nonbinding", "mean"),
                  qhat_median=("qhat", "median"),
                  frac_binding=("frac_binding_of_censored", "first")).reset_index())
    os.makedirs("tables", exist_ok=True)
    table.to_csv("tables/censored_upper.csv", index=False)
    print(table.to_string(index=False))
    print("\nwrote tables/censored_upper.csv")
    return table


if __name__ == "__main__":
    main()
