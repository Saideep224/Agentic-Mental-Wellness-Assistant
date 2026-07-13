"""Conversation and Message models."""
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, SafeUUID


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = mapped_column(SafeUUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(SafeUUID, ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="New Conversation", nullable=False)
    emotional_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_id: Mapped[str] = mapped_column(String(50), default="buddy", nullable=False)
    active_specialists: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="conversations")  # noqa: F821
    messages: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[uuid.UUID] = mapped_column(SafeUUID, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(SafeUUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(SafeUUID, ForeignKey("profiles.user_id", ondelete="CASCADE"), nullable=False, index=True)
    # native_enum=False is intentional: production has a TEXT column. This preserves
    # MessageRole objects in Python without PostgreSQL text=enum operator failures.
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, native_enum=False, values_callable=lambda e: [x.value for x in e]), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mood_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    agent_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    emotional_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")
    user: Mapped["User"] = relationship("User", back_populates="chat_messages")  # noqa: F821
