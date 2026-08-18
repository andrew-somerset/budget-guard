# Data dictionary — BAGEN token-budget prefix samples

Produced by `budget_guard/extract.py`, a faithful port of
`ragen/env/token_estimation/env.py` (`_flatten_rollouts`). One **prefix sample** per row.

## What a row is
A rollout with `N` usable turns yields `N − 1` rows, one per `k = completed_turns` (1…N−1),
id `rollout-{i}-turn-{k}`. Turns are sorted by `turn_idx`; everything from the first
context-truncated turn onward is dropped; only turns with assistant content are kept.

## Columns
| Column | Meaning | Role |
| --- | --- | --- |
| `rollout_index` | which rollout | id / **split key** |
| `sample_id` | `rollout-{i}-turn-{k}` | id |
| `k` | completed turns (prefix length) | **feature** |
| `N` | total usable turns | **LEAK — do not use** |
| `tokens_so_far` | cumulative tokens through turn k | **feature** |
| `total_rollout_tokens` | total tokens of the full logged rollout | **LEAK** |
| `y` | `max(0, total_rollout_tokens − tokens_so_far)` = remaining tokens | **TARGET** |
| `can_finish` | `rollout_success AND total_rollout_tokens ≤ max_ctx` | feasibility label |
| `rollout_success` | did the whole rollout succeed | **LEAK** |
| `per_turn_total` | per-turn totals for turns 1…k | **feature source** (rolling stats) |

## Rules that keep coverage numbers valid
- **Legal features** at prefix `t`: `k`, `tokens_so_far`, and anything derived from
  `per_turn_total[1..k]` (last, mean, std, max, slope). Optionally the model's self-estimate.
- **Never** use `N`, `k/N` (relative progress), `y`, `total_rollout_tokens`, or `rollout_success`
  as features — they are computed from the full rollout and leak the answer.
- **Split by `rollout_index`**, never by prefix: prefixes of one rollout share
  `total_rollout_tokens` and are highly correlated; a prefix-level split inflates coverage.

## Why `y` is well-defined
`y` uses the *logged* full rollout, so the "future" is fixed → this offline replay is what makes
the target tractable (the closed-loop / performative version is future work).

## Evaluation
Rollout-level splits and rollout-safe online label revelation are required for valid coverage
under transfer; see [`docs/results_explained.md`](../docs/results_explained.md).

## Fidelity
Validate `y` against the official harness once on Colab (walkthrough §6): target 0 mismatches.
If real rollouts log input tokens that include replayed history, port
`_convert_request_usage_to_turn_usage` from `env.py`.
