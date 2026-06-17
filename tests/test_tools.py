from __future__ import annotations

import pytest

from app.tools.registry import TOOLS, ToolValidationError, call_tool


def test_get_invoice_history_returns_seeded_invoices():
    out = call_tool("get_invoice_history", {"customer_id": "cus_001"})
    assert out["tool"] == "get_invoice_history"
    assert out["requires_approval"] is False
    invoices = out["result"]["invoices"]
    assert len(invoices) == 3
    assert any("duplicate" in inv["description"].lower() for inv in invoices)


def test_get_customer_profile_unknown_customer():
    out = call_tool("get_customer_profile", {"customer_id": "nope"})
    assert out["result"]["error"] == "customer_not_found"


def test_risky_tool_is_flagged_and_not_executed():
    out = call_tool(
        "create_refund_ticket",
        {"customer_id": "cus_001", "invoice_id": "inv_1003", "amount": 49.0, "reason": "duplicate"},
    )
    assert out["requires_approval"] is True
    assert out["result"]["status"] == "pending_approval"
    assert out["result"]["requires_human_approval"] is True


def test_unknown_tool_raises():
    with pytest.raises(ToolValidationError):
        call_tool("does_not_exist", {})


def test_invalid_args_raise():
    # amount must be > 0
    with pytest.raises(ToolValidationError):
        call_tool(
            "create_refund_ticket",
            {"customer_id": "cus_001", "invoice_id": "inv_1", "amount": -5, "reason": "x"},
        )


def test_every_tool_exposes_a_schema():
    for tool in TOOLS.values():
        schema = tool.args_model.model_json_schema()
        assert "properties" in schema
