"""
User-related request/response schemas.
"""

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, Field, field_serializer


class UserCreate(BaseModel):
    """Body for POST /api/auth/register."""
    name: str = Field(..., min_length=1, max_length=255, examples=["Alice"])
    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["securePass123"])


class UserLogin(BaseModel):
    """Body for POST /api/auth/login."""
    email: EmailStr = Field(..., examples=["alice@example.com"])
    password: str = Field(..., examples=["securePass123"])


class UserResponse(BaseModel):
    """Public user representation returned from the API."""
    id: uuid.UUID
    email: str
    name: str
    onboarding_completed: bool
    avatar_url: str | None = None
    provider: str = "credentials"
    github_username: str | None = None
    created_at: datetime
    last_login: datetime | None = None

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    @field_serializer("last_login")
    def serialize_last_login(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class TokenResponse(BaseModel):
    """JWT token response after login/register."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
