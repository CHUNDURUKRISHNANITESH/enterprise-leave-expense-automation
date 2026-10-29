
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models.models import AuditEvent


def record_audit_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor_employee_id: str | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    reason: str | None = None,
    correlation_id: str | None = None,
    source: str = "API",
) -> AuditEvent:
    """Stage an append-only audit event in the current transaction."""

    audit_event = AuditEvent(
        event_id=f"EVT-{uuid4().hex}",
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        actor_employee_id=actor_employee_id,
        old_values=old_values,
        new_values=new_values,
        reason=reason,
        correlation_id=correlation_id,
        source=source,
        extra={},
    )

    db.add(audit_event)

    # Do not commit here. The calling service owns the transaction.
    return audit_event
