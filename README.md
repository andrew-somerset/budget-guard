# budget-guard

Distribution-free, multi-resource **budget guards** for long-horizon agents: a training-free
wrapper that outputs calibrated prediction intervals on an agent's *remaining budget*
(tokens / $ / time) via online conformal prediction. Built on the logged rollouts from
**BAGEN** (arXiv:2606.00198).

**CPU-only Python** — no `verl`, no `vllm`, no GPU. The full plan is in [`docs/`](docs/).

## Setup

```bash
conda create -n budget python=3.12 -c conda-forge --override-channels -y
conda activate budget
pip install -r requirements.txt
```

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
Full Week-1 steps: [`docs/bagen_week1_walkthrough.md`](docs/bagen_week1_walkthrough.md).

## Use the guard (wrapper API)

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
accounting the guard was calibrated on). No BAGEN data needed to try the API — see the
synthetic examples in [`tests/test_guard.py`](tests/test_guard.py).

## Layout

```
budget_guard/   # the offline conformal infrastructure (the critical path)
  extract.py    # Week 1: rollout JSON -> (prefix, x_t, y_t)
  guard.py      # BudgetGuard: the drop-in wrapper (intervals + abort)
  data_dictionary.md
notes/          # weekly notes + the reproduced-number log
docs/           # the project plan + walkthrough (synced across devices)
```

## Sync model
Code syncs via Git; data + figures do not. See [`docs/bagen_week1_walkthrough.md`](docs/bagen_week1_walkthrough.md) §7.
