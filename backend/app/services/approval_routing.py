
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.models import ApprovalRule, ApprovalStep, Employee, LeaveRequest


def validate_approver(
    db: Session,
    *,
    approver_employee_id: str,
    requester_employee_id: str,
) -> Employee:
    """Validate an approver before assigning an approval step."""

    if approver_employee_id == requester_employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An employee cannot approve their own request.",
        )

    approver = db.get(Employee, approver_employee_id)

    if approver is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configured approver does not exist.",
        )

    if approver.employment_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configured approver is not an active employee.",
        )

    if not approver.is_approver:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee does not have approval authority.",
        )

    return approver


def resolve_manager_approver(
    db: Session,
    *,
    requester_employee_id: str,
) -> Employee:
    """Resolve and validate the requester's reporting manager."""

    requester = db.get(Employee, requester_employee_id)

    if requester is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requester employee does not exist.",
        )

    if requester.manager_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requester does not have a reporting manager.",
        )

    return validate_approver(
        db,
        approver_employee_id=requester.manager_id,
        requester_employee_id=requester.id,
    )


def resolve_explicit_approver(
    db: Session,
    *,
    requester_employee_id: str,
    approver_employee_id: str | None,
) -> Employee:
    """Resolve a specifically configured employee approver."""

    if not approver_employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval rule does not specify an approver employee.",
        )

    return validate_approver(
        db,
        approver_employee_id=approver_employee_id,
        requester_employee_id=requester_employee_id,
    )


def resolve_role_approver(
    db: Session,
    *,
    requester_employee_id: str,
    approver_role: str | None,
) -> Employee:
    """Resolve one authorized employee for a configured approval role."""

    if not approver_role or not approver_role.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approval rule does not specify an approver role.",
        )

    role = approver_role.strip()

    employees = db.scalars(
        select(Employee).where(
            Employee.is_approver.is_(True),
            Employee.employment_status == "ACTIVE",
        )
    ).all()

    eligible = []

    for employee in employees:
        attributes = employee.attributes

        if not isinstance(attributes, dict):
            continue

        roles = attributes.get("approval_roles", [])

        if not isinstance(roles, list):
            continue

        if not all(isinstance(item, str) for item in roles):
            continue

        if role not in roles:
            continue

        if employee.id == requester_employee_id:
            continue

        eligible.append(employee)

    if not eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No eligible approver found for role '{role}'.",
        )

    if len(eligible) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Multiple eligible approvers found for role '{role}'.",
        )

    return validate_approver(
        db,
        approver_employee_id=eligible[0].id,
        requester_employee_id=requester_employee_id,
    )


def find_matching_leave_rules(
    db: Session,
    *,
    country: str,
    as_of_date: date,
) -> list[ApprovalRule]:
    """Find applicable leave approval rules in deterministic order."""

    rules = db.scalars(
        select(ApprovalRule).where(
            ApprovalRule.is_active.is_(True),
            ApprovalRule.effective_from <= as_of_date,
            (
                (ApprovalRule.effective_to.is_(None))
                | (ApprovalRule.effective_to >= as_of_date)
            ),
            (
                (ApprovalRule.country == country)
                | (ApprovalRule.country.is_(None))
            ),
            (
                (ApprovalRule.category == "LEAVE")
                | (ApprovalRule.category.is_(None))
            ),
        )
    ).all()

    eligible = []

    for rule in rules:
        # Nonempty conditions require explicit implementation.
        if rule.conditions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Approval rule '{rule.id}' contains conditions "
                    "that are not supported yet."
                ),
            )

        # Expense-specific thresholds must not apply to leave.
        if (
            rule.min_amount != 0
            or rule.max_amount is not None
            or rule.currency is not None
        ):
            continue

        eligible.append(rule)

    # Prefer country-specific and leave-specific rules,
    # then use priority to resolve competition within a level.
    eligible.sort(
        key=lambda rule: (
            rule.approval_level,
            0 if rule.country == country else 1,
            0 if rule.category == "LEAVE" else 1,
            rule.priority,
            rule.id,
        )
    )

    selected = {}

    for rule in eligible:
        level = rule.approval_level

        if level not in selected:
            selected[level] = rule
            continue

        existing = selected[level]

        existing_rank = (
            0 if existing.country == country else 1,
            0 if existing.category == "LEAVE" else 1,
            existing.priority,
        )

        current_rank = (
            0 if rule.country == country else 1,
            0 if rule.category == "LEAVE" else 1,
            rule.priority,
        )

        if current_rank == existing_rank:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ambiguous approval rules at level {level}: "
                    f"'{existing.id}' and '{rule.id}'."
                ),
            )

    if not selected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No applicable leave approval rules configured.",
        )

    return [selected[level] for level in sorted(selected)]




def create_leave_approval_steps(
    db: Session,
    *,
    leave_request: LeaveRequest,
    as_of_date: date,
) -> list[ApprovalStep]:
    """Generate approval assignments for a submitted leave request.

    The caller is responsible for committing or rolling back.
    """

    existing_step = db.scalar(
        select(ApprovalStep.id).where(
            ApprovalStep.leave_request_id == leave_request.id
        )
    )

    if existing_step is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval steps already exist for this leave request.",
        )

    requester = db.get(Employee, leave_request.employee_id)

    if requester is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leave requester employee does not exist.",
        )

    rules = find_matching_leave_rules(
        db,
        country=requester.country,
        as_of_date=as_of_date,
    )

    steps = []

    for step_number, rule in enumerate(rules, start=1):
        approver_type = rule.approver_type.strip().upper()

        if approver_type == "MANAGER":
            approver = resolve_manager_approver(
                db,
                requester_employee_id=requester.id,
            )

        elif approver_type == "EMPLOYEE":
            approver = resolve_explicit_approver(
                db,
                requester_employee_id=requester.id,
                approver_employee_id=rule.approver_employee_id,
            )

        elif approver_type == "ROLE":
            approver = resolve_role_approver(
                db,
                requester_employee_id=requester.id,
                approver_role=rule.approver_role,
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported approver type: '{rule.approver_type}'.",
            )

        step = ApprovalStep(
            id=f"APR-{leave_request.id}-{step_number:02d}",
            leave_request_id=leave_request.id,
            expense_claim_id=None,
            rule_id=rule.id,
            step_number=step_number,
            approver_employee_id=approver.id,
            approver_role=rule.approver_role,
            status="PENDING",
            assigned_at=datetime.now(UTC),
            is_required=True,
            decision_metadata={},
        )

        steps.append(step)

    db.add_all(steps)

    return steps

