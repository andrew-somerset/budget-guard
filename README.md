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

## Layout

```
budget_guard/   # the offline conformal infrastructure (the critical path)
  extract.py    # Week 1: rollout JSON -> (prefix, x_t, y_t)
  data_dictionary.md
notes/          # weekly notes + the reproduced-number log
docs/           # the project plan + walkthrough (synced across devices)
```

## Sync model
Code syncs via Git; data + figures do not. See [`docs/bagen_week1_walkthrough.md`](docs/bagen_week1_walkthrough.md) §7.
