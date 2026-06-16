"""
Chat-related request/response schemas.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class ChatMessageRequest(BaseModel):
    """Body for POST /api/chat/message."""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: uuid.UUID | None = Field(
        default=None,
        description="Optional conversation to append to. A new one is created if omitted.",
    )


class MessageResponse(BaseModel):
    """A single message returned from the API."""
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    sender_type: str | None = "user"
    emotion_detected: str | None = None
    mood_score: float | None = None
    emotion_score: float | None = None
    stress_score: float | None = None
    anxiety_score: float | None = None
    agent_analysis: dict[str, Any] | None = None
    emotional_context: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class ConversationResponse(BaseModel):
    """Conversation header (without full messages)."""
    id: uuid.UUID
    title: str
    created_at: datetime
    message_count: int = 0
    agent_id: str = "buddy"
    active_specialists: list[str] | None = []
    last_message: str | None = None
    last_message_timestamp: str | None = None

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class ConversationCreateRequest(BaseModel):
    """Body for POST /api/chat/conversations."""
    title: str = Field(default="New Conversation", max_length=512)


class ConversationUpdateRequest(BaseModel):
    """Body for PATCH /api/chat/conversations/{conversation_id}."""
    title: str = Field(..., min_length=1, max_length=512)
