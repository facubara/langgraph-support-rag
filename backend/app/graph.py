"""Builds and runs the multi-agent graph.

    router ──(billing intent)──▶ billing_rag ──▶ policy_safety ──▶ response ──▶ END
       └────(other intent)─────────────────────────────────────▶ response

`run_conversation` invokes the compiled graph, persists every traced step to the run
store, and returns a compact result for the API. The full step trace is what powers the
observability dashboard and deterministic replay.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from .agents import nodes
from .agents.state import AgentState
from .config import settings
from .llm.factory import get_llm
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


def _persist_steps(run_id: str, trace: list[dict[str, Any]]) -> None:
    for i, step in enumerate(trace):
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


def _persist(run_id: str, final_state: dict[str, Any]) -> None:
    _persist_steps(run_id, final_state.get("trace", []))
    run_store.finish_run(
        run_id,
        intent=final_state.get("intent"),
        final_response=final_state.get("final_response"),
        status=final_state.get("status", "completed"),
        pending_action=final_state.get("pending_action"),
    )


def _result(run_id: str, final_state: dict[str, Any],
            conversation_id: str | None = None) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "conversation_id": conversation_id,
        "intent": final_state.get("intent"),
        "response": final_state.get("final_response"),
        "status": final_state.get("status"),
        "pending_action": final_state.get("pending_action"),
        "grounded": bool(final_state.get("grounded", False)),
        "tools": [t["tool"] for t in final_state.get("tool_calls", [])],
    }


def _begin_conversation(
    conversation_id: str | None, user_id: str | None, customer_id: str | None,
) -> tuple[int | None, list[dict[str, Any]], str | None]:
    """Set up a multi-turn run: ensure the thread exists, compute the turn index, load prior
    turns as history, and resolve a sticky customer id. Returns (turn_index, history, customer_id).

    For single-turn calls (no conversation_id) this is a no-op: (None, [], customer_id)."""
    if not conversation_id:
        return None, [], customer_id

    if not run_store.conversation_exists(conversation_id):
        run_store.create_conversation(conversation_id, user_id=user_id, customer_id=customer_id)

    convo = run_store.get_conversation(conversation_id) or {"conversation": {}, "turns": []}
    if not customer_id:
        customer_id = convo["conversation"].get("customer_id")

    history: list[dict[str, Any]] = []
    for turn in convo["turns"][-settings.conversation_history_turns:]:
        history.append({"role": "user", "text": turn.get("user_message", "")})
        if turn.get("final_response"):
            history.append({"role": "assistant", "text": turn["final_response"]})

    turn_index = run_store.next_turn_index(conversation_id)
    return turn_index, history, customer_id


def run_conversation(message: str, customer_id: str | None = None,
                     run_id: str | None = None, replay_of: str | None = None,
                     recorded_responses: list | None = None,
                     conversation_id: str | None = None,
                     user_id: str | None = None) -> dict[str, Any]:
    run_id = run_id or uuid.uuid4().hex[:12]
    turn_index, history, customer_id = _begin_conversation(conversation_id, user_id, customer_id)
    run_store.create_run(run_id, message, replay_of=replay_of,
                         conversation_id=conversation_id, turn_index=turn_index)

    initial: AgentState = {"run_id": run_id, "message": message, "customer_id": customer_id,
                           "conversation_id": conversation_id, "history": history}

    # When replaying, install the recorded LLM outputs for the duration of this invocation
    # so the Response agent reproduces the original phrasing deterministically.
    token = None
    if recorded_responses is not None:
        from . import replay

        token = replay.begin(recorded_responses)
    try:
        final_state = get_graph().invoke(initial)
    finally:
        if token is not None:
            from . import replay

            replay.end(token)

    _persist(run_id, final_state)
    if conversation_id:
        run_store.touch_conversation(conversation_id, customer_id=customer_id)

    return _result(run_id, final_state, conversation_id)


# ---------------------------------------------------------------------- streaming (SSE)
# Token streaming of the response happens after the (synchronous) graph has run; the
# pre-response trace steps are replayed to the client as structured events.
def _trace_to_events(trace: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for step in trace:
        name = step.get("name")
        if name == "router":
            yield {"type": "router", "data": step.get("output", {})}
        elif name == "billing_rag":
            yield {"type": "rag", "data": step.get("output", {})}
        elif name == "policy_safety":
            yield {"type": "policy", "data": step.get("output", {})}
        elif step.get("step_type") == "tool":
            yield {"type": "tool", "data": {"tool": name, "result": step.get("output")}}


def run_conversation_streaming(
    message: str, customer_id: str | None = None, run_id: str | None = None,
    conversation_id: str | None = None, user_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Run a turn and stream it as a sequence of event dicts.

    The graph runs synchronously (so routing/policy/replay stay deterministic); only the
    Response agent's text is streamed token-by-token. Events:
    run_started → router → rag → tool* → policy → token* → done  (or `error`).
    """
    run_id = run_id or uuid.uuid4().hex[:12]
    turn_index, history, customer_id = _begin_conversation(conversation_id, user_id, customer_id)
    run_store.create_run(run_id, message, conversation_id=conversation_id, turn_index=turn_index)

    initial: AgentState = {"run_id": run_id, "message": message, "customer_id": customer_id,
                           "conversation_id": conversation_id, "history": history,
                           "stream_response": True}

    try:
        final_state = get_graph().invoke(initial)
        yield {"type": "run_started", "data": {"run_id": run_id, "conversation_id": conversation_id}}
        yield from _trace_to_events(final_state.get("trace", []))

        pending = final_state.get("pending_action")
        trace = list(final_state.get("trace", []))
        prompt = final_state.get("response_prompt")

        if prompt is not None:
            system = final_state.get("response_system", "")
            started = time.perf_counter()
            llm = get_llm()
            chunks: list[str] = []
            for chunk in llm.stream(system=system, prompt=prompt):
                chunks.append(chunk)
                yield {"type": "token", "data": {"text": chunk}}
            raw_text = "".join(chunks)
            text, status = nodes.apply_pending_suffix(raw_text, pending)
            suffix = text[len(raw_text):]
            if suffix:
                yield {"type": "token", "data": {"text": suffix}}
            trace.append({
                "step_type": "llm", "name": llm.model,
                "input": {"prompt": prompt}, "output": {"text": raw_text},
                "latency_ms": (time.perf_counter() - started) * 1000, "cost_usd": 0.0,
            })
        else:
            # Refusal path: no LLM call — stream the prepared text out as one token.
            text = final_state.get("final_response", "")
            status = final_state.get("status", "completed")
            yield {"type": "token", "data": {"text": text}}

        final_state["final_response"] = text
        final_state["status"] = status
        _persist_steps(run_id, trace)
        run_store.finish_run(run_id, intent=final_state.get("intent"), final_response=text,
                             status=status, pending_action=pending)
        if conversation_id:
            run_store.touch_conversation(conversation_id, customer_id=customer_id)

        yield {"type": "done", "data": _result(run_id, final_state, conversation_id)}
    except Exception as err:  # noqa: BLE001 - surface as an SSE error, never crash the stream
        run_store.finish_run(run_id, status="error", final_response=str(err))
        yield {"type": "error", "data": {"detail": str(err)}}
