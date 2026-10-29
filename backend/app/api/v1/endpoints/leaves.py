from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.api.deps import CurrentUser
from app.db.models.models import Employee, LeaveBalance, LeavePolicy, LeaveRequest
from app.db.session import get_db
from app.schemas.leaves import (
    LeaveBalanceResponse,
    LeaveRequestCreate,
    LeaveRequestResponse,
)
from app.services.approval_decisions import approve_leave_request, reject_leave_request
from app.services.approval_routing import create_leave_approval_steps
from app.services.audit import record_audit_event
from app.services.leave_balance import validate_leave_balances
from app.services.leave_calculator import calculate_working_days
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/leaves", tags=["Leaves"])

VALID_STATUSES = {
    "DRAFT",
    "SUBMITTED",
    "PENDING_APPROVAL",
    "NEEDS_REVIEW",
    "APPROVED",
    "REJECTED",
    "CANCELLED",
}


class AvailableLeavePolicyResponse(BaseModel):
    id: str
    name: str
    leave_type: str
    available_days: Decimal
    annual_entitlement: Decimal
    max_consecutive_days: int | None
    effective_from: date
    effective_to: date | None


@router.get(
    "/policies",
    response_model=list[AvailableLeavePolicyResponse],
)
def get_available_leave_policies(
    current_user: CurrentUser,
    year: int = Query(
        default_factory=lambda: date.today().year,
        ge=2000,
        le=2200,
    ),
    db: Session = Depends(get_db),
) -> list[AvailableLeavePolicyResponse]:
    """Return leave policies linked to the authenticated employee's balances."""

    employee = db.get(Employee, current_user.employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    statement = (
        select(LeavePolicy, LeaveBalance)
        .join(
            LeaveBalance,
            LeaveBalance.leave_policy_id == LeavePolicy.id,
        )
        .where(
            LeaveBalance.employee_id == current_user.employee_id,
            LeaveBalance.period_year == year,
            LeavePolicy.country == employee.country,
        )
        .order_by(LeavePolicy.name)
    )

    results = db.execute(statement).all()

    return [
        AvailableLeavePolicyResponse(
            id=policy.id,
            name=policy.name,
            leave_type=policy.leave_type,
            available_days=balance.available_days,
            annual_entitlement=policy.annual_entitlement,
            max_consecutive_days=policy.max_consecutive_days,
            effective_from=policy.effective_from,
            effective_to=policy.effective_to,
        )
        for policy, balance in results
    ]



@router.post(
    "",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_201_CREATED,
)

def create_leave_request(
    payload: LeaveRequestCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> LeaveRequest:
    employee = db.get(Employee, payload.employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee does not exist.",
        )

    if payload.employee_id != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees can only create leave requests for themselves.",
        )

    policy = db.get(LeavePolicy, payload.leave_policy_id)

    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave policy does not exist.",
        )

    if employee.country.upper() != policy.country.upper():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave policy country does not match employee country.",
        )

    if (
        payload.start_date < policy.effective_from
        or (
            policy.effective_to is not None
            and payload.end_date > policy.effective_to
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave dates fall outside the policy effective period.",
        )

    if employee.employment_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active employees can create leave requests.",
        )

    if payload.start_date < employee.employment_start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave cannot start before the employee's employment date.",
        )

    if (
        employee.employment_end_date is not None
        and payload.end_date > employee.employment_end_date
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave cannot extend beyond the employee's employment end date.",
        )

    working_days = calculate_working_days(
        payload.start_date,
        payload.end_date,
    )

    if working_days == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave request must include at least one working day.",
        )

    if payload.requested_days != Decimal(working_days):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Requested days must equal {working_days} "
                "working days for the selected date range."
            ),
        )

    if (
        policy.max_consecutive_days is not None
        and working_days > policy.max_consecutive_days
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested leave exceeds the policy's consecutive-day limit.",
        )

    validate_leave_balances(
        db=db,
        employee_id=payload.employee_id,
        leave_policy_id=payload.leave_policy_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )

    leave_request = LeaveRequest(
        id=f"LVE-{payload.start_date.year}-{uuid4().hex[:12]}",
        employee_id=payload.employee_id,
        leave_policy_id=payload.leave_policy_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        requested_days=payload.requested_days,
        reason=payload.reason,
        metadata_json=payload.metadata_json,
        status="DRAFT",
    )

    db.add(leave_request)

    try:
        db.commit()
        db.refresh(leave_request)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Leave request could not be created because a database constraint was violated.",
        )

    return leave_request


