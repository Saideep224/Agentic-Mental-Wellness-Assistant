"""
User model.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Registered user account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="credentials", nullable=False)
    github_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────
    conversations: Mapped[list["Conversation"]] = relationship(  # noqa: F821
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    user_profile: Mapped["UserProfile | None"] = relationship(  # noqa: F821
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    onboarding_responses: Mapped[list["OnboardingResponse"]] = relationship(  # noqa: F821
        "OnboardingResponse", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def emotional_profile(self):
        """Backward compatibility for existing routes/services referencing emotional_profile."""
        return self.user_profile

    def __repr__(self) -> str:
        return f"<User {self.email}>"
