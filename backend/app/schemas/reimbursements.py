
"""Pydantic schemas for reimbursement operations."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReimbursementCreate(BaseModel):
    claim_id: str = Field(min_length=1, max_length=40)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ReimbursementPayment(BaseModel):
    payment_reference: str = Field(
        min_length=1,
        max_length=150,
    )


class ReimbursementFailure(BaseModel):
    failure_reason: str = Field(min_length=1)


class ReimbursementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_id: str
    amount: Decimal
    currency: str
    status: Literal[
        "PENDING",
        "PROCESSING",
        "PAID",
        "FAILED",
        "CANCELLED",
    ]
    idempotency_key: str
    payment_reference: str | None
    initiated_at: datetime | None
    paid_at: datetime | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
