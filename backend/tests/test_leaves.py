from datetime import date
from decimal import Decimal
from uuid import uuid4
from app.db.models.models import LeaveBalance, LeavePolicy
from app.db.models.models import LeaveRequest
from app.db.models.models import ApprovalRule
from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db.models import Employee, UserAccount
from sqlalchemy import select
import pytest


BASE_URL = "/api/v1/leaves"
EMPLOYEE_URL = "/api/v1/employees"


def employee_payload(**overrides):
    """Return a valid employee payload for leave tests."""
    payload = {
        "employee_number": "EMP001",
        "first_name": "Nitesh",
        "last_name": "Kumar",
        "email": "nitesh@example.com",
        "job_title": "Software Developer",
        "department": "Engineering",
        "country": "US",
        "currency": "USD",
        "manager_id": None,
        "cost_center_id": None,
        "employment_start_date": "2024-01-01",
        "employment_end_date": None,
        "employment_status": "ACTIVE",
        "is_approver": False,
        "attributes": {},
    }
    payload.update(overrides)
    return payload


def create_employee(client, **overrides):
    """Create an employee using an authenticated ADMIN account."""

    from app.core.security import create_access_token, hash_password
    from app.db.models import Employee, UserAccount
    from datetime import date
    from uuid import uuid4

    # Access the isolated test database.
    db_generator = client.app.dependency_overrides[get_db]()
    db_session = next(db_generator)

    try:
        # Find an existing active ADMIN account.
        admin_user = db_session.scalar(
            select(UserAccount).where(
                UserAccount.role == "ADMIN",
                UserAccount.is_active.is_(True),
            )
        )

        if admin_user is None:
            # Bootstrap an ADMIN account directly in the test database.
            admin_employee = Employee(
                id=f"EMP-{uuid4().hex[:27]}",
                employee_number=f"ADMIN-{uuid4().hex[:8]}",
                first_name="Test",
                last_name="Administrator",
                email=f"admin-{uuid4().hex[:8]}@example.com",
                department="HR",
                country="IN",
                currency="INR",
                employment_start_date=date(2026, 1, 1),
                employment_status="ACTIVE",
                is_approver=False,
            )

            db_session.add(admin_employee)
            db_session.flush()

            admin_user = UserAccount(
                id=uuid4().hex,
                employee_id=admin_employee.id,
                password_hash=hash_password("TestPassword123!"),
                role="ADMIN",
                is_active=True,
            )

            db_session.add(admin_user)
            db_session.commit()

        token = create_access_token(admin_user.id)

        return client.post(
            EMPLOYEE_URL,
            json=employee_payload(**overrides),
            headers={"Authorization": f"Bearer {token}"},
        )

    finally:
        db_generator.close()


def create_policy(db_session, **overrides):
    """Insert a valid leave policy into the test database."""
    policy_data = {
        "id": "POL-ANNUAL-2026",
        "policy_code": "ANNUAL",
        "name": "Annual Leave",
        "description": "Annual paid leave policy",
        "leave_type": "ANNUAL",
        "country": "US",
        "annual_entitlement": Decimal("20.00"),
        "accrual_frequency": "ANNUAL",
        "carryover_limit": Decimal("5.00"),
        "requires_documentation_after_days": 3,
        "max_consecutive_days": 10,
        "is_paid": True,
        "effective_from": date(2026, 1, 1),
        "effective_to": date(2026, 12, 31),
        "version": 1,
        "rules": {},
    }

    policy_data.update(overrides)

    policy = LeavePolicy(**policy_data)
    db_session.add(policy)
    db_session.commit()
    db_session.refresh(policy)
    return policy


def leave_payload(employee_id, leave_policy_id, **overrides):
    """Return a valid leave request payload."""
    payload = {
        "employee_id": employee_id,
        "leave_policy_id": leave_policy_id,
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        "requested_days": "3.00",
        "reason": "Personal leave",
        "metadata_json": {},
    }
    payload.update(overrides)
    return payload



def create_leave_request(client, employee_id, leave_policy_id, **overrides):
    """Create a leave request through the API using a valid JWT."""

    # Retrieve the test database session configured by conftest.py.
    db_generator = client.app.dependency_overrides[get_db]()
    db_session = next(db_generator)

    try:
        employee = db_session.get(Employee, employee_id)

        # For tests involving a nonexistent employee ID, authenticate
        # as another existing employee so the API can validate the
        # requested employee ID independently.
        if employee is None:
            employee = db_session.scalar(
                select(Employee).where(
                    Employee.employment_status == "ACTIVE"
                )
            )

        # If no employee exists yet, create a test actor through
        # the existing employee API helper.
        if employee is None:
            actor_response = create_employee(
                client,
                employee_number=f"TEST-{uuid4().hex[:8]}",
                email=f"test-{uuid4().hex[:8]}@example.com",
            )
            assert actor_response.status_code == 201
            actor_id = actor_response.json()["id"]
            employee = db_session.get(Employee, actor_id)

        user = db_session.scalar(
            select(UserAccount).where(
                UserAccount.employee_id == employee.id
            )
        )

        if user is None:
            user = UserAccount(
                id=uuid4().hex,
                employee_id=employee.id,
                password_hash=hash_password("TestPassword123!"),
                role="MANAGER" if employee.is_approver else "EMPLOYEE",
                is_active=True,
            )
            db_session.add(user)
            db_session.commit()

        token = create_access_token(user.id)

        return client.post(
            BASE_URL,
            json=leave_payload(
                employee_id,
                leave_policy_id,
                **overrides,
            ),
            headers={"Authorization": f"Bearer {token}"},
        )

    finally:
        db_generator.close()




def setup_leave_data(client, db_session):
    """Create an employee, manager, policy, balance, and approval rule."""
    from datetime import date
    from uuid import uuid4

    # Create an active reporting manager with approval authority.
    manager_response = create_employee(
        client,
        employee_number=f"MGR-{uuid4().hex[:8]}",
        email=f"manager-{uuid4().hex[:8]}@example.com",
        first_name="Test",
        last_name="Manager",
        is_approver=True,
        attributes={"approval_roles": ["MANAGER"]},
    )
    assert manager_response.status_code == 201
    manager_id = manager_response.json()["id"]

    # Create the leave requester reporting to this manager.
    employee_response = create_employee(
        client,
        manager_id=manager_id,
    )
    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]
    policy = create_policy(db_session)

    balance = LeaveBalance(
        id="BAL-EMP001-2026",
        employee_id=employee_id,
        leave_policy_id=policy.id,
        period_year=2026,
        entitled_days=Decimal("20.00"),
        used_days=Decimal("0.00"),
        pending_days=Decimal("0.00"),
        carryover_days=Decimal("0.00"),
        adjustment_days=Decimal("0.00"),
    )

    approval_rule = ApprovalRule(
        id=f"RULE-{uuid4().hex[:24]}",
        name="US Leave Manager Approval",
        country="US",
        category="LEAVE",
        min_amount=Decimal("0.00"),
        approver_type="MANAGER",
        approval_level=1,
        effective_from=date(2026, 1, 1),
        priority=100,
        is_active=True,
        conditions={},
    )

    db_session.add_all([balance, approval_rule])
    db_session.commit()

    return employee_id, policy.id




