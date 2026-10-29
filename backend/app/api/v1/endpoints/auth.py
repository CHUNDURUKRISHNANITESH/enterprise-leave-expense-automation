
"""Authentication API endpoints."""

from datetime import UTC, datetime

from app.api.deps import CurrentUser, DBSession
from app.core.config import settings
from app.core.security import (
    create_access_token,
    verify_password,
)
from app.db.models import Employee, UserAccount
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DBSession):
    """Authenticate an employee and issue a JWT access token."""

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    employee = db.scalar(
        select(Employee).where(
            Employee.email == str(payload.email)
        )
    )

    if employee is None:
        raise invalid_credentials

    user = db.scalar(
        select(UserAccount).where(
            UserAccount.employee_id == employee.id
        )
    )

    if user is None:
        raise invalid_credentials

    if not verify_password(
        payload.password,
        user.password_hash,
    ):
        raise invalid_credentials

    if not user.is_active or employee.employment_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    user.last_login_at = datetime.now(UTC)
    db.commit()

    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )

@router.get("/me", response_model=CurrentUserResponse)
def get_authenticated_user(
    current_user: CurrentUser,
) -> CurrentUserResponse:
    """Return the authenticated user's account ID, employee ID and role."""

    return CurrentUserResponse(
        user_id=current_user.id,
        employee_id=current_user.employee_id,
        role=current_user.role,
    )
