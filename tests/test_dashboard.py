from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "dash.sqlite"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_dashboard_index_renders(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Runs" in resp.text


def test_dashboard_run_detail_shows_trace_and_replay(client):
    run_id = client.post(
        "/runs", json={"message": "I was charged twice", "customer_id": "cus_001"}
    ).json()["run_id"]

    resp = client.get(f"/dashboard/runs/{run_id}")
    assert resp.status_code == 200
    assert run_id in resp.text
    assert "Trace" in resp.text
    assert "Replay this run" in resp.text


def test_dashboard_detail_lists_replays(client):
    run_id = client.post(
        "/runs", json={"message": "I was charged twice", "customer_id": "cus_001"}
    ).json()["run_id"]
    replay_id = client.post(f"/runs/{run_id}/replay").json()["replay_run_id"]

    resp = client.get(f"/dashboard/runs/{run_id}")
    assert replay_id in resp.text


def test_dashboard_missing_run_404(client):
    assert client.get("/dashboard/runs/nope").status_code == 404
