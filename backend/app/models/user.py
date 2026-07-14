"""
User model – representing the 'profiles' table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, JSON, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, SafeUUID


class User(Base):
    """User profile record mapped to the profiles table."""

    __tablename__ = "profiles"

    # Map Python `id` to database column `user_id` (primary key)
    id: Mapped[uuid.UUID] = mapped_column(
        "user_id", SafeUUID, primary_key=True, index=True, nullable=False
    )
    
    # Map Python `profile_id` to database column `id`
    profile_id: Mapped[uuid.UUID] = mapped_column(
        "id", SafeUUID, unique=True, default=uuid.uuid4
    )

    @property
    def user_id(self) -> uuid.UUID:
        return self.id

    @user_id.setter
    def user_id(self, value: uuid.UUID) -> None:
        self.id = value

    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column("full_name", String(255), default="", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="credentials", nullable=False)
    github_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    onboarding_step: Mapped[int | None] = mapped_column(
        Integer, default=1, nullable=True
    )
    
    # New profile fields stored directly on the profiles table
    personality_profile: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    interests: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)
    communication_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    
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
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ────────────────────────────────────────
    conversations: Mapped[list["Conversation"]] = relationship(  # noqa: F821
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # noqa: F821
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )
    user_profile: Mapped["UserProfile | None"] = relationship(  # noqa: F821
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    personal_profile: Mapped["UserPersonalProfile | None"] = relationship(  # noqa: F821
        "UserPersonalProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    knowledge_graph: Mapped[list["KnowledgeGraphRelation"]] = relationship(  # noqa: F821
        "KnowledgeGraphRelation", back_populates="user", cascade="all, delete-orphan"
    )
    user_entities: Mapped[list["UserEntity"]] = relationship(  # noqa: F821
        "UserEntity", back_populates="user", cascade="all, delete-orphan"
    )
    user_relationships: Mapped[list["UserRelationship"]] = relationship(  # noqa: F821
        "UserRelationship", back_populates="user", cascade="all, delete-orphan"
    )
    onboarding_answers: Mapped[list["UserAnswer"]] = relationship(  # noqa: F821
        "UserAnswer", back_populates="user", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        # Automatically default profile_id (column 'id') to user_id (column 'user_id')
        if "profile_id" not in kwargs:
            val = kwargs.get("id") or kwargs.get("user_id")
            if val:
                kwargs["profile_id"] = val
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<User {self.email}>"