def test_create_leave_request(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(client, employee_id, policy_id)

    assert response.status_code == 201
    data = response.json()
    assert data["employee_id"] == employee_id
    assert data["leave_policy_id"] == policy_id
    assert data["start_date"] == "2026-11-10"
    assert data["end_date"] == "2026-11-12"
    assert Decimal(data["requested_days"]) == Decimal("3.00")
    assert data["status"] == "DRAFT"
    assert data["id"].startswith("LVE-2026-")
    assert "created_at" in data
    assert "updated_at" in data


def test_create_leave_request_with_optional_fields_omitted(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        reason=None,
    )

    assert response.status_code == 201
    assert response.json()["reason"] is None
    assert response.json()["metadata_json"] == {}


def test_reject_leave_request_for_missing_employee(client, db_session):
    policy = create_policy(db_session)

    response = create_leave_request(
        client,
        "EMP-MISSING",
        policy.id,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Employee does not exist."


def test_reject_leave_request_for_missing_policy(client):
    employee_response = create_employee(client)
    employee_id = employee_response.json()["id"]

    response = create_leave_request(
        client,
        employee_id,
        "POL-MISSING",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Leave policy does not exist."


def test_reject_policy_from_different_country(client, db_session):
    employee_response = create_employee(client)
    employee_id = employee_response.json()["id"]
    policy = create_policy(db_session, country="IN")

    response = create_leave_request(client, employee_id, policy.id)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Leave policy country does not match employee country."
    )


def test_reject_leave_dates_outside_policy_period(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2025-12-29",
        end_date="2025-12-31",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Leave dates fall outside the policy effective period."
    )


def test_reject_leave_for_inactive_employee(client, db_session):
    employee_response = create_employee(
        client,
        employment_status="INACTIVE",
    )
    employee_id = employee_response.json()["id"]
    policy = create_policy(db_session)

    response = create_leave_request(client, employee_id, policy.id)

    assert response.status_code == 403
    assert response.json()["detail"] == "Employee account is not active"


def test_reject_leave_before_employment_start(client, db_session):
    employee_response = create_employee(
        client,
        employment_start_date="2026-02-01",
    )
    employee_id = employee_response.json()["id"]
    policy = create_policy(db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy.id,
        start_date="2026-01-10",
        end_date="2026-01-12",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Leave cannot start before the employee's employment date."
    )


def test_reject_leave_beyond_employment_end(client, db_session):
    employee_response = create_employee(
        client,
        employment_end_date="2026-11-11",
    )
    employee_id = employee_response.json()["id"]
    policy = create_policy(db_session)

    response = create_leave_request(client, employee_id, policy.id)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Leave cannot extend beyond the employee's employment end date."
    )


def test_reject_leave_exceeding_policy_consecutive_day_limit(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-24",
        requested_days="11.00",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Requested leave exceeds the policy's consecutive-day limit."
    )


def test_reject_end_date_before_start_date(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-12",
        end_date="2026-11-10",
    )

    assert response.status_code == 422



def test_reject_missing_required_leave_fields(client, db_session):
    from app.core.security import create_access_token
    from app.db.models import Employee, UserAccount

    employee_id, policy_id = setup_leave_data(client, db_session)
    payload = leave_payload(employee_id, policy_id)
    del payload["start_date"]

    employee = db_session.get(Employee, employee_id)
    user = db_session.query(UserAccount).filter_by(
        employee_id=employee_id
    ).first()

    if user is None:
        from uuid import uuid4
        from app.core.security import hash_password

        user = UserAccount(
            id=uuid4().hex,
            employee_id=employee_id,
            password_hash=hash_password("TestPassword123!"),
            role="EMPLOYEE",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

    token = create_access_token(user.id)

    response = client.post(
        BASE_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422



def test_reject_zero_requested_leave_days(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        requested_days="0",
    )

    assert response.status_code == 422


def test_list_leave_requests(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)
    create_leave_request(client, employee_id, policy_id)

    response = get_leave_requests(client, db_session, employee_id)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_id"] == employee_id


def test_filter_leave_requests_by_employee(client, db_session):
    first_employee_id, policy_id = setup_leave_data(client, db_session)
    create_leave_request(client, first_employee_id, policy_id)

    second_employee_response = create_employee(
        client,
        employee_number="EMP002",
        email="second@example.com",
    )
    second_employee_id = second_employee_response.json()["id"]
    create_leave_request(client, second_employee_id, policy_id)

    response = get_leave_requests(client,db_session,first_employee_id,params={"employee_id": first_employee_id},)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_id"] == first_employee_id


def test_filter_leave_requests_by_status(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)
    create_leave_request(client, employee_id, policy_id)

    response = get_leave_requests(client,db_session,employee_id,params={"status": "DRAFT"},)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "DRAFT"



def test_reject_invalid_leave_status_filter(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    # Create a test account through the existing helper.
    created = create_leave_request(client, employee_id, policy_id)
    assert created.status_code == 201

    response = get_leave_requests(
        client,
        db_session,
        employee_id,
        params={"status": "INVALID"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid leave request status."


def test_reject_invalid_leave_pagination(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    created = create_leave_request(client, employee_id, policy_id)
    assert created.status_code == 201

    response = get_leave_requests(
        client,
        db_session,
        employee_id,
        params={"limit": 0},
    )

    assert response.status_code == 422



def test_get_leave_request_by_id(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    created = create_leave_request(
        client, employee_id, policy_id
    )
    assert created.status_code == 201

    leave_id = created.json()["id"]

    user = db_session.scalar(
        select(UserAccount).where(
            UserAccount.employee_id == employee_id
        )
    )
    assert user is not None

    token = create_access_token(user.id)

    response = client.get(
        f"{BASE_URL}/{leave_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == leave_id


def test_get_leave_request_not_found(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    created = create_leave_request(
        client, employee_id, policy_id
    )
    assert created.status_code == 201

    user = db_session.scalar(
        select(UserAccount).where(
            UserAccount.employee_id == employee_id
        )
    )
    assert user is not None

    token = create_access_token(user.id)

    response = client.get(
        f"{BASE_URL}/LVE-NOT-FOUND",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Leave request not found."



def test_get_employee_leave_balances(client, db_session):
    employee_response = create_employee(client)
    employee_id = employee_response.json()["id"]
    policy = create_policy(db_session)

    balance = LeaveBalance(
        id="BAL-EMP001-2026",
        employee_id=employee_id,
        leave_policy_id=policy.id,
        period_year=2026,
        entitled_days=Decimal("20.00"),
        used_days=Decimal("4.00"),
        pending_days=Decimal("2.00"),
        carryover_days=Decimal("1.00"),
        adjustment_days=Decimal("0.00"),
        notes=None,
    )
    db_session.add(balance)
    db_session.commit()

    # Create a user account for this employee if one does not exist.
    user = db_session.scalar(
        select(UserAccount).where(
            UserAccount.employee_id == employee_id
        )
    )

    if user is None:
        user = UserAccount(
            id=uuid4().hex,
            employee_id=employee_id,
            password_hash=hash_password("TestPassword123!"),
            role="EMPLOYEE",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

    token = create_access_token(user.id)

    response = client.get(
        f"{BASE_URL}/balances/{employee_id}",
        params={"year": 2026},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_id"] == employee_id
    assert Decimal(data[0]["available_days"]) == Decimal("15.00")



def test_get_balances_for_employee_without_balances(client, db_session):
    employee_response = create_employee(client)
    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    # Create an active user account for the employee.
    user = UserAccount(
        id=uuid4().hex,
        employee_id=employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)

    response = client.get(
        f"{BASE_URL}/balances/{employee_id}",
        params={"year": 2026},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []




def test_get_balances_for_missing_employee(client, db_session):
    employee_response = create_employee(client)
    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    user = UserAccount(
        id=uuid4().hex,
        employee_id=employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)

    response = client.get(
        f"{BASE_URL}/balances/EMP-MISSING",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Employees can only view their own leave balances."
    )



def test_reject_cross_year_leave_when_second_year_balance_is_insufficient(
    client, db_session
):
    employee_id, policy_id = setup_leave_data(client, db_session)

    policy = db_session.get(LeavePolicy, policy_id)
    policy.effective_to = date(2027, 12, 31)

    balance_2027 = LeaveBalance(
        id="BAL-EMP001-2027",
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2027,
        entitled_days=Decimal("1.00"),
        used_days=Decimal("0.00"),
        pending_days=Decimal("0.00"),
        carryover_days=Decimal("0.00"),
        adjustment_days=Decimal("0.00"),
    )

    db_session.add(balance_2027)
    db_session.commit()

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-12-29",
        end_date="2027-01-04",
        requested_days="5.00",
    )

    assert response.status_code == 400
    assert "Insufficient leave balance for year 2027" in response.json()["detail"]

    remaining_requests = get_leave_requests(client,db_session,employee_id,params={"employee_id": employee_id},)

    assert remaining_requests.status_code == 200
    assert remaining_requests.json() == []


def test_reject_weekend_only_leave_request(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-14",
        end_date="2026-11-15",
        requested_days="2.00",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Leave request must include at least one working day."
    )


def test_reject_leave_request_with_mismatched_working_days(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="2.00",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Requested days must equal 3 working days for the selected date range."
    )



def test_create_leave_request_spanning_weekend(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-13",
        end_date="2026-11-16",
        requested_days="2.00",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"
    assert Decimal(str(response.json()["requested_days"])) == Decimal("2.00")



def submit_leave_request(client, db_session, leave_request_id):
    """Submit a leave request using its owner's JWT."""

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    leave = db_session.get(LeaveRequest, leave_request_id)
    if leave is None:
        return client.post(f"{BASE_URL}/{leave_request_id}/submit")

    user = db_session.scalar(
        select(UserAccount).where(
            UserAccount.employee_id == leave.employee_id
        )
    )

    if user is None:
        user = UserAccount(
            id=uuid4().hex,
            employee_id=leave.employee_id,
            password_hash=hash_password("TestPassword123!"),
            role="MANAGER"
            if db_session.get(Employee, leave.employee_id).is_approver
            else "EMPLOYEE",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

    token = create_access_token(user.id)

    return client.post(
        f"{BASE_URL}/{leave_request_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )


def get_leave_request_as_employee(
    client, db_session, leave_request_id, employee_id
):
    """Retrieve a leave request using the employee's JWT."""

    user = db_session.scalar(
        select(UserAccount).where(
            UserAccount.employee_id == employee_id
        )
    )

    assert user is not None, (
        f"No user account exists for employee {employee_id}"
    )

    token = create_access_token(user.id)

    return client.get(
        f"{BASE_URL}/{leave_request_id}",
        headers={"Authorization": f"Bearer {token}"},
    )



def get_leave_requests(
    client,
    db_session,
    employee_id,
    **kwargs,
):
    """List leave requests using the employee's JWT."""

    from app.core.security import create_access_token
    from app.db.models import UserAccount
    from sqlalchemy import select

    user = db_session.scalar(
        select(UserAccount).where(
            UserAccount.employee_id == employee_id
        )
    )

    assert user is not None, (
        f"No test user account exists for employee {employee_id}"
    )

    token = create_access_token(user.id)

    return client.get(
        BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
        **kwargs,
    )



def test_reject_draft_when_leave_balance_is_insufficient(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    balance.entitled_days = Decimal("2.00")
    db_session.commit()

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert response.status_code == 400
    assert "Insufficient leave balance for year 2026" in response.json()["detail"]

    remaining_requests = get_leave_requests(client,db_session,employee_id,params={"employee_id": employee_id},)

    assert remaining_requests.status_code == 200
    assert remaining_requests.json() == []


def test_reject_draft_when_leave_balance_is_missing(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.delete(balance)
    db_session.commit()

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Leave balance not found for year 2026."
    )

    remaining_requests = get_leave_requests(client,db_session,employee_id,params={"employee_id": employee_id},)

    assert remaining_requests.status_code == 200
    assert remaining_requests.json() == []



def test_create_cross_year_leave_with_sufficient_balances(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    policy = db_session.get(LeavePolicy, policy_id)
    policy.effective_to = date(2027, 12, 31)

    balance_2027 = LeaveBalance(
        id="BAL-EMP001-2027",
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2027,
        entitled_days=Decimal("20.00"),
        used_days=Decimal("0.00"),
        pending_days=Decimal("0.00"),
        carryover_days=Decimal("0.00"),
        adjustment_days=Decimal("0.00"),
    )

    db_session.add(balance_2027)
    db_session.commit()

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-12-29",
        end_date="2027-01-04",
        requested_days="5.00",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"
    assert Decimal(str(response.json()["requested_days"])) == Decimal("5.00")

    balance_2026 = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance_2026)
    db_session.refresh(balance_2027)

    assert balance_2026.pending_days == Decimal("0.00")
    assert balance_2027.pending_days == Decimal("0.00")


def test_submit_leave_request_reserves_balance(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    # Create a draft requesting 3 working days.
    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    # Submit the draft.
    submit_response = submit_leave_request(
       client, db_session, leave_request_id
    )
    assert submit_response.status_code == 200

    data = submit_response.json()
    assert data["status"] == "SUBMITTED"
    assert data["submitted_at"] is not None

    # Verify the leave balance was reserved.
    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("3.00")
    assert balance.used_days == Decimal("0.00")
    assert balance.available_days == Decimal("17.00")


def test_cannot_submit_same_leave_request_twice(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    # First submission should succeed.
    first_response = submit_leave_request(
        client, db_session, leave_request_id
    )
    assert first_response.status_code == 200
    assert first_response.json()["status"] == "SUBMITTED"

    # Second submission should be rejected.
    second_response = submit_leave_request(
        client, db_session, leave_request_id
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Only draft leave requests can be submitted."
    )

    # Verify that leave days were reserved only once.
    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("3.00")
    assert balance.available_days == Decimal("17.00")


def test_cannot_submit_overlapping_leave_requests(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    # Create and submit the first leave request.
    first_create = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert first_create.status_code == 201
    first_id = first_create.json()["id"]

    first_submit = submit_leave_request(client, db_session, first_id)
    assert first_submit.status_code == 200

    # Create another draft overlapping the first request.
    second_create = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-11",
        end_date="2026-11-13",
        requested_days="3.00",
    )

    assert second_create.status_code == 201
    second_id = second_create.json()["id"]

    # Submitting the overlapping request must fail.
    second_submit = submit_leave_request(client, db_session, second_id)

    assert second_submit.status_code == 409
    assert "overlaps" in second_submit.json()["detail"].lower()

    # The second request must remain a draft.
    second_get = get_leave_request_as_employee(client, db_session, second_id, employee_id)

    assert second_get.status_code == 200
    assert second_get.json()["status"] == "DRAFT"

    # Only the first request's 3 days should be reserved.
    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("3.00")
    assert balance.available_days == Decimal("17.00")


def test_submit_cross_year_leave_reserves_both_years(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)

    # Extend the policy into 2027.
    policy = db_session.get(LeavePolicy, policy_id)
    policy.effective_to = date(2027, 12, 31)

    # Create the employee's 2027 balance.
    balance_2027 = LeaveBalance(
        id=f"BAL-2027-{uuid4().hex[:12]}",
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2027,
        entitled_days=Decimal("20.00"),
        used_days=Decimal("0.00"),
        pending_days=Decimal("0.00"),
        carryover_days=Decimal("0.00"),
        adjustment_days=Decimal("0.00"),
    )

    db_session.add(balance_2027)
    db_session.commit()

    # December 29–31 = 3 working days.
    # January 1 and 4 = 2 working days.
    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-12-29",
        end_date="2027-01-04",
        requested_days="5.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)

    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "SUBMITTED"

    balances = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
    ).all()

    for balance in balances:
        db_session.refresh(balance)

    balances_by_year = {
        balance.period_year: balance for balance in balances
    }

    assert balances_by_year[2026].pending_days == Decimal("3.00")
    assert balances_by_year[2027].pending_days == Decimal("2.00")

    assert balances_by_year[2026].available_days == Decimal("17.00")
    assert balances_by_year[2027].available_days == Decimal("18.00")



def test_cross_year_submission_rolls_back_when_balance_insufficient(
    client, db_session
):
    employee_id, policy_id = setup_leave_data(client, db_session)

    # Extend the policy into 2027.
    policy = db_session.get(LeavePolicy, policy_id)
    policy.effective_to = date(2027, 12, 31)

    balance_2027 = LeaveBalance(
        id=f"BAL-2027-{uuid4().hex[:12]}",
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2027,
        entitled_days=Decimal("20.00"),
        used_days=Decimal("0.00"),
        pending_days=Decimal("0.00"),
        carryover_days=Decimal("0.00"),
        adjustment_days=Decimal("0.00"),
    )

    db_session.add(balance_2027)
    db_session.commit()

    # Create a draft while both years have sufficient balances.
    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-12-29",
        end_date="2027-01-04",
        requested_days="5.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    # Simulate another operation consuming the 2027 balance.
    balance_2027.pending_days = Decimal("19.00")
    db_session.commit()

    # Submission requires 2 days in 2027, but only 1 is available.

    submit_response = submit_leave_request(client, db_session, leave_request_id)

    assert submit_response.status_code == 400
    assert "Insufficient leave balance for year 2027" in (
        submit_response.json()["detail"]
    )

    # The leave request must remain a draft.
    request_response = get_leave_request_as_employee(client, db_session, leave_request_id, employee_id)
    assert request_response.status_code == 200
    assert request_response.json()["status"] == "DRAFT"
    assert request_response.json()["submitted_at"] is None

    # Verify neither year's balance was changed by submission.
    balance_2026 = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance_2026)
    db_session.refresh(balance_2027)

    assert balance_2026.pending_days == Decimal("0.00")
    assert balance_2027.pending_days == Decimal("19.00")
    assert balance_2026.available_days == Decimal("20.00")
    assert balance_2027.available_days == Decimal("1.00")

from app.db.models.models import AuditEvent
def test_submit_leave_rolls_back_when_commit_fails(
    client, db_session, monkeypatch
):
    from sqlalchemy.orm import Session

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    original_commit = Session.commit

    def failing_commit(self):
        # Flush pending updates to SQLite, then simulate failure.
        self.flush()
        raise RuntimeError("Simulated database commit failure")

    monkeypatch.setattr(Session, "commit", failing_commit)

    # The endpoint should roll back and propagate the error.
    with pytest.raises(
        RuntimeError,
        match="Simulated database commit failure",
    ):
       submit_leave_request(client, db_session, leave_request_id)

    # Restore normal commit behavior for verification.
    monkeypatch.setattr(Session, "commit", original_commit)

    leave_request = db_session.get(LeaveRequest, leave_request_id)
    db_session.refresh(leave_request)

    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    # No partial submission changes should survive.
    assert leave_request.status == "DRAFT"
    assert leave_request.submitted_at is None

    assert balance.pending_days == Decimal("0.00")
    assert balance.used_days == Decimal("0.00")
    assert balance.available_days == Decimal("20.00")
    
    # A failed transaction must not persist an audit event.
    audit_events = (
        db_session.query(AuditEvent)
        .filter_by(
            entity_type="LEAVE_REQUEST",
            entity_id=leave_request_id,
            event_type="LEAVE_SUBMITTED",
        )
        .all()
    )

    assert len(audit_events) == 0



def test_submit_leave_creates_audit_event(client, db_session):
    from app.db.models.models import AuditEvent

    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert response.status_code == 201
    leave_request_id = response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    events = (
        db_session.query(AuditEvent)
        .filter_by(
            entity_type="LEAVE_REQUEST",
            entity_id=leave_request_id,
            event_type="LEAVE_SUBMITTED",
        )
        .all()
    )

    assert len(events) == 1

    event = events[0]

    assert event.actor_employee_id == employee_id
    assert event.old_values == {"status": "DRAFT"}
    assert event.new_values == {"status": "SUBMITTED"}
    assert event.event_id
    assert event.occurred_at is not None


def test_submit_leave_creates_manager_approval_step(client, db_session):
    from sqlalchemy import select
    from app.db.models.models import ApprovalStep, Employee

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)

    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "SUBMITTED"

    steps = db_session.scalars(
        select(ApprovalStep).where(
            ApprovalStep.leave_request_id == leave_request_id
        )
    ).all()

    assert len(steps) == 1

    step = steps[0]
    requester = db_session.get(Employee, employee_id)

    assert step.step_number == 1
    assert step.approver_employee_id == requester.manager_id
    assert step.status == "PENDING"
    assert step.rule_id is not None
    assert step.expense_claim_id is None
    assert step.assigned_at is not None


def test_submit_leave_rolls_back_when_approver_inactive(client, db_session):
    from decimal import Decimal
    from sqlalchemy import select

    from app.db.models.models import (
        ApprovalStep,
        Employee,
        LeaveBalance,
        LeaveRequest,
    )

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    requester = db_session.get(Employee, employee_id)
    manager = db_session.get(Employee, requester.manager_id)

    # Simulate the manager becoming inactive before submission.
    manager.employment_status = "INACTIVE"
    db_session.commit()

    submit_response = submit_leave_request(client, db_session, leave_request_id)

    assert submit_response.status_code == 400
    assert "not an active employee" in submit_response.json()["detail"]

    # Submission must remain a draft.
    leave_request = db_session.get(LeaveRequest, leave_request_id)
    db_session.refresh(leave_request)

    assert leave_request.status == "DRAFT"
    assert leave_request.submitted_at is None

    # Pending leave days must not be reserved.
    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("0.00")
    assert balance.available_days == Decimal("20.00")

    # No approval steps should be persisted.
    steps = db_session.scalars(
        select(ApprovalStep).where(
            ApprovalStep.leave_request_id == leave_request_id
        )
    ).all()

    assert steps == []



def test_manager_final_approval_updates_leave_balance(client, db_session):
    from decimal import Decimal

    from app.db.models.models import (
        ApprovalStep,
        Employee,
        LeaveBalance,
        LeaveRequest,
    )
    from app.services.approval_decisions import approve_leave_request

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    result = approve_leave_request(
        db=db_session,
        leave_request_id=leave_request_id,
        actor_employee_id=manager_id,
        reason="Leave approved by manager.",
    )

    assert result.status == "APPROVED"
    assert result.decided_at is not None
    assert result.decision_reason == "Leave approved by manager."

    step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
    ).one()

    assert step.status == "APPROVED"
    assert step.decision == "APPROVED"
    assert step.approver_employee_id == manager_id
    assert step.decided_at is not None

    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("0.00")
    assert balance.used_days == Decimal("3.00")
    assert balance.available_days == Decimal("17.00")

    leave_request = db_session.get(LeaveRequest, leave_request_id)
    assert leave_request.status == "APPROVED"



def test_manager_rejection_releases_reserved_leave_balance(client, db_session):
    from decimal import Decimal

    from app.db.models.models import (
        ApprovalStep,
        Employee,
        LeaveBalance,
        LeaveRequest,
    )
    from app.services.approval_decisions import reject_leave_request

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    # Confirm that leave days were reserved during submission.
    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)
    assert balance.pending_days == Decimal("3.00")

    result = reject_leave_request(
        db=db_session,
        leave_request_id=leave_request_id,
        actor_employee_id=manager_id,
        reason="Insufficient team coverage.",
    )

    assert result.status == "REJECTED"
    assert result.decided_at is not None
    assert result.decision_reason == "Insufficient team coverage."

    step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
    ).one()

    assert step.status == "REJECTED"
    assert step.decision == "REJECTED"
    assert step.approver_employee_id == manager_id
    assert step.decided_at is not None
    assert step.decision_reason == "Insufficient team coverage."

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("0.00")
    assert balance.used_days == Decimal("0.00")
    assert balance.available_days == Decimal("20.00")

    leave_request = db_session.get(LeaveRequest, leave_request_id)
    assert leave_request.status == "REJECTED"



def test_unassigned_approver_cannot_approve_leave(client, db_session):
    from decimal import Decimal

    from fastapi import HTTPException

    from app.db.models.models import ApprovalStep, LeaveBalance
    from app.services.approval_decisions import approve_leave_request

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    # Create another active approver who is not assigned to this request.
    other_approver_response = create_employee(
        client,
        employee_number="EMP-OTHER-APPROVER",
        email="other.approver@example.com",
        is_approver=True,
    )
    assert other_approver_response.status_code == 201

    other_approver_id = other_approver_response.json()["id"]

    try:
        approve_leave_request(
            db=db_session,
            leave_request_id=leave_request_id,
            actor_employee_id=other_approver_id,
        )
        assert False, "Expected HTTPException for unauthorized approval."
    except HTTPException as exc:
        assert exc.status_code == 403

    # Verify the leave request was not approved.
    get_response = get_leave_request_as_employee(client, db_session, leave_request_id, employee_id)
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "SUBMITTED"

    # Verify the assigned approval step is still pending.
    step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
    ).one()

    assert step.status == "PENDING"
    assert step.decided_at is None

    # Verify reserved leave days remain unchanged.
    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("3.00")
    assert balance.used_days == Decimal("0.00")



def test_second_level_cannot_approve_before_first_level(client, db_session):
    from fastapi import HTTPException

    from app.db.models.models import ApprovalStep, Employee
    from app.services.approval_decisions import (
        approve_leave_request,
    )

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    # Create a second-level approver.
    level_two_response = create_employee(
        client,
        employee_number="EMP-LEVEL2",
        email="level2@example.com",
        is_approver=True,
        attributes={"approval_roles": ["HR"]},
    )
    assert level_two_response.status_code == 201

    level_two_id = level_two_response.json()["id"]

    # Add a second approval step to the submitted request.
    first_step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
        step_number=1,
    ).one()

    second_step = ApprovalStep(
        id=f"APR-{leave_request_id}-02",
        leave_request_id=leave_request_id,
        expense_claim_id=None,
        rule_id=first_step.rule_id,
        step_number=2,
        approver_employee_id=level_two_id,
        approver_role="HR",
        status="PENDING",
        is_required=True,
        decision_metadata={},
    )

    db_session.add(second_step)
    db_session.commit()

    # Level 2 must not bypass Level 1.
    try:
        approve_leave_request(
            db=db_session,
            leave_request_id=leave_request_id,
            actor_employee_id=level_two_id,
        )
        assert False, "Expected Level 2 approval to be rejected."
    except HTTPException as exc:
        assert exc.status_code == 403

    db_session.refresh(first_step)
    db_session.refresh(second_step)

    assert first_step.status == "PENDING"
    assert second_step.status == "PENDING"

    get_response = get_leave_request_as_employee(client, db_session, leave_request_id, employee_id)
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "SUBMITTED"



def test_two_level_leave_approval_finalizes_only_after_last_step(client, db_session):
    from decimal import Decimal

    from app.db.models.models import ApprovalStep, Employee, LeaveBalance
    from app.services.approval_decisions import approve_leave_request

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    hr_response = create_employee(
        client,
        employee_number="EMP-HR-LEVEL2",
        email="hr.level2@example.com",
        is_approver=True,
        attributes={"approval_roles": ["HR"]},
    )
    assert hr_response.status_code == 201
    hr_id = hr_response.json()["id"]

    first_step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
        step_number=1,
    ).one()

    second_step = ApprovalStep(
        id=f"APR-{leave_request_id}-02",
        leave_request_id=leave_request_id,
        expense_claim_id=None,
        rule_id=first_step.rule_id,
        step_number=2,
        approver_employee_id=hr_id,
        approver_role="HR",
        status="PENDING",
        is_required=True,
        decision_metadata={},
    )

    db_session.add(second_step)
    db_session.commit()

    # Level 1 approval must not finalize the leave.
    first_result = approve_leave_request(
        db=db_session,
        leave_request_id=leave_request_id,
        actor_employee_id=manager_id,
        reason="Manager approved.",
    )

    assert first_result.status == "PENDING_APPROVAL"
    assert first_result.decided_at is None

    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)
    assert balance.pending_days == Decimal("3.00")
    assert balance.used_days == Decimal("0.00")

    db_session.refresh(first_step)
    db_session.refresh(second_step)

    assert first_step.status == "APPROVED"
    assert second_step.status == "PENDING"

    # Level 2 approval completes the request.
    final_result = approve_leave_request(
        db=db_session,
        leave_request_id=leave_request_id,
        actor_employee_id=hr_id,
        reason="HR approved.",
    )

    assert final_result.status == "APPROVED"
    assert final_result.decided_at is not None

    db_session.refresh(balance)
    assert balance.pending_days == Decimal("0.00")
    assert balance.used_days == Decimal("3.00")
    assert balance.available_days == Decimal("17.00")

    db_session.refresh(second_step)
    assert second_step.status == "APPROVED"
    assert second_step.approver_employee_id == hr_id



def test_second_level_rejection_releases_leave_balance(client, db_session):
    from decimal import Decimal

    from app.db.models.models import ApprovalStep, Employee, LeaveBalance
    from app.services.approval_decisions import (
        approve_leave_request,
        reject_leave_request,
    )

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    hr_response = create_employee(
        client,
        employee_number="EMP-HR-REJECT",
        email="hr.reject@example.com",
        is_approver=True,
        attributes={"approval_roles": ["HR"]},
    )
    assert hr_response.status_code == 201
    hr_id = hr_response.json()["id"]

    first_step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
        step_number=1,
    ).one()

    second_step = ApprovalStep(
        id=f"APR-{leave_request_id}-02",
        leave_request_id=leave_request_id,
        expense_claim_id=None,
        rule_id=first_step.rule_id,
        step_number=2,
        approver_employee_id=hr_id,
        approver_role="HR",
        status="PENDING",
        is_required=True,
        decision_metadata={},
    )
    db_session.add(second_step)
    db_session.commit()

    first_result = approve_leave_request(
        db=db_session,
        leave_request_id=leave_request_id,
        actor_employee_id=manager_id,
        reason="Manager approved.",
    )
    assert first_result.status == "PENDING_APPROVAL"

    rejection_result = reject_leave_request(
        db=db_session,
        leave_request_id=leave_request_id,
        actor_employee_id=hr_id,
        reason="Insufficient staffing coverage.",
    )

    assert rejection_result.status == "REJECTED"
    assert rejection_result.decided_at is not None
    assert rejection_result.decision_reason == "Insufficient staffing coverage."

    db_session.refresh(first_step)
    db_session.refresh(second_step)

    assert first_step.status == "APPROVED"
    assert second_step.status == "REJECTED"
    assert second_step.decision_reason == "Insufficient staffing coverage."

    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("0.00")
    assert balance.used_days == Decimal("0.00")
    assert balance.available_days == Decimal("20.00")


def test_cannot_approve_already_approved_leave(client, db_session):
    import pytest
    from decimal import Decimal
    from fastapi import HTTPException

    from app.db.models.models import ApprovalStep, Employee, LeaveBalance
    from app.services.approval_decisions import approve_leave_request

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    # First approval succeeds.
    result = approve_leave_request(
        db=db_session,
        leave_request_id=leave_request_id,
        actor_employee_id=manager_id,
        reason="Approved.",
    )
    assert result.status == "APPROVED"

    # Second approval must fail.
    with pytest.raises(HTTPException) as exc_info:
        approve_leave_request(
            db=db_session,
            leave_request_id=leave_request_id,
            actor_employee_id=manager_id,
            reason="Duplicate approval.",
        )

    assert exc_info.value.status_code == 409

    # Verify the original approval remains unchanged.
    step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
    ).one()

    assert step.status == "APPROVED"
    assert step.decision_reason == "Approved."

    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("0.00")
    assert balance.used_days == Decimal("3.00")
    assert balance.available_days == Decimal("17.00")



def test_cannot_reject_already_rejected_leave(client, db_session):
    import pytest
    from decimal import Decimal
    from fastapi import HTTPException

    from app.db.models.models import (
        ApprovalStep,
        Employee,
        LeaveBalance,
        LeaveRequest,
    )
    from app.services.approval_decisions import reject_leave_request

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    # First rejection succeeds.
    result = reject_leave_request(
        db=db_session,
        leave_request_id=leave_request_id,
        actor_employee_id=manager_id,
        reason="Insufficient team coverage.",
    )

    assert result.status == "REJECTED"

    # A second rejection must fail.
    with pytest.raises(HTTPException) as exc_info:
        reject_leave_request(
            db=db_session,
            leave_request_id=leave_request_id,
            actor_employee_id=manager_id,
            reason="Duplicate rejection.",
        )

    assert exc_info.value.status_code == 409

    # Verify the original rejection remains unchanged.
    leave_request = db_session.get(LeaveRequest, leave_request_id)
    db_session.refresh(leave_request)

    assert leave_request.status == "REJECTED"
    assert leave_request.decision_reason == "Insufficient team coverage."

    step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
    ).one()

    assert step.status == "REJECTED"
    assert step.decision_reason == "Insufficient team coverage."

    # Verify reserved days were not released twice.
    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    db_session.refresh(balance)

    assert balance.pending_days == Decimal("0.00")
    assert balance.used_days == Decimal("0.00")
    assert balance.available_days == Decimal("20.00")


def test_approval_rolls_back_when_commit_fails(
    client, db_session, monkeypatch
):
    import pytest
    from decimal import Decimal

    from app.db.models.models import (
        ApprovalStep,
        Employee,
        LeaveBalance,
        LeaveRequest,
    )
    from app.services.approval_decisions import approve_leave_request

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    # Flush changes, then simulate a database commit failure.
    original_commit = db_session.commit

    def failing_commit():
        db_session.flush()
        raise RuntimeError("Simulated database commit failure")

    monkeypatch.setattr(db_session, "commit", failing_commit)

    with pytest.raises(
        RuntimeError,
        match="Simulated database commit failure",
    ):
        approve_leave_request(
            db=db_session,
            leave_request_id=leave_request_id,
            actor_employee_id=manager_id,
            reason="Manager approved.",
        )

    # Restore normal commit behavior.
    monkeypatch.setattr(db_session, "commit", original_commit)

    # Expire cached ORM objects to read the database state.
    db_session.expire_all()

    leave_request = db_session.get(LeaveRequest, leave_request_id)

    assert leave_request.status == "SUBMITTED"
    assert leave_request.decided_at is None

    step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
    ).one()

    assert step.status == "PENDING"
    assert step.decided_at is None

    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    assert balance.pending_days == Decimal("3.00")
    assert balance.used_days == Decimal("0.00")
    assert balance.available_days == Decimal("17.00")



def test_rejection_rolls_back_when_commit_fails(
    client, db_session, monkeypatch
):
    import pytest
    from decimal import Decimal

    from app.db.models.models import (
        ApprovalStep,
        Employee,
        LeaveBalance,
        LeaveRequest,
    )
    from app.services.approval_decisions import reject_leave_request

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    # Simulate a commit failure after flushing changes.
    original_commit = db_session.commit

    def failing_commit():
        db_session.flush()
        raise RuntimeError("Simulated rejection commit failure")

    monkeypatch.setattr(db_session, "commit", failing_commit)

    with pytest.raises(
        RuntimeError,
        match="Simulated rejection commit failure",
    ):
        reject_leave_request(
            db=db_session,
            leave_request_id=leave_request_id,
            actor_employee_id=manager_id,
            reason="Insufficient team coverage.",
        )

    # Restore the original commit method.
    monkeypatch.setattr(db_session, "commit", original_commit)

    # Read the database state after rollback.
    db_session.expire_all()

    leave_request = db_session.get(LeaveRequest, leave_request_id)

    assert leave_request.status == "SUBMITTED"
    assert leave_request.decided_at is None
    assert leave_request.decision_reason is None

    step = db_session.query(ApprovalStep).filter_by(
        leave_request_id=leave_request_id,
    ).one()

    assert step.status == "PENDING"
    assert step.decided_at is None
    assert step.decision_reason is None

    balance = db_session.query(LeaveBalance).filter_by(
        employee_id=employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
    ).one()

    assert balance.pending_days == Decimal("3.00")
    assert balance.used_days == Decimal("0.00")
    assert balance.available_days == Decimal("17.00")



def test_approval_audit_event_rolls_back_on_commit_failure(
    client, db_session, monkeypatch
):
    import pytest

    from app.db.models.models import AuditEvent, Employee
    from app.services.approval_decisions import approve_leave_request

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201

    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    original_commit = db_session.commit

    def failing_commit():
        db_session.flush()
        raise RuntimeError("Simulated approval audit commit failure")

    monkeypatch.setattr(db_session, "commit", failing_commit)

    try:
        with pytest.raises(
            RuntimeError,
            match="Simulated approval audit commit failure",
        ):
            approve_leave_request(
                db=db_session,
                leave_request_id=leave_request_id,
                actor_employee_id=manager_id,
                reason="Manager approved.",
            )
    finally:
        monkeypatch.setattr(db_session, "commit", original_commit)

    db_session.expire_all()

    approval_events = db_session.query(AuditEvent).filter_by(
        entity_type="LEAVE_REQUEST",
        entity_id=leave_request_id,
        event_type="LEAVE_APPROVED",
    ).all()

    assert approval_events == []

def test_unassigned_manager_cannot_approve_leave(client, db_session):
    """A valid JWT does not grant permission to approve another manager's request."""
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import select

    from app.core.security import create_access_token, hash_password
    from app.db.models import ApprovalStep, Employee, LeaveBalance, LeaveRequest, UserAccount

    # Create the requester and their assigned manager.
    employee_id, policy_id = setup_leave_data(client, db_session)

    response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert response.status_code == 201
    leave_request_id = response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    assigned_manager_id = requester.manager_id

    # Create another manager who is NOT assigned to this request.
    other_manager_response = create_employee(
        client,
        employee_number=f"MGR-{uuid4().hex[:8]}",
        email=f"other-manager-{uuid4().hex[:8]}@example.com",
        first_name="Other",
        last_name="Manager",
        is_approver=True,
        attributes={"approval_roles": ["MANAGER"]},
    )
    assert other_manager_response.status_code == 201

    other_manager_id = other_manager_response.json()["id"]
    assert other_manager_id != assigned_manager_id

    # Give the other manager an active account and valid JWT.
    user_id = uuid4().hex
    db_session.add(
        UserAccount(
            id=user_id,
            employee_id=other_manager_id,
            password_hash=hash_password("TestPassword123!"),
            role="MANAGER",
            is_active=True,
        )
    )
    db_session.commit()

    token = create_access_token(user_id)

    # Record database state before the unauthorized attempt.
    step = db_session.scalar(
        select(ApprovalStep).where(
            ApprovalStep.leave_request_id == leave_request_id
        )
    )
    assert step is not None
    assert step.approver_employee_id == assigned_manager_id
    assert step.status == "PENDING"

    leave = db_session.get(LeaveRequest, leave_request_id)
    original_status = leave.status

    balance = db_session.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_policy_id == policy_id,
        )
    )
    assert balance is not None
    original_pending_days = balance.pending_days
    original_used_days = balance.used_days

    # Attempt approval with the wrong manager's valid JWT.
    approval_response = client.post(
        f"{BASE_URL}/{leave_request_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert approval_response.status_code == 403
    assert approval_response.json()["detail"] == (
        "Employee is not assigned to the current approval step."
    )

    # Confirm the rejected attempt did not change approval state.
    db_session.expire_all()

    step = db_session.get(ApprovalStep, step.id)
    leave = db_session.get(LeaveRequest, leave_request_id)
    balance = db_session.get(LeaveBalance, balance.id)

    assert step.status == "PENDING"
    assert leave.status == original_status
    assert balance.pending_days == original_pending_days
    assert balance.used_days == original_used_days

def test_assigned_manager_can_approve_leave_with_jwt(client, db_session):
    """The assigned manager can approve leave through the authenticated API."""
    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import select

    from app.core.security import create_access_token, hash_password
    from app.db.models import (
        ApprovalStep,
        Employee,
        LeaveBalance,
        LeaveRequest,
        UserAccount,
    )

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )

    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    # Identify the manager assigned to this employee.
    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id

    assert manager_id is not None

    # Create an active login account for the assigned manager.
    user_id = uuid4().hex

    db_session.add(
        UserAccount(
            id=user_id,
            employee_id=manager_id,
            password_hash=hash_password("TestPassword123!"),
            role="MANAGER",
            is_active=True,
        )
    )
    db_session.commit()

    token = create_access_token(user_id)

    # Approve through the actual HTTP endpoint.
    response = client.post(
        f"{BASE_URL}/{leave_request_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"

    # Verify the approval was persisted.
    db_session.expire_all()

    leave = db_session.get(LeaveRequest, leave_request_id)

    step = db_session.scalar(
        select(ApprovalStep).where(
            ApprovalStep.leave_request_id == leave_request_id
        )
    )

    balance = db_session.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_policy_id == policy_id,
        )
    )

    assert leave.status == "APPROVED"
    assert leave.decided_at is not None

    assert step.status == "APPROVED"
    assert step.approver_employee_id == manager_id

    assert balance.pending_days == Decimal("0.00")
    assert balance.used_days == Decimal("3.00")



def test_assigned_manager_can_reject_leave_with_jwt(client, db_session):
    """The assigned manager can reject leave through the authenticated API."""

    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import select

    from app.core.security import create_access_token, hash_password
    from app.db.models import (
        ApprovalStep,
        Employee,
        LeaveBalance,
        LeaveRequest,
        UserAccount,
    )

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    manager_id = requester.manager_id
    assert manager_id is not None

    user_id = uuid4().hex
    db_session.add(
        UserAccount(
            id=user_id,
            employee_id=manager_id,
            password_hash=hash_password("TestPassword123!"),
            role="MANAGER",
            is_active=True,
        )
    )
    db_session.commit()

    token = create_access_token(user_id)

    balance = db_session.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_policy_id == policy_id,
        )
    )
    assert balance.pending_days == Decimal("3.00")
    assert balance.used_days == Decimal("0.00")

    response = client.post(
        f"{BASE_URL}/{leave_request_id}/reject",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Insufficient staffing."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    assert response.json()["decision_reason"] == "Insufficient staffing."

    db_session.expire_all()

    leave = db_session.get(LeaveRequest, leave_request_id)
    step = db_session.scalar(
        select(ApprovalStep).where(
            ApprovalStep.leave_request_id == leave_request_id
        )
    )
    balance = db_session.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_policy_id == policy_id,
        )
    )

    assert leave.status == "REJECTED"
    assert leave.decided_at is not None
    assert step.status == "REJECTED"
    assert step.approver_employee_id == manager_id

    assert balance.pending_days == Decimal("0.00")
    assert balance.used_days == Decimal("0.00")
    assert balance.available_days == Decimal("20.00")



