
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.db.models.models import LeaveBalance, LeavePolicy
from app.services.leave_balance_initializer import (
    initialize_employee_leave_balances,
)


def test_employee_creation_initializes_prorated_balances(
    client,
    db_session,
    admin_auth_headers,
):
    policies = [
        ("GEN-IN-ANNUAL", "ANNUAL", Decimal("20.00"), Decimal("5.00")),
        ("GEN-IN-SICK", "SICK", Decimal("10.00"), Decimal("0.00")),
    ]

    for code, leave_type, entitlement, carryover in policies:
        db_session.add(
            LeavePolicy(
                id=f"LP-{uuid4().hex[:27]}",
                policy_code=code,
                name=f"IN {leave_type} Leave",
                leave_type=leave_type,
                country="IN",
                annual_entitlement=entitlement,
                accrual_frequency="ANNUAL",
                carryover_limit=carryover,
                is_paid=True,
                effective_from=date(2026, 1, 1),
                version=1,
                rules={"business_days_only": True},
            )
        )

    db_session.commit()

    payload = {
        "employee_number": f"TEST-{uuid4().hex[:8]}",
        "first_name": "Test",
        "last_name": "Employee",
        "email": f"test-{uuid4().hex[:8]}@example.com",
        "department": "Engineering",
        "country": "IN",
        "currency": "INR",
        "employment_start_date": "2026-10-29",
        "employment_status": "ACTIVE",
        "is_approver": False,
        "attributes": {},
    }

    response = client.post(
        "/api/v1/employees",
        json=payload,
        headers=admin_auth_headers,
    )

    assert response.status_code == 201, response.text

    employee_id = response.json()["id"]

    balances = db_session.scalars(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.period_year == 2026,
        )
    ).all()

    assert len(balances) == 2

    policy_types = {
        policy.id: policy.leave_type
        for policy in db_session.scalars(
            select(LeavePolicy)
        ).all()
    }

    entitlements = {
        policy_types[balance.leave_policy_id]: balance.entitled_days
        for balance in balances
    }

    assert entitlements["ANNUAL"] == Decimal("3.51")
    assert entitlements["SICK"] == Decimal("1.75")

    # Repeating initialization must not create duplicate records.
    employee = balances[0].employee

    created_again = initialize_employee_leave_balances(
        db_session,
        employee,
        2026,
    )

    db_session.flush()

    assert created_again == []

    final_balances = db_session.scalars(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.period_year == 2026,
        )
    ).all()

    assert len(final_balances) == 2


def test_initialization_preserves_existing_balance(
    client,
    db_session,
    admin_auth_headers,
):
    from app.db.models.models import Employee

    policy = LeavePolicy(
        id=f"LP-{uuid4().hex[:27]}",
        policy_code="TEST-IN-ANNUAL",
        name="Test India Annual Leave",
        leave_type="ANNUAL",
        country="IN",
        annual_entitlement=Decimal("20.00"),
        accrual_frequency="ANNUAL",
        carryover_limit=Decimal("5.00"),
        is_paid=True,
        effective_from=date(2026, 1, 1),
        version=1,
        rules={},
    )
    db_session.add(policy)

    employee = Employee(
        id=f"EMP-{uuid4().hex[:27]}",
        employee_number=f"TEST-{uuid4().hex[:8]}",
        first_name="Existing",
        last_name="Employee",
        email=f"existing-{uuid4().hex[:8]}@example.com",
        department="Engineering",
        country="IN",
        currency="INR",
        employment_start_date=date(2026, 1, 1),
        employment_status="ACTIVE",
        is_approver=False,
    )
    db_session.add(employee)
    db_session.flush()

    balance = LeaveBalance(
        id=f"LB-{uuid4().hex[:27]}",
        employee_id=employee.id,
        leave_policy_id=policy.id,
        period_year=2026,
        entitled_days=Decimal("20.00"),
        used_days=Decimal("5.00"),
        pending_days=Decimal("2.00"),
        carryover_days=Decimal("3.00"),
        adjustment_days=Decimal("1.00"),
    )
    db_session.add(balance)
    db_session.commit()

    created = initialize_employee_leave_balances(
        db_session,
        employee,
        2026,
    )
    db_session.flush()

    assert created == []

    saved = db_session.get(LeaveBalance, balance.id)

    assert saved.entitled_days == Decimal("20.00")
    assert saved.used_days == Decimal("5.00")
    assert saved.pending_days == Decimal("2.00")
    assert saved.carryover_days == Decimal("3.00")
    assert saved.adjustment_days == Decimal("1.00")
    assert saved.available_days == Decimal("17.00")

    all_balances = db_session.scalars(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee.id,
            LeaveBalance.period_year == 2026,
        )
    ).all()

    assert len(all_balances) == 1


def test_employee_creation_rolls_back_when_initialization_fails(
    client,
    db_session,
    admin_auth_headers,
    monkeypatch,
):
    from sqlalchemy import select

    from app.db.models.models import Employee
    from app.api.v1.endpoints import employees as employees_endpoint

    employee_number = f"ROLLBACK-{uuid4().hex[:8]}"
    employee_email = f"rollback-{uuid4().hex[:8]}@example.com"

    def simulate_initialization_failure(*args, **kwargs):
        raise RuntimeError(
            "Simulated leave balance initialization failure"
        )

    monkeypatch.setattr(
        employees_endpoint,
        "initialize_employee_leave_balances",
        simulate_initialization_failure,
    )

    payload = {
        "employee_number": employee_number,
        "first_name": "Rollback",
        "last_name": "Test",
        "email": employee_email,
        "department": "Engineering",
        "country": "IN",
        "currency": "INR",
        "employment_start_date": "2026-10-29",
        "employment_status": "ACTIVE",
        "is_approver": False,
        "attributes": {},
    }

    try:
        client.post(
            "/api/v1/employees",
            json=payload,
            headers=admin_auth_headers,
        )
    except RuntimeError as exc:
        assert "Simulated leave balance initialization failure" in str(exc)
    else:
        raise AssertionError("Expected initialization failure")

    saved_employee = db_session.scalar(
        select(Employee).where(
            Employee.employee_number == employee_number
        )
    )

    assert saved_employee is None

   

