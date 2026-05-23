"""
Emotional profile model – built from onboarding and refined over time.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmotionalProfile(Base):
    """Stores the comprehensive emotional/personality profile of a user."""

    __tablename__ = "emotional_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Profile sections (all JSON blobs) ─────────────────────
    personality_type: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    emotional_baseline: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    comfort_preferences: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    communication_style: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Extra personalization details
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
    user: Mapped["User"] = relationship("User", back_populates="emotional_profile")  # noqa: F821

    def __repr__(self) -> str:
        return f"<EmotionalProfile user={self.user_id}>"