def test_unassigned_manager_cannot_reject_leave(client, db_session):
    """An unassigned manager cannot reject another manager's request."""

    from decimal import Decimal
    from uuid import uuid4

    from sqlalchemy import select

    from app.core.security import create_access_token, hash_password
    from app.db.models import (
        ApprovalStep,
        Employee,
        LeaveBalance,
        LeaveRequest,
        UserAccount,
    )

    employee_id, policy_id = setup_leave_data(client, db_session)

    create_response = create_leave_request(
        client,
        employee_id,
        policy_id,
        start_date="2026-11-10",
        end_date="2026-11-12",
        requested_days="3.00",
    )
    assert create_response.status_code == 201
    leave_request_id = create_response.json()["id"]

    submit_response = submit_leave_request(client, db_session, leave_request_id)
    assert submit_response.status_code == 200

    requester = db_session.get(Employee, employee_id)
    assigned_manager_id = requester.manager_id

    other_manager_response = create_employee(
        client,
        employee_number=f"MGR-{uuid4().hex[:8]}",
        email=f"other-manager-{uuid4().hex[:8]}@example.com",
        first_name="Other",
        last_name="Manager",
        is_approver=True,
        attributes={"approval_roles": ["MANAGER"]},
    )
    assert other_manager_response.status_code == 201

    other_manager_id = other_manager_response.json()["id"]
    assert other_manager_id != assigned_manager_id

    user_id = uuid4().hex
    db_session.add(
        UserAccount(
            id=user_id,
            employee_id=other_manager_id,
            password_hash=hash_password("TestPassword123!"),
            role="MANAGER",
            is_active=True,
        )
    )
    db_session.commit()

    token = create_access_token(user_id)

    step = db_session.scalar(
        select(ApprovalStep).where(
            ApprovalStep.leave_request_id == leave_request_id
        )
    )
    balance = db_session.scalar(
        select(LeaveBalance).where(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_policy_id == policy_id,
        )
    )

    original_pending_days = balance.pending_days
    original_used_days = balance.used_days
    original_leave_status = db_session.get(
        LeaveRequest, leave_request_id
    ).status

    response = client.post(
        f"{BASE_URL}/{leave_request_id}/reject",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Unauthorized rejection attempt."},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Employee is not assigned to the current approval step."
    )

    db_session.expire_all()

    step = db_session.get(ApprovalStep, step.id)
    leave = db_session.get(LeaveRequest, leave_request_id)
    balance = db_session.get(LeaveBalance, balance.id)

    assert step.status == "PENDING"
    assert leave.status == original_leave_status
    assert balance.pending_days == original_pending_days
    assert balance.used_days == original_used_days
    assert balance.available_days == Decimal("17.00")


