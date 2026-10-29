"""Deterministic expense approval routing based on configured, effective rules."""
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.models import ApprovalRule, ApprovalStep, ExpenseClaim
from app.services.approval_routing import (
    resolve_explicit_approver,
    resolve_manager_approver,
    resolve_role_approver,
)


def create_expense_approval_steps(db: Session, *, claim: ExpenseClaim, categories: set[str]) -> list[ApprovalStep]:
    if db.scalar(select(ApprovalStep.id).where(ApprovalStep.expense_claim_id == claim.id).limit(1)):
        raise HTTPException(409, 'Approval steps already exist for this expense claim.')
    rules = list(db.scalars(select(ApprovalRule).where(
        ApprovalRule.is_active.is_(True),
        ApprovalRule.effective_from <= claim.expense_date,
        (ApprovalRule.effective_to.is_(None) | (ApprovalRule.effective_to >= claim.expense_date)),
        (ApprovalRule.country.is_(None) | (ApprovalRule.country == claim.country)),
        (ApprovalRule.currency.is_(None) | (ApprovalRule.currency == claim.currency)),
        ApprovalRule.min_amount <= claim.total_amount,
        (ApprovalRule.max_amount.is_(None) | (ApprovalRule.max_amount >= claim.total_amount)),
    )).all())
    eligible = []
    for rule in rules:
        if rule.category not in (None, 'EXPENSE') and rule.category not in categories:
            continue
        if rule.conditions:
            raise HTTPException(400, f'Unsupported approval conditions in rule {rule.id}.')
        if rule.approval_level < 1:
            raise HTTPException(400, f'Invalid approval level in rule {rule.id}.')
        eligible.append(rule)
    selected = {}
    for rule in eligible:
        specificity = (int(rule.country == claim.country), int(rule.category in categories),
                       int(rule.currency == claim.currency), rule.min_amount)
        rank = (-specificity[0], -specificity[1], -specificity[2], -specificity[3], rule.priority)
        previous = selected.get(rule.approval_level)
        if previous is None or rank < previous[0]:
            selected[rule.approval_level] = (rank, rule)
        elif rank == previous[0]:
            raise HTTPException(409, f'Ambiguous expense approval rules at level {rule.approval_level}.')
    if not selected:
        # No configured rules: preserve the original single-manager workflow.
        manager = resolve_manager_approver(db, requester_employee_id=claim.employee_id)
        assignments = [(None, manager)]
    else:
        assignments = []
        for level in sorted(selected):
            rule = selected[level][1]
            kind = rule.approver_type.strip().upper()
            if kind == 'MANAGER':
                approver = resolve_manager_approver(db, requester_employee_id=claim.employee_id)
            elif kind == 'EMPLOYEE':
                approver = resolve_explicit_approver(db, requester_employee_id=claim.employee_id,
                                                    approver_employee_id=rule.approver_employee_id)
            elif kind == 'ROLE':
                approver = resolve_role_approver(db, requester_employee_id=claim.employee_id,
                                                approver_role=rule.approver_role)
            else:
                raise HTTPException(400, f'Unsupported expense approver type: {kind}.')
            assignments.append((rule, approver))
    steps = []
    for number, (rule, approver) in enumerate(assignments, 1):
        steps.append(ApprovalStep(
            id=f'APR-{claim.id}-{number:02d}', expense_claim_id=claim.id,
            step_number=number, rule_id=rule.id if rule else None,
            approver_employee_id=approver.id, approver_role=rule.approver_role if rule else None,
            status='PENDING', assigned_at=datetime.now(UTC), is_required=True,
            decision_metadata={},
        ))
    db.add_all(steps)
    return steps
