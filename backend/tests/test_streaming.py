"""Day 9 — SSE streaming.

The streamed run must (a) emit the agent events in order, (b) produce text identical to the
non-streaming path (streaming is a transport detail, not a different answer), and (c) persist a
trace that can still be replayed deterministically.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "stream.sqlite"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        ev: dict = {}
        for line in block.splitlines():
            if line.startswith("event:"):
                ev["event"] = line[len("event:"):].strip()
            elif line.startswith("data:"):
                ev["data"] = json.loads(line[len("data:"):].strip())
        events.append(ev)
    return events


def test_stream_event_order_and_text_matches_complete(client):
    resp = client.post("/runs/stream", json={"message": "I was charged twice", "customer_id": "cus_001"})
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    types = [e["event"] for e in events]

    # Ordered pipeline: start → router → rag → tool(s) → policy → token(s) → done.
    assert types[0] == "run_started"
    assert "router" in types and "rag" in types and "policy" in types
    assert types.index("router") < types.index("rag") < types.index("policy")
    assert "tool" in types
    assert types[-1] == "done"
    assert types.count("token") >= 1
    # tokens come before done, after policy
    assert max(i for i, t in enumerate(types) if t == "token") < types.index("done")

    streamed_text = "".join(e["data"]["text"] for e in events if e["event"] == "token")
    done = next(e["data"] for e in events if e["event"] == "done")
    assert streamed_text == done["response"]

    # Same input through the non-streaming endpoint yields identical text.
    plain = client.post("/runs", json={"message": "I was charged twice", "customer_id": "cus_001"})
    assert plain.json()["response"] == streamed_text


def test_stream_refusal_path_has_no_tools(client):
    resp = client.post("/runs/stream", json={"message": "what is the weather today"})
    events = parse_sse(resp.text)
    types = [e["event"] for e in events]
    assert "tool" not in types and "rag" not in types
    streamed_text = "".join(e["data"]["text"] for e in events if e["event"] == "token")
    assert "don't have enough information" in streamed_text
    done = next(e["data"] for e in events if e["event"] == "done")
    assert done["status"] == "completed"


def test_streamed_run_is_replayable(client):
    resp = client.post("/runs/stream", json={"message": "Tell me about my plan", "customer_id": "cus_001"})
    done = next(e["data"] for e in parse_sse(resp.text) if e["event"] == "done")
    run_id = done["run_id"]

    replay = client.post(f"/runs/{run_id}/replay")
    assert replay.status_code == 200
    assert replay.json()["comparison"]["match"] is True
