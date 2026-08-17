#!/usr/bin/env python3
"""Verify every quantitative claim in the paper against the generated tables.

Companion to check_headline_numbers.py: that script guards the project's headline
claims; this one covers all 35 quantitative statements in the submission, section
by section. Each check names the paper location, so a failure points straight at
the sentence to fix. Rounding convention: the paper quotes 2dp unless noted.

Usage: python scripts/check_paper_numbers.py   (regenerate tables/ first: make repro)
"""
import sys
from pathlib import Path

import pandas as pd

T = Path(__file__).resolve().parent.parent / "tables"
results = []


def check(loc, claim, ok, detail=""):
    results.append((ok, loc, claim, detail))


def r2(x):
    return round(float(x), 2)


cov = pd.read_csv(f"{T}/coverage.csv")
allr = pd.read_csv(f"{T}/allruns.csv")
tenv = pd.read_csv(f"{T}/transfer_env.csv")
tswb = pd.read_csv(f"{T}/transfer_swebench.csv")
twh = pd.read_csv(f"{T}/transfer_warehouse.csv")
mr = pd.read_csv(f"{T}/multiresource.csv")
cen = pd.read_csv(f"{T}/censored_upper.csv")
gat = pd.read_csv(f"{T}/gated_intervals.csv")
cond = pd.read_csv(f"{T}/conditional_coverage.csv")
ab = pd.read_csv(f"{T}/abort_frontier_warehouse.csv")
cop = pd.read_csv(f"{T}/cost_of_pass_warehouse.csv")


def C(env, method, col="coverage"):
    return cov[(cov.env == env) & (cov.method == method)][col].iloc[0]


# --- §5.1 / abstract ---
check("§5.1", "agent 0.51/0.23/0.35",
      [r2(C(e, "agent self-report")) for e in ("sokoban", "searchr1", "swebench")] == [0.51, 0.23, 0.35])
core = cov[cov.method.isin(["split-CQR", "ACI-CQR", "windowed-CQR", "DtACI"])]
check("§5.1+abstract", "four conformal methods span 0.87–0.96",
      (r2(core.coverage.min()), r2(core.coverage.max())) == (0.87, 0.96),
      f"min {core.coverage.min():.4f} max {core.coverage.max():.4f}")
onl = cov[cov.method.isin(["ACI-CQR", "windowed-CQR", "DtACI"])]
check("§5.1", "online methods span 0.87–0.94",
      (r2(onl.coverage.min()), r2(onl.coverage.max())) == (0.87, 0.94))
check("§5.1", "DtACI searchr1 0.94 @ 16% unbounded",
      r2(C("searchr1", "DtACI")) == 0.94 and round(C("searchr1", "DtACI", "frac_unbounded") * 100) == 16)
check("§5.1", "ACI swebench 0.94 @ 14% unbounded",
      r2(C("swebench", "ACI-CQR")) == 0.94 and round(C("swebench", "ACI-CQR", "frac_unbounded") * 100) == 14)
check("§5.1", "windowed 0.92/0.92/0.87 @ 0% unbounded",
      [r2(C(e, "windowed-CQR")) for e in ("sokoban", "searchr1", "swebench")] == [0.92, 0.92, 0.87]
      and all(C(e, "windowed-CQR", "frac_unbounded") == 0 for e in ("sokoban", "searchr1", "swebench")))
check("§5.1", "conformalized-agent 0.93/0.90/0.97",
      [r2(C(e, "conformalized-agent")) for e in ("sokoban", "searchr1", "swebench")] == [0.93, 0.90, 0.97])
check("§5.1", "split-absres 0.89/0.94/0.95",
      [r2(C(e, "split-absres")) for e in ("sokoban", "searchr1", "swebench")] == [0.89, 0.94, 0.95])
w, d, s = allr["windowed-CQR"], allr["DtACI"], allr["split-CQR"]
check("§5.1+abstract", "breadth: windowed ≥0.85 in 18/19, ≥0.90 in 11/19",
      ((w >= 0.85).sum(), (w >= 0.90).sum()) == (18, 11))
check("§5.1", "DtACI 14 and 8; split-CQR 14 and 12",
      ((d >= 0.85).sum(), (d >= 0.90).sum(), (s >= 0.85).sum(), (s >= 0.90).sum()) == (14, 8, 14, 12))

# --- §5.2 cross-env ---
def TE(env, m, col="coverage"):
    return tenv[(tenv.target_env == env) & (tenv.method == m)][col].iloc[0]

check("§5.2", "frozen swebench 0.10 [0.06, 0.15]",
      r2(TE("swebench", "split-CQR (frozen)")) == 0.10
      and r2(TE("swebench", "split-CQR (frozen)", "ci_lo")) == 0.06
      and r2(TE("swebench", "split-CQR (frozen)", "ci_hi")) == 0.15)
