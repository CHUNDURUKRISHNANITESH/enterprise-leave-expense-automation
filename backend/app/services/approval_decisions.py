
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.models import ApprovalStep, Employee, LeaveRequest
from app.services.audit import record_audit_event
from app.services.leave_balance import get_reserved_leave_balances


def get_next_pending_approval_step(
    db: Session,
    leave_request: LeaveRequest,
) -> ApprovalStep:
    """Return the first pending step after all earlier steps are approved."""

    steps = list(
        db.scalars(
            select(ApprovalStep)
            .where(
                ApprovalStep.leave_request_id == leave_request.id
            )
            .order_by(ApprovalStep.step_number)
            .with_for_update()
        ).all()
    )

    if not steps:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No approval steps exist for this leave request.",
        )

    for step in steps:
        if step.status in ("APPROVED", "SKIPPED"):
            continue

        if step.status == "PENDING":
            return step

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Approval step {step.step_number} "
                f"cannot proceed because its status is {step.status}."
            ),
        )

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="No pending approval steps remain.",
    )


def validate_leave_approval_actor(
    db: Session,
    leave_request: LeaveRequest,
    approval_step: ApprovalStep,
    actor_employee_id: str,
) -> Employee:
    """Validate the employee making a leave approval decision."""

    if leave_request.status not in ("SUBMITTED", "PENDING_APPROVAL"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Leave request is not awaiting approval.",
        )

    if actor_employee_id == leave_request.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees cannot approve their own leave requests.",
        )

    actor = db.get(Employee, actor_employee_id)

    if actor is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Approver does not exist.",
        )

    if actor.employment_status != "ACTIVE" or not actor.is_approver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee is not an active authorized approver.",
        )

    if approval_step.approver_employee_id != actor_employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee is not assigned to the current approval step.",
        )

    return actor


def approve_leave_request(
    db: Session,
    leave_request_id: str,
    actor_employee_id: str,
    reason: str | None = None,
) -> LeaveRequest:
    """Approve the next eligible step and finalize leave if all steps pass."""

    try:
        leave_request = db.scalar(
            select(LeaveRequest)
            .where(LeaveRequest.id == leave_request_id)
            .with_for_update()
        )

        if leave_request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found.",
            )

        step = get_next_pending_approval_step(db, leave_request)

        validate_leave_approval_actor(
            db=db,
            leave_request=leave_request,
            approval_step=step,
            actor_employee_id=actor_employee_id,
        )

        # Verify the reserved balance before changing the final step.
        remaining_steps = list(
            db.scalars(
                select(ApprovalStep)
                .where(
                    ApprovalStep.leave_request_id == leave_request.id,
                    ApprovalStep.step_number > step.step_number,
                    ApprovalStep.is_required.is_(True),
                )
                .order_by(ApprovalStep.step_number)
            ).all()
        )

        is_final_approval = len(remaining_steps) == 0

        reserved_balances = []
        if is_final_approval:
            reserved_balances = get_reserved_leave_balances(
                db=db,
                employee_id=leave_request.employee_id,
                leave_policy_id=leave_request.leave_policy_id,
                start_date=leave_request.start_date,
                end_date=leave_request.end_date,
            )

        now = datetime.now(UTC)
        old_status = leave_request.status

        step.status = "APPROVED"
        step.decision = "APPROVED"
        step.decision_reason = reason
        step.decided_at = now

        if is_final_approval:
            for balance, required_days in reserved_balances:
                balance.pending_days -= required_days
                balance.used_days += required_days

            leave_request.status = "APPROVED"
            leave_request.decided_at = now
            leave_request.decision_reason = reason
        else:
            leave_request.status = "PENDING_APPROVAL"

        record_audit_event(
            db=db,
            entity_type="LEAVE_REQUEST",
            entity_id=leave_request.id,
            event_type="LEAVE_APPROVED" if is_final_approval else "LEAVE_STEP_APPROVED",
            actor_employee_id=actor_employee_id,
            old_values={"status": old_status},
            new_values={
                "status": leave_request.status,
                "approval_step": step.step_number,
            },
            reason=reason or "Leave approval step completed.",
        )

        db.commit()
        db.refresh(leave_request)
        return leave_request

    except Exception:
        db.rollback()
        raise


def reject_leave_request(
    db: Session,
    leave_request_id: str,
    actor_employee_id: str,
    reason: str,
) -> LeaveRequest:
    """Reject the next approval step and release reserved leave days."""

    if not reason or not reason.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A rejection reason is required.",
        )

    try:
        leave_request = db.scalar(
            select(LeaveRequest)
            .where(LeaveRequest.id == leave_request_id)
            .with_for_update()
        )

        if leave_request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leave request not found.",
            )

        step = get_next_pending_approval_step(
            db=db,
            leave_request=leave_request,
        )

        validate_leave_approval_actor(
            db=db,
            leave_request=leave_request,
            approval_step=step,
            actor_employee_id=actor_employee_id,
        )

        reserved_balances = get_reserved_leave_balances(
            db=db,
            employee_id=leave_request.employee_id,
            leave_policy_id=leave_request.leave_policy_id,
            start_date=leave_request.start_date,
            end_date=leave_request.end_date,
        )

        now = datetime.now(UTC)
        old_status = leave_request.status

        step.status = "REJECTED"
        step.decision = "REJECTED"
        step.decision_reason = reason.strip()
        step.decided_at = now

        for balance, required_days in reserved_balances:
            balance.pending_days -= required_days

        leave_request.status = "REJECTED"
        leave_request.decided_at = now
        leave_request.decision_reason = reason.strip()

        record_audit_event(
            db=db,
            entity_type="LEAVE_REQUEST",
            entity_id=leave_request.id,
            event_type="LEAVE_REJECTED",
            actor_employee_id=actor_employee_id,
            old_values={"status": old_status},
            new_values={
                "status": "REJECTED",
                "approval_step": step.step_number,
            },
            reason=reason.strip(),
        )

        db.commit()
        db.refresh(leave_request)

        return leave_request

    except Exception:
        db.rollback()
        raise



