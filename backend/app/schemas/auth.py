
"""Pydantic schemas for authentication APIs."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class CurrentUserResponse(BaseModel):
    user_id: str
    employee_id: str
    role: str