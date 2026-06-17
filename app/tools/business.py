"""Mock business APIs backed by seeded JSON. Risky actions (refund ticket, escalation)
return a `pending_approval` envelope rather than executing — the human-in-the-loop gate
is enforced by the orchestration layer (Day 4)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=None)
def _load(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def get_customer_profile(customer_id: str) -> dict[str, Any]:
    customers = _load("customers.json")
    profile = customers.get(customer_id)
    if profile is None:
        return {"error": "customer_not_found", "customer_id": customer_id}
    return profile


def get_invoice_history(customer_id: str) -> dict[str, Any]:
    invoices = _load("invoices.json")
    return {"customer_id": customer_id, "invoices": invoices.get(customer_id, [])}


def check_refund_policy(plan: str, reason: str | None = None) -> dict[str, Any]:
    policy = _load("refund_policy.json")
    rule = policy.get(plan, policy["default"])
    return {"plan": plan, "reason": reason, "policy": rule}


def create_refund_ticket(
    customer_id: str, invoice_id: str, amount: float, reason: str
) -> dict[str, Any]:
    return {
        "status": "pending_approval",
        "action": "create_refund_ticket",
        "requires_human_approval": True,
        "customer_id": customer_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "reason": reason,
    }


def escalate_to_human(customer_id: str, reason: str) -> dict[str, Any]:
    return {
        "status": "pending_approval",
        "action": "escalate_to_human",
        "requires_human_approval": True,
        "customer_id": customer_id,
        "reason": reason,
    }
