"""PostgreSQL persistence models for leave, expense, approval, and audit workflows."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint("employment_end_date IS NULL OR employment_end_date >= employment_start_date",
                        name="ck_employee_employment_dates"),
        Index("ix_employees_manager_id", "manager_id"),
        Index("ix_employees_country_department", "country", "department"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # EMP-000001
    employee_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(150))
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    cost_center_id: Mapped[str | None] = mapped_column(ForeignKey("cost_centers.id", ondelete="SET NULL"))
    employment_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    employment_end_date: Mapped[date | None] = mapped_column(Date)
    employment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    is_approver: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)

    manager: Mapped[Employee | None] = relationship(
        "Employee", remote_side="Employee.id", back_populates="direct_reports"
    )
    direct_reports: Mapped[list[Employee]] = relationship("Employee", back_populates="manager")
    leave_balances: Mapped[list[LeaveBalance]] = relationship(back_populates="employee")
    leave_requests: Mapped[list[LeaveRequest]] = relationship(
        back_populates="employee", foreign_keys="LeaveRequest.employee_id"
    )
    expense_claims: Mapped[list[ExpenseClaim]] = relationship(
        back_populates="employee", foreign_keys="ExpenseClaim.employee_id"
    )


class LeavePolicy(TimestampMixin, Base):
    __tablename__ = "leave_policies"
    __table_args__ = (
        CheckConstraint("annual_entitlement >= 0", name="ck_leave_policy_entitlement_nonnegative"),
        CheckConstraint("max_consecutive_days IS NULL OR max_consecutive_days > 0",
                        name="ck_leave_policy_max_days_positive"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from",
                        name="ck_leave_policy_effective_dates"),
        UniqueConstraint("policy_code", "version", name="uq_leave_policy_code_version"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    policy_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    leave_type: Mapped[str] = mapped_column(String(40), nullable=False)  # ANNUAL, SICK, etc.
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    annual_entitlement: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    accrual_frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="ANNUAL")
    carryover_limit: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    requires_documentation_after_days: Mapped[int | None] = mapped_column(Integer)
    max_consecutive_days: Mapped[int | None] = mapped_column(Integer)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rules: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)

    balances: Mapped[list[LeaveBalance]] = relationship(back_populates="policy")
    requests: Mapped[list[LeaveRequest]] = relationship(back_populates="policy")


class LeaveBalance(TimestampMixin, Base):
    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("employee_id", "leave_policy_id", "period_year",
                         name="uq_leave_balance_employee_policy_year"),
        CheckConstraint("entitled_days >= 0", name="ck_leave_balance_entitled_nonnegative"),
        CheckConstraint("used_days >= 0", name="ck_leave_balance_used_nonnegative"),
        CheckConstraint("pending_days >= 0", name="ck_leave_balance_pending_nonnegative"),
        Index("ix_leave_balances_employee_year", "employee_id", "period_year"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_policy_id: Mapped[str] = mapped_column(ForeignKey("leave_policies.id", ondelete="RESTRICT"), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    entitled_days: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    used_days: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    pending_days: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    carryover_days: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    adjustment_days: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False, default=0)
    last_calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    employee: Mapped[Employee] = relationship(back_populates="leave_balances")
    policy: Mapped[LeavePolicy] = relationship(back_populates="balances")
    # available_days is intentionally computed, not stored independently.
    @property
    def available_days(self) -> Decimal:
        return self.entitled_days + self.carryover_days + self.adjustment_days - self.used_days - self.pending_days


class LeaveRequest(TimestampMixin, Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_leave_request_date_order"),
        CheckConstraint("requested_days > 0", name="ck_leave_request_days_positive"),
        CheckConstraint("status IN ('DRAFT','SUBMITTED','PENDING_APPROVAL','NEEDS_REVIEW','APPROVED','REJECTED','CANCELLED')",
                        name="ck_leave_request_status"),
        Index("ix_leave_requests_employee_dates", "employee_id", "start_date", "end_date"),
        Index("ix_leave_requests_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # LVE-2026-000001
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    leave_policy_id: Mapped[str] = mapped_column(ForeignKey("leave_policies.id", ondelete="RESTRICT"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_days: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    anomaly_flags: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_TYPE, nullable=False, default=dict)

    employee: Mapped[Employee] = relationship(back_populates="leave_requests", foreign_keys=[employee_id])
    policy: Mapped[LeavePolicy] = relationship(back_populates="requests")
    approval_steps: Mapped[list[ApprovalStep]] = relationship(back_populates="leave_request")


class ExpensePolicy(TimestampMixin, Base):
    __tablename__ = "expense_policies"
    __table_args__ = (
        CheckConstraint("max_amount IS NULL OR max_amount >= 0", name="ck_expense_policy_max_nonnegative"),
        CheckConstraint("min_receipt_amount >= 0", name="ck_expense_policy_receipt_threshold_nonnegative"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from",
                        name="ck_expense_policy_effective_dates"),
        UniqueConstraint("policy_code", "version", name="uq_expense_policy_code_version"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    policy_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    per_item_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    min_receipt_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    receipt_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_business_purpose: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rules: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)


class CostCenter(TimestampMixin, Base):
    __tablename__ = "cost_centers"
    __table_args__ = (
        UniqueConstraint("code", "country", name="uq_cost_center_code_country"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    owner_employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)


class ExpenseClaim(TimestampMixin, Base):
    __tablename__ = "expense_claims"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_expense_claim_total_nonnegative"),
        CheckConstraint("status IN ('DRAFT','SUBMITTED','PENDING_APPROVAL','NEEDS_REVIEW','APPROVED','REJECTED','REIMBURSEMENT_PENDING','REIMBURSED','CANCELLED')",
                        name="ck_expense_claim_status"),
        Index("ix_expense_claim_employee_expense_date", "employee_id", "expense_date"),
        Index("ix_expense_claim_status_created", "status", "created_at"),
        Index("ix_expense_claim_receipt_hash", "receipt_hash"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # EXP-2026-000001
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    cost_center_id: Mapped[str | None] = mapped_column(ForeignKey("cost_centers.id", ondelete="SET NULL"))
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    business_purpose: Mapped[str | None] = mapped_column(Text)
    merchant: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    receipt_uri: Mapped[str | None] = mapped_column(Text)
    receipt_hash: Mapped[str | None] = mapped_column(String(128))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    anomaly_flags: Mapped[list[str]] = mapped_column(JSON_TYPE, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_TYPE, nullable=False, default=dict)

    employee: Mapped[Employee] = relationship(back_populates="expense_claims", foreign_keys=[employee_id])
    cost_center: Mapped[CostCenter | None] = relationship(foreign_keys=[cost_center_id])
    lines: Mapped[list[ExpenseLine]] = relationship(back_populates="claim", cascade="all, delete-orphan")
    approval_steps: Mapped[list[ApprovalStep]] = relationship(back_populates="expense_claim")
    reimbursement: Mapped[Reimbursement | None] = relationship(back_populates="claim", uselist=False)


class ExpenseLine(TimestampMixin, Base):
    __tablename__ = "expense_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_expense_line_quantity_positive"),
        CheckConstraint("unit_amount >= 0", name="ck_expense_line_unit_amount_nonnegative"),
        CheckConstraint("line_amount >= 0", name="ck_expense_line_amount_nonnegative"),
        UniqueConstraint("claim_id", "line_number", name="uq_expense_line_claim_line_number"),
        Index("ix_expense_lines_category_expense_date", "category", "expense_date"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # EXPL-<claim-id>-01
    claim_id: Mapped[str] = mapped_column(ForeignKey("expense_claims.id", ondelete="CASCADE"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=1)
    unit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    receipt_uri: Mapped[str | None] = mapped_column(Text)
    receipt_hash: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_TYPE, nullable=False, default=dict)

    claim: Mapped[ExpenseClaim] = relationship(back_populates="lines")


class ApprovalRule(TimestampMixin, Base):
    __tablename__ = "approval_rules"
    __table_args__ = (
        CheckConstraint("min_amount >= 0", name="ck_approval_rule_min_amount_nonnegative"),
        CheckConstraint("max_amount IS NULL OR max_amount >= min_amount", name="ck_approval_rule_amount_range"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from",
                        name="ck_approval_rule_effective_dates"),
        Index("ix_approval_rules_match", "country", "category", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    country: Mapped[str | None] = mapped_column(String(2))
    category: Mapped[str | None] = mapped_column(String(60))
    min_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    approver_type: Mapped[str] = mapped_column(String(30), nullable=False)  # MANAGER, ROLE, FINANCE, etc.
    approver_role: Mapped[str | None] = mapped_column(String(80))
    approver_employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    approval_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    conditions: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)


class ApprovalStep(TimestampMixin, Base):
    __tablename__ = "approval_steps"
    __table_args__ = (
        CheckConstraint(
            "(leave_request_id IS NOT NULL AND expense_claim_id IS NULL) OR "
            "(leave_request_id IS NULL AND expense_claim_id IS NOT NULL)",
            name="ck_approval_step_exactly_one_parent"
        ),
        CheckConstraint("step_number > 0", name="ck_approval_step_number_positive"),
        CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','SKIPPED','NEEDS_INFO')",
                        name="ck_approval_step_status"),
        UniqueConstraint("leave_request_id", "step_number", name="uq_approval_step_leave_number"),
        UniqueConstraint("expense_claim_id", "step_number", name="uq_approval_step_expense_number"),
        Index("ix_approval_steps_approver_status", "approver_employee_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # APR-<request-id>-01
    leave_request_id: Mapped[str | None] = mapped_column(ForeignKey("leave_requests.id", ondelete="CASCADE"))
    expense_claim_id: Mapped[str | None] = mapped_column(ForeignKey("expense_claims.id", ondelete="CASCADE"))
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("approval_rules.id", ondelete="SET NULL"))
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    approver_role: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    decision: Mapped[str | None] = mapped_column(String(20))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    decision_metadata: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)

    leave_request: Mapped[LeaveRequest | None] = relationship(back_populates="approval_steps")
    expense_claim: Mapped[ExpenseClaim | None] = relationship(back_populates="approval_steps")
    rule: Mapped[ApprovalRule | None] = relationship()


class Reimbursement(TimestampMixin, Base):
    __tablename__ = "reimbursements"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_reimbursement_amount_positive"),
        CheckConstraint("status IN ('PENDING','PROCESSING','PAID','FAILED','CANCELLED')",
                        name="ck_reimbursement_status"),
        UniqueConstraint("idempotency_key", name="uq_reimbursement_idempotency_key"),
        Index("ix_reimbursements_status_created", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # RMB-2026-000001
    claim_id: Mapped[str] = mapped_column(ForeignKey("expense_claims.id", ondelete="RESTRICT"), nullable=False, unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    payment_reference: Mapped[str | None] = mapped_column(String(150))
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_TYPE, nullable=False, default=dict)

    claim: Mapped[ExpenseClaim] = relationship(back_populates="reimbursement")


class AuditEvent(Base):
    """Append-only event log. Application code should INSERT only, never UPDATE/DELETE."""
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_entity_time", "entity_type", "entity_id", "occurred_at"),
        Index("ix_audit_events_actor_time", "actor_employee_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE)
    reason: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="API")
    extra: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)


class UserAccount(TimestampMixin, Base):
    """Authentication account associated with an employee."""

    __tablename__ = "user_accounts"

    __table_args__ = (
        CheckConstraint(
            "role IN ('EMPLOYEE', 'MANAGER', 'HR', 'ADMIN')",
            name="ck_user_account_role",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
    )

    employee_id: Mapped[str] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="EMPLOYEE",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    employee: Mapped[Employee] = relationship(
        "Employee",
    )


