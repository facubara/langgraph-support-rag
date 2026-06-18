from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.llm.base import LLMResponse
from app.replay import (
    ReplayExhaustedError,
    ReplayLLM,
    compare_runs,
    recorded_customer_id,
    recorded_llm_responses,
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "replay.sqlite"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_replay_llm_serves_recorded_responses_in_order():
    llm = ReplayLLM([LLMResponse(text="one", model="m"), LLMResponse(text="two", model="m")])
    assert llm.complete("s", "p").text == "one"
    assert llm.complete("s", "p").text == "two"
    with pytest.raises(ReplayExhaustedError):
        llm.complete("s", "p")


def test_recorded_helpers_read_from_trace():
    run_data = {
        "run": {},
        "steps": [
            {"step_type": "router", "name": "router", "output": {"customer_id": "cus_007"}},
            {"step_type": "tool", "name": "get_invoice_history", "output": {}},
            {"step_type": "llm", "name": "mock-llm", "output": {"text": "hi"}, "cost_usd": 0.0},
        ],
    }
    assert recorded_customer_id(run_data) == "cus_007"
    responses = recorded_llm_responses(run_data)
    assert [r.text for r in responses] == ["hi"]


def test_replay_reproduces_run_and_matches(client):
    created = client.post(
        "/runs", json={"message": "I was charged twice", "customer_id": "cus_001"}
    ).json()
    run_id = created["run_id"]

    replayed = client.post(f"/runs/{run_id}/replay").json()
    assert replayed["original_run_id"] == run_id
    assert replayed["replay_run_id"] != run_id
    assert replayed["comparison"]["match"] is True
    assert replayed["comparison"]["diffs"] == []

    # The replay run is linked back to its source.
    new_detail = client.get(f"/runs/{replayed['replay_run_id']}").json()
    assert new_detail["run"]["replay_of"] == run_id


def test_replay_preserves_tool_sequence_and_response(client):
    run_id = client.post(
        "/runs", json={"message": "I was charged twice", "customer_id": "cus_001"}
    ).json()["run_id"]
    original = client.get(f"/runs/{run_id}").json()

    new_run_id = client.post(f"/runs/{run_id}/replay").json()["replay_run_id"]
    replay = client.get(f"/runs/{new_run_id}").json()

    def tools(d):
        return [s["name"] for s in d["steps"] if s["step_type"] == "tool"]

    assert tools(original) == tools(replay)
    assert original["run"]["final_response"] == replay["run"]["final_response"]
    assert original["run"]["status"] == replay["run"]["status"]


def test_replay_missing_run_404(client):
    assert client.post("/runs/nope/replay").status_code == 404


def test_compare_runs_reports_diffs():
    original = {"run": {"intent": "refund_request", "status": "completed",
                        "final_response": "a", "pending_action": None}, "steps": []}
    replay = {"run": {"intent": "refund_request", "status": "completed",
                      "final_response": "b", "pending_action": None}, "steps": []}
    result = compare_runs(original, replay)
    assert result["match"] is False
    assert any(d["field"] == "final_response" for d in result["diffs"])
