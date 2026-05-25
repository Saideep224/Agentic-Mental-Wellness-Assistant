"""
MoodLog model – stores emotional metrics for real-time dashboard analytics.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, UUID, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MoodLog(Base):
    """Stores real emotion analysis logs for user metrics."""

    __tablename__ = "mood_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mood_score: Mapped[float] = mapped_column(Float, nullable=False)
    mood_label: Mapped[str] = mapped_column(String(100), nullable=False)
    detected_emotion: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Emotional analysis dimensions (scores between 0.0 and 1.0)
    stress: Mapped[float | None] = mapped_column(Float, nullable=True)
    happiness: Mapped[float | None] = mapped_column(Float, nullable=True)
    sadness: Mapped[float | None] = mapped_column(Float, nullable=True)
    anxiety: Mapped[float | None] = mapped_column(Float, nullable=True)
    motivation: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MoodLog {self.detected_emotion} score={self.mood_score}>"
