"""Per-user rate limiting.

A sliding-window counter keyed on the authenticated user id (or client IP when anonymous). The
default backend is an in-process dict — zero dependencies, correct for a single instance (the
showcase runs one Render instance). For horizontal scaling, swap in Redis; the dependency surface
stays the same. Limits are read from settings at call time so tests can tune them.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Response

from .auth import AuthUser, require_user
from .config import settings


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int, float]:
        """Record a hit and report (allowed, remaining, reset_epoch)."""
        now = time.time()
        window = settings.rate_limit_window_seconds
        limit = settings.rate_limit_requests
        with self._lock:
            hits = [t for t in self._hits[key] if now - t < window]
            if len(hits) >= limit:
                self._hits[key] = hits
                return False, 0, hits[0] + window
            hits.append(now)
            self._hits[key] = hits
            return True, limit - len(hits), now + window

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def enforce_rate_limit(response: Response, user: AuthUser = Depends(require_user)) -> AuthUser:
    """Dependency for write endpoints: authenticate, then enforce the per-user window."""
    allowed, remaining, reset = limiter.check(user.id)
    headers = {
        "X-RateLimit-Limit": str(settings.rate_limit_requests),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(int(reset)),
    }
    for k, v in headers.items():
        response.headers[k] = v
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded",
            headers={**headers, "Retry-After": str(max(1, int(reset - time.time())))},
        )
    return user
