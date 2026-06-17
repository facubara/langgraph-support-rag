from __future__ import annotations

import pytest

from app.config import settings


@pytest.fixture()
def graphdb(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "graph.sqlite"))
    from app.store import run_store

    run_store.init_db()
    from app.graph import run_conversation

    return run_conversation


def test_router_classifies_intents(graphdb):
    assert graphdb("I was charged twice this month", customer_id="cus_001")["intent"] == "duplicate_charge"
    assert graphdb("Can I get a refund?", customer_id="cus_002")["intent"] == "refund_request"
    assert graphdb("I want to speak to a human", customer_id="cus_001")["intent"] == "escalation"
    assert graphdb("What's the weather?")["intent"] == "other"


def test_duplicate_charge_proposes_refund_and_awaits_approval(graphdb):
    out = graphdb("I was charged twice", customer_id="cus_001")
    assert out["intent"] == "duplicate_charge"
    assert out["status"] == "awaiting_approval"
    assert out["pending_action"]["action"] == "create_refund_ticket"
    assert out["pending_action"]["invoice_id"] == "inv_1003"  # the planted duplicate


def test_enterprise_duplicate_escalates_for_review(graphdb):
    # cus_003 is enterprise (duplicate_charges = review_required); no duplicate exists,
    # so a plain refund request outside the (0-day) window escalates to a human.
    out = graphdb("I'd like a refund please", customer_id="cus_003")
    assert out["status"] == "awaiting_approval"
    assert out["pending_action"]["action"] == "escalate_to_human"


def test_ungrounded_question_is_refused_not_hallucinated(graphdb):
    out = graphdb("What's the capital of France?")
    assert out["intent"] == "other"
    assert out["status"] == "completed"
    assert out["pending_action"] is None
    assert "don't have enough information" in out["response"]


def test_escalation_intent_sets_pending_escalation(graphdb):
    out = graphdb("Let me speak to a manager", customer_id="cus_001")
    assert out["status"] == "awaiting_approval"
    assert out["pending_action"]["action"] == "escalate_to_human"
