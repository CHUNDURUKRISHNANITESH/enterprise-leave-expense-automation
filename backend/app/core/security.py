
"""Authentication and password security utilities."""

from datetime import UTC, datetime, timedelta

import jwt
from app.core.config import settings
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Generate a secure Argon2 password hash."""
    if not password:
        raise ValueError("Password cannot be empty")

    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a password against its stored hash."""
    return password_hasher.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(user_id: str) -> str:
    """Create a signed JWT access token."""

    if not user_id:
        raise ValueError("User ID cannot be empty")

    now = datetime.now(UTC)

    expires_at = now + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    payload = {
        "sub": user_id,
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_access_token(token: str) -> str | None:
    """Validate an access token and return its user ID."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={
                "require": ["sub", "iat", "exp", "type"],
            },
        )

        if payload.get("type") != "access":
            return None

        user_id = payload.get("sub")

        if not isinstance(user_id, str) or not user_id:
            return None

        return user_id

    except InvalidTokenError:
        return None
