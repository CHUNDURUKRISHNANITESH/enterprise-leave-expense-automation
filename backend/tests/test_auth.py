
"""Tests for JWT authentication and authorization."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user


def test_missing_token_returns_401(client):
    """Protected endpoints must reject missing JWT tokens."""

    app = FastAPI()

    @app.get("/protected")
    def protected_route(user=Depends(get_current_user)):
        return {"authenticated": True}

    # Reuse the database override from the existing test client.
    app.dependency_overrides.update(
        client.app.dependency_overrides
    )

    with TestClient(app) as test_client:
        response = test_client.get("/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_token_returns_401(client):
    """Protected endpoints must reject invalid JWT tokens."""

    app = FastAPI()

    @app.get("/protected")
    def protected_route(user=Depends(get_current_user)):
        return {"authenticated": True}

    app.dependency_overrides.update(
        client.app.dependency_overrides
    )

    with TestClient(app) as test_client:
        response = test_client.get(
            "/protected",
            headers={
                "Authorization": "Bearer invalid.jwt.token"
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )
    assert response.headers["www-authenticate"] == "Bearer"



def test_valid_token_nonexistent_user_returns_401(client):
    """A valid JWT must not authenticate a nonexistent user."""

    from app.core.security import create_access_token

    app = FastAPI()

    @app.get("/protected")
    def protected_route(user=Depends(get_current_user)):
        return {"authenticated": True}

    app.dependency_overrides.update(
        client.app.dependency_overrides
    )

    token = create_access_token("nonexistent-user-123")

    with TestClient(app) as test_client:
        response = test_client.get(
            "/protected",
            headers={
                "Authorization": f"Bearer {token}"
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )



def test_inactive_user_account_returns_401(client, db_session):
    """A valid JWT must not authenticate an inactive account."""

    from datetime import date
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import Employee, UserAccount

    employee_id = uuid4().hex
    user_id = uuid4().hex

    employee = Employee(
        id=employee_id,
        employee_number="AUTH001",
        first_name="Test",
        last_name="Employee",
        email="auth001@example.com",
        department="Engineering",
        country="US",
        currency="USD",
        employment_start_date=date(2024, 1, 1),
        employment_status="ACTIVE",
        is_approver=False,
    )

    user = UserAccount(
        id=user_id,
        employee_id=employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=False,
    )

    db_session.add_all([employee, user])
    db_session.commit()

    app = FastAPI()

    @app.get("/protected")
    def protected_route(user=Depends(get_current_user)):
        return {"authenticated": True}

    app.dependency_overrides.update(
        client.app.dependency_overrides
    )

    token = create_access_token(user_id)

    with TestClient(app) as test_client:
        response = test_client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )



def test_active_user_with_valid_token_returns_200(client, db_session):
    """An active account with a valid JWT can access protected APIs."""

    from datetime import date
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import Employee, UserAccount

    employee_id = uuid4().hex
    user_id = uuid4().hex

    employee = Employee(
        id=employee_id,
        employee_number="AUTH002",
        first_name="Active",
        last_name="Employee",
        email="auth002@example.com",
        department="Engineering",
        country="US",
        currency="USD",
        employment_start_date=date(2024, 1, 1),
        employment_status="ACTIVE",
        is_approver=False,
    )

    user = UserAccount(
        id=user_id,
        employee_id=employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add_all([employee, user])
    db_session.commit()

    app = FastAPI()

    @app.get("/protected")
    def protected_route(
        current_user=Depends(get_current_user),
    ):
        return {
            "authenticated": True,
            "user_id": current_user.id,
            "employee_id": current_user.employee_id,
        }

    app.dependency_overrides.update(
        client.app.dependency_overrides
    )

    token = create_access_token(user_id)

    with TestClient(app) as test_client:
        response = test_client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "authenticated": True,
        "user_id": user_id,
        "employee_id": employee_id,
    }


def test_inactive_employee_returns_403(client, db_session):
    """An inactive employee must not access protected APIs."""

    from datetime import date
    from uuid import uuid4

    from app.core.security import create_access_token, hash_password
    from app.db.models import Employee, UserAccount

    employee_id = uuid4().hex
    user_id = uuid4().hex

    employee = Employee(
        id=employee_id,
        employee_number="AUTH003",
        first_name="Inactive",
        last_name="Employee",
        email="auth003@example.com",
        department="Engineering",
        country="US",
        currency="USD",
        employment_start_date=date(2024, 1, 1),
        employment_status="INACTIVE",
        is_approver=False,
    )

    user = UserAccount(
        id=user_id,
        employee_id=employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add_all([employee, user])
    db_session.commit()

    app = FastAPI()

    @app.get("/protected")
    def protected_route(
        current_user=Depends(get_current_user),
    ):
        return {"authenticated": True}

    app.dependency_overrides.update(
        client.app.dependency_overrides
    )

    token = create_access_token(user_id)

    with TestClient(app) as test_client:
        response = test_client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Employee account is not active"
    )



def test_employee_cannot_access_admin_route(client, db_session):
    """An EMPLOYEE must not access an ADMIN-only endpoint."""

    from datetime import date
    from uuid import uuid4

    from app.api.deps import require_roles
    from app.core.security import create_access_token
    from app.db.models import Employee, UserAccount

    employee_id = uuid4().hex
    user_id = uuid4().hex

    employee = Employee(
        id=employee_id,
        employee_number="AUTH004",
        first_name="Regular",
        last_name="Employee",
        email="auth004@example.com",
        department="Engineering",
        country="US",
        currency="USD",
        employment_start_date=date(2024, 1, 1),
        employment_status="ACTIVE",
        is_approver=False,
    )

    user = UserAccount(
        id=user_id,
        employee_id=employee_id,
        password_hash="test-hash-not-used-for-jwt-auth",
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add_all([employee, user])
    db_session.commit()

    app = FastAPI()

    @app.get("/admin-only")
    def admin_route(
        current_user=Depends(require_roles("ADMIN")),
    ):
        return {"message": "Admin access granted"}

    app.dependency_overrides.update(
        client.app.dependency_overrides
    )

    token = create_access_token(user_id)

    with TestClient(app) as test_client:
        response = test_client.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Insufficient permissions"
    )



def test_admin_can_access_admin_route(client, db_session):
    """An active ADMIN can access an ADMIN-only endpoint."""

    from datetime import date
    from uuid import uuid4

    from app.api.deps import require_roles
    from app.core.security import create_access_token
    from app.db.models import Employee, UserAccount

    employee_id = uuid4().hex
    user_id = uuid4().hex

    employee = Employee(
        id=employee_id,
        employee_number="AUTH005",
        first_name="System",
        last_name="Administrator",
        email="auth005@example.com",
        department="IT",
        country="US",
        currency="USD",
        employment_start_date=date(2024, 1, 1),
        employment_status="ACTIVE",
        is_approver=False,
    )

    user = UserAccount(
        id=user_id,
        employee_id=employee_id,
        password_hash="test-hash-not-used-for-jwt-auth",
        role="ADMIN",
        is_active=True,
    )

    db_session.add_all([employee, user])
    db_session.commit()

    app = FastAPI()

    @app.get("/admin-only")
    def admin_route(
        current_user=Depends(require_roles("ADMIN")),
    ):
        return {
            "message": "Admin access granted",
            "user_id": current_user.id,
        }

    app.dependency_overrides.update(
        client.app.dependency_overrides
    )

    token = create_access_token(user_id)

    with TestClient(app) as test_client:
        response = test_client.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Admin access granted",
        "user_id": user_id,
    }



def test_login_success_returns_jwt(client, db_session):
    """Valid employee credentials should return a JWT."""

    from datetime import date
    from uuid import uuid4

    from app.core.security import hash_password, verify_access_token
    from app.db.models import Employee, UserAccount

    employee_id = uuid4().hex
    user_id = uuid4().hex

    employee = Employee(
        id=employee_id,
        employee_number="AUTH006",
        first_name="Login",
        last_name="Tester",
        email="auth006@example.com",
        department="Engineering",
        country="US",
        currency="USD",
        employment_start_date=date(2024, 1, 1),
        employment_status="ACTIVE",
        is_approver=False,
    )

    user = UserAccount(
        id=user_id,
        employee_id=employee_id,
        password_hash=hash_password("TestPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add_all([employee, user])
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "auth006@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800
    assert isinstance(data["access_token"], str)

    assert verify_access_token(data["access_token"]) == user_id

    db_session.refresh(user)
    assert user.last_login_at is not None


def test_login_wrong_password_returns_401(client, db_session):
    """Login must reject an incorrect password."""

    from datetime import date
    from uuid import uuid4

    from app.core.security import hash_password
    from app.db.models import Employee, UserAccount

    employee_id = uuid4().hex
    user_id = uuid4().hex

    employee = Employee(
        id=employee_id,
        employee_number="AUTH007",
        first_name="Password",
        last_name="Tester",
        email="auth007@example.com",
        department="Engineering",
        country="US",
        currency="USD",
        employment_start_date=date(2024, 1, 1),
        employment_status="ACTIVE",
        is_approver=False,
    )

    user = UserAccount(
        id=user_id,
        employee_id=employee_id,
        password_hash=hash_password("CorrectPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add_all([employee, user])
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "auth007@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password"
    }

    db_session.refresh(user)
    assert user.last_login_at is None


def test_login_inactive_account_returns_403(client, db_session):
    """Inactive accounts must not be allowed to log in."""

    from datetime import date
    from uuid import uuid4

    from app.core.security import hash_password
    from app.db.models import Employee, UserAccount

    employee_id = uuid4().hex
    user_id = uuid4().hex

    employee = Employee(
        id=employee_id,
        employee_number="AUTH008",
        first_name="Inactive",
        last_name="Login",
        email="auth008@example.com",
        department="Engineering",
        country="US",
        currency="USD",
        employment_start_date=date(2024, 1, 1),
        employment_status="ACTIVE",
        is_approver=False,
    )

    user = UserAccount(
        id=user_id,
        employee_id=employee_id,
        password_hash=hash_password("CorrectPassword123!"),
        role="EMPLOYEE",
        is_active=False,
    )

    db_session.add_all([employee, user])
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "auth008@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Account is inactive"
    }

    db_session.refresh(user)
    assert user.last_login_at is None


def test_login_inactive_employee_returns_403(client, db_session):
    """Inactive employees must not receive JWT access tokens."""

    from datetime import date
    from uuid import uuid4

    from app.core.security import hash_password
    from app.db.models import Employee, UserAccount

    employee_id = uuid4().hex
    user_id = uuid4().hex

    employee = Employee(
        id=employee_id,
        employee_number="AUTH009",
        first_name="Inactive",
        last_name="Employee",
        email="auth009@example.com",
        department="Engineering",
        country="US",
        currency="USD",
        employment_start_date=date(2024, 1, 1),
        employment_status="INACTIVE",
        is_approver=False,
    )

    user = UserAccount(
        id=user_id,
        employee_id=employee_id,
        password_hash=hash_password("CorrectPassword123!"),
        role="EMPLOYEE",
        is_active=True,
    )

    db_session.add_all([employee, user])
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "auth009@example.com",
            "password": "CorrectPassword123!",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Account is inactive"
    }

    db_session.refresh(user)
    assert user.last_login_at is None



def test_leave_approval_without_token_returns_401(client):
    """An unauthenticated user cannot approve a leave request."""

    response = client.post(
        "/api/v1/leaves/nonexistent-leave-id/approve"
    )

    assert response.status_code == 401

    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )

    assert response.headers["www-authenticate"] == "Bearer"

def test_leave_approval_with_invalid_token_returns_401(client):
    """A request with an invalid JWT cannot approve leave."""

    response = client.post(
        "/api/v1/leaves/nonexistent-leave-id/approve",
        headers={
            "Authorization": "Bearer invalid.jwt.token"
        },
    )

    assert response.status_code == 401

    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )

    assert response.headers["www-authenticate"] == "Bearer"

def test_leave_rejection_without_token_returns_401(client):
    """Unauthenticated users cannot reject leave requests."""

    response = client.post(
        "/api/v1/leaves/nonexistent-leave-id/reject",
        json={"reason": "Insufficient staffing."},
    )

    assert response.status_code == 401

    assert response.json()["detail"] == (
        "Invalid or missing authentication credentials"
    )

    assert response.headers["www-authenticate"] == "Bearer"


