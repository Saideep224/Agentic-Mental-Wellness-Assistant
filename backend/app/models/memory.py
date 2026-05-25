"""
Memory model – stores user emotional memories with optional vector embeddings.
Replaces the old raw-SQLite memories.db approach with a proper SQLAlchemy model
that works with both SQLite (local) and PostgreSQL (Supabase production).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, UUID, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Memory(Base):
    """A single emotional memory entry for semantic recall."""

    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    embedding_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Memory {self.id} user={self.user_id}>"
