"""
Onboarding response model – stores answers to the 20-question onboarding quiz.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserOnboardingAnswer(Base):
    """One answer from the onboarding questionnaire."""

    __tablename__ = "user_onboarding_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    selected_answers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    custom_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="onboarding_answers")  # noqa: F821

    def __repr__(self) -> str:
        return f"<UserOnboardingAnswer q={self.question_id} user={self.user_id}>"
