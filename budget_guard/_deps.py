"""Dependency import helpers that turn opaque system-library failures into instructions.

LightGBM ships a compiled library that links against an OpenMP runtime it does not
bundle. On macOS that runtime (`libomp.dylib`) is absent unless installed separately, so
`import lightgbm` raises an OSError from the dynamic loader naming only a dylib path —
no package, no remedy. It cannot be fixed by pinning anything in requirements.txt or
pyproject.toml, because it is a system library rather than a Python one.

That error is the first thing a new user hits on macOS, at the first model fit rather
than at install time, which makes it read like a bug in this project. Translate it.
"""

from __future__ import annotations

import platform

_OPENMP_HINT = """\
LightGBM could not load its OpenMP runtime, so no model can be fit.

This is a missing SYSTEM library, not a missing Python package — installing it cannot be
expressed in requirements.txt or pyproject.toml, so it has to be done once by hand:

  macOS (conda):  conda install -c conda-forge llvm-openmp
  macOS (brew):   brew install libomp
  Debian/Ubuntu:  apt-get install libgomp1

The reproducibility container already installs it; see the Dockerfile. Original loader
error follows.
"""


def require_lightgbm():
    """Import and return the ``lightgbm`` module, or raise with an actionable message."""
    try:
        import lightgbm
    except (OSError, ImportError) as exc:
        text = str(exc)
        if "omp" in text.lower() or platform.system() == "Darwin":
            raise ImportError(f"{_OPENMP_HINT}\n{type(exc).__name__}: {exc}") from exc
        raise
    return lightgbm
