"""Day 9 — multi-turn conversations.

A conversation carries context across turns: prior turns feed back into the response prompt,
and the customer id resolved on turn 1 is sticky for later turns. Single-turn behavior (no
conversation_id) is unchanged, and a conversation turn is still deterministically replayable.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "convo.sqlite"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def _llm_prompt(client, run_id: str) -> str:
    steps = client.get(f"/runs/{run_id}").json()["steps"]
    llm = next(s for s in steps if s["step_type"] == "llm")
    return llm["input"]["prompt"]


def test_second_turn_carries_history_and_sticky_customer(client):
    cid = "conv_test_1"
    t1 = client.post("/runs", json={"message": "Tell me about my plan", "customer_id": "cus_001",
                                    "conversation_id": cid}).json()
    assert t1["conversation_id"] == cid

    # Turn 2 omits customer_id — it must be inherited from the thread (sticky), so it still grounds.
    t2 = client.post("/runs", json={"message": "and can I get a refund?", "conversation_id": cid}).json()
    assert t2["grounded"] is True

    prompt = _llm_prompt(client, t2["run_id"])
    assert "Conversation so far" in prompt
    assert "Tell me about my plan" in prompt   # turn 1's user message is in turn 2's prompt


def test_conversation_endpoint_lists_turns_in_order(client):
    cid = "conv_test_2"
    client.post("/runs", json={"message": "first question about my invoice", "customer_id": "cus_001",
                               "conversation_id": cid})
    client.post("/runs", json={"message": "second question about a refund", "conversation_id": cid})

    data = client.get(f"/conversations/{cid}").json()
    assert data["conversation"]["id"] == cid
    assert [t["turn_index"] for t in data["turns"]] == [0, 1]
    assert data["turns"][0]["user_message"] == "first question about my invoice"


def test_single_turn_unchanged_without_conversation_id(client):
    r = client.post("/runs", json={"message": "Tell me about my plan", "customer_id": "cus_001"}).json()
    assert r["conversation_id"] is None
    prompt = _llm_prompt(client, r["run_id"])
    assert "Conversation so far" not in prompt   # no history block for a standalone run


def test_conversation_turn_is_replayable(client):
    cid = "conv_test_3"
    client.post("/runs", json={"message": "Tell me about my plan", "customer_id": "cus_001",
                               "conversation_id": cid})
    t2 = client.post("/runs", json={"message": "I was charged twice", "conversation_id": cid}).json()

    replay = client.post(f"/runs/{t2['run_id']}/replay")
    assert replay.status_code == 200
    assert replay.json()["comparison"]["match"] is True


def test_missing_conversation_404(client):
    assert client.get("/conversations/nope").status_code == 404
