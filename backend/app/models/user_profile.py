"""
UserProfile model – stores personality details, styles, answers, triggers, and compatibility fields.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserProfile(Base):
    """UserProfile model mapping to the user_profiles database table."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )

    # ── Required profiles sections ────────────────────────────
    personality_type: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    emotional_style: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    interests: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    communication_style: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    stress_triggers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    strengths: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    weaknesses: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    onboarding_answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # ── Onboarding Additions ──────────────────────────────────
    onboarding_completed: Mapped[bool] = mapped_column(Boolean := __import__('sqlalchemy').Boolean, default=False, nullable=False)
    personality_profile: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    personality_type_text: Mapped[str | None] = mapped_column(Text := __import__('sqlalchemy').Text, nullable=True)
    communication_style_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Backward compatibility columns ──────────────────────────
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
