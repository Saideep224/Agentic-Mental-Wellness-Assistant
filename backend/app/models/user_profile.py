"""User personality profile mapped to the production user_personality table."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, SafeUUID


class UserProfile(Base):
    __tablename__ = "user_personality"
    id: Mapped[uuid.UUID] = mapped_column(SafeUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(SafeUUID, ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality_profile: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    personality_type: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    communication_style: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    interests: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    stress_indicators: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="user_profile")  # noqa: F821

    def __repr__(self) -> str:
        return f"<UserProfile user={self.user_id}>"
