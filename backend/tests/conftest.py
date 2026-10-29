from datetime import date
from uuid import uuid4

from app.core.security import create_access_token, hash_password
from app.db.models import Employee, UserAccount
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
import app.db.models  # Ensure every model is registered with Base.metadata


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def admin_auth_headers(db_session):
    """Create an active ADMIN account for authenticated API tests."""

    employee = Employee(
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

    db_session.add(employee)
    db_session.flush()

    user = UserAccount(
        id=uuid4().hex,
        employee_id=employee.id,
        password_hash=hash_password("TestPassword123!"),
        role="ADMIN",
        is_active=True,
    )

    db_session.add(user)
    db_session.commit()

    token = create_access_token(user.id)

    return {"Authorization": f"Bearer {token}"}

