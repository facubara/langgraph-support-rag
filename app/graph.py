"""Builds and runs the multi-agent graph.

    router ──(billing intent)──▶ billing_rag ──▶ policy_safety ──▶ response ──▶ END
       └────(other intent)─────────────────────────────────────▶ response

`run_conversation` invokes the compiled graph, persists every traced step to the run
store, and returns a compact result for the API. The full step trace is what powers the
observability dashboard and deterministic replay.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from .agents import nodes
from .agents.state import AgentState
from .store import run_store


@lru_cache(maxsize=1)
def get_graph():
    g = StateGraph(AgentState)
    g.add_node("router", nodes.router)
    g.add_node("billing_rag", nodes.billing_rag)
    g.add_node("policy_safety", nodes.policy_safety)
    g.add_node("response", nodes.response)

    g.add_edge(START, "router")
    g.add_conditional_edges("router", nodes.route_after_router,
                            {"billing_rag": "billing_rag", "response": "response"})
    g.add_edge("billing_rag", "policy_safety")
    g.add_edge("policy_safety", "response")
    g.add_edge("response", END)
    return g.compile()


def _persist(run_id: str, final_state: dict[str, Any]) -> None:
    for i, step in enumerate(final_state.get("trace", [])):
        run_store.add_step(
            run_id,
            step_index=i,
            step_type=step.get("step_type", "step"),
            name=step.get("name"),
            input=step.get("input"),
            output=step.get("output"),
            latency_ms=step.get("latency_ms"),
            cost_usd=step.get("cost_usd"),
            error=step.get("error"),
        )
    run_store.finish_run(
        run_id,
        intent=final_state.get("intent"),
        final_response=final_state.get("final_response"),
        status=final_state.get("status", "completed"),
        pending_action=final_state.get("pending_action"),
    )


def run_conversation(message: str, customer_id: str | None = None,
                     run_id: str | None = None) -> dict[str, Any]:
    run_id = run_id or uuid.uuid4().hex[:12]
    run_store.create_run(run_id, message)

    initial: AgentState = {"run_id": run_id, "message": message, "customer_id": customer_id}
    final_state = get_graph().invoke(initial)
    _persist(run_id, final_state)

    return {
        "run_id": run_id,
        "intent": final_state.get("intent"),
        "response": final_state.get("final_response"),
        "status": final_state.get("status"),
        "pending_action": final_state.get("pending_action"),
        "grounded": bool(final_state.get("grounded", False)),
        "tools": [t["tool"] for t in final_state.get("tool_calls", [])],
    }
