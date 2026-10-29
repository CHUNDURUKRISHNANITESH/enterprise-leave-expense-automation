from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    employee_number: str = Field(min_length=1, max_length=32)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    job_title: str | None = Field(default=None, max_length=150)
    department: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=2, max_length=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    manager_id: str | None = None
    cost_center_id: str | None = None
    employment_start_date: date
    employment_end_date: date | None = None
    employment_status: str = Field(default="ACTIVE", max_length=20)
    is_approver: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class EmployeeUpdate(BaseModel):
    employee_number: str | None = Field(default=None, min_length=1, max_length=32)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    job_title: str | None = Field(default=None, max_length=150)
    department: str | None = Field(default=None, min_length=1, max_length=120)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    manager_id: str | None = None
    cost_center_id: str | None = None
    employment_start_date: date | None = None
    employment_end_date: date | None = None
    employment_status: str | None = Field(default=None, max_length=20)
    is_approver: bool | None = None
    attributes: dict[str, Any] | None = None


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_number: str
    first_name: str
    last_name: str
    email: str
    job_title: str | None
    department: str
    country: str
    currency: str
    manager_id: str | None
    cost_center_id: str | None
    employment_start_date: date
    employment_end_date: date | None
    employment_status: str
    is_approver: bool
    attributes: dict[str, Any]
    created_at: datetime
    updated_at: datetime