
"""Authenticated reimbursement API endpoints."""

from app.api.deps import CurrentUser, require_roles
from app.db.models.models import ExpenseClaim, Reimbursement
from app.db.session import get_db
from app.schemas.reimbursements import (
    ReimbursementCreate,
    ReimbursementFailure,
    ReimbursementPayment,
    ReimbursementResponse,
)
from app.services.reimbursements import (
    fail_reimbursement,
    initiate_reimbursement,
    pay_reimbursement,
    process_reimbursement,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/reimbursements",
    tags=["Reimbursements"],
)

FinanceUser = Depends(require_roles("ADMIN", "HR"))


@router.post(
    "",
    response_model=ReimbursementResponse,
    status_code=201,
    dependencies=[FinanceUser],
)
def create_reimbursement(
    payload: ReimbursementCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    return initiate_reimbursement(
        db,
        claim_id=payload.claim_id,
        idempotency_key=payload.idempotency_key,
        actor_employee_id=current_user.employee_id,
    )


@router.get(
    "",
    response_model=list[ReimbursementResponse],
)
def list_reimbursements(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    statement = (
        select(Reimbursement)
        .order_by(Reimbursement.created_at.desc())
        .limit(200)
    )

    # ADMIN and HR can view all reimbursements.
    # Other users can view only their own reimbursements.
    if current_user.role not in ("ADMIN", "HR"):
        statement = (
            statement
            .join(
                ExpenseClaim,
                ExpenseClaim.id == Reimbursement.claim_id,
            )
            .where(
                ExpenseClaim.employee_id
                == current_user.employee_id
            )
        )

    return list(db.scalars(statement).all())


@router.get(
    "/{reimbursement_id}",
    response_model=ReimbursementResponse,
)
def get_reimbursement(
    reimbursement_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    reimbursement = db.get(
        Reimbursement,
        reimbursement_id,
    )

    if reimbursement is None:
        raise HTTPException(
            status_code=404,
            detail="Reimbursement not found.",
        )

    # ADMIN and HR can access any reimbursement.
    # Other users can access only their own reimbursements.
    if (
        current_user.role not in ("ADMIN", "HR")
        and reimbursement.claim.employee_id
        != current_user.employee_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied.",
        )

    return reimbursement


@router.post(
    "/{reimbursement_id}/process",
    response_model=ReimbursementResponse,
    dependencies=[FinanceUser],
)
def process_payment(
    reimbursement_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    return process_reimbursement(
        db,
        reimbursement_id=reimbursement_id,
        actor_employee_id=current_user.employee_id,
    )


@router.post(
    "/{reimbursement_id}/pay",
    response_model=ReimbursementResponse,
    dependencies=[FinanceUser],
)
def confirm_payment(
    reimbursement_id: str,
    payload: ReimbursementPayment,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    return pay_reimbursement(
        db,
        reimbursement_id=reimbursement_id,
        payment_reference=payload.payment_reference,
        actor_employee_id=current_user.employee_id,
    )


@router.post(
    "/{reimbursement_id}/fail",
    response_model=ReimbursementResponse,
    dependencies=[FinanceUser],
)
def record_payment_failure(
    reimbursement_id: str,
    payload: ReimbursementFailure,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    return fail_reimbursement(
        db,
        reimbursement_id=reimbursement_id,
        failure_reason=payload.failure_reason,
        actor_employee_id=current_user.employee_id,
    )
