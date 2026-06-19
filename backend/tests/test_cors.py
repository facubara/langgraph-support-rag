"""Day 8 — CORS for the split-stack frontend.

The Next.js app is a separate origin; a browser preflight (OPTIONS) must come back with the
configured origin echoed and credentials allowed, or the frontend can't call the API in local dev.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "cors.sqlite"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_origins_list_parses_comma_separated(monkeypatch):
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://localhost:3000, https://demo.vercel.app ")
    from app.config import Settings

    s = Settings(_env_file=None)
    assert s.cors_origins_list == ["http://localhost:3000", "https://demo.vercel.app"]


def test_preflight_echoes_allowed_origin(client):
    resp = client.options(
        "/runs",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert resp.headers["access-control-allow-credentials"] == "true"


def test_disallowed_origin_is_not_echoed(client):
    resp = client.options(
        "/runs",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Starlette returns 400 for a disallowed preflight origin and never echoes it back.
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example.com"
