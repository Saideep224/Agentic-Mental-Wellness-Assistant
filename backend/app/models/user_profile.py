"""User personality profile mapped to the production user_personality table."""
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, SafeUUID


class FlexibleJSONText(TypeDecorator):
    """Expose a legacy TEXT column as dict/list without assuming old rows are valid JSON."""
    impl = Text
    cache_ok = True
    def process_bind_param(self, value, dialect):
        if value is None: return None
        return json.dumps(value) if not isinstance(value, str) else value
    def process_result_value(self, value, dialect):
        if value is None: return {}
        if not isinstance(value, str): return value
        try: return json.loads(value)
        except Exception: return {"legacy_value": value}


class UserProfile(Base):
    __tablename__ = "user_personality"
    user_id: Mapped[uuid.UUID] = mapped_column(SafeUUID, ForeignKey("profiles.user_id", ondelete="CASCADE"), primary_key=True, nullable=False, index=True)
    personality_profile: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    personality_type: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    communication_style: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    interests: Mapped[dict] = mapped_column(FlexibleJSONText(), default=dict, nullable=True)
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
