
"""Shared FastAPI authentication and database dependencies."""

from typing import Annotated

from app.core.security import verify_access_token
from app.db.models import Employee, UserAccount
from app.db.session import get_db
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

bearer_scheme = HTTPBearer(auto_error=False)

DBSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DBSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> UserAccount:
    """Return the authenticated, active user account."""

    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise auth_error

    user_id = verify_access_token(credentials.credentials)

    if user_id is None:
        raise auth_error

    user = db.get(UserAccount, user_id)

    if user is None or not user.is_active:
        raise auth_error

    employee = db.get(Employee, user.employee_id)

    if employee is None or employee.employment_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employee account is not active",
        )

    return user


CurrentUser = Annotated[UserAccount, Depends(get_current_user)]


def require_roles(*allowed_roles: str):
    """Require an authenticated user with an allowed role."""

    def check_role(current_user: CurrentUser) -> UserAccount:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return check_role
