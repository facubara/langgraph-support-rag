"""The four agents, implemented as LangGraph nodes.

Design note: control-flow decisions (intent, tool selection, policy, grounding) are
deterministic rule logic so the system is reproducible and evaluable. The LLM is used for
the user-facing *phrasing* in the Response agent. Swapping the rule-based router for an
LLM classifier is a drop-in change — the node boundary is the same.
"""

from __future__ import annotations

import re
import time
from typing import Any

from ..config import settings
from ..llm.factory import get_llm
from ..tools.registry import call_tool

_CUSTOMER_RE = re.compile(r"cus_\d+")

# Keyword sets for intent classification, checked in priority order.
_INTENT_RULES = [
    ("escalation", ("speak to a human", "speak to someone", "real person", "manager",
                     "escalate", "representative", "agent please")),
    ("duplicate_charge", ("duplicate", "charged twice", "double charge", "double charged",
                          "billed twice", "two charges", "charged me twice")),
    ("refund_request", ("refund", "money back", "reimburse", "reimbursement")),
    ("billing_question", ("invoice", "charge", "bill", "billed", "payment", "price",
                          "plan", "subscription", "receipt")),
]


def _step(step_type: str, name: str, started: float, **fields: Any) -> dict[str, Any]:
    step = {
        "step_type": step_type,
        "name": name,
        "latency_ms": (time.perf_counter() - started) * 1000,
        "cost_usd": 0.0,
    }
    step.update(fields)
    return step