def test_employee_cannot_list_another_employees_leaves(client, db_session):
    first_employee_id, policy_id = setup_leave_data(client, db_session)

    first_created = create_leave_request(
        client, first_employee_id, policy_id
    )
    assert first_created.status_code == 201

    second_employee = create_employee(
        client,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"employee-{uuid4().hex[:8]}@example.com",
    )
    assert second_employee.status_code == 201

    second_employee_id = second_employee.json()["id"]
    
    # Give the second employee a leave balance for 2026.
    second_balance = LeaveBalance(
        id=f"BAL-{uuid4().hex[:12]}",
        employee_id=second_employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
        entitled_days=Decimal("20.00"),
        used_days=Decimal("0.00"),
        pending_days=Decimal("0.00"),
        carryover_days=Decimal("0.00"),
        adjustment_days=Decimal("0.00"),
    )

    db_session.add(second_balance)
    db_session.commit()


    second_created = create_leave_request(
        client, second_employee_id, policy_id
    )
    print("SECOND EMPLOYEE ERROR:", second_created.status_code, second_created.json())

    assert second_created.status_code == 201

    # First employee attempts to retrieve the second employee's requests.
    response = get_leave_requests(
        client,
        db_session,
        first_employee_id,
        params={"employee_id": second_employee_id},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_leave_requests_requires_authentication(client):
    response = client.get(BASE_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )



def test_employee_cannot_get_another_employees_leave_by_id(
    client, db_session
):
    first_employee_id, policy_id = setup_leave_data(
        client, db_session
    )

    first_created = create_leave_request(
        client, first_employee_id, policy_id
    )
    assert first_created.status_code == 201

    second_employee_response = create_employee(
        client,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"employee-{uuid4().hex[:8]}@example.com",
    )
    assert second_employee_response.status_code == 201

    second_employee_id = second_employee_response.json()["id"]

    # The second employee needs a leave balance.
    second_balance = LeaveBalance(
        id=f"BAL-{uuid4().hex[:12]}",
        employee_id=second_employee_id,
        leave_policy_id=policy_id,
        period_year=2026,
        entitled_days=Decimal("20.00"),
        used_days=Decimal("0.00"),
        pending_days=Decimal("0.00"),
        carryover_days=Decimal("0.00"),
        adjustment_days=Decimal("0.00"),
    )
    db_session.add(second_balance)
    db_session.commit()

    second_created = create_leave_request(
        client, second_employee_id, policy_id
    )
    assert second_created.status_code == 201

    second_leave_id = second_created.json()["id"]

    # Authenticate as the first employee.
    user = db_session.scalar(
        select(UserAccount).where(
            UserAccount.employee_id == first_employee_id
        )
    )
    assert user is not None

    token = create_access_token(user.id)

    # Attempt to access the second employee's leave request.
    response = client.get(
        f"{BASE_URL}/{second_leave_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Employees can only view their own leave requests."
    )


def test_get_leave_request_by_id_requires_authentication(client):
    response = client.get(
        f"{BASE_URL}/LVE-NOT-FOUND"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )


def test_get_leave_balances_requires_authentication(client):
    response = client.get(
        f"{BASE_URL}/balances/EMP-MISSING",
        params={"year": 2026},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )


def test_employee_cannot_view_another_employees_leave_balances(
    client, db_session
):
    # Create two different employees.
    first_response = create_employee(
        client,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"first-{uuid4().hex[:8]}@example.com",
    )
    assert first_response.status_code == 201

    second_response = create_employee(
        client,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"second-{uuid4().hex[:8]}@example.com",
    )
    assert second_response.status_code == 201

    first_employee_id = first_response.json()["id"]
    second_employee_id = second_response.json()["id"]

    # Create an account for Employee A.
    first_user = UserAccount(
        id=uuid4().hex,
        employee_id=first_employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )
    db_session.add(first_user)
    db_session.commit()

    # Generate Employee A's JWT.
    token = create_access_token(first_user.id)

    # Employee A attempts to access Employee B's balances.
    response = client.get(
        f"{BASE_URL}/balances/{second_employee_id}",
        params={"year": 2026},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Employees can only view their own leave balances."
    )


def test_create_employee_requires_authentication(client):
    response = client.post(
        EMPLOYEE_URL,
        json=employee_payload(
            employee_number=f"EMP-{uuid4().hex[:8]}",
            email=f"unauthorized-{uuid4().hex[:8]}@example.com",
        ),
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )


def test_regular_employee_cannot_create_employee(client, db_session):
    # Create an employee using the authorized ADMIN test helper.
    employee_response = create_employee(
        client,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"regular-{uuid4().hex[:8]}@example.com",
    )
    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    # Create a regular EMPLOYEE user account.
    user = UserAccount(
        id=uuid4().hex,
        employee_id=employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)

    # Attempt to create another employee using the EMPLOYEE JWT.
    response = client.post(
        EMPLOYEE_URL,
        json=employee_payload(
            employee_number=f"EMP-{uuid4().hex[:8]}",
            email=f"blocked-{uuid4().hex[:8]}@example.com",
        ),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"



def test_manager_cannot_create_employee(client, db_session):
    # Create an employee using the authorized ADMIN helper.
    manager_response = create_employee(
        client,
        employee_number=f"MGR-{uuid4().hex[:8]}",
        email=f"manager-{uuid4().hex[:8]}@example.com",
        is_approver=True,
    )
    assert manager_response.status_code == 201

    manager_id = manager_response.json()["id"]

    # Create an authenticated MANAGER account.
    manager_user = UserAccount(
        id=uuid4().hex,
        employee_id=manager_id,
        password_hash=hash_password("TestPassword123!"),
        role="MANAGER",
        is_active=True,
    )

    db_session.add(manager_user)
    db_session.commit()

    token = create_access_token(manager_user.id)

    # Attempt to create another employee as MANAGER.
    response = client.post(
        EMPLOYEE_URL,
        json=employee_payload(
            employee_number=f"EMP-{uuid4().hex[:8]}",
            email=f"blocked-{uuid4().hex[:8]}@example.com",
        ),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"



def test_hr_can_create_employee(client, db_session):
    # Create an employee using the authorized ADMIN helper.
    hr_response = create_employee(
        client,
        employee_number=f"HR-{uuid4().hex[:8]}",
        email=f"hr-{uuid4().hex[:8]}@example.com",
    )
    assert hr_response.status_code == 201

    hr_employee_id = hr_response.json()["id"]

    # Create an active HR user account.
    hr_user = UserAccount(
        id=uuid4().hex,
        employee_id=hr_employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="HR",
        is_active=True,
    )

    db_session.add(hr_user)
    db_session.commit()

    # Generate a valid HR JWT.
    token = create_access_token(hr_user.id)

    # Create another employee using HR permissions.
    response = client.post(
        EMPLOYEE_URL,
        json=employee_payload(
            employee_number=f"EMP-{uuid4().hex[:8]}",
            email=f"new-employee-{uuid4().hex[:8]}@example.com",
        ),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["id"] is not None

    # Confirm the employee was actually saved.
    created_employee = db_session.get(
        Employee, response.json()["id"]
    )

    assert created_employee is not None


def test_admin_can_create_employee(client, admin_auth_headers, db_session):
    response = client.post(
        EMPLOYEE_URL,
        json=employee_payload(
            employee_number=f"EMP-{uuid4().hex[:8]}",
            email=f"admin-created-{uuid4().hex[:8]}@example.com",
        ),
        headers=admin_auth_headers,
    )

    assert response.status_code == 201

    employee_id = response.json()["id"]
    assert employee_id is not None

    # Verify the employee was saved in the database.
    employee = db_session.get(Employee, employee_id)

    assert employee is not None
    assert employee.id == employee_id


def test_update_employee_requires_authentication(client):
    response = client.patch(
        f"{EMPLOYEE_URL}/EMP-NOT-FOUND",
        json={"department": "Finance"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )


def test_regular_employee_cannot_update_employee(client, db_session):
    # Create an employee using the authorized ADMIN helper.
    employee_response = create_employee(
        client,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"regular-{uuid4().hex[:8]}@example.com",
    )
    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    # Create an active EMPLOYEE user account.
    user = UserAccount(
        id=uuid4().hex,
        employee_id=employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)

    # Attempt to update the employee record.
    response = client.patch(
        f"{EMPLOYEE_URL}/{employee_id}",
        json={"department": "Finance"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

    # Verify that the unauthorized update was not applied.
    db_session.expire_all()
    employee = db_session.get(Employee, employee_id)

    assert employee is not None
    assert employee.department != "Finance"


def test_manager_cannot_update_employee(client, db_session):
    # Create a manager using the authorized ADMIN helper.
    manager_response = create_employee(
        client,
        employee_number=f"MGR-{uuid4().hex[:8]}",
        email=f"manager-{uuid4().hex[:8]}@example.com",
        is_approver=True,
    )
    assert manager_response.status_code == 201

    manager_id = manager_response.json()["id"]

    # Create an active MANAGER user account.
    manager_user = UserAccount(
        id=uuid4().hex,
        employee_id=manager_id,
        password_hash=hash_password("TestPassword123!"),
        role="MANAGER",
        is_active=True,
    )

    db_session.add(manager_user)
    db_session.commit()

    token = create_access_token(manager_user.id)

    # Attempt to update the manager's own employee record.
    response = client.patch(
        f"{EMPLOYEE_URL}/{manager_id}",
        json={"department": "Finance"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

    # Confirm the unauthorized change was not saved.
    db_session.expire_all()

    manager = db_session.get(Employee, manager_id)

    assert manager is not None
    assert manager.department != "Finance"


def test_hr_can_update_employee(client, db_session):
    # Create an HR employee using the ADMIN helper.
    hr_response = create_employee(
        client,
        employee_number=f"HR-{uuid4().hex[:8]}",
        email=f"hr-{uuid4().hex[:8]}@example.com",
    )
    assert hr_response.status_code == 201

    hr_employee_id = hr_response.json()["id"]

    # Create an active HR user account.
    hr_user = UserAccount(
        id=uuid4().hex,
        employee_id=hr_employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="HR",
        is_active=True,
    )

    db_session.add(hr_user)
    db_session.commit()

    token = create_access_token(hr_user.id)

    # Create the employee whose record HR will update.
    target_response = create_employee(
        client,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"target-{uuid4().hex[:8]}@example.com",
    )
    assert target_response.status_code == 201

    target_id = target_response.json()["id"]

    # Update the employee using HR authorization.
    response = client.patch(
        f"{EMPLOYEE_URL}/{target_id}",
        json={"department": "Finance"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["department"] == "Finance"

    # Verify the update was saved in the database.
    db_session.expire_all()

    updated_employee = db_session.get(Employee, target_id)

    assert updated_employee is not None
    assert updated_employee.department == "Finance"


def test_admin_can_update_employee(
    client, admin_auth_headers, db_session
):
    # Create an employee using the authorized ADMIN helper.
    employee_response = create_employee(
        client,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"admin-update-{uuid4().hex[:8]}@example.com",
    )
    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]

    # Update the employee using ADMIN authorization.
    response = client.patch(
        f"{EMPLOYEE_URL}/{employee_id}",
        json={"department": "Finance"},
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["department"] == "Finance"

    # Verify the update was saved in the database.
    db_session.expire_all()

    updated_employee = db_session.get(Employee, employee_id)

    assert updated_employee is not None
    assert updated_employee.department == "Finance"




