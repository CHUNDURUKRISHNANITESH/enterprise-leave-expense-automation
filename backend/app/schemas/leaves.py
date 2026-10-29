
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeaveRequestCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=32)
    leave_policy_id: str = Field(min_length=1, max_length=40)
    start_date: date
    end_date: date
    requested_days: Decimal = Field(gt=0, max_digits=7, decimal_places=2)
    reason: str | None = Field(default=None, max_length=2000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_date_range(self) -> "LeaveRequestCreate":
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date.")
        return self


class LeaveRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    leave_policy_id: str
    start_date: date
    end_date: date
    requested_days: Decimal
    reason: str | None
    status: str
    submitted_at: datetime | None
    decided_at: datetime | None
    decision_reason: str | None
    anomaly_flags: list[str]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class LeaveBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    leave_policy_id: str
    period_year: int
    entitled_days: Decimal
    used_days: Decimal
    pending_days: Decimal
    carryover_days: Decimal
    adjustment_days: Decimal
    available_days: Decimal
    last_calculated_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
