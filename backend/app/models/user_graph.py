"""
UserEntity and UserRelationship models – representing user specific entities and their relationships.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, SafeUUID


class UserEntity(Base):
    """Stores entities associated with a user (e.g. girlfriend, exams)."""

    __tablename__ = "user_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    entity: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="user_entities")  # noqa: F821

    def __repr__(self) -> str:
        return f"<UserEntity user={self.user_id} entity={self.entity} type={self.type}>"


class UserRelationship(Base):
    """Stores semantic relationships between entities (e.g. user -> has_relationship -> girlfriend)."""

    __tablename__ = "user_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SafeUUID,
        ForeignKey("profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_name: Mapped[str] = mapped_column("relationship", String(255), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="user_relationships")  # noqa: F821

    @property
    def relationship(self) -> str:
        return self.relationship_name

    @relationship.setter
    def relationship(self, value: str) -> None:
        self.relationship_name = value

    def __repr__(self) -> str:
        return f"<UserRelationship user={self.user_id} triple=({self.source}, {self.relationship_name}, {self.target})>"
