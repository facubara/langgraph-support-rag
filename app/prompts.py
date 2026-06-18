"""Versioned prompts.

Keeping prompts versioned (rather than inline) is what makes prompt regression testing
possible: the eval runner can run the suite under v1 vs v2 and the compare tool reports any
metric drift. Select the active version with `PROMPT_VERSION` in the environment.
"""

from __future__ import annotations

RESPONSE_PROMPTS: dict[str, str] = {
    "v1": (
        "You are a SaaS customer-support assistant. Answer the user's question using the "
        "provided context. If a refund or escalation is proposed, mention it."
    ),
    "v2": (
        "You are a SaaS customer-support assistant. Answer ONLY using the provided context "
        "(tool results and knowledge-base passages). If the context does not support an "
        "answer, say you don't have enough information and offer to escalate. Never invent "
        "account details. When an action requires human approval, state that clearly."
    ),
}


def get_response_prompt(version: str) -> str:
    return RESPONSE_PROMPTS.get(version, RESPONSE_PROMPTS["v2"])
