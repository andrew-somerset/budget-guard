"""Session-level preflight for the test suite.

Most of this suite fits LightGBM models. On a machine without an OpenMP runtime that
fails 24 separate times with 24 separate tracebacks, which buries the one fact that
matters: a system library is missing. Check once, up front, and say so plainly.

The check is a no-op wherever OpenMP is present — every Linux distribution this runs on,
the reproducibility container, and CI.
"""

from __future__ import annotations

import pytest


def pytest_sessionstart(session: pytest.Session) -> None:
    try:
        from budget_guard._deps import require_lightgbm

        require_lightgbm()
    except ImportError as exc:  # raised by require_lightgbm with install instructions
        pytest.exit(
            f"\n{exc}\n\nAborting before running tests: every model-fitting test would "
            "fail with this same error.",
            returncode=1,
        )
