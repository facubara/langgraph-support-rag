"""Tool registry + a single validating gateway. Every tool call goes through
`call_tool`, which validates arguments against the tool's schema before execution and
flags whether the action needs human approval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from . import business, schemas


class ToolValidationError(Exception):
    """Raised when a tool name is unknown or its arguments fail validation."""


@dataclass(frozen=True)
class Tool:
    name: str
    func: Callable[..., dict[str, Any]]
    args_model: type[BaseModel]
    requires_approval: bool
    description: str


_TOOL_LIST = [
    Tool(
        "get_customer_profile",
        business.get_customer_profile,
        schemas.GetCustomerProfileArgs,
        False,
        "Fetch a customer's profile, plan, and account status.",
    ),
    Tool(
        "get_invoice_history",
        business.get_invoice_history,
        schemas.GetInvoiceHistoryArgs,
        False,
        "List a customer's invoices and charges.",
    ),
    Tool(
        "check_refund_policy",
        business.check_refund_policy,
        schemas.CheckRefundPolicyArgs,
        False,
        "Look up the refund policy that applies to a plan.",
    ),
    Tool(
        "create_refund_ticket",
        business.create_refund_ticket,
        schemas.CreateRefundTicketArgs,
        True,
        "Create a refund ticket. Risky — requires human approval.",
    ),
    Tool(
        "escalate_to_human",
        business.escalate_to_human,
        schemas.EscalateToHumanArgs,
        True,
        "Escalate the conversation to a human agent. Requires approval.",
    ),
]

TOOLS: dict[str, Tool] = {t.name: t for t in _TOOL_LIST}


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    tool = TOOLS.get(name)
    if tool is None:
        raise ToolValidationError(f"Unknown tool: {name!r}")
    try:
        validated = tool.args_model(**args)
    except ValidationError as err:
        raise ToolValidationError(f"Invalid arguments for {name!r}: {err}") from err
    result = tool.func(**validated.model_dump())
    return {"tool": name, "requires_approval": tool.requires_approval, "result": result}
