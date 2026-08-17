# budget-guard

Training-free, distribution-free **budget guards** for long-horizon LLM agents. Wrap any
agent loop in a monitor that returns, at every turn, a *calibrated* prediction interval on
the resources the run still needs (tokens / dollars / time) plus an abort decision — using
online conformal prediction, with no fine-tuning, no logits, and no GPU.

Built on the logged rollouts from **BAGEN** (arXiv:2606.00198). Results summary:
[`docs/results_explained.md`](docs/results_explained.md).

```python
from budget_guard import BudgetGuard

guard = BudgetGuard.from_logs(completed_runs, budget=7060)   # calibrate once, no training
guard.reset()
for turn_tokens in agent_turn_usage_stream():
    step = guard.step(turn_tokens)
    print(f"turn {step.k}: remaining budget in [{step.lo:.0f}, {step.hi:.0f}]")
    if step.abort:          # projected spend exceeds the budget
        break
else:
    guard.observe()         # run finished cleanly: fold its labels back into calibration
```

## Install

```bash
pip install -e .
python examples/quickstart.py     # runnable demo, no data needed
```

Dependencies are numpy / pandas / lightgbm / scikit-learn. CPU only.

> **macOS:** LightGBM needs an OpenMP runtime that its PyPI wheel does not ship, so
> `import lightgbm` fails with `dlopen ... Library not loaded: @rpath/libomp.dylib`.
> Fix with `conda install -c conda-forge llvm-openmp` or `brew install libomp`. Linux
> wheels use the system `libgomp` and need nothing extra. This is a system library, so
> it cannot be expressed in `requirements.txt` or `pyproject.toml`.

## Reproduce the paper

Everything runs inside a digest-pinned container, so results do not depend on which
machine you are sitting at. Requires Docker.

```bash
python scripts/fetch_bagen.py   # ~2.7 GB, pinned dataset revision
make repro-all                  # regenerate EVERY figure and table, then verify
```

`make repro-all` is the run-all button: it runs every experiment, draws all 20 figures
and 23 tables, and then machine-verifies the paper's numbers against what it just
generated — 11 headline claims and all 35 quantitative claims in the paper. It exits
non-zero if any claim no longer matches.

| command | what it does |
|---|---|
| `make repro-all` | **everything**: all experiments, all figures/tables, both checkers |
| `make repro-paper` | just the set the paper embeds (faster), plus both checkers |
| `make repro` | the headline figures/tables only |
| `make test` | the test suite inside the container |
| `make check-numbers` | verify the paper's headline numbers against `tables/` |
| `make doctor` | diagnose why a run differs (commit, data, package versions, tables) |
| `make clean` | delete generated figures/ and tables/ so the next run starts fresh |
| `make help` | list every target |

**Getting different numbers?** Run `make doctor` first. It checks the things that
actually cause divergence — running an old commit, an incomplete BAGEN download (the
experiments silently skip the model-swap and breadth runs on partial data), package
versions that differ from the lockfile, and unexpected table row counts — and each
failure names its own fix.

The container reproduces reported numbers bit-identically across host architectures;
interval widths can differ by one ULP (2.2e-16), the floating-point floor. Dependency
changes go through `requirements-repro.in` + `make lock`, never by editing
`requirements.lock.txt`; CI fails if the two drift apart.

## Use your own data

The extractor turns rollout JSON into the `(prefix, x_t, y_t)` table the guard
calibrates on:

```bash
python budget_guard/extract.py                      # bundled sample
python budget_guard/extract.py /path/to/dialogues.json
```

It prints the table and runs invariant checks. Field definitions:
[`budget_guard/data_dictionary.md`](budget_guard/data_dictionary.md). To point at a local
BAGEN checkout, set `BAGEN_DIR` (defaults to `../BAGEN`).

## How it works

At turn *k* the guard sees only the prefix — resources spent so far, burn rate, recent
per-turn usage, and the agent's own estimate when it emits one. Gradient-boosted quantile
regression predicts the remaining requirement; conformal calibration turns that into an
interval with a coverage guarantee. Calibration splits are always **by rollout, never by
prefix** (prefixes of one rollout share its final total, so splitting them apart leaks
the answer), and online methods only learn from rollouts that have *finished* — the label
does not exist before then.

- **Offline:** split conformal, CQR, Mondrian (per-turn-depth) CQR
- **Online, for deployment shift:** ACI, DtACI, windowed-CQR
- **Several budgets at once:** Bonferroni and empirical-copula joint intervals
- **Runs that can no longer finish:** censoring-aware upper bounds behind a feasibility
  gate, giving a *selective* guarantee (coverage conditional on passing the gate)
- **Stopping:** abort when the feasibility score crosses a threshold calibrated so the
  per-run false-abort rate is at most δ

## Layout

```
budget_guard/    # the library and the experiment drivers
  extract.py     # rollout JSON -> (prefix, x_t, y_t)
  guard.py       # the BudgetGuard wrapper
  conformal.py   # split/CQR/Mondrian + ACI/DtACI/windowed-CQR
  multiresource.py, censored.py, economic.py
  run_*.py       # one driver per experiment
scripts/         # data fetch, figure generators, number checkers, doctor
tables/          # generated results (committed, so reported numbers are diffable)
docs/            # results summary
paper/           # related-work note
```

Generated figures and the BAGEN data are gitignored by design — regenerate them with
`make repro-all`.

## License

MIT. See [LICENSE](LICENSE).
