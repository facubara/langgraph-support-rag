from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Force mock provider + an isolated DB so tests need no API key and don't pollute data/.
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "api.sqlite"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_tools(client):
    resp = client.get("/tools")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert names == {
        "get_customer_profile",
        "get_invoice_history",
        "check_refund_policy",
        "create_refund_ticket",
        "escalate_to_human",
    }


def test_invoke_tool_validation_error(client):
    resp = client.post("/tools/create_refund_ticket", json={"args": {"customer_id": "cus_001"}})
    assert resp.status_code == 400


def test_run_creates_traced_record(client):
    resp = client.post("/runs", json={"message": "I want a refund for a duplicate charge"})
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]
    assert "[mock]" in resp.json()["response"]

    detail = client.get(f"/runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["run"]["status"] == "completed"
    assert len(body["steps"]) == 1
    assert body["steps"][0]["step_type"] == "llm"


def test_get_missing_run_404(client):
    assert client.get("/runs/nope").status_code == 404
