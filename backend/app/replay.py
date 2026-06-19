"""Deterministic replay.

A run is reproducible because everything in the graph is deterministic *except* the
user-facing phrasing produced by the LLM in the Response agent (under a real provider the
same prompt can yield different text). Replay closes that gap: it re-runs the graph for a
recorded run while serving the **recorded** LLM outputs in order instead of calling the
provider. Tool results already come from static fixtures and routing/policy are rule-based,
so a replayed run reproduces the original outcome byte-for-byte.

The provider swap is wired through a context variable that `llm.factory.get_llm` consults,
so no node has to know whether it is running live or in replay.
"""

from __future__ import annotations

import contextvars
from typing import Any

from .llm.base import LLMClient, LLMResponse

# When set, `get_llm()` returns a ReplayLLM seeded with these recorded responses.
_replay_responses: contextvars.ContextVar[list[LLMResponse] | None] = contextvars.ContextVar(
    "replay_responses", default=None
)


class ReplayExhaustedError(RuntimeError):
    """The replayed graph asked for more LLM calls than the original run recorded."""


class ReplayLLM(LLMClient):
    """Serves recorded LLM responses in call order; never touches a provider."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.model = "replay"
        self._responses = list(responses)
        self._index = 0

    def complete(self, system: str, prompt: str) -> LLMResponse:
        if self._index >= len(self._responses):
            raise ReplayExhaustedError(
                f"replay ran out of recorded LLM responses after {self._index} call(s)"
            )
        resp = self._responses[self._index]
        self._index += 1
        return resp


def active_replay() -> list[LLMResponse] | None:
    """The recorded responses for the current replay, or None when running live."""
    return _replay_responses.get()


def begin(responses: list[LLMResponse]) -> contextvars.Token:
    return _replay_responses.set(responses)


def end(token: contextvars.Token) -> None:
    _replay_responses.reset(token)


def recorded_llm_responses(run_data: dict[str, Any]) -> list[LLMResponse]:
    """Reconstruct the LLM responses from a stored run's step trace, in call order.

    Token counts aren't persisted; replay only needs the text/model/latency/cost that the
    trace records, which is everything the downstream graph and comparison consume.
    """
    responses: list[LLMResponse] = []
    for step in run_data.get("steps", []):
        if step.get("step_type") != "llm":
            continue
        output = step.get("output") or {}
        responses.append(
            LLMResponse(
                text=output.get("text", ""),
                model=step.get("name") or "replay",
                cost_usd=step.get("cost_usd") or 0.0,
                latency_ms=step.get("latency_ms") or 0.0,
            )
        )
    return responses


def recorded_customer_id(run_data: dict[str, Any]) -> str | None:
    """Recover the customer id the original run resolved, from its router step.

    The router records the resolved id in its output, so replay reuses the exact same input
    even when the id was supplied out-of-band rather than parsed from the message text.
    """
    for step in run_data.get("steps", []):
        if step.get("step_type") == "router":
            return (step.get("output") or {}).get("customer_id")
    return None


def _tool_sequence(run_data: dict[str, Any]) -> list[str]:
    return [s["name"] for s in run_data.get("steps", []) if s.get("step_type") == "tool"]


def compare_runs(original: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    """Diff a replayed run against the original on the outcome fields that must match."""
    orig_run, new_run = original["run"], replay["run"]
    diffs: list[dict[str, Any]] = []

    def check(field: str, a: Any, b: Any) -> None:
        if a != b:
            diffs.append({"field": field, "original": a, "replay": b})

    check("intent", orig_run.get("intent"), new_run.get("intent"))
    check("status", orig_run.get("status"), new_run.get("status"))
    check("final_response", orig_run.get("final_response"), new_run.get("final_response"))
    check("pending_action", orig_run.get("pending_action"), new_run.get("pending_action"))
    check("tool_sequence", _tool_sequence(original), _tool_sequence(replay))

    return {"match": not diffs, "diffs": diffs}
