
BASE_URL = "/api/v1/employees"


def employee_payload(**overrides):
    """Return a valid employee payload with optional field overrides."""
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


def create_employee(client,admin_auth_headers, **overrides):
    """Create an employee and return the HTTP response."""
    return client.post(BASE_URL, json=employee_payload(**overrides),headers=admin_auth_headers,)


def test_create_employee(client, admin_auth_headers):
    response = create_employee(client,admin_auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["employee_number"] == "EMP001"
    assert data["first_name"] == "Nitesh"
    assert data["email"] == "nitesh@example.com"
    assert data["department"] == "Engineering"
    assert data["country"] == "US"
    assert data["id"].startswith("EMP-")
    assert "created_at" in data
    assert "updated_at" in data


def test_list_employees(client, admin_auth_headers):
    create_employee(
        client,
        admin_auth_headers,
        employee_number="EMP002",
        email="two@example.com",
        first_name="Ravi",
    )

    response = client.get(
        BASE_URL,
        headers=admin_auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    employee_numbers = {
        item["employee_number"] for item in data
    }

    assert "EMP002" in employee_numbers
    assert any(
        number.startswith("ADMIN-")
        for number in employee_numbers
    )

def test_get_employee_by_id(client, admin_auth_headers):
    created = create_employee(client, admin_auth_headers)
    employee_id = created.json()["id"]

    response = client.get(
        f"{BASE_URL}/{employee_id}",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee_id
    assert response.json()["email"] == "nitesh@example.com"


def test_get_employee_not_found(client, admin_auth_headers):
    response = client.get(
        f"{BASE_URL}/EMP-NOT-FOUND",
        headers=admin_auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found."


def test_update_employee(client, admin_auth_headers):
    created = create_employee(client, admin_auth_headers)
    assert created.status_code == 201

    employee_id = created.json()["id"]

    response = client.patch(
        f"{BASE_URL}/{employee_id}",
        json={
            "first_name": "Krishna",
            "department": "Product",
        },
        headers=admin_auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["first_name"] == "Krishna"
    assert data["department"] == "Product"
    assert data["employee_number"] == "EMP001"


def test_update_employee_not_found(client, admin_auth_headers):
    response = client.patch(
        f"{BASE_URL}/EMP-NOT-FOUND",
        json={"first_name": "Updated"},
        headers=admin_auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found."


def test_update_employee_with_empty_payload(
    client, admin_auth_headers
):
    created = create_employee(client, admin_auth_headers)
    assert created.status_code == 201

    employee_id = created.json()["id"]

    response = client.patch(
        f"{BASE_URL}/{employee_id}",
        json={},
        headers=admin_auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Provide at least one field to update."
    )


def test_reject_duplicate_employee_number(
    client, admin_auth_headers
):
    # Create the first employee.
    first = create_employee(
        client,
        admin_auth_headers,
    )

    assert first.status_code == 201

    # Attempt to create another employee with the same number.
    response = create_employee(
        client,
        admin_auth_headers,
        employee_number="EMP001",
        email="another@example.com",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Employee number already exists."
    )


def test_reject_duplicate_email(
    client, admin_auth_headers
):
    # Create the first employee.
    first = create_employee(
        client,
        admin_auth_headers,
    )

    assert first.status_code == 201

    # Attempt to create another employee with the same email.
    response = create_employee(
        client,
        admin_auth_headers,
        employee_number="EMP002",
        email="nitesh@example.com",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Email address already exists."
    )


def test_reject_duplicate_email_during_update(
    client, admin_auth_headers
):
    # Create the first employee.
    first = create_employee(
        client,
        admin_auth_headers,
        employee_number="EMP001",
        email="one@example.com",
    )

    assert first.status_code == 201

    # Create the second employee.
    second = create_employee(
        client,
        admin_auth_headers,
        employee_number="EMP002",
        email="two@example.com",
    )

    assert second.status_code == 201

    # Attempt to assign the first employee's email
    # to the second employee.
    response = client.patch(
        f"{BASE_URL}/{second.json()['id']}",
        json={"email": "one@example.com"},
        headers=admin_auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Email address already exists."
    )


def test_reject_invalid_employment_date_range(
    client, admin_auth_headers
):
    response = create_employee(
        client,
        admin_auth_headers,
        employment_start_date="2024-06-01",
        employment_end_date="2024-05-01",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Employment end date cannot be before the start date."
    )


def test_reject_invalid_date_range_during_update(
    client, admin_auth_headers
):
    # Create an employee with a valid employment start date.
    created = create_employee(
        client,
        admin_auth_headers,
        employment_start_date="2024-01-01",
    )

    assert created.status_code == 201
    employee_id = created.json()["id"]

    # Attempt to set an end date before the start date.
    response = client.patch(
        f"{BASE_URL}/{employee_id}",
        json={"employment_end_date": "2023-12-31"},
        headers=admin_auth_headers,
    )

    assert response.status_code == 422


def test_reject_invalid_manager(
    client, admin_auth_headers
):
    # Attempt to create an employee with a nonexistent manager.
    response = create_employee(
        client,
        admin_auth_headers,
        manager_id="EMP-MISSING-MANAGER",
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_reject_invalid_cost_center(
    client, admin_auth_headers
):
    # Attempt to create an employee with a nonexistent cost center.
    response = create_employee(
        client,
        admin_auth_headers,
        cost_center_id="CC-MISSING",
    )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_employee_cannot_be_own_manager(
    client, admin_auth_headers
):
    # Create an employee using ADMIN authentication.
    created = create_employee(
        client,
        admin_auth_headers,
    )

    assert created.status_code == 201
    employee_id = created.json()["id"]

    # Attempt to assign the employee as their own manager.
    response = client.patch(
        f"{BASE_URL}/{employee_id}",
        json={"manager_id": employee_id},
        headers=admin_auth_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "An employee cannot be their own manager."
    )


def test_filter_employees_by_department(
    client, admin_auth_headers
):
    # Create an Engineering employee.
    first = create_employee(
        client,
        admin_auth_headers,
        employee_number="EMP001",
        email="one@example.com",
        department="Engineering",
    )

    assert first.status_code == 201

    # Create a Finance employee.
    second = create_employee(
        client,
        admin_auth_headers,
        employee_number="EMP002",
        email="two@example.com",
        department="Finance",
    )

    assert second.status_code == 201

    # Request only Finance employees.
    response = client.get(
        BASE_URL,
        params={"department": "Finance"},
        headers=admin_auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["department"] == "Finance"
    assert data[0]["employee_number"] == "EMP002"


def test_filter_employees_by_country(
    client, admin_auth_headers
):
    # Create an employee in the United States.
    first = create_employee(
        client,
        admin_auth_headers,
        employee_number="EMP001",
        email="us@example.com",
        country="US",
    )

    assert first.status_code == 201

    # Create an employee in India.
    second = create_employee(
        client,
        admin_auth_headers,
        employee_number="EMP002",
        email="in@example.com",
        country="IN",
    )

    assert second.status_code == 201

    # Filter employees by country.
    response = client.get(
        BASE_URL,
        params={"country": "in"},
        headers=admin_auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    # Both the Indian employee and the ADMIN fixture
    # employee (country="IN") should be returned.
    assert len(data) == 2
    assert all(employee["country"] == "IN" for employee in data)
    assert second.json()["id"] in {
        employee["id"] for employee in data
    }


def test_paginate_employees(client, admin_auth_headers):
    # Create three employees using ADMIN authentication.
    created_ids = set()

    for number in range(1, 4):
        response = create_employee(
            client,
            admin_auth_headers,
            employee_number=f"EMP{number:03d}",
            email=f"employee{number}@example.com",
        )

        assert response.status_code == 201
        created_ids.add(response.json()["id"])

    # Request the second record with a page size of one.
    response = client.get(
        BASE_URL,
        params={"offset": 1, "limit": 1},
        headers=admin_auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    # The returned employee must be one of the records
    # available in the directory.
    assert "id" in data[0]


def test_reject_invalid_pagination_parameters(
    client, admin_auth_headers
):
    # Limit must be at least 1.
    response = client.get(
        BASE_URL,
        params={"limit": 0},
        headers=admin_auth_headers,
    )

    assert response.status_code == 422


def test_reject_missing_required_fields(
    client, admin_auth_headers
):
    # Prepare an employee payload.
    payload = employee_payload()

    # Remove a required field.
    del payload["first_name"]

    # Send the request with ADMIN authentication.
    response = client.post(
        BASE_URL,
        json=payload,
        headers=admin_auth_headers,
    )

    assert response.status_code == 422

def test_reject_invalid_country_length(client, admin_auth_headers):
    response = create_employee(
        client,
        admin_auth_headers,
        country="USA",
    )

    assert response.status_code == 422


def test_update_employee_cannot_set_required_field_to_null(client, admin_auth_headers):
    created = create_employee(client, admin_auth_headers)
    employee_id = created.json()["id"]

    response = client.patch(
        f"{BASE_URL}/{employee_id}",
        json={"first_name": None},
        headers=admin_auth_headers,
    )

    assert response.status_code == 422


def test_update_employee_end_date_to_null(client, admin_auth_headers):
    created = create_employee(
        client,
        admin_auth_headers,
        employment_end_date="2025-01-01",
    )
    employee_id = created.json()["id"]

    response = client.patch(
        f"{BASE_URL}/{employee_id}",
        json={"employment_end_date": None},
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["employment_end_date"] is None

def test_get_employee_without_jwt_returns_401(
    client, admin_auth_headers
):
    # Create an employee using ADMIN authentication.
    created = create_employee(client, admin_auth_headers)
    assert created.status_code == 201

    employee_id = created.json()["id"]

    # Attempt to access the profile without a JWT.
    response = client.get(
        f"{BASE_URL}/{employee_id}"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )

def test_employee_cannot_view_another_employee(
    client, admin_auth_headers, db_session
):
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    # Create two employees.
    first = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"first-{uuid4().hex[:8]}@example.com",
    )

    second = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"second-{uuid4().hex[:8]}@example.com",
    )

    assert first.status_code == 201
    assert second.status_code == 201

    first_employee_id = first.json()["id"]
    second_employee_id = second.json()["id"]

    # Create an EMPLOYEE user account for the first employee.
    user = UserAccount(
        id=uuid4().hex,
        employee_id=first_employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)

    # First employee attempts to view the second employee.
    response = client.get(
        f"{BASE_URL}/{second_employee_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

def test_employee_can_view_own_profile(
    client, admin_auth_headers, db_session
):
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    # Create an employee using ADMIN authentication.
    created = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"own-{uuid4().hex[:8]}@example.com",
    )

    assert created.status_code == 201
    employee_id = created.json()["id"]

    # Create a user account linked to this employee.
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

    # Employee requests their own profile.
    response = client.get(
        f"{BASE_URL}/{employee_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee_id
    assert response.json()["email"] == created.json()["email"]

def test_manager_can_view_direct_report(
    client, admin_auth_headers, db_session
):
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    # Create the manager's employee record.
    manager_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"MGR-{uuid4().hex[:8]}",
        email=f"manager-{uuid4().hex[:8]}@example.com",
    )

    assert manager_response.status_code == 201
    manager_id = manager_response.json()["id"]

    # Create an employee reporting directly to this manager.
    employee_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"report-{uuid4().hex[:8]}@example.com",
        manager_id=manager_id,
    )

    assert employee_response.status_code == 201
    employee_id = employee_response.json()["id"]

    # Create a MANAGER user account.
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

    # Manager requests their direct report's profile.
    response = client.get(
        f"{BASE_URL}/{employee_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee_id
    assert response.json()["manager_id"] == manager_id

def test_manager_cannot_view_unrelated_employee(
    client, admin_auth_headers, db_session
):
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    # Create the manager's employee record.
    manager_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"MGR-{uuid4().hex[:8]}",
        email=f"manager-{uuid4().hex[:8]}@example.com",
    )

    assert manager_response.status_code == 201
    manager_id = manager_response.json()["id"]

    # Create an employee who does NOT report to this manager.
    other_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"unrelated-{uuid4().hex[:8]}@example.com",
    )

    assert other_response.status_code == 201
    other_employee_id = other_response.json()["id"]

    # Confirm the employee is not a direct report.
    assert other_response.json()["manager_id"] != manager_id

    # Create a MANAGER user account.
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

    # Manager attempts to view an unrelated employee.
    response = client.get(
        f"{BASE_URL}/{other_employee_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

def test_hr_can_view_any_employee(
    client, admin_auth_headers, db_session
):
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    # Create an employee whose profile HR will access.
    employee_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"employee-{uuid4().hex[:8]}@example.com",
    )

    assert employee_response.status_code == 201
    employee_id = employee_response.json()["id"]

    # Create a separate employee to represent the HR user.
    hr_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"HR-{uuid4().hex[:8]}",
        email=f"hr-{uuid4().hex[:8]}@example.com",
        department="HR",
    )

    assert hr_response.status_code == 201
    hr_employee_id = hr_response.json()["id"]

    # Create an authenticated HR user account.
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

    # HR requests another employee's profile.
    response = client.get(
        f"{BASE_URL}/{employee_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee_id
    assert response.json()["email"] == employee_response.json()["email"]

def test_manager_can_view_own_profile(
    client, admin_auth_headers, db_session
):
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    # Create the manager's employee record.
    manager_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"MGR-{uuid4().hex[:8]}",
        email=f"manager-{uuid4().hex[:8]}@example.com",
    )

    assert manager_response.status_code == 201
    manager_id = manager_response.json()["id"]

    # Create a MANAGER user account.
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

    # Manager requests their own profile.
    response = client.get(
        f"{BASE_URL}/{manager_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == manager_id
    assert response.json()["email"] == manager_response.json()["email"]

def test_list_employees_without_jwt_returns_401(client):
    # Attempt to retrieve the employee directory without a JWT.
    response = client.get(BASE_URL)

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )

def test_employee_cannot_list_employees(
    client, admin_auth_headers, db_session
):
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    # Create an employee using ADMIN authentication.
    employee_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"employee-{uuid4().hex[:8]}@example.com",
    )

    assert employee_response.status_code == 201
    employee_id = employee_response.json()["id"]

    # Create an authenticated EMPLOYEE user.
    employee_user = UserAccount(
        id=uuid4().hex,
        employee_id=employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add(employee_user)
    db_session.commit()

    token = create_access_token(employee_user.id)

    # EMPLOYEE attempts to retrieve the employee directory.
    response = client.get(
        BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"

def test_manager_can_list_only_direct_reports(
    client, admin_auth_headers, db_session
):
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    # Create the manager.
    manager_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"MGR-{uuid4().hex[:8]}",
        email=f"manager-{uuid4().hex[:8]}@example.com",
    )

    assert manager_response.status_code == 201
    manager_id = manager_response.json()["id"]

    # Create two employees reporting to this manager.
    direct_report_ids = set()

    for _ in range(2):
        response = create_employee(
            client,
            admin_auth_headers,
            employee_number=f"EMP-{uuid4().hex[:8]}",
            email=f"report-{uuid4().hex[:8]}@example.com",
            manager_id=manager_id,
        )

        assert response.status_code == 201
        direct_report_ids.add(response.json()["id"])

    # Create an unrelated employee.
    unrelated_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"EMP-{uuid4().hex[:8]}",
        email=f"unrelated-{uuid4().hex[:8]}@example.com",
    )

    assert unrelated_response.status_code == 201
    unrelated_id = unrelated_response.json()["id"]

    # Create a MANAGER user account.
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

    # Manager requests the employee directory.
    response = client.get(
        BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    employees = response.json()
    returned_ids = {employee["id"] for employee in employees}

    # Only the two direct reports should be returned.
    assert len(employees) == 2
    assert returned_ids == direct_report_ids

    # Manager and unrelated employee must not appear.
    assert manager_id not in returned_ids
    assert unrelated_id not in returned_ids

def test_hr_can_list_all_employees(
    client, admin_auth_headers, db_session
):
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import UserAccount

    # Create two regular employees.
    expected_ids = set()

    for _ in range(2):
        response = create_employee(
            client,
            admin_auth_headers,
            employee_number=f"EMP-{uuid4().hex[:8]}",
            email=f"employee-{uuid4().hex[:8]}@example.com",
        )

        assert response.status_code == 201
        expected_ids.add(response.json()["id"])

    # Create the HR employee record.
    hr_response = create_employee(
        client,
        admin_auth_headers,
        employee_number=f"HR-{uuid4().hex[:8]}",
        email=f"hr-{uuid4().hex[:8]}@example.com",
        department="HR",
    )

    assert hr_response.status_code == 201
    hr_employee_id = hr_response.json()["id"]

    # Create an HR user account.
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

    # HR requests the complete employee directory.
    response = client.get(
        BASE_URL,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    employees = response.json()
    returned_ids = {employee["id"] for employee in employees}

    # HR can see all created employees.
    assert expected_ids.issubset(returned_ids)
    assert hr_employee_id in returned_ids

    # HR can also see the ADMIN fixture's employee.
    assert len(employees) == 4

def test_admin_can_list_all_employees(
    client, admin_auth_headers
):
    from uuid import uuid4

    # Create two employees using ADMIN authentication.
    expected_ids = set()

    for _ in range(2):
        response = create_employee(
            client,
            admin_auth_headers,
            employee_number=f"EMP-{uuid4().hex[:8]}",
            email=f"employee-{uuid4().hex[:8]}@example.com",
        )

        assert response.status_code == 201
        expected_ids.add(response.json()["id"])

    # ADMIN requests the complete employee directory.
    response = client.get(
        BASE_URL,
        headers=admin_auth_headers,
    )

    assert response.status_code == 200

    employees = response.json()
    returned_ids = {employee["id"] for employee in employees}

    # Both employees must be visible to ADMIN.
    assert expected_ids.issubset(returned_ids)

    # The ADMIN fixture creates one additional employee.
    assert len(employees) == 3