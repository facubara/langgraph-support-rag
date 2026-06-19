"""Shared test fixtures.

The rate limiter is a process-wide singleton, so without a reset the cumulative request count
across the whole suite would trip the limit and fail unrelated tests. Reset it before each test.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.ratelimit import limiter

    limiter.reset()
    yield
    limiter.reset()
