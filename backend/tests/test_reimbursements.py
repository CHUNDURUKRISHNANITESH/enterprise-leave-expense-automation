
"""Automated tests for reimbursement API endpoints."""


BASE_URL = "/api/v1/reimbursements"


def test_reimbursement_requires_authentication(client):
    """Unauthenticated users cannot create reimbursements."""

    response = client.post(
        BASE_URL,
        json={
            "claim_id": "EXP-TEST-001",
            "idempotency_key": "test-auth-required-001",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )


def test_employee_cannot_create_reimbursement(client, db_session):
    """An authenticated EMPLOYEE cannot initiate reimbursement."""

    from datetime import date
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import Employee, UserAccount

    employee = Employee(
        id=f"EMP-{uuid4().hex[:27]}",
        employee_number=f"TEST-{uuid4().hex[:8]}",
        first_name="Test",
        last_name="Employee",
        email=f"employee-{uuid4().hex[:8]}@example.com",
        department="Engineering",
        country="IN",
        currency="INR",
        employment_start_date=date(2026, 1, 1),
        employment_status="ACTIVE",
        is_approver=False,
    )

    db_session.add(employee)
    db_session.flush()

    user = UserAccount(
        id=uuid4().hex,
        employee_id=employee.id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)

    response = client.post(
        BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "claim_id": "EXP-TEST-001",
            "idempotency_key": "test-employee-forbidden-001",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_admin_can_create_reimbursement(
    client,
    db_session,
    admin_auth_headers,
):
    """ADMIN can initiate reimbursement for an approved expense."""

    from datetime import date
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import select

    from app.db.models import (
        ApprovalStep,
        AuditEvent,
        ExpenseClaim,
        UserAccount,
    )
    from app.db.models.models import Reimbursement

    admin = db_session.scalar(
        select(UserAccount).where(UserAccount.role == "ADMIN")
    )

    assert admin is not None

    claim_id = f"EXP-TEST-{uuid4().hex[:12]}"

    claim = ExpenseClaim(
        id=claim_id,
        employee_id=admin.employee_id,
        expense_date=date(2026, 10, 28),
        description="Automated reimbursement integration test",
        business_purpose="Project-related meal",
        country="IN",
        currency="INR",
        total_amount=Decimal("500.00"),
        status="APPROVED",
        anomaly_flags=[],
        metadata_json={},
    )

    db_session.add(claim)
    db_session.flush()

    approval = ApprovalStep(
        id=f"APR-{uuid4().hex[:20]}",
        expense_claim_id=claim_id,
        step_number=1,
        approver_employee_id=admin.employee_id,
        status="APPROVED",
        decision="APPROVED",
        is_required=True,
        decision_metadata={},
    )

    db_session.add(approval)
    db_session.commit()

    response = client.post(
        BASE_URL,
        headers=admin_auth_headers,
        json={
            "claim_id": claim_id,
            "idempotency_key": f"reimbursement-{uuid4().hex}",
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["claim_id"] == claim_id
    assert Decimal(data["amount"]) == Decimal("500.00")
    assert data["currency"] == "INR"
    assert data["status"] == "PENDING"

    reimbursement = db_session.get(
        Reimbursement,
        data["id"],
    )

    assert reimbursement is not None
    assert reimbursement.claim_id == claim_id

    db_session.refresh(claim)

    assert claim.status == "REIMBURSEMENT_PENDING"

    audit_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_id == claim_id,
            AuditEvent.event_type == "REIMBURSEMENT_CREATED",
        )
    )

    assert audit_event is not None
    assert audit_event.actor_employee_id == admin.employee_id

    print("PASS: ADMIN reimbursement creation verified.")


def test_reimbursement_idempotency(
    client,
    db_session,
    admin_auth_headers,
):
    """Retrying with the same key returns the existing reimbursement."""

    from datetime import date
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import func, select

    from app.db.models import ApprovalStep, ExpenseClaim, UserAccount
    from app.db.models.models import Reimbursement

    admin = db_session.scalar(
        select(UserAccount).where(UserAccount.role == "ADMIN")
    )
    assert admin is not None

    claim_id = f"EXP-TEST-{uuid4().hex[:12]}"

    db_session.add(
        ExpenseClaim(
            id=claim_id,
            employee_id=admin.employee_id,
            expense_date=date(2026, 10, 28),
            description="Reimbursement idempotency test",
            country="IN",
            currency="INR",
            total_amount=Decimal("500.00"),
            status="APPROVED",
            anomaly_flags=[],
            metadata_json={},
        )
    )

    db_session.add(
        ApprovalStep(
            id=f"APR-{uuid4().hex[:20]}",
            expense_claim_id=claim_id,
            step_number=1,
            approver_employee_id=admin.employee_id,
            status="APPROVED",
            decision="APPROVED",
            is_required=True,
            decision_metadata={},
        )
    )

    db_session.commit()

    payload = {
        "claim_id": claim_id,
        "idempotency_key": f"idem-{uuid4().hex}",
    }

    first = client.post(
        BASE_URL,
        headers=admin_auth_headers,
        json=payload,
    )

    second = client.post(
        BASE_URL,
        headers=admin_auth_headers,
        json=payload,
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    assert first.json()["id"] == second.json()["id"]

    count = db_session.scalar(
        select(func.count())
        .select_from(Reimbursement)
        .where(Reimbursement.claim_id == claim_id)
    )

    assert count == 1


def test_complete_reimbursement_payment_workflow(
    client,
    db_session,
    admin_auth_headers,
):
    """Verify reimbursement creation, processing, and payment."""

    from datetime import date
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import select

    from app.db.models import (
        ApprovalStep,
        AuditEvent,
        ExpenseClaim,
        UserAccount,
    )
    from app.db.models.models import Reimbursement

    admin = db_session.scalar(
        select(UserAccount).where(UserAccount.role == "ADMIN")
    )
    assert admin is not None

    claim_id = f"EXP-TEST-{uuid4().hex[:12]}"

    claim = ExpenseClaim(
        id=claim_id,
        employee_id=admin.employee_id,
        expense_date=date(2026, 10, 28),
        description="Automated payment workflow test",
        country="IN",
        currency="INR",
        total_amount=Decimal("500.00"),
        status="APPROVED",
        anomaly_flags=[],
        metadata_json={},
    )

    db_session.add(claim)
    db_session.flush()

    db_session.add(
        ApprovalStep(
            id=f"APR-{uuid4().hex[:20]}",
            expense_claim_id=claim_id,
            step_number=1,
            approver_employee_id=admin.employee_id,
            status="APPROVED",
            decision="APPROVED",
            is_required=True,
            decision_metadata={},
        )
    )

    db_session.commit()

    # Step 1: Initiate reimbursement
    create_response = client.post(
        BASE_URL,
        headers=admin_auth_headers,
        json={
            "claim_id": claim_id,
            "idempotency_key": f"workflow-{uuid4().hex}",
        },
    )

    assert create_response.status_code == 201, create_response.text
    reimbursement_id = create_response.json()["id"]
    assert create_response.json()["status"] == "PENDING"

    # Step 2: Move to PROCESSING
    process_response = client.post(
        f"{BASE_URL}/{reimbursement_id}/process",
        headers=admin_auth_headers,
    )

    assert process_response.status_code == 200, process_response.text
    assert process_response.json()["status"] == "PROCESSING"
    assert process_response.json()["initiated_at"] is not None

    # Step 3: Record simulated payment
    payment_reference = f"SIM-PAY-{uuid4().hex[:12]}"

    pay_response = client.post(
        f"{BASE_URL}/{reimbursement_id}/pay",
        headers=admin_auth_headers,
        json={"payment_reference": payment_reference},
    )

    assert pay_response.status_code == 200, pay_response.text

    data = pay_response.json()

    assert data["status"] == "PAID"
    assert data["payment_reference"] == payment_reference
    assert data["paid_at"] is not None
    assert Decimal(data["amount"]) == Decimal("500.00")

    # Verify persisted database state
    reimbursement = db_session.get(
        Reimbursement,
        reimbursement_id,
    )

    db_session.refresh(reimbursement)
    db_session.refresh(claim)

    assert reimbursement.status == "PAID"
    assert claim.status == "REIMBURSED"

    # Verify audit events
    events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_id.in_(
                [claim_id, reimbursement_id]
            )
        )
    ).all()

    event_types = {event.event_type for event in events}

    assert "REIMBURSEMENT_CREATED" in event_types
    assert "REIMBURSEMENT_PROCESSING" in event_types
    assert "REIMBURSEMENT_PAID" in event_types
    assert "EXPENSE_REIMBURSED" in event_types


def test_failed_reimbursement_workflow(
    client,
    db_session,
    admin_auth_headers,
):
    """Verify failed payment recording and rejection of later payment."""

    from datetime import date
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import select

    from app.db.models import (
        ApprovalStep,
        AuditEvent,
        ExpenseClaim,
        UserAccount,
    )
    from app.db.models.models import Reimbursement

    admin = db_session.scalar(
        select(UserAccount).where(UserAccount.role == "ADMIN")
    )
    assert admin is not None

    claim_id = f"EXP-TEST-{uuid4().hex[:12]}"

    claim = ExpenseClaim(
        id=claim_id,
        employee_id=admin.employee_id,
        expense_date=date(2026, 10, 28),
        description="Automated failed reimbursement test",
        country="IN",
        currency="INR",
        total_amount=Decimal("500.00"),
        status="APPROVED",
        anomaly_flags=[],
        metadata_json={},
    )

    db_session.add(claim)
    db_session.flush()

    db_session.add(
        ApprovalStep(
            id=f"APR-{uuid4().hex[:20]}",
            expense_claim_id=claim_id,
            step_number=1,
            approver_employee_id=admin.employee_id,
            status="APPROVED",
            decision="APPROVED",
            is_required=True,
            decision_metadata={},
        )
    )

    db_session.commit()

    # 1. Create reimbursement
    create_response = client.post(
        BASE_URL,
        headers=admin_auth_headers,
        json={
            "claim_id": claim_id,
            "idempotency_key": f"failure-{uuid4().hex}",
        },
    )

    assert create_response.status_code == 201, create_response.text

    reimbursement_id = create_response.json()["id"]

    # 2. Start processing
    process_response = client.post(
        f"{BASE_URL}/{reimbursement_id}/process",
        headers=admin_auth_headers,
    )

    assert process_response.status_code == 200, process_response.text
    assert process_response.json()["status"] == "PROCESSING"

    # 3. Record simulated payment failure
    failure_reason = "Simulated bank rejection"

    fail_response = client.post(
        f"{BASE_URL}/{reimbursement_id}/fail",
        headers=admin_auth_headers,
        json={"failure_reason": failure_reason},
    )

    assert fail_response.status_code == 200, fail_response.text
    assert fail_response.json()["status"] == "FAILED"
    assert fail_response.json()["failure_reason"] == failure_reason

    # 4. Verify a failed reimbursement cannot be paid
    pay_response = client.post(
        f"{BASE_URL}/{reimbursement_id}/pay",
        headers=admin_auth_headers,
        json={"payment_reference": "SIM-INVALID-AFTER-FAILURE"},
    )

    assert pay_response.status_code == 409

    # 5. Verify persisted state
    reimbursement = db_session.get(Reimbursement, reimbursement_id)

    db_session.refresh(reimbursement)
    db_session.refresh(claim)

    assert reimbursement.status == "FAILED"
    assert reimbursement.paid_at is None
    assert claim.status == "REIMBURSEMENT_PENDING"

    # 6. Verify failure audit event
    audit_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_id == reimbursement_id,
            AuditEvent.event_type == "REIMBURSEMENT_FAILED",
        )
    )

    assert audit_event is not None
    assert audit_event.actor_employee_id == admin.employee_id
    assert audit_event.new_values["status"] == "FAILED"



