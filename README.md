# budget-guard

Distribution-free, multi-resource **budget guards** for long-horizon agents: a training-free
wrapper that outputs calibrated prediction intervals on an agent's *remaining budget*
(tokens / $ / time) via online conformal prediction. Built on the logged rollouts from
**BAGEN** (arXiv:2606.00198).

**CPU-only Python** — no `verl`, no `vllm`, no GPU. Reproduce reported numbers with
the pinned container (`make repro` below).

## Setup

```bash
conda create -n budget python=3.12 -c conda-forge --override-channels -y
conda activate budget
conda install -c conda-forge llvm-openmp -y   # macOS: required by lightgbm, see below
pip install -r requirements.txt
```

> **macOS: LightGBM needs an OpenMP runtime.** The PyPI `lightgbm` wheel links against
> `@rpath/libomp.dylib` but does not ship it, so without one `import lightgbm` fails with
> a `dlopen ... Library not loaded: @rpath/libomp.dylib` error that names no package.
> `conda install -c conda-forge llvm-openmp` (or `brew install libomp`) fixes it. Linux
> wheels use the system `libgomp`, which is already present on most distributions — and
> the container installs it explicitly. There is no pip-only fix: this is a system
> library, so it cannot be expressed in `requirements.txt` or `pyproject.toml`.

## Reproducible environment (recommended for reproducing reported numbers)

The commands above install into whatever OS and CPU architecture you happen to be on.
For regenerating reported numbers, use the pinned container instead — it fixes the OS,
the architecture, the full transitive dependency tree (hash-verified), and the thread
count that floating-point summation order depends on:

```bash
make build          # digest-pinned python:3.12-slim, linux/amd64
make test           # full suite inside the container
make repro          # regenerate figures/ + tables/, then re-check notes/ claims
make check-numbers  # verify notes/ headline numbers against tables/ (no Docker needed)
```

Verified 2026-08-01: the container reproduces `tables/transfer_env.csv` from a macOS
arm64 host run with every coverage, CI bound, and unbounded-fraction **bit-identical**;
a single `normalized_width` differs by 1 ULP (2.2e-16), the floor for cross-architecture
float arithmetic. See `Dockerfile` for why each pin is there.

Dependency changes go through `requirements-repro.in` + `make lock`, never by editing
`requirements.lock.txt` directly; CI fails if the two drift apart.

## Point at the BAGEN data

The extractor reads BAGEN rollouts. Set `BAGEN_DIR`, or keep the `BAGEN` repo as a sibling
folder (the default is `../BAGEN`):

```bash
export BAGEN_DIR=/path/to/BAGEN   # optional; defaults to ../BAGEN
```

## Run the Week-1 extractor

```bash
python budget_guard/extract.py                  # uses the bundled _smoke sample
python budget_guard/extract.py /path/to/dialogues.json
```

It prints the `(x_t, y_t)` table and runs invariants. Field definitions:
[`budget_guard/data_dictionary.md`](budget_guard/data_dictionary.md).

## Reproduce the transfer experiments

Fetch the exact pinned BAGEN revision used by the reported tables, then run the internal
(token) and external (Warehouse) model-swap experiments:

```bash
python scripts/fetch_bagen.py
python -m budget_guard.run_transfer
python -m budget_guard.run_transfer_warehouse
```

The Warehouse experiment compares frozen baselines with rollout-safe adaptive joint
calibration: all prefixes in a rollout are predicted first, and the three-resource error
window updates only after that rollout finishes. It writes aggregate and per-seed CSVs plus
`figures/transfer_warehouse.png`. Data and generated artifacts are gitignored by design.

## Generic loop-engineering API (development)

`LoopBudgetGuard` is the task-neutral resource-control layer. It works with any
long-running loop whose additive resources can be measured per step and whose naturally
completed runs reveal final totals:

