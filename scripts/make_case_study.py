#!/usr/bin/env python3
"""Case study: one Sokoban rollout, turn by turn: agent self-report vs Budget Guard.

Selection rule, fixed before looking at any rollout: the FIRST rollout in the seed-0
test stream (lowest rollout_index) of the Claude Opus 4.7 Sokoban run. No hand-picking.
At every prefix of that rollout the script records the agent's own remaining-token
interval, the guard's split-CQR (offline) and windowed-CQR (online) intervals, and
the true remaining spend, plus whether spend-so-far plus the guard's upper bound fits
inside the 2,500-token budget, which is the reading a deployer would make.

So the example cannot stand alone, the script also tallies EVERY rollout in the same
test split: on how many does the guard cover a larger / equal / smaller fraction of
prefixes than the self-report. The paper draft quotes that tally next to the example.

Writes tables/case_study_sokoban.csv (per-turn rows), tables/case_study_sokoban.tex
(table body), tables/case_study_sokoban_tally.csv and figures/case_study_sokoban.png.

Usage: python scripts/make_case_study.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from budget_guard.conformal import DEFAULT_ALPHA, cqr_split, windowed_cqr  # noqa: E402
from budget_guard.data import ENVS, load_agent_estimates, load_env  # noqa: E402
from budget_guard.economic import calibrate_threshold, evaluate_stopping, fit_feasibility  # noqa: E402
from budget_guard.features import build_xy  # noqa: E402
from budget_guard.split import group_split  # noqa: E402

ENV = "sokoban"
SEED = 0
ROLLOUT = None  # None = first rollout in the seed-0 test stream; an int overrides for inspection
DELTA = 0.10    # false-abort tolerance for the gate, the paper's headline operating point


def main() -> pd.DataFrame:
    df, _ = load_env(ENV)
    budget = ENVS[ENV]["max_ctx"]
    est = load_agent_estimates(ENV)
    X, y, groups = build_xy(df)
    m = group_split(df, seed=SEED)
    tr, ca, te = m["train"], m["cal"], m["test"]
    lo_s, hi_s = cqr_split(X[tr], y[tr], X[ca], y[ca], X[te], alpha=DEFAULT_ALPHA)[:2]
    lo_w, hi_w = windowed_cqr(X[tr], y[tr], X[ca], y[ca], X[te], y[te],
                              alpha=DEFAULT_ALPHA, groups=groups[te])[:2]
    # Feasibility gate, fitted and calibrated exactly as in run_economic.py: abort a
    # run at the first prefix whose score drops below tau, with tau set so that at
    # most DELTA of feasible calibration runs would be aborted.
    gate = fit_feasibility(X[tr], df.loc[tr, "can_finish"])
    s_cal = gate.predict_proba(X[ca])[:, 1]
    s_te = gate.predict_proba(X[te])[:, 1]
    tau = calibrate_threshold(df[ca], s_cal, DELTA)
    gate_split = evaluate_stopping(df[te], s_te, tau)
    t = df[te].copy()
    t["split_lo"], t["split_hi"], t["win_lo"], t["win_hi"] = lo_s, hi_s, lo_w, hi_w
    t["gate_score"] = s_te
    t = t.merge(est, on="sample_id", how="left")
    for col, lo, hi in (("agent", "agent_lo", "agent_hi"), ("split", "split_lo", "split_hi"),
                        ("win", "win_lo", "win_hi")):
        t[f"{col}_cov"] = (t[lo] <= t["y"]) & (t["y"] <= t[hi])   # NaN self-report counts as a miss
    per = (t.groupby("rollout_index")
             .agg(n_prefixes=("k", "size"), agent=("agent_cov", "mean"),
                  split=("split_cov", "mean"), win=("win_cov", "mean"),
                  success=("rollout_success", "first")).sort_index())
    tally = pd.DataFrame([{"method": m, "guard_higher": int((per[m] > per.agent).sum()),
                           "equal": int((per[m] == per.agent).sum()),
                           "agent_higher": int((per[m] < per.agent).sum()),
                           "n_rollouts": len(per)} for m in ("split", "win")])

    rollout = int(per.index.min()) if ROLLOUT is None else ROLLOUT
    assert rollout in set(t["rollout_index"]), "ROLLOUT is not in the seed-0 test split"
    r = t[t["rollout_index"] == rollout].sort_values("k").reset_index(drop=True)

    out = pd.DataFrame({
        "turn": r["k"].astype(int),
        "tokens_spent": r["tokens_so_far"].astype(int),
        "true_remaining": r["y"].astype(int),
        "agent_lo": r["agent_lo"].astype(int), "agent_hi": r["agent_hi"].astype(int),
        "split_lo": r["split_lo"].round().astype(int), "split_hi": r["split_hi"].round().astype(int),
        "win_lo": r["win_lo"].round().astype(int), "win_hi": r["win_hi"].round().astype(int),
        "gate_score": r["gate_score"].round(3),
    })
    out["gate_decision"] = np.where(out["gate_score"] >= tau, "continue", "abort")
    out["agent_covers"] = (out.agent_lo <= out.true_remaining) & (out.true_remaining <= out.agent_hi)
    out["split_covers"] = (out.split_lo <= out.true_remaining) & (out.true_remaining <= out.split_hi)
    out["win_covers"] = (out.win_lo <= out.true_remaining) & (out.true_remaining <= out.win_hi)
    out["spent_plus_split_hi"] = out.tokens_spent + out.split_hi
    out["fits_budget_at_0.90"] = out["spent_plus_split_hi"] <= budget
    out.attrs.update(env=ENV, seed=SEED, rollout=rollout, budget=budget, tau=float(tau), delta=DELTA,
                     total_turns=int(r["N"].iloc[0]), success=bool(r["rollout_success"].iloc[0]))

    os.makedirs("tables", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    out.to_csv(f"tables/case_study_{ENV}.csv", index=False)
    tally.to_csv(f"tables/case_study_{ENV}_tally.csv", index=False)
    pd.DataFrame([{"delta": DELTA, "tau": float(tau), **gate_split}]).to_csv(
        f"tables/case_study_{ENV}_gate.csv", index=False)

    # LaTeX rows (booktabs body only; the draft supplies the header and caption).
    def mark(ok):
        return r"\checkmark" if ok else r"$\times$"
    lines = []
    for _, q in out.iterrows():
        lines.append(f"{q.turn} & {q.tokens_spent:,} & {q.true_remaining:,} & "
                     f"[{q.agent_lo:,}, {q.agent_hi:,}] {mark(q.agent_covers)} & "
                     f"[{q.split_lo:,}, {q.split_hi:,}] {mark(q.split_covers)} & "
                     f"{q.spent_plus_split_hi:,} {'$\\leq$' if q['fits_budget_at_0.90'] else '$>$'} {budget:,} & "
                     f"{q.gate_score:.2f} {q.gate_decision} \\\\")
    with open(f"tables/case_study_{ENV}.tex", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.2, 3.0), constrained_layout=True)
    k = out["turn"].to_numpy()
    w = 0.26
    ax.bar(k - w / 2, out.agent_hi - out.agent_lo, bottom=out.agent_lo, width=w,
           color="#8B93A1", label="agent self-report interval")
    ax.bar(k + w / 2, out.split_hi - out.split_lo, bottom=out.split_lo, width=w,
           color="#1baf7a", label="Budget Guard interval (split-CQR)")
    ax.plot(k, out.true_remaining, "o-", color="#1C2128", ms=5, lw=1, label="true remaining tokens")
    ax.plot(k, budget - out.tokens_spent, "s--", color="#e34948", ms=4, lw=1,
            label=f"budget left ({budget:,} minus spent)")
    ax.set_xticks(k, [f"{turn}\ngate {sc:.2f}: {dec}" for turn, sc, dec in
                      zip(k, out["gate_score"], out["gate_decision"])], fontsize=8)
    ax.set_xlabel("turn")
    ax.set_ylabel("remaining tokens")
    ax.set_ylim(0, None)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    fig.savefig(f"figures/case_study_{ENV}.png", dpi=200, bbox_inches="tight")

    print(out.to_string(index=False))
    print(f"\nrollout {rollout} (first in seed-{SEED} test stream): {out.attrs['total_turns']} turns, "
          f"success={out.attrs['success']}, budget={budget}, gate tau={tau:.3f} at delta={DELTA}")
    print("\ngate over the whole test split at this delta:", {k: (round(v, 3) if isinstance(v, float) else v)
                                                              for k, v in gate_split.items()})
    print("\nper-rollout tally over the whole test split (fraction of prefixes covered):")
    print(tally.to_string(index=False))
    print(f"\nwrote tables/case_study_{ENV}.csv, tables/case_study_{ENV}.tex, "
          f"tables/case_study_{ENV}_tally.csv, tables/case_study_{ENV}_gate.csv, figures/case_study_{ENV}.png")
    return out


if __name__ == "__main__":
    main()