# --------------------------------------------------------------------------- router
def router(state: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    message = state["message"]
    low = message.lower()

    customer_id = state.get("customer_id")
    if not customer_id:
        match = _CUSTOMER_RE.search(message)
        customer_id = match.group(0) if match else None

    intent = "other"
    for label, keywords in _INTENT_RULES:
        if any(k in low for k in keywords):
            intent = label
            break

    return {
        "customer_id": customer_id,
        "intent": intent,
        "trace": [
            _step("router", "router", started,
                  input={"message": message},
                  output={"intent": intent, "customer_id": customer_id})
        ],
    }


def route_after_router(state: dict[str, Any]) -> str:
    """Conditional edge: billing-ish intents go through tools/RAG; everything else
    hands straight off to the Response agent."""
    from .state import BILLING_INTENTS

    return "billing_rag" if state.get("intent") in BILLING_INTENTS else "response"


# ----------------------------------------------------------------- billing / RAG agent
def billing_rag(state: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    intent = state.get("intent")
    customer_id = state.get("customer_id")

    tool_calls: list[dict[str, Any]] = []
    context: list[dict[str, Any]] = []

    # RAG: retrieve top-k KB candidates, then split by score threshold so we can show
    # exactly what context was included vs. excluded for this run.
    candidates: list[dict[str, Any]] = []
    try:
        from ..rag.retriever import get_retriever

        candidates = get_retriever().search(state["message"], k=settings.rag_top_k)
    except Exception:
        candidates = []
    threshold = settings.rag_min_score
    retrieved = [c for c in candidates if c["score"] >= threshold]
    excluded = [{"source": "kb", **c} for c in candidates if c["score"] < threshold]
    context.extend({"source": "kb", **c} for c in retrieved)

    # Tool use: pull the customer's profile + invoices when we know who they are.
    if customer_id:
        for tool in ("get_customer_profile", "get_invoice_history"):
            out = call_tool(tool, {"customer_id": customer_id})
            tool_calls.append(out)
            context.append({"source": "tool", "tool": tool, "data": out["result"]})

    # Refund/duplicate questions need the policy too.
    if intent in ("refund_request", "duplicate_charge"):
        plan = "default"
        for c in context:
            if c.get("source") == "tool" and c.get("tool") == "get_customer_profile":
                plan = c["data"].get("plan", "default")
        out = call_tool("check_refund_policy", {"plan": plan, "reason": intent})
        tool_calls.append(out)
        context.append({"source": "tool", "tool": "check_refund_policy", "data": out["result"]})

    trace = [_step("tool", tc["tool"], started, output=tc["result"]) for tc in tool_calls]
    trace.insert(0, _step("agent", "billing_rag", started,
                          input={"intent": intent, "customer_id": customer_id},
                          output={
                              "included": [{"title": c["title"], "score": c["score"]} for c in retrieved],
                              "excluded": [{"title": c["title"], "score": c["score"]} for c in excluded],
                              "tools": [t["tool"] for t in tool_calls],
                          }))

    return {
        "retrieved": retrieved,
        "context_included": context,
        "context_excluded": excluded,
        "tool_calls": tool_calls,
        "trace": trace,
    }


# --------------------------------------------------------------- policy / safety agent
def _find_duplicate(invoices: list[dict[str, Any]]) -> dict[str, Any] | None:
    seen: dict[tuple, dict] = {}
    for inv in invoices:
        key = (inv.get("amount"), inv.get("date"))
        if key in seen:
            return inv  # the second occurrence is the duplicate
        seen[key] = inv
    return None


def policy_safety(state: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    intent = state.get("intent")
    context = state.get("context_included", [])
    customer_id = state.get("customer_id")

    profile = next((c["data"] for c in context if c.get("tool") == "get_customer_profile"), {})
    invoices = next((c["data"]["invoices"] for c in context if c.get("tool") == "get_invoice_history"), [])
    policy = next((c["data"]["policy"] for c in context if c.get("tool") == "check_refund_policy"), {})

    grounded = bool(context)
    pending_action: dict[str, Any] | None = None
    decision: dict[str, Any] = {"intent": intent}

    if intent == "escalation":
        pending_action = {"action": "escalate_to_human", "customer_id": customer_id,
                          "reason": "customer requested a human"}
        decision["outcome"] = "escalate"

    elif intent == "duplicate_charge":
        dup = _find_duplicate(invoices)
        if dup is None:
            decision["outcome"] = "no_duplicate_found"
        elif policy.get("duplicate_charges") == "review_required":
            pending_action = {"action": "escalate_to_human", "customer_id": customer_id,
                              "reason": f"duplicate on {dup['invoice_id']} needs review"}
            decision["outcome"] = "escalate_review"
        else:
            pending_action = {"action": "create_refund_ticket", "customer_id": customer_id,
                              "invoice_id": dup["invoice_id"], "amount": dup["amount"],
                              "reason": "duplicate charge"}
            decision["outcome"] = "propose_refund"

    elif intent == "refund_request":
        if not policy:
            decision["outcome"] = "no_policy"
        elif policy.get("window_days", 0) <= 0:
            pending_action = {"action": "escalate_to_human", "customer_id": customer_id,
                              "reason": "refund outside automated policy"}
            decision["outcome"] = "escalate_contract"
        elif invoices:
            target = invoices[-1]
            pending_action = {"action": "create_refund_ticket", "customer_id": customer_id,
                              "invoice_id": target["invoice_id"], "amount": target["amount"],
                              "reason": "refund requested within window"}
            decision["outcome"] = "propose_refund"
        else:
            decision["outcome"] = "no_invoice"

    else:  # billing_question
        decision["outcome"] = "informational"

    return {
        "grounded": grounded,
        "pending_action": pending_action,
        "trace": [_step("agent", "policy_safety", started,
                        input={"intent": intent}, output=decision)],
    }


# ---------------------------------------------------------------------- response agent
_SYSTEM = (
    "You are a SaaS customer-support assistant. Answer ONLY using the provided context "
    "(tool results and knowledge-base passages). If the context does not support an answer, "
    "say you don't have enough information and offer to escalate. Never invent account details."
)


def _context_to_text(context: list[dict[str, Any]]) -> str:
    lines = []
    for c in context:
        if c.get("source") == "tool":
            lines.append(f"[tool:{c['tool']}] {c['data']}")
        elif c.get("source") == "kb":
            lines.append(f"[kb:{c.get('title', '?')}] {c.get('text', '')}")
    return "\n".join(lines) if lines else "(no context retrieved)"


def response(state: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    grounded = state.get("grounded", False)
    pending = state.get("pending_action")
    context = state.get("context_included", [])

    if not grounded:
        text = ("I don't have enough information in our records or knowledge base to answer that "
                "confidently. I can connect you with a human agent if you'd like.")
        return {
            "final_response": text,
            "status": "completed",
            "trace": [_step("agent", "response", started, output={"mode": "refusal"})],
        }

    prompt = (
        f"User message: {state['message']}\n\n"
        f"Context:\n{_context_to_text(context)}\n\n"
        f"Proposed action requiring human approval: {pending}\n\n"
        "Write a concise, grounded reply."
    )
    llm = get_llm()
    resp = llm.complete(system=_SYSTEM, prompt=prompt)

    text = resp.text
    if pending is not None:
        text = (f"{text}\n\nProposed next step (awaiting human approval): "
                f"{pending['action']}.")
        status = "awaiting_approval"
    else:
        status = "completed"

    return {
        "final_response": text,
        "status": status,
        "trace": [_step("llm", resp.model, started,
                        input={"prompt": prompt}, output={"text": resp.text},
                        latency_ms=resp.latency_ms, cost_usd=resp.cost_usd)],
    }