check("§5.2", "frozen searchr1 0.51 [0.40, 0.62]",
      r2(TE("searchr1", "split-CQR (frozen)")) == 0.51
      and r2(TE("searchr1", "split-CQR (frozen)", "ci_lo")) == 0.40
      and r2(TE("searchr1", "split-CQR (frozen)", "ci_hi")) == 0.62)
check("§5.2", "windowed recovers 0.80 / 0.71 @ 0% unbounded",
      r2(TE("swebench", "windowed-CQR")) == 0.80 and r2(TE("searchr1", "windowed-CQR")) == 0.71
      and TE("swebench", "windowed-CQR", "frac_unbounded") == 0 and TE("searchr1", "windowed-CQR", "frac_unbounded") == 0)
ad = tenv[tenv.method.isin(["ACI-CQR", "DtACI"])]
check("§5.2", "ACI/DtACI up to 0.91 at 60–88% unbounded",
      r2(ad.coverage.max()) == 0.91
      and round(ad.frac_unbounded.min() * 100) == 60 and round(ad.frac_unbounded.max() * 100) == 88)

# --- §5.2 model swap ---
fz = tswb[tswb.method == "split-CQR (frozen)"]
wd = tswb[tswb.method == "windowed-CQR"]
check("§5.2", "model swap frozen 0.64–0.89 (std 0.12–0.22)",
      (r2(fz.coverage.min()), r2(fz.coverage.max())) == (0.64, 0.89)
      and (round(fz.cov_std.min(), 2), round(fz.cov_std.max(), 2)) == (0.12, 0.22))
check("§5.2", "model swap windowed 0.66–0.89 (std 0.006–0.011)",
      (r2(wd.coverage.min()), r2(wd.coverage.max())) == (0.66, 0.89)
      and (round(wd.cov_std.min(), 3), round(wd.cov_std.max(), 3)) == (0.006, 0.011))
aci = tswb[tswb.method == "ACI-CQR"]
dt = tswb[tswb.method == "DtACI"]
check("§5.2", "swap ACI 0.87–0.91 @ 22–61%; DtACI 0.41–0.83",
      (r2(aci.coverage.min()), r2(aci.coverage.max())) == (0.87, 0.91)
      and (round(aci.frac_unbounded.min() * 100), round(aci.frac_unbounded.max() * 100)) == (22, 61)
      and (r2(dt.coverage.min()), r2(dt.coverage.max())) == (0.41, 0.83))

# --- §5.2 warehouse swap ---
j = twh[twh.resource == "ALL (joint)"]
fb = j[j.method == "frozen Bonferroni"]
fc = j[j.method == "frozen joint copula"]
aj = j[j.method == "adaptive joint copula"]
check("§5.2", "warehouse frozen Bonferroni 0.66–0.79",
      (r2(fb.coverage.min()), r2(fb.coverage.max())) == (0.66, 0.79))
check("§5.2", "frozen copula 0.56–0.68",
      (r2(fc.coverage.min()), r2(fc.coverage.max())) == (0.56, 0.68))
check("§5.2+abstract", "adaptive joint 0.86–0.88 overall, 0.87–0.90 late",
      (r2(aj.coverage.min()), r2(aj.coverage.max())) == (0.86, 0.88)
      and (r2(aj.late_coverage.min()), r2(aj.late_coverage.max())) == (0.87, 0.90))
widths = aj.ci_hi - aj.ci_lo
check("§5.2", "adaptive CIs ~0.09 wide, all contain 0.90, widest fails to exclude 0.82",
      abs(widths.mean() - 0.09) < 0.02
      and ((aj.ci_lo <= 0.90) & (0.90 <= aj.ci_hi)).all()
      and (aj.ci_lo.min() <= 0.82) and (aj.ci_lo > 0.82).sum() == 3)

# --- §5.3 conditional ---
def CD(env, m, sl, col="coverage"):
    return cond[(cond.env == env) & (cond.method == m) & (cond.slice == sl)][col].iloc[0]

check("§5.3", "sokoban split 0.92 → 0.86/0.93/0.96 by depth; Mondrian k=1 0.93",
      r2(CD("sokoban", "split-CQR", "marginal")) == 0.92
      and [r2(CD("sokoban", "split-CQR", s)) for s in ("k=1", "k=2", "k>=3")] == [0.86, 0.93, 0.96]
      and r2(CD("sokoban", "Mondrian-CQR", "k=1")) == 0.93)
check("§5.3", "searchr1 marginal 0.90→0.89, k=1 0.91→0.89 under Mondrian",
      r2(CD("searchr1", "split-CQR", "marginal")) == 0.90
      and r2(CD("searchr1", "Mondrian-CQR", "marginal")) == 0.89
      and r2(CD("searchr1", "split-CQR", "k=1")) == 0.91
      and r2(CD("searchr1", "Mondrian-CQR", "k=1")) == 0.89)

# --- §5.4 joint ---
check("§5.4", "agent 0.42 / independent 0.80 / Bonferroni 0.95 / copula 0.89",
      [r2(mr[mr.scheme == s].joint.iloc[0]) for s in
       ("agent self-report", "independent", "bonferroni", "copula")] == [0.42, 0.80, 0.95, 0.89])
