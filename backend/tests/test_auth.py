"""Day 11 — auth, rate limiting, and sign-in tracking.

Default (anonymous) mode keeps the demo + suite open; enforced mode demands the BFF's shared
secret + identity. Rate limiting is per-user (per-IP when anonymous). Sign-ins are recorded via a
shared-secret-gated endpoint and visible only to the owner.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "auth.sqlite"))
    from app.main import app

    with TestClient(app) as c:
        yield c


# ----------------------------------------------------------------------------- auth
def test_anonymous_mode_allows_requests(client):
    # auth_required defaults False — no headers needed.
    assert client.post("/runs", json={"message": "Tell me about my plan", "customer_id": "cus_001"}).status_code == 200


def test_enforced_mode_blocks_without_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "service_shared_secret", "s3cret")

    assert client.post("/runs", json={"message": "hi"}).status_code == 401
    # wrong secret
    assert client.post("/runs", json={"message": "hi"}, headers={"x-internal-secret": "nope", "x-user-id": "u1"}).status_code == 401
    # valid secret + identity
    ok = client.post("/runs", json={"message": "Tell me about my plan", "customer_id": "cus_001"},
                     headers={"x-internal-secret": "s3cret", "x-user-id": "u1", "x-user-email": "u1@x.com"})
    assert ok.status_code == 200


def test_health_stays_open_when_enforced(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_required", True)
    monkeypatch.setattr(settings, "service_shared_secret", "s3cret")
    assert client.get("/health").status_code == 200


# ------------------------------------------------------------------------ rate limit
def test_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_requests", 3)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 60)
    body = {"message": "Tell me about my plan", "customer_id": "cus_001"}

    for _ in range(3):
        assert client.post("/runs", json=body).status_code == 200
    blocked = client.post("/runs", json=body)
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1
    assert blocked.headers["x-ratelimit-remaining"] == "0"


def test_rate_limit_headers_on_success(client):
    resp = client.post("/runs", json={"message": "Tell me about my plan", "customer_id": "cus_001"})
    assert resp.status_code == 200
    assert "x-ratelimit-limit" in resp.headers
    assert "x-ratelimit-remaining" in resp.headers


# ------------------------------------------------------------------- sign-in tracking
def test_sign_in_recorded_and_visible_to_owner(client, monkeypatch):
    monkeypatch.setattr(settings, "service_shared_secret", "s3cret")
    monkeypatch.setattr(settings, "owner_email", "owner@x.com")

    r = client.post("/auth/sign-in", json={"user_id": "u42", "email": "u42@x.com", "name": "User 42"},
                    headers={"x-internal-secret": "s3cret"})
    assert r.status_code == 204

    # Owner can see the sign-in.
    owner_h = {"x-user-email": "owner@x.com"}
    sign_ins = client.get("/admin/sign-ins", headers=owner_h)
    assert sign_ins.status_code == 200
    assert any(e["user_id"] == "u42" for e in sign_ins.json())
    users = client.get("/admin/users", headers=owner_h)
    assert any(u["id"] == "u42" and u["sign_in_count"] == 1 for u in users.json())


def test_sign_in_requires_shared_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "service_shared_secret", "s3cret")
    assert client.post("/auth/sign-in", json={"user_id": "u1"}).status_code == 401
    assert client.post("/auth/sign-in", json={"user_id": "u1"}, headers={"x-internal-secret": "bad"}).status_code == 401


def test_admin_requires_owner(client, monkeypatch):
    monkeypatch.setattr(settings, "owner_email", "owner@x.com")
    assert client.get("/admin/users").status_code == 403            # no identity → not owner
    assert client.get("/admin/users", headers={"x-user-email": "rando@x.com"}).status_code == 403
    assert client.get("/admin/users", headers={"x-user-email": "owner@x.com"}).status_code == 200
