"""
Memory model – stores user emotional memories with optional vector embeddings.
Replaces the old raw-SQLite memories.db approach with a proper SQLAlchemy model
that works with both SQLite (local) and PostgreSQL (Supabase production).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, SafeUUID


class Memory(Base):
    """A single emotional memory entry for semantic recall."""

    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    memory_summary: Mapped[str] = mapped_column(Text, nullable=False)
    behavior_patterns: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def content(self) -> str:
        return self.memory_summary

    @content.setter
    def content(self, value: str) -> None:
        self.memory_summary = value

    @property
    def metadata_json(self) -> dict:
        # Return behavior_patterns without the "embedding" key
        if isinstance(self.behavior_patterns, dict):
            return {k: v for k, v in self.behavior_patterns.items() if k != "embedding"}
        return {}

    @metadata_json.setter
    def metadata_json(self, value: dict) -> None:
        if not isinstance(self.behavior_patterns, dict):
            self.behavior_patterns = {}
        # Ensure we do a shallow copy to trigger SQLAlchemy change tracking
        new_patterns = dict(self.behavior_patterns)
        for k, v in value.items():
            if k != "embedding":
                new_patterns[k] = v
        self.behavior_patterns = new_patterns

    @property
    def embedding_json(self) -> list[float] | None:
        if isinstance(self.behavior_patterns, dict):
            return self.behavior_patterns.get("embedding")
        return None

    @embedding_json.setter
    def embedding_json(self, value: list[float] | None) -> None:
        if not isinstance(self.behavior_patterns, dict):
            self.behavior_patterns = {}
        # Ensure we do a shallow copy to trigger SQLAlchemy change tracking
        new_patterns = dict(self.behavior_patterns)
        if value is None:
            new_patterns.pop("embedding", None)
        else:
            new_patterns["embedding"] = value
        self.behavior_patterns = new_patterns

    def __repr__(self) -> str:
        return f"<Memory {self.id} user={self.user_id}>"
