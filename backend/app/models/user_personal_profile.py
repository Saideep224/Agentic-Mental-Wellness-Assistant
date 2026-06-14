"""
UserPersonalProfile model – stores personal profile context for user personalization.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, SafeUUID


class UserPersonalProfile(Base):
    """UserPersonalProfile model mapping to the user_profile database table."""

    __tablename__ = "user_profile"

    id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    age: Mapped[str | None] = mapped_column(String(50), nullable=True)
    profession: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_of_work: Mapped[str | None] = mapped_column(String(255), nullable=True)
    university: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_challenge: Mapped[str | None] = mapped_column(String(255), nullable=True)
    advice_preference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_support_need: Mapped[str | None] = mapped_column(String(255), nullable=True)
    student_year: Mapped[str | None] = mapped_column(String(100), nullable=True)
    communication_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    interests: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    hobbies: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    goals: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    stress_triggers: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    coping_mechanisms: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    support_system: Mapped[str | None] = mapped_column(Text, nullable=True)
    sleep_habits: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="personal_profile")  # noqa: F821

    def __repr__(self) -> str:
        return f"<UserPersonalProfile user_id={self.user_id}>"
