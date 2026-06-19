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

    # Multi-turn (seeded once at entry, not an additive reducer)
    conversation_id: str | None
    history: list[dict[str, Any]]      # [{"role": "user"|"assistant", "text": ...}, ...]

    # Context optimization (filled by the RAG/billing agent)
    retrieved: list[dict[str, Any]]
    context_included: list[dict[str, Any]]
    context_excluded: list[dict[str, Any]]

    # Tool use
    tool_calls: Annotated[list[dict[str, Any]], operator.add]

    # Safety / HITL
    pending_action: dict[str, Any] | None
    grounded: bool

    # Streaming: when set, the Response node prepares the prompt but defers the LLM call to
    # the streaming layer, which stashes (system, prompt) here instead of completing inline.
    stream_response: bool
    response_system: str | None
    response_prompt: str | None

    # Output
    final_response: str | None
    status: str

    # Observability — every node appends one or more step dicts here
    trace: Annotated[list[dict[str, Any]], operator.add]


# Intents the router can assign, in priority order (first match wins).
BILLING_INTENTS = {"duplicate_charge", "refund_request", "billing_question", "escalation"}
