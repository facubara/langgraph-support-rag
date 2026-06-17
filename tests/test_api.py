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
    resp = client.post("/runs", json={"message": "Tell me about my plan", "customer_id": "cus_001"})
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    detail = client.get(f"/runs/{run_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["run"]["status"] == "completed"
    step_types = {s["step_type"] for s in body["steps"]}
    assert "router" in step_types and "llm" in step_types


def test_hitl_approve_flow(client):
    resp = client.post("/runs", json={"message": "I was charged twice", "customer_id": "cus_001"})
    body = resp.json()
    run_id = body["run_id"]
    assert body["status"] == "awaiting_approval"
    assert body["pending_action"]["action"] == "create_refund_ticket"

    approved = client.post(f"/runs/{run_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"
    assert approved.json()["result"]["status"] == "completed"

    # Approving again should fail — it's no longer awaiting approval.
    assert client.post(f"/runs/{run_id}/approve").status_code == 400


def test_hitl_reject_flow(client):
    run_id = client.post(
        "/runs", json={"message": "I want to speak to a human", "customer_id": "cus_001"}
    ).json()["run_id"]
    rejected = client.post(f"/runs/{run_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_get_missing_run_404(client):
    assert client.get("/runs/nope").status_code == 404
