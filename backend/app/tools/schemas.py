"""Pydantic argument models — every tool call is validated against one of these."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GetCustomerProfileArgs(BaseModel):
    customer_id: str = Field(..., description="Customer id, e.g. cus_001")


class GetInvoiceHistoryArgs(BaseModel):
    customer_id: str = Field(..., description="Customer id, e.g. cus_001")


class CheckRefundPolicyArgs(BaseModel):
    plan: str = Field(..., description="Plan name, e.g. pro, team, enterprise")
    reason: str | None = Field(None, description="Optional refund reason")


class CreateRefundTicketArgs(BaseModel):
    customer_id: str
    invoice_id: str
    amount: float = Field(..., gt=0, description="Refund amount in USD")
    reason: str


class EscalateToHumanArgs(BaseModel):
    customer_id: str
    reason: str
