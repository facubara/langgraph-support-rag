"""Authentication for the BFF boundary.

The Next.js app is the only caller: its server-side route handlers read the Auth.js session
and forward each request with a shared secret (`X-Internal-Secret`) plus the signed-in user's
identity (`X-User-Id` / `X-User-Email`). FastAPI trusts those identity headers *only* because the
secret gates them.

`auth_required` defaults False so the demo and the test suite run unauthenticated against the mock
provider; flip it on in production. (A JWT-verification model is the documented hardening alt.)
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request

from .config import settings


@dataclass
class AuthUser:
    id: str
    email: str | None = None
    is_owner: bool = False


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_owner(email: str | None) -> bool:
    return bool(settings.owner_email) and email == settings.owner_email


def _secret_ok(provided: str | None) -> bool:
    secret = settings.service_shared_secret
    return bool(secret) and bool(provided) and hmac.compare_digest(provided, secret)


def require_user(
    request: Request,
    x_internal_secret: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> AuthUser:
    """Resolve the caller. Enforced mode demands a valid shared secret + user id; anonymous mode
    (the default) attributes requests to the supplied id or the client IP so rate limiting still works."""
    if not settings.auth_required:
        uid = x_user_id or f"anon:{_client_ip(request)}"
        return AuthUser(id=uid, email=x_user_email, is_owner=_is_owner(x_user_email))

    if not _secret_ok(x_internal_secret):
        raise HTTPException(status_code=401, detail="invalid or missing internal secret")
    if not x_user_id:
        raise HTTPException(status_code=401, detail="missing user identity")
    return AuthUser(id=x_user_id, email=x_user_email, is_owner=_is_owner(x_user_email))


def require_internal(x_internal_secret: str | None = Header(default=None)) -> None:
    """Gate server-to-server endpoints (e.g. /auth/sign-in) by the shared secret whenever one is
    configured. Open in local dev when no secret is set."""
    if settings.service_shared_secret and not _secret_ok(x_internal_secret):
        raise HTTPException(status_code=401, detail="invalid internal secret")


def require_owner(user: AuthUser = Depends(require_user)) -> AuthUser:
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="owner only")
    return user
