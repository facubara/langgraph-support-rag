"""Shared graph state.

`trace` and `tool_calls` use additive reducers so each node can append its own entries
and LangGraph merges them — the accumulated `trace` is what we persist for observability
and replay.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    run_id: str
    message: str
    customer_id: str | None
    intent: str | None

    # Context optimization (filled by the RAG/billing agent)
    retrieved: list[dict[str, Any]]
    context_included: list[dict[str, Any]]
    context_excluded: list[dict[str, Any]]

    # Tool use
    tool_calls: Annotated[list[dict[str, Any]], operator.add]

    # Safety / HITL
    pending_action: dict[str, Any] | None
    grounded: bool

    # Output
    final_response: str | None
    status: str

    # Observability — every node appends one or more step dicts here
    trace: Annotated[list[dict[str, Any]], operator.add]


# Intents the router can assign, in priority order (first match wins).
BILLING_INTENTS = {"duplicate_charge", "refund_request", "billing_question", "escalation"}
