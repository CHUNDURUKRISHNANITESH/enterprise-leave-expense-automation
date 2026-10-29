from datetime import date
from decimal import Decimal

from app.db.models.models import LeaveBalance, LeavePolicy


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
    """Create an employee through the employee API."""
    return client.post(EMPLOYEE_URL, json=employee_payload(**overrides))


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
    """Create a leave request through the leave API."""
    return client.post(
        BASE_URL,
        json=leave_payload(employee_id, leave_policy_id, **overrides),
    )


def setup_leave_data(client, db_session):
    """Create an employee and policy for a leave request test."""
    employee_response = create_employee(client)
    assert employee_response.status_code == 201

    employee_id = employee_response.json()["id"]
    policy = create_policy(db_session)

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

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only active employees can create leave requests."
    )


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
        end_date="2026-11-20",
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
    employee_id, policy_id = setup_leave_data(client, db_session)
    payload = leave_payload(employee_id, policy_id)
    del payload["start_date"]

    response = client.post(BASE_URL, json=payload)

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

    response = client.get(BASE_URL)

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

    response = client.get(
        BASE_URL,
        params={"employee_id": first_employee_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_id"] == first_employee_id


def test_filter_leave_requests_by_status(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)
    create_leave_request(client, employee_id, policy_id)

    response = client.get(BASE_URL, params={"status": "DRAFT"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "DRAFT"


def test_reject_invalid_leave_status_filter(client):
    response = client.get(BASE_URL, params={"status": "INVALID"})

    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid leave request status."


def test_reject_invalid_leave_pagination(client):
    response = client.get(BASE_URL, params={"limit": 0})

    assert response.status_code == 422


def test_get_leave_request_by_id(client, db_session):
    employee_id, policy_id = setup_leave_data(client, db_session)
    created = create_leave_request(client, employee_id, policy_id)
    leave_id = created.json()["id"]

    response = client.get(f"{BASE_URL}/{leave_id}")

    assert response.status_code == 200
    assert response.json()["id"] == leave_id


def test_get_leave_request_not_found(client):
    response = client.get(f"{BASE_URL}/LVE-NOT-FOUND")

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

    response = client.get(
        f"{BASE_URL}/balances/{employee_id}",
        params={"year": 2026},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_id"] == employee_id
    assert Decimal(data[0]["available_days"]) == Decimal("15.00")


def test_get_balances_for_employee_without_balances(client):
    employee_response = create_employee(client)

    response = client.get(
        f"{BASE_URL}/balances/{employee_response.json()['id']}",
        params={"year": 2026},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_get_balances_for_missing_employee(client):
    response = client.get(f"{BASE_URL}/balances/EMP-MISSING")

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found."
