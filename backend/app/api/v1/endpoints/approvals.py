"""Phase 3 approval inbox and decisions for expense claims."""
from datetime import UTC, datetime

from app.api.deps import CurrentUser
from app.db.models.models import ApprovalStep, CostCenter, Employee, ExpenseClaim
from app.db.session import get_db
from app.services.audit import record_audit_event
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter(prefix='/approvals', tags=['Approvals'])

class DecisionInput(BaseModel):
    reason: str = Field(min_length=1)

class ApprovalOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    expense_claim_id: str | None
    leave_request_id: str | None
    step_number: int
    approver_employee_id: str | None
    status: str

@router.get('/inbox', response_model=list[ApprovalOutput])
def approval_inbox(current_user: CurrentUser, db: Session = Depends(get_db)):
    steps = list(db.scalars(select(ApprovalStep).where(
        ApprovalStep.approver_employee_id == current_user.employee_id,
        ApprovalStep.status == 'PENDING').order_by(ApprovalStep.step_number)).all())
    actionable = []
    for step in steps:
        parent_filter = (ApprovalStep.expense_claim_id == step.expense_claim_id) if step.expense_claim_id else (
            ApprovalStep.leave_request_id == step.leave_request_id)
        prior = list(db.scalars(select(ApprovalStep.status).where(
            parent_filter, ApprovalStep.step_number < step.step_number)).all())
        if all(status in ('APPROVED', 'SKIPPED') for status in prior):
            actionable.append(step)
    return actionable

@router.post('/expenses/{claim_id}/{decision}', response_model=dict)
def decide_expense(claim_id: str, decision: str, payload: DecisionInput,
                   current_user: CurrentUser, db: Session = Depends(get_db)):
    if decision not in ('approve', 'reject'):
        raise HTTPException(400, 'Decision must be approve or reject.')
    try:
        claim = db.scalar(select(ExpenseClaim).where(ExpenseClaim.id == claim_id).with_for_update())
        if claim is None:
            raise HTTPException(404, 'Expense claim not found.')
        if claim.status != 'PENDING_APPROVAL':
            raise HTTPException(409, 'Claim is not awaiting approval.')
        if claim.employee_id == current_user.employee_id:
            raise HTTPException(403, 'Requesters cannot approve their own claims.')
        actor = db.get(Employee, current_user.employee_id)
        if actor is None or actor.employment_status != 'ACTIVE' or not actor.is_approver:
            raise HTTPException(403, 'Approver is not authorized.')
        steps = list(db.scalars(select(ApprovalStep).where(ApprovalStep.expense_claim_id == claim.id)
                                .order_by(ApprovalStep.step_number).with_for_update()).all())
        step = next((s for s in steps if s.status == 'PENDING'), None)
        if step is None or any(s.status not in ('APPROVED', 'SKIPPED') for s in steps if s.step_number < step.step_number):
            raise HTTPException(409, 'No eligible pending approval step.')
        if step.approver_employee_id != current_user.employee_id:
            raise HTTPException(403, 'This step is assigned to another approver.')
        approved = decision == 'approve'
        step.status = 'APPROVED' if approved else 'REJECTED'
        step.decision = step.status
        step.decision_reason = payload.reason
        step.decided_at = datetime.now(UTC)
        if not approved:
            claim.status = 'REJECTED'
            center = db.scalar(select(CostCenter).where(CostCenter.id == claim.cost_center_id).with_for_update())
            if center is not None:
                center.committed_amount -= claim.total_amount
        elif all(s.status in ('APPROVED', 'SKIPPED') for s in steps):
            claim.status = 'APPROVED'
        claim.decision_reason = payload.reason
        record_audit_event(db, entity_type='EXPENSE_CLAIM', entity_id=claim.id,
                           event_type='EXPENSE_APPROVAL_STEP_' + step.status,
                           actor_employee_id=current_user.employee_id,
                           old_values={'status': 'PENDING_APPROVAL'},
                           new_values={'status': claim.status, 'step': step.step_number}, reason=payload.reason)
        db.commit()
        return {'claim_id': claim.id, 'status': claim.status, 'step_status': step.status}
    except Exception:
        db.rollback()
        raise
