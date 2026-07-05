"""budget_guard/run_censored.py — mask-and-measure validation of censored conformal.

Warehouse remaining-cost. Rows with can_finish=False are treated exactly as a
deployment would see them (label masked, only the bound b = budget − spent known);
their recoverable totals are used ONLY to measure true coverage afterwards.

Usage: python -m budget_guard.run_censored
Writes tables/censored_upper.csv.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .censored import upper_qhat
from .economic import fit_feasibility, fit_remaining_regressor
from .multiresource import build_features, load_warehouse
from .run_multiresource import PATH
from .split import group_split

ALPHA = 0.1
METHODS = ("drop", "infinity", "bound", "ipcw")


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4)):
    df = load_warehouse(PATH, keep_censored=True)
    X = build_features(df)
    y = df["y_cost_usd"].to_numpy(dtype=float)  # recovered truth (masked below)
    cens = df["censored"].to_numpy(dtype=bool)
    bound = (df["budget_cost_usd"] - df["spent_cost_usd"]).to_numpy(dtype=float)

    # how tight is the censoring bound, really? (uses recovered truth; report only)
    bound_valid = float(np.mean(y[cens] > bound[cens]))
    print(f"censored rows: {cens.mean():.0%}; bound y > budget−spent holds on "
          f"{bound_valid:.1%} of them (recovered truth)")

    rows = []
    for seed in seeds:
        masks = group_split(df, seed=seed)
        tr, ca, te = masks["train"], masks["cal"], masks["test"]
        tr_unc = tr & ~cens  # deployment could not train on censored labels
        reg = fit_remaining_regressor(X[tr_unc], y[tr_unc])
        clf = fit_feasibility(X[tr], ~cens[tr])  # P(uncensored | x)

        pred_ca, pred_te = reg.predict(X[ca]), reg.predict(X[te])
        ca_unc, ca_cen = ca & ~cens, ca & cens
        s_unc = y[ca_unc] - reg.predict(X[ca_unc])
        s_cens_lb = bound[ca_cen] - reg.predict(X[ca_cen])
        p_unc = clf.predict_proba(X[ca_unc])[:, 1]

        for method in METHODS:
            qhat = upper_qhat(s_unc, s_cens_lb, ALPHA, method,
                              p_uncensored=p_unc if method == "ipcw" else None)
            hi = pred_te + qhat
            cov_all = float(np.mean(y[te] <= hi))
            cov_cens = float(np.mean(y[te & cens] <= hi[cens[te]]))
            cov_unc = float(np.mean(y[te & ~cens] <= hi[~cens[te]]))
            rows.append({"seed": seed, "method": method, "qhat": qhat,
                         "cov_all": cov_all, "cov_censored": cov_cens,
                         "cov_uncensored": cov_unc})

    table = (pd.DataFrame(rows).groupby("method", sort=False)
             .agg(cov_all=("cov_all", "mean"), cov_censored=("cov_censored", "mean"),
                  cov_uncensored=("cov_uncensored", "mean"),
                  qhat_median=("qhat", "median")).reset_index())
    os.makedirs("tables", exist_ok=True)
    table.to_csv("tables/censored_upper.csv", index=False)
    print(table.to_string(index=False))
    print("\nwrote tables/censored_upper.csv")
    return table


if __name__ == "__main__":
    main()
