"""scripts/run_closed_loop.py — item 9: the counterfactual-free (closed-loop) limitation.

Toy, SYNTHETIC demonstration (no BAGEN data) of the feedback loop that logged evaluation
cannot see. When the guard aborts doomed runs in deployment, those runs never complete,
so their labels never enter the calibration stream. The calibration set becomes a
self-selected sample of only the easy runs the guard let finish; its residual quantile
shrinks; and its coverage on the FULL population it still faces drifts below nominal —
while the guard, measuring coverage only on its self-selected stream, believes it is fine.

Closed-loop (calibrate on completed runs only) vs an oracle that counterfactually sees
every run's label. Numbers are REAL (the sim runs); the DGP is synthetic by design and
tuned only to make the mechanism visible.

Usage: python scripts/run_closed_loop.py     (writes figures/closed_loop.png)
"""
import os

import numpy as np

ALPHA = 0.1
BUDGET = 220.0          # pred(d) = 100 + 200 d ; guard aborts when predicted spend >= budget (d >= 0.6)
KEEP_D = (BUDGET - 100.0) / 200.0


def _pred(d):
    return 100.0 + 200.0 * d


def _draw(rng, n):
    d = rng.uniform(0.0, 1.0, n)
    y = _pred(d) + rng.normal(0.0, 10.0 + 150.0 * d)   # heteroscedastic: hard runs, big spread
    return d, y


def simulate(closed_loop: bool, n_rounds: int = 25, batch: int = 60, seed: int = 0):
    rng = np.random.default_rng(seed)
    d_test, y_test = _draw(rng, 2000)                  # fixed FULL-population test set
    r_test = y_test - _pred(d_test)
    keep_test = d_test < KEEP_D                         # the easy runs the guard would keep
    d0, y0 = _draw(rng, 60)
    cal_r = list(y0 - _pred(d0))                        # seed calibration (full population)

    cov_full, cov_selfsel, qhats = [], [], []
    for _ in range(n_rounds):
        cal = np.asarray(cal_r)
        lvl = min(1.0, np.ceil((len(cal) + 1) * (1 - ALPHA)) / len(cal))
        qhat = float(np.quantile(cal, lvl, method="higher"))
        qhats.append(qhat)
        cov_full.append(float(np.mean(r_test <= qhat)))               # the TRUTH (full pop)
        cov_selfsel.append(float(np.mean(r_test[keep_test] <= qhat)))  # what the guard measures
        d, y = _draw(rng, batch)
        r = y - _pred(d)
        aborted = _pred(d) >= BUDGET                                   # guard aborts predicted doom
        keep = (~aborted) if closed_loop else np.ones(batch, dtype=bool)
        cal_r.extend(r[keep].tolist())
    return np.array(cov_full), np.array(cov_selfsel), np.array(qhats)


def main(seeds: tuple[int, ...] = (0, 1, 2, 3, 4)):
    cl = np.mean([simulate(True, seed=s)[0] for s in seeds], axis=0)
    cl_self = np.mean([simulate(True, seed=s)[1] for s in seeds], axis=0)
    orc = np.mean([simulate(False, seed=s)[0] for s in seeds], axis=0)
    rounds = np.arange(len(cl))
    print(f"final full-population coverage: closed-loop {cl[-1]:.3f} vs oracle {orc[-1]:.3f} "
          f"(nominal {1 - ALPHA:.2f}); guard's self-measured {cl_self[-1]:.3f}")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs("figures", exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.6, 4.4), constrained_layout=True)
    ax.plot(rounds, orc, marker="o", ms=4, lw=2, color="#1baf7a",
            label="oracle (sees every label): true full-pop coverage")
    ax.plot(rounds, cl, marker="o", ms=4, lw=2, color="#e34948",
            label="closed-loop: TRUE full-pop coverage")
    ax.plot(rounds, cl_self, marker="o", ms=4, lw=2, ls="--", color="#8B93A1",
            label="closed-loop: guard's self-measured coverage")
    ax.axhline(1 - ALPHA, color="#4A5361", lw=1.2, ls=":")
    ax.set_xlabel("deployment round")
    ax.set_ylabel("upper-bound coverage")
    ax.set_ylim(0.5, 1.02)
    ax.set_title("Closed-loop feedback (toy, synthetic): aborting doomed runs self-selects the\n"
                 "calibration stream — true coverage drifts down while the guard thinks it is fine")
    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    fig.savefig("figures/closed_loop.png", dpi=200)
    print("wrote figures/closed_loop.png")
    return cl, orc, cl_self


if __name__ == "__main__":
    main()
