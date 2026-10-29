
"""Reimbursement business logic."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.models import (
    ApprovalStep,
    ExpenseClaim,
    Reimbursement,
)
from app.services.audit import record_audit_event


def initiate_reimbursement(
    db: Session,
    *,
    claim_id: str,
    idempotency_key: str,
    actor_employee_id: str,
) -> Reimbursement:
    """Create one reimbursement for a fully approved expense."""

    try:
        claim = db.scalar(
            select(ExpenseClaim)
            .where(ExpenseClaim.id == claim_id)
            .with_for_update()
        )

        if claim is None:
            raise HTTPException(404, "Expense claim not found.")

        existing = db.scalar(
            select(Reimbursement).where(
                Reimbursement.claim_id == claim_id
            )
        )

        if existing is not None:
            if existing.idempotency_key == idempotency_key:
                return existing

            raise HTTPException(
                409,
                "A reimbursement already exists for this claim.",
            )

        key_owner = db.scalar(
            select(Reimbursement).where(
                Reimbursement.idempotency_key == idempotency_key
            )
        )

        if key_owner is not None:
            raise HTTPException(
                409,
                "Idempotency key belongs to another reimbursement.",
            )

        if claim.status != "APPROVED":
            raise HTTPException(
                409,
                "Only approved expenses can be reimbursed.",
            )

        steps = list(
            db.scalars(
                select(ApprovalStep).where(
                    ApprovalStep.expense_claim_id == claim_id
                )
            ).all()
        )

        if not steps or any(
            step.status not in ("APPROVED", "SKIPPED")
            for step in steps
        ):
            raise HTTPException(
                409,
                "Expense approval workflow is incomplete.",
            )

        reimbursement = Reimbursement(
            id=f"RMB-{uuid4().hex[:20]}",
            claim_id=claim_id,
            amount=claim.total_amount,
            currency=claim.currency,
            status="PENDING",
            idempotency_key=idempotency_key,
            metadata_json={},
        )

        db.add(reimbursement)
        claim.status = "REIMBURSEMENT_PENDING"

        record_audit_event(
            db,
            entity_type="EXPENSE_CLAIM",
            entity_id=claim_id,
            event_type="REIMBURSEMENT_CREATED",
            actor_employee_id=actor_employee_id,
            old_values={"status": "APPROVED"},
            new_values={
                "status": "REIMBURSEMENT_PENDING",
                "reimbursement_id": reimbursement.id,
            },
        )

        db.commit()
        db.refresh(reimbursement)
        return reimbursement

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409,
            "Conflicting reimbursement or idempotency key.",
        )
    except Exception:
        db.rollback()
        raise


def process_reimbursement(
    db: Session,
    *,
    reimbursement_id: str,
    actor_employee_id: str,
) -> Reimbursement:
    """Move a pending reimbursement into processing."""

    try:
        reimbursement = db.scalar(
            select(Reimbursement)
            .where(Reimbursement.id == reimbursement_id)
            .with_for_update()
        )

        if reimbursement is None:
            raise HTTPException(404, "Reimbursement not found.")

        if reimbursement.status != "PENDING":
            raise HTTPException(
                409,
                "Only pending reimbursements can be processed.",
            )

        reimbursement.status = "PROCESSING"
        reimbursement.initiated_at = datetime.now(UTC)

        record_audit_event(
            db,
            entity_type="REIMBURSEMENT",
            entity_id=reimbursement.id,
            event_type="REIMBURSEMENT_PROCESSING",
            actor_employee_id=actor_employee_id,
            old_values={"status": "PENDING"},
            new_values={"status": "PROCESSING"},
        )

        db.commit()
        db.refresh(reimbursement)
        return reimbursement

    except Exception:
        db.rollback()
        raise


def pay_reimbursement(
    db: Session,
    *,
    reimbursement_id: str,
    payment_reference: str,
    actor_employee_id: str,
) -> Reimbursement:
    """Record a confirmed successful payment."""

    try:
        reimbursement = db.scalar(
            select(Reimbursement)
            .where(Reimbursement.id == reimbursement_id)
            .with_for_update()
        )

        if reimbursement is None:
            raise HTTPException(404, "Reimbursement not found.")

        if reimbursement.status != "PROCESSING":
            raise HTTPException(
                409,
                "Only processing reimbursements can be paid.",
            )

        claim = db.scalar(
            select(ExpenseClaim)
            .where(ExpenseClaim.id == reimbursement.claim_id)
            .with_for_update()
        )

        if claim is None or claim.status != "REIMBURSEMENT_PENDING":
            raise HTTPException(
                409,
                "Expense is not awaiting reimbursement.",
            )

        reimbursement.status = "PAID"
        reimbursement.payment_reference = payment_reference
        reimbursement.paid_at = datetime.now(UTC)
        claim.status = "REIMBURSED"

        record_audit_event(
            db,
            entity_type="REIMBURSEMENT",
            entity_id=reimbursement.id,
            event_type="REIMBURSEMENT_PAID",
            actor_employee_id=actor_employee_id,
            old_values={"status": "PROCESSING"},
            new_values={
                "status": "PAID",
                "payment_reference": payment_reference,
            },
        )

        record_audit_event(
            db,
            entity_type="EXPENSE_CLAIM",
            entity_id=claim.id,
            event_type="EXPENSE_REIMBURSED",
            actor_employee_id=actor_employee_id,
            old_values={"status": "REIMBURSEMENT_PENDING"},
            new_values={"status": "REIMBURSED"},
        )

        db.commit()
        db.refresh(reimbursement)
        return reimbursement

    except Exception:
        db.rollback()
        raise


def fail_reimbursement(
    db: Session,
    *,
    reimbursement_id: str,
    failure_reason: str,
    actor_employee_id: str,
) -> Reimbursement:
    """Record a failed reimbursement attempt."""

    try:
        reimbursement = db.scalar(
            select(Reimbursement)
            .where(Reimbursement.id == reimbursement_id)
            .with_for_update()
        )

        if reimbursement is None:
            raise HTTPException(404, "Reimbursement not found.")

        if reimbursement.status != "PROCESSING":
            raise HTTPException(
                409,
                "Only processing reimbursements can fail.",
            )

        reimbursement.status = "FAILED"
        reimbursement.failure_reason = failure_reason

        record_audit_event(
            db,
            entity_type="REIMBURSEMENT",
            entity_id=reimbursement.id,
            event_type="REIMBURSEMENT_FAILED",
            actor_employee_id=actor_employee_id,
            old_values={"status": "PROCESSING"},
            new_values={
                "status": "FAILED",
                "failure_reason": failure_reason,
            },
        )

        db.commit()
        db.refresh(reimbursement)
        return reimbursement

    except Exception:
        db.rollback()
        raise