```python
from budget_guard import LoopBudgetGuard, ResourceSpec

resources = (
  ResourceSpec("tokens", "tokens", 8_000),
  ResourceSpec("usd", "USD", 3.00),
  ResourceSpec("seconds", "seconds", 600),
)

# completed_traces use the framework-neutral RunStart/StepUsage/RunFinish schema
guard = LoopBudgetGuard.from_traces(completed_traces)
guard.start("task-123", resources, {"task_type": "coding"})

decision = guard.after_step(
  {"tokens": 420, "usd": 0.06, "seconds": 18},
  {"tests_passing": 7},
)
print(decision.action, decision.intervals, decision.reasons)

if decision.should_stop:
  guard.abort(decision.action.value)  # never invents an unobserved completion label
else:
  guard.finish(success=True)          # updates only after natural completion
```

The estimator and intervention policy are separate. The default policy recommends
`continue`, `replan`, `reduce_scope`, `ask_human`, `pause`, or `abort`; it does not perform
side effects. A low shifted feasibility score escalates to a human by default rather than
auto-aborting. With too little evidence for a finite 90% interval, the guard fails safe to
open intervals and recommends pausing.

Telemetry adapters are dependency-free: `OpenAIUsageAdapter`, `LangChainUsageAdapter`,
and `MappingUsageAdapter`. Pricing is caller-supplied, avoiding stale provider prices.
Delayed authoritative usage can replace an earlier estimate via `guard.correct_usage(...)`
without double-counting.

Run the no-data three-resource demo:

```bash
python examples/loop_quickstart.py
```

Run the cross-family, order/window, and closed-loop evaluations:

```bash
python -m budget_guard.run_loop_validation
python -m budget_guard.run_loop_stress
python -m budget_guard.run_loop_closed_loop
```

Or regenerate all generic-loop evidence and a SHA-256 output manifest in one command:

```bash
python scripts/run_loop_artifact.py --quick  # development smoke
python scripts/run_loop_artifact.py --full   # submission evidence grid
```

**Scope:** validated on BAGEN token tasks, BAGEN Warehouse, and a non-agent sequential-
text pipeline smoke test. The source-text case proves software generality, not agent-domain
performance. This is not yet evidence from a second independent agent benchmark or live
production deployment.

## Specialized token wrapper (original API)

`BudgetGuard` is the drop-in artifact: wrap any agent loop with a **training-free**
monitor that, each turn, returns a calibrated interval on remaining budget and an
abort decision. It calibrates from completed runs only (no LLM fine-tuning) and, in
online mode, self-recalibrates from the deployment stream's own finished runs.

```python
from budget_guard.data import load_env
from budget_guard.guard import BudgetGuard

# Calibrate on completed rollouts — training-free, no GPU.
cal_df, _ = load_env("swebench")
guard = BudgetGuard.from_logs(cal_df, budget=7060)   # 7060 = swebench context budget

# Monitor a live run: one step() per agent turn.
guard.reset()
for turn_tokens in agent_turn_usage_stream():        # your agent's per-turn usage
    step = guard.step(turn_tokens)
    print(f"turn {step.k}: remaining budget in [{step.lo:.0f}, {step.hi:.0f}]")
    if step.abort:                                   # projected spend exceeds budget
        break
else:
    guard.observe()   # run finished cleanly: fold its labels back into calibration
```

`step()` takes the turn's **history-excluded** total tokens (the `turn_excluding_history`
accounting the guard was calibrated on).

**Install** the wrapper — numpy/pandas/lightgbm only, no GPU, no API — and run the
no-data demo (calibrates on synthetic runs, streams a live one):

```bash
pip install -e .
python examples/quickstart.py
```

See [`examples/quickstart.py`](examples/quickstart.py) and the tests in
[`tests/test_guard.py`](tests/test_guard.py); no BAGEN data is needed to try the API.

## Layout

```
budget_guard/   # the offline conformal infrastructure (the critical path)
  extract.py    # Week 1: rollout JSON -> (prefix, x_t, y_t)
  guard.py      # original token-only BudgetGuard
  loop_schema.py      # task-neutral events + validated resource ledger
  loop_features.py    # generic prefix-only resource/progress features
  loop_guard.py       # stateful multi-resource live guard
  loop_policy.py      # intervention recommendations (separate from estimator)
  loop_adapters.py    # framework telemetry translation only
  data_dictionary.md
notes/          # positioning note
paper/          # related-work note
```

## Sync model
Code syncs via Git; data + generated figures/tables are gitignored by design —
regenerate via `scripts/fetch_bagen.py` and the `run_*` scripts.
