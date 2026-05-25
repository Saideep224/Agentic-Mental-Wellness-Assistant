"""
User model – representing the 'profiles' table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, UUID, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """User profile record mapped to the profiles table."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="credentials", nullable=False)
    github_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    
    # New profile fields stored directly on the profiles table
    personality_profile: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    interests: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    communication_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ────────────────────────────────────────
    conversations: Mapped[list["Conversation"]] = relationship(  # noqa: F821
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    user_profile: Mapped["UserProfile | None"] = relationship(  # noqa: F821
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    onboarding_answers: Mapped[list["UserAnswer"]] = relationship(  # noqa: F821
        "UserAnswer", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