check("§5.4", "time_weeks margin ≈3e-4 weeks; scheme coverage 0.99–1.00",
      abs(cen[(cen.resource == "time_weeks") & (cen.method == "drop")].qhat_median.iloc[0] - 3e-4) < 1e-4
      and mr[mr.scheme != "agent self-report"].time_weeks.min() >= 0.99)

# --- §5.5 censored ---
cd_ = cen[cen.resource == "cost_usd"]
check("§5.5", "cost drop: feasible 0.88, censored-binding 0.50; resource_bound 0.46",
      r2(cd_[cd_.method == "drop"].cov_feasible.iloc[0]) == 0.88
      and r2(cd_[cd_.method == "drop"].cov_cens_binding.iloc[0]) == 0.50
      and r2(cd_[cd_.method == "resource_bound"].cov_cens_binding.iloc[0]) == 0.46)
g = gat[(gat.resource == "cost_usd") & (gat.delta == 0.1)]
check("§5.5", "gated @δ=0.1: cov 0.92, catch 72%, kept 80%, false-abort 0.10",
      r2(g.cov_kept_feasible.iloc[0]) == 0.92 and round(g.gate_catch_doomed.iloc[0] * 100) == 72
      and round(g.kept_frac.iloc[0] * 100) == 80 and r2(g.false_abort_feasible.iloc[0]) == 0.10)

# --- §5.6 economics ---
gd = ab[(ab.rule == "guard") & (ab.param == 0.1)]
check("§5.6+abstract", "86.3% doomed spend saved @ 0 false aborts (δ=0.1)",
      round(gd.doomed_savings_frac.iloc[0] * 1000) / 10 == 86.3 and gd.false_abort_rate.iloc[0] == 0.0)
check("§5.6+abstract", "CoP $1.61M → $0.87M, passes 15.6, retention 1.0",
      round(cop[cop.policy == "agent alone"].cost_of_pass_usd.iloc[0] / 1e4) == 161
      and round(cop[(cop.policy == "guard") & (cop.param == 0.1)].cost_of_pass_usd.iloc[0] / 1e4) == 87
      and cop[(cop.policy == "guard") & (cop.param == 0.1)].pass_rate_retained.iloc[0] == 1.0)
caps = ab[ab.rule == "hard cap ($ spent)"]
tight = caps[caps.false_abort_rate == 0]
check("§5.6", "tightest full-retention cap saves 0.2%; 4%→19% false; 15%→55%",
      round(tight.doomed_savings_frac.max() * 1000) / 10 == 0.2
      and round(caps[abs(caps.doomed_savings_frac - 0.04) < 0.005].false_abort_rate.iloc[0] * 100) == 19
      and round(caps[abs(caps.doomed_savings_frac - 0.15) < 0.005].false_abort_rate.iloc[0] * 100) == 55)
g3 = ab[(ab.rule == "guard") & (ab.param == 0.3)]
check("§5.6", "δ=0.3: ~+1.4pt savings at 4.2% false aborts",
      round((g3.doomed_savings_frac.iloc[0] - gd.doomed_savings_frac.iloc[0]) * 1000) / 10 == 1.4
      and round(g3.false_abort_rate.iloc[0] * 1000) / 10 == 4.2)

# --- §6 widths ---
def NW(env, m):
    return C(env, m, "normalized_width")

check("§6", "sokoban windowed 22% narrower than constant (0.92 vs 0.88)",
      round((1 - NW("sokoban", "windowed-CQR") / NW("sokoban", "constant-quantile")) * 100) == 22
      and r2(C("sokoban", "windowed-CQR")) == 0.92 and r2(C("sokoban", "constant-quantile")) == 0.88)
check("§6", "searchr1 constant 19% narrower (0.77 vs guard 0.92)",
      round((1 - NW("searchr1", "constant-quantile") / NW("searchr1", "windowed-CQR")) * 100) == 19
      and r2(C("searchr1", "constant-quantile")) == 0.77)
check("§6", "swebench guard 55% narrower (0.87 vs 0.92)",
      round((1 - NW("swebench", "windowed-CQR") / NW("swebench", "constant-quantile")) * 100) == 55
      and r2(C("swebench", "constant-quantile")) == 0.92)
agrows = twh[(twh.method == "agent self-report") & (twh.resource == "time_weeks")]
check("§6", "agent baseline scored on 472–528 of 640 rows",
      (int(agrows.n_test.min()), int(agrows.n_test.max())) == (472, 528))

# --- report ---
fails = [x for x in results if not x[0]]
for ok, loc, claim, detail in results:
    mark = "PASS" if ok else "FAIL"
    print(f"{mark}  {loc:14s} {claim}" + (f"   [{detail}]" if detail and not ok else ""))
print(f"\n{len(results) - len(fails)}/{len(results)} draft claims match the generated tables.")
sys.exit(1 if fails else 0)
