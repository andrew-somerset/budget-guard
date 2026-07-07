"""Item-9 pilot test: the closed-loop feedback under-covers vs the oracle.

Pins the qualitative claim of scripts/run_closed_loop.py — self-selecting the calibration
stream (aborting doomed runs) drives true full-population coverage below both the oracle
and nominal, while the guard's self-measured coverage stays ~nominal (its blind spot).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import run_closed_loop as clp  # noqa: E402


def _final(closed_loop, key, seeds=range(4)):
    return float(np.mean([clp.simulate(closed_loop=closed_loop, seed=s)[key][-1] for s in seeds]))


def test_closed_loop_undercovers_full_population_vs_oracle():
    cl_full = _final(True, 0)      # closed-loop, true full-population coverage
    orc_full = _final(False, 0)    # oracle, true full-population coverage
    cl_self = _final(True, 1)      # closed-loop, guard's self-measured coverage
    assert cl_full < orc_full - 0.03, (cl_full, orc_full)
    assert cl_full < 0.88, cl_full
    assert cl_self >= 0.87, cl_self  # blind spot: self-measured stays ~nominal
