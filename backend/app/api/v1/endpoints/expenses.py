"""Phase 3 expense CRUD and submission; reimbursement processing belongs to Phase 5."""
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.api.deps import CurrentUser
from app.db.models.models import (
    CostCenter,
    Employee,
    ExpenseClaim,
    ExpenseLine,
    ExpensePolicy,
)
from app.db.session import get_db
from app.services.audit import record_audit_event
from app.services.expense_routing import create_expense_approval_steps
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

router = APIRouter(prefix='/expenses', tags=['Expenses'])
MONEY = Decimal('0.01')

class LineInput(BaseModel):
    category: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1)
    expense_date: date
    quantity: Decimal = Field(gt=0)
    unit_amount: Decimal = Field(ge=0)
    receipt_uri: str | None = None
    receipt_hash: str | None = None

class ClaimInput(BaseModel):
    employee_id: str
    cost_center_id: str | None = None
    expense_date: date
    description: str = Field(min_length=1)
    business_purpose: str | None = None
    merchant: str | None = None
    currency: str = Field(min_length=3, max_length=3)
    lines: list[LineInput] = Field(min_length=1, max_length=10)

class LineOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    category: str
    line_amount: Decimal
    receipt_hash: str | None

class ClaimOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    employee_id: str
    cost_center_id: str | None
    currency: str
    total_amount: Decimal
    status: str
    anomaly_flags: list[str]
    lines: list[LineOutput]


def load_claim(db: Session, claim_id: str) -> ExpenseClaim:
    claim = db.scalar(select(ExpenseClaim).options(selectinload(ExpenseClaim.lines)).where(ExpenseClaim.id == claim_id))
    if claim is None:
        raise HTTPException(404, 'Expense claim not found.')
    return claim


def check_access(claim: ExpenseClaim, user: CurrentUser):
    if claim.employee_id != user.employee_id and user.role not in ('ADMIN', 'HR'):
        raise HTTPException(403, 'Not authorized to access this claim.')


