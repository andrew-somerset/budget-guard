"""budget-guard: distribution-free, multi-resource budget guards for long-horizon agents.

A standalone offline extractor turns logged BAGEN rollouts into (prefix, x_t, y_t)
tables — no `ragen`/`verl`/GPU needed — and ``BudgetGuard`` is the drop-in wrapper
that emits calibrated remaining-budget intervals + abort decisions for a live run.
"""
from .extract import (
    PrefixSample,
    flatten_to_samples,
    load_rollouts,
    samples_to_dataframe,
)
from .guard import BudgetGuard, GuardStep

__all__ = [
    "PrefixSample",
    "flatten_to_samples",
    "load_rollouts",
    "samples_to_dataframe",
    "BudgetGuard",
    "GuardStep",
]
