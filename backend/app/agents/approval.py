"""Execution of human-approved risky actions.

Risky tools (`create_refund_ticket`, `escalate_to_human`) never execute inside the graph —
they only ever produce a `pending_action`. Once a human approves, this module performs the
action for real. Ticket/case ids are derived with a stable hash (not the per-process
randomized built-in `hash()`) so runs and their replays produce identical ids.
"""

from __future__ import annotations

import hashlib
from typing import Any


def _stable_id(prefix: str, seed: str) -> str:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()[:5]
    return f"{prefix}_{digest}"


def execute_approved_action(action: dict[str, Any]) -> dict[str, Any]:
    name = action.get("action")
    if name == "create_refund_ticket":
        seed = f"{action.get('customer_id')}-{action.get('invoice_id')}"
        return {
            "status": "completed",
            "action": name,
            "ticket_id": _stable_id("tkt", seed),
            "customer_id": action.get("customer_id"),
            "invoice_id": action.get("invoice_id"),
            "amount": action.get("amount"),
            "reason": action.get("reason"),
        }
    if name == "escalate_to_human":
        seed = f"{action.get('customer_id')}-{action.get('reason')}"
        return {
            "status": "completed",
            "action": name,
            "case_id": _stable_id("case", seed),
            "customer_id": action.get("customer_id"),
            "reason": action.get("reason"),
        }
    return {"status": "completed", "action": name, "note": "no-op"}
