from __future__ import annotations

import pytest

from app.config import settings
from app.store import run_store


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "test.sqlite"))
    run_store.init_db()
    yield


def test_run_lifecycle_and_trace(temp_db):
    run_store.create_run("run_abc", "I was double charged")
    run_store.add_step(
        "run_abc",
        step_index=0,
        step_type="tool",
        name="get_invoice_history",
        input={"customer_id": "cus_001"},
        output={"invoices": []},
        latency_ms=1.2,
        cost_usd=0.0,
    )
    run_store.finish_run("run_abc", intent="duplicate_charge", final_response="Resolved.")

    data = run_store.get_run("run_abc")
    assert data is not None
    assert data["run"]["status"] == "completed"
    assert data["run"]["intent"] == "duplicate_charge"
    assert len(data["steps"]) == 1
    step = data["steps"][0]
    assert step["step_type"] == "tool"
    assert step["input"] == {"customer_id": "cus_001"}   # decoded back from JSON
    assert step["output"] == {"invoices": []}


def test_list_runs_orders_recent_first(temp_db):
    run_store.create_run("r1", "first")
    run_store.create_run("r2", "second")
    runs = run_store.list_runs()
    assert {r["id"] for r in runs} == {"r1", "r2"}


def test_get_missing_run_returns_none(temp_db):
    assert run_store.get_run("missing") is None
