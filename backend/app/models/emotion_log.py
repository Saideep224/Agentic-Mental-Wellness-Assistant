"""
EmotionLog model – stores classification results of user messages.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, SafeUUID


class EmotionLog(Base):
    """Logs the results of emotion classification for each user message."""

    __tablename__ = "emotion_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detected_emotion: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<EmotionLog user={self.user_id} emotion={self.detected_emotion} confidence={self.confidence_score}>"