def test_double_payment_is_rejected(
    client,
    db_session,
    admin_auth_headers,
):
    """A paid reimbursement cannot be paid a second time."""

    from datetime import date
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import func, select

    from app.db.models import (
        ApprovalStep,
        AuditEvent,
        ExpenseClaim,
        UserAccount,
    )
    from app.db.models.models import Reimbursement

    admin = db_session.scalar(
        select(UserAccount).where(UserAccount.role == "ADMIN")
    )
    assert admin is not None

    claim_id = f"EXP-TEST-{uuid4().hex[:12]}"

    claim = ExpenseClaim(
        id=claim_id,
        employee_id=admin.employee_id,
        expense_date=date(2026, 10, 28),
        description="Double payment prevention test",
        country="IN",
        currency="INR",
        total_amount=Decimal("500.00"),
        status="APPROVED",
        anomaly_flags=[],
        metadata_json={},
    )

    db_session.add(claim)
    db_session.flush()

    db_session.add(
        ApprovalStep(
            id=f"APR-{uuid4().hex[:20]}",
            expense_claim_id=claim_id,
            step_number=1,
            approver_employee_id=admin.employee_id,
            status="APPROVED",
            decision="APPROVED",
            is_required=True,
            decision_metadata={},
        )
    )

    db_session.commit()

    # Create reimbursement.
    create_response = client.post(
        BASE_URL,
        headers=admin_auth_headers,
        json={
            "claim_id": claim_id,
            "idempotency_key": f"double-payment-{uuid4().hex}",
        },
    )

    assert create_response.status_code == 201, create_response.text
    reimbursement_id = create_response.json()["id"]

    # Start processing.
    process_response = client.post(
        f"{BASE_URL}/{reimbursement_id}/process",
        headers=admin_auth_headers,
    )

    assert process_response.status_code == 200, process_response.text

    # Record first simulated payment.
    first_reference = f"SIM-FIRST-{uuid4().hex[:12]}"

    first_payment = client.post(
        f"{BASE_URL}/{reimbursement_id}/pay",
        headers=admin_auth_headers,
        json={"payment_reference": first_reference},
    )

    assert first_payment.status_code == 200, first_payment.text
    assert first_payment.json()["status"] == "PAID"

    # Attempt a second payment.
    second_payment = client.post(
        f"{BASE_URL}/{reimbursement_id}/pay",
        headers=admin_auth_headers,
        json={"payment_reference": "SIM-DUPLICATE-PAYMENT"},
    )

    assert second_payment.status_code == 409
    assert second_payment.json()["detail"] == (
        "Only processing reimbursements can be paid."
    )

    # Confirm the first payment remains unchanged.
    reimbursement = db_session.get(
        Reimbursement,
        reimbursement_id,
    )

    db_session.refresh(reimbursement)
    db_session.refresh(claim)

    assert reimbursement.status == "PAID"
    assert reimbursement.payment_reference == first_reference
    assert claim.status == "REIMBURSED"

    # Only one successful-payment audit event must exist.
    payment_event_count = db_session.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.entity_id == reimbursement_id,
            AuditEvent.event_type == "REIMBURSEMENT_PAID",
        )
    )

    assert payment_event_count == 1


