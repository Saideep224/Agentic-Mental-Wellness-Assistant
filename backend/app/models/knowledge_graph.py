"""Knowledge graph relation model.

Python uses subject/predicate/object while the production table's original physical
columns are source/relation/target. Explicit column mapping prevents schema drift.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, SafeUUID


class KnowledgeGraphRelation(Base):
    __tablename__ = "knowledge_graph"
    id: Mapped[uuid.UUID] = mapped_column(SafeUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(SafeUUID, ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column("source", String(255), default="User", nullable=False)
    predicate: Mapped[str] = mapped_column("relation", String(255), nullable=False)
    object: Mapped[str] = mapped_column("target", String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="knowledge_graph")  # noqa: F821

    def __repr__(self) -> str:
        return f"<KnowledgeGraphRelation user={self.user_id} triple=({self.subject}, {self.predicate}, {self.object})>"
