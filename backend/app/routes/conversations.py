"""
Conversations route — CRUD operations for chat conversations.

Extracted from the monolithic chat.py for better separation of concerns.
"""

import uuid
import logging
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.routes.auth import get_current_user
from app.schemas.chat import (
    ConversationResponse,
    ConversationCreateRequest,
    ConversationUpdateRequest,
    MessageResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Conversations"])




@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the authenticated user, newest first (Buddy first)."""
    # 1. Ensure the Buddy conversation exists
    buddy_info = ("buddy", "💙 Buddy", "Hi! I'm Buddy, your personal companion. I'm here to listen, support, and help you navigate whatever is on your mind. How are you feeling today?")
    
    existing_result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == current_user.id,
            Conversation.agent_id == "buddy"
        )
    )
    existing_convs = existing_result.scalars().all()
    existing_agent_ids = {c.agent_id for c in existing_convs}

    if "buddy" not in existing_agent_ids:
        # Create the Buddy conversation
        conv = Conversation(
            user_id=current_user.id,
            agent_id="buddy",
            title=buddy_info[1],
            active_specialists=[]
        )
        db.add(conv)
        await db.flush()
        await db.commit()

    # 2. Fetch only Buddy conversations for the user
    conv_query = await db.execute(
        select(Conversation).where(
            Conversation.user_id == current_user.id,
            Conversation.agent_id == "buddy"
        )
    )
    all_convs = conv_query.scalars().all()

    response_list = []
    for conv in all_convs:
        # Message count
        count_res = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        )
        msg_count = count_res.scalar() or 0

        # Last message
        last_msg_res = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg_res.scalar_one_or_none()

        last_message_text = last_msg.content if last_msg else None
        last_message_ts = last_msg.created_at.isoformat().replace("+00:00", "Z") if last_msg else None

        response_list.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                message_count=msg_count,
                agent_id=conv.agent_id or "buddy",
                active_specialists=conv.active_specialists or [],
                last_message=last_message_text,
                last_message_timestamp=last_message_ts
            )
        )

    # Sort Buddy conversations by updated_at or created_at desc
    response_list.sort(key=lambda c: c.created_at, reverse=True)
    return response_list


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all messages in a conversation, oldest first."""
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    if conv_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return [MessageResponse.model_validate(m) for m in result.scalars().all()]


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new empty conversation."""
    logger.info("[CONVERSATION CREATE] user_id=%s title=%s", current_user.id, body.title)
    try:
        conv = Conversation(user_id=current_user.id, title=body.title, agent_id="buddy")
        db.add(conv)
        await db.flush()
        await db.commit()
        await db.refresh(conv)
        logger.info("[CONVERSATION CREATE SUCCESS] conversation_id=%s user_id=%s", conv.id, current_user.id)
    except Exception as exc:
        logger.error("[CONVERSATION CREATE ERROR] user_id=%s error=%s", current_user.id, exc, exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation",
        )

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        message_count=0,
        agent_id=conv.agent_id or "buddy",
        active_specialists=conv.active_specialists or []
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update conversation properties (like title)."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    conv.title = body.title
    await db.commit()
    await db.refresh(conv)
    
    msg_count_result = await db.execute(
        select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    )
    message_count = msg_count_result.scalar() or 0
    
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        message_count=message_count,
        agent_id=conv.agent_id or "buddy",
        active_specialists=conv.active_specialists or []
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    
    await db.delete(conv)
    await db.commit()
    return None




