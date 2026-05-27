"""
UserProfile model – storing personality metrics and maps to the 'user_personality' table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, SafeUUID


class UserProfile(Base):
    """UserProfile model mapping to the user_personality database table."""

    __tablename__ = "user_personality"

    user_id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    # ── Required profiles sections ────────────────────────────
    personality_profile: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    personality_type: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    communication_style: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    interests: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    stress_indicators: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # ── Backward compatibility columns ──────────────────────────
    personality_type_dict: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    emotional_style: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    stress_triggers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    strengths: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    weaknesses: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    onboarding_answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    emotional_baseline: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    comfort_preferences: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    emotional_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    stress_patterns: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    emotional_triggers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    preferred_response_style: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
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

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="user_profile")  # noqa: F821

    def __repr__(self) -> str:
        return f"<UserProfile user={self.user_id}>"
