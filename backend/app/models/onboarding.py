"""
Onboarding response model – stores answers to the onboarding questionnaire inside 'user_answers' table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, SafeUUID


class UserAnswer(Base):
    """One answer from the onboarding questionnaire stored in user_question_answers table."""

    __tablename__ = "user_question_answers"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question_answers_user_question"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    selected_answers: Mapped[list[str]] = mapped_column("selected_answer", JSON, default=list, nullable=False)
    custom_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    user: Mapped["User"] = relationship("User", back_populates="onboarding_answers")  # noqa: F821

    def __repr__(self) -> str:
        return f"<UserAnswer q={self.question_id} user={self.user_id}>"