@router.post('', response_model=ClaimOutput, status_code=201)
def create_claim(payload: ClaimInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    if payload.employee_id != current_user.employee_id and current_user.role not in ('ADMIN', 'HR'):
        raise HTTPException(403, 'Cannot create claims for another employee.')
    employee = db.get(Employee, payload.employee_id)
    if employee is None or employee.employment_status != 'ACTIVE':
        raise HTTPException(400, 'Employee must exist and be active.')
    if payload.expense_date < employee.employment_start_date or (employee.employment_end_date and payload.expense_date > employee.employment_end_date):
        raise HTTPException(400, 'Expense date is outside employment dates.')
    if payload.currency.upper() != employee.currency.upper():
        raise HTTPException(400, 'Currency does not match employee currency.')
    if payload.cost_center_id:
        center = db.get(CostCenter, payload.cost_center_id)
        if center is None or not center.is_active or center.country != employee.country or center.currency != employee.currency:
            raise HTTPException(400, 'Invalid cost center for employee.')
    try:
        # PostgreSQL advisory transaction lock prevents concurrent duplicate counters.
        if db.bind.dialect.name == 'postgresql':
            db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': 800000 + payload.expense_date.year})
        prefix = f'EXP-{payload.expense_date.year}-'
        existing = db.scalars(select(ExpenseClaim.id).where(ExpenseClaim.id.like(prefix + '%'))).all()
        sequence = max((int(item[len(prefix):]) for item in existing
                        if item[len(prefix):].isdigit()), default=0) + 1
        claim_id = f'{prefix}{sequence:06d}'
        claim = ExpenseClaim(id=claim_id, employee_id=employee.id, cost_center_id=payload.cost_center_id,
                             expense_date=payload.expense_date, description=payload.description,
                             business_purpose=payload.business_purpose, merchant=payload.merchant,
                             country=employee.country, currency=employee.currency, total_amount=Decimal(0),
                             status='DRAFT', anomaly_flags=[], metadata_json={})
        db.add(claim)
        total = Decimal(0)
        for index, line in enumerate(payload.lines, 1):
            if line.expense_date < employee.employment_start_date or (employee.employment_end_date and line.expense_date > employee.employment_end_date):
                raise HTTPException(400, 'Expense line date is outside employment dates.')
            amount = (line.quantity * line.unit_amount).quantize(MONEY, rounding=ROUND_HALF_UP)
            total += amount
            db.add(ExpenseLine(id=f'EXPL-{claim_id}-{index:02d}', claim_id=claim_id,
                               line_number=index, category=line.category, description=line.description,
                               expense_date=line.expense_date, quantity=line.quantity, unit_amount=line.unit_amount,
                               line_amount=amount, currency=employee.currency, receipt_uri=line.receipt_uri,
                               receipt_hash=line.receipt_hash, metadata_json={}))
        if total <= 0:
            raise HTTPException(400, 'Expense claim total must be positive.')
        claim.total_amount = total
        record_audit_event(db, entity_type='EXPENSE_CLAIM', entity_id=claim_id,
                           event_type='EXPENSE_CREATED', actor_employee_id=current_user.employee_id,
                           new_values={'status': 'DRAFT', 'total_amount': str(total)})
        db.commit()
        return load_claim(db, claim_id)
    except Exception:
        db.rollback()
        raise


@router.get('', response_model=list[ClaimOutput])
def list_claims(current_user: CurrentUser, db: Session = Depends(get_db)):
    stmt = select(ExpenseClaim).options(selectinload(ExpenseClaim.lines)).order_by(ExpenseClaim.created_at.desc())
    if current_user.role not in ('ADMIN', 'HR'):
        stmt = stmt.where(ExpenseClaim.employee_id == current_user.employee_id)
    return list(db.scalars(stmt).all())


@router.get('/{claim_id}', response_model=ClaimOutput)
def get_claim(claim_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    claim = load_claim(db, claim_id)
    check_access(claim, current_user)
    return claim


@router.post('/{claim_id}/submit', response_model=ClaimOutput)
def submit_claim(claim_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    try:
        claim = db.scalar(select(ExpenseClaim).where(ExpenseClaim.id == claim_id).with_for_update())
        if claim is None:
            raise HTTPException(404, 'Expense claim not found.')
        if claim.employee_id != current_user.employee_id:
            raise HTTPException(403, 'Only the requester can submit their claim.')
        if claim.status != 'DRAFT':
            raise HTTPException(409, 'Only draft claims can be submitted.')
        employee = db.get(Employee, claim.employee_id)
        if employee is None or employee.employment_status != 'ACTIVE':
            raise HTTPException(400, 'Requester is not active.')
        lines = list(db.scalars(select(ExpenseLine).where(ExpenseLine.claim_id == claim.id)).all())
        if not lines or sum((line.line_amount for line in lines), Decimal(0)) != claim.total_amount:
            raise HTTPException(409, 'Claim line totals do not reconcile.')
        if claim.cost_center_id is None:
            raise HTTPException(400, 'A cost center is required to submit an expense.')
        center = db.scalar(select(CostCenter).where(CostCenter.id == claim.cost_center_id).with_for_update())
        if center is None or not center.is_active or center.country != claim.country or center.currency != claim.currency:
            raise HTTPException(400, 'Invalid or inactive cost center.')
        if center.budget_amount is not None and center.committed_amount + claim.total_amount > center.budget_amount:
            raise HTTPException(400, 'Cost center budget would be exceeded.')
        for line in lines:
            policy = db.scalar(select(ExpensePolicy).where(
                ExpensePolicy.country == claim.country, ExpensePolicy.category == line.category,
                ExpensePolicy.currency == claim.currency, ExpensePolicy.effective_from <= line.expense_date,
                (ExpensePolicy.effective_to.is_(None) | (ExpensePolicy.effective_to >= line.expense_date))
            ).order_by(ExpensePolicy.version.desc()))
            if policy is None:
                raise HTTPException(400, f'No applicable expense policy for category {line.category}.')
            if policy.per_item_limit is not None and line.line_amount > policy.per_item_limit:
                raise HTTPException(400, f'Per-item policy limit exceeded for {line.category}.')
            if policy.max_amount is not None and line.line_amount > policy.max_amount:
                raise HTTPException(400, f'Policy amount limit exceeded for {line.category}.')
            if policy.requires_business_purpose and not claim.business_purpose:
                raise HTTPException(400, 'Business purpose is required.')
            if policy.receipt_required and line.line_amount >= policy.min_receipt_amount and not line.receipt_uri:
                raise HTTPException(400, f'Receipt required for {line.category}.')
            if line.receipt_hash and db.scalar(select(ExpenseLine.id).join(ExpenseClaim).where(
                ExpenseLine.receipt_hash == line.receipt_hash, ExpenseLine.claim_id != claim.id,
                ExpenseClaim.status != 'CANCELLED').limit(1)):
                raise HTTPException(409, 'Duplicate receipt detected.')
        steps = create_expense_approval_steps(db, claim=claim,
                                              categories={line.category for line in lines})
        center.committed_amount += claim.total_amount
        claim.status = 'PENDING_APPROVAL'
        claim.submitted_at = datetime.now(UTC)
        record_audit_event(db, entity_type='EXPENSE_CLAIM', entity_id=claim.id,
                           event_type='EXPENSE_SUBMITTED', actor_employee_id=current_user.employee_id,
                           old_values={'status': 'DRAFT'}, new_values={'status': claim.status,
                           'approver_ids': [step.approver_employee_id for step in steps]}, reason='Expense policy and budget checks passed.')
        db.commit()
        return load_claim(db, claim.id)
    except Exception:
        db.rollback()
        raise