@router.post(
    "/{leave_request_id}/submit",
    response_model=LeaveRequestResponse,
)
def submit_leave_request(
    leave_request_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> LeaveRequest:
    try:
        # Read the request to identify its employee.
        leave_request = db.get(LeaveRequest, leave_request_id)

        if leave_request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found.",
            )
        if leave_request.employee_id != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only submit their own leave requests.",
            )

        # Serialize submissions for the same employee in PostgreSQL.
        employee = db.scalar(
            select(Employee)
            .where(Employee.id == leave_request.employee_id)
            .with_for_update()
        )

        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found.",
            )

        # Refresh the request after acquiring the employee lock.
        db.refresh(leave_request)

        if leave_request.status != "DRAFT":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft leave requests can be submitted.",
            )

        if employee.employment_status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only active employees can submit leave requests.",
            )

        # Detect overlapping active leave requests.
        overlapping_request = db.scalar(
            select(LeaveRequest.id).where(
                LeaveRequest.employee_id == leave_request.employee_id,
                LeaveRequest.id != leave_request.id,
                LeaveRequest.status.in_(
                    [
                        "SUBMITTED",
                        "PENDING_APPROVAL",
                        "NEEDS_REVIEW",
                        "APPROVED",
                    ]
                ),
                LeaveRequest.start_date <= leave_request.end_date,
                LeaveRequest.end_date >= leave_request.start_date,
            ).limit(1)
        )

        if overlapping_request is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Leave request overlaps with an existing active leave request.",
            )

        # Revalidate balances and lock the matching balance records.
        validated_balances = validate_leave_balances(
            db=db,
            employee_id=leave_request.employee_id,
            leave_policy_id=leave_request.leave_policy_id,
            start_date=leave_request.start_date,
            end_date=leave_request.end_date,
            lock_for_update=True,
        )

        # Reserve days without marking them as used.
        for balance, required_days in validated_balances:
            balance.pending_days += required_days

        leave_request.status = "SUBMITTED"
        leave_request.submitted_at = datetime.now(UTC)
        # Generate approval assignments within the same transaction.
        create_leave_approval_steps(
            db=db,
            leave_request=leave_request,
            as_of_date=leave_request.submitted_at.date(),
        )

        record_audit_event(
            db=db,
            entity_type="LEAVE_REQUEST",
            entity_id=leave_request.id,
            event_type="LEAVE_SUBMITTED",
            actor_employee_id=leave_request.employee_id,
            old_values={"status": "DRAFT"},
            new_values={"status": "SUBMITTED"},
            reason="Leave request submitted for approval.",
        )

        db.commit()
        db.refresh(leave_request)

        return leave_request

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

@router.get("", response_model=list[LeaveRequestResponse])

def list_leave_requests(
    current_user: CurrentUser,
    employee_id: str | None = None,
    leave_status: str | None = Query(default=None, alias="status"),
    start_date: date | None = None,
    end_date: date | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[LeaveRequest]:
    if leave_status is not None and leave_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid leave request status.",
        )

    if start_date is not None and end_date is not None and end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="End date cannot be before start date.",
        )

    statement = select(LeaveRequest).where(LeaveRequest.employee_id == current_user.employee_id).order_by(
        LeaveRequest.created_at.desc(),
        LeaveRequest.id,
    )

    if employee_id is not None:
        statement = statement.where(LeaveRequest.employee_id == employee_id)

    if leave_status is not None:
        statement = statement.where(LeaveRequest.status == leave_status)

    if start_date is not None:
        statement = statement.where(LeaveRequest.end_date >= start_date)

    if end_date is not None:
        statement = statement.where(LeaveRequest.start_date <= end_date)

    statement = statement.offset(offset).limit(limit)
    return list(db.scalars(statement).all())



@router.get(
    "/balances/{employee_id}",
    response_model=list[LeaveBalanceResponse],
)
def get_employee_leave_balances(
    employee_id: str,
    current_user: CurrentUser,
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2200),
    db: Session = Depends(get_db),
) -> list[LeaveBalance]:

    # HR and ADMIN can view employee leave balances.
    # Other users can only view their own balances.
    if (
        employee_id != current_user.employee_id
        and current_user.role not in ("HR", "ADMIN")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees can only view their own leave balances.",
        )

    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found.",
        )

    statement = (
        select(LeaveBalance)
        .where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.period_year == year,
        )
        .order_by(LeaveBalance.leave_policy_id)
    )

    return list(db.scalars(statement).all())



@router.get("/{leave_request_id}", response_model=LeaveRequestResponse)
def get_leave_request(
    leave_request_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> LeaveRequest:
    leave_request = db.get(LeaveRequest, leave_request_id)

    if leave_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Leave request not found.",
        )
    if leave_request.employee_id != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees can only view their own leave requests.",
        )    

    return leave_request


@router.post(
    "/{leave_request_id}/approve",
    response_model=LeaveRequestResponse,
)
def approve_leave_request_endpoint(
    leave_request_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> LeaveRequest:
    """Approve a leave request as the authenticated assigned approver."""

    return approve_leave_request(
        db=db,
        leave_request_id=leave_request_id,
        actor_employee_id=current_user.employee_id,
    )

class LeaveRejectionRequest(BaseModel):
    reason: str = Field(min_length=1)


@router.post(
    "/{leave_request_id}/reject",
    response_model=LeaveRequestResponse,
)
def reject_leave_request_endpoint(
    leave_request_id: str,
    payload: LeaveRejectionRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> LeaveRequest:
    """Reject a leave request as the authenticated assigned approver."""

    return reject_leave_request(
        db=db,
        leave_request_id=leave_request_id,
        actor_employee_id=current_user.employee_id,
        reason=payload.reason,
    )
