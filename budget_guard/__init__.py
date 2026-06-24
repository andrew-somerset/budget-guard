"""budget-guard: distribution-free, multi-resource budget guards for long-horizon agents.

Week 1 scope: a standalone offline extractor that turns logged BAGEN rollouts into
(prefix, x_t, y_t) tables — no `ragen`/`verl`/GPU needed.
"""
from .extract import (
    PrefixSample,
    flatten_to_samples,
    load_rollouts,
    samples_to_dataframe,
)

__all__ = [
    "PrefixSample",
    "flatten_to_samples",
    "load_rollouts",
    "samples_to_dataframe",
]
