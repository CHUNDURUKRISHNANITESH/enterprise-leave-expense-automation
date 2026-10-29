
from decimal import Decimal

from app.api.deps import require_roles
from app.db.models.models import (
    ApprovalStep,
    Employee,
    ExpenseClaim,
    LeaveRequest,
    Reimbursement,
)
from app.db.session import get_db
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    dependencies=[Depends(require_roles("ADMIN"))],
)
def dashboard_summary(db: Session = Depends(get_db)):
    total_employees = db.scalar(
        select(func.count()).select_from(Employee)
    ) or 0

    total_leave_requests = db.scalar(
        select(func.count()).select_from(LeaveRequest)
    ) or 0

    pending_leave_requests = db.scalar(
        select(func.count())
        .select_from(LeaveRequest)
        .where(LeaveRequest.status == "PENDING")
    ) or 0

    total_expense_claims = db.scalar(
        select(func.count()).select_from(ExpenseClaim)
    ) or 0

    pending_approval_steps = db.scalar(
        select(func.count())
        .select_from(ApprovalStep)
        .where(ApprovalStep.status == "PENDING")
    ) or 0

    total_reimbursements = db.scalar(
        select(func.count()).select_from(Reimbursement)
    ) or 0

    expense_amounts = db.execute(
        select(
            ExpenseClaim.currency,
            func.sum(ExpenseClaim.total_amount),
        ).group_by(ExpenseClaim.currency)
    ).all()

    paid_amounts = db.execute(
        select(
            Reimbursement.currency,
            func.sum(Reimbursement.amount),
        )
        .where(Reimbursement.status == "PAID")
        .group_by(Reimbursement.currency)
    ).all()

    def format_amounts(rows):
        return {
            currency: str(amount or Decimal(0))
            for currency, amount in rows
        }

    return {
        "total_employees": total_employees,
        "total_leave_requests": total_leave_requests,
        "pending_leave_requests": pending_leave_requests,
        "total_expense_claims": total_expense_claims,
        "total_expense_amounts_by_currency": format_amounts(
            expense_amounts
        ),
        "pending_approval_steps": pending_approval_steps,
        "total_reimbursements": total_reimbursements,
        "paid_reimbursement_amounts_by_currency": format_amounts(
            paid_amounts
        ),
    }
