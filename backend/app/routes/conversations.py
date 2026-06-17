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


class ConnectSpecialistRequest(BaseModel):
    specialist_id: str


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

        # Add greeting message
        msg = Message(
            conversation_id=conv.id,
            user_id=current_user.id,
            role="assistant",
            content=buddy_info[2],
            sender_type="buddy"
        )
        db.add(msg)
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


@router.post("/conversations/{conversation_id}/connect-specialist", response_model=list[MessageResponse])
async def connect_specialist(
    conversation_id: uuid.UUID,
    body: ConnectSpecialistRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connect a specialist to the conversation and generate their context-shared greeting."""
    from app.agents.specialist_registry import SPECIALIST_REGISTRY
    from datetime import datetime, timezone, timedelta

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    specialist_id = body.specialist_id.lower()
    spec_info = SPECIALIST_REGISTRY.get(specialist_id)
    if not spec_info:
        raise HTTPException(status_code=400, detail=f"Specialist '{specialist_id}' not found.")

    # Check if already active
    active = list(conv.active_specialists or [])
    if specialist_id in active:
        return []

    # Add to active specialists list
    active.append(specialist_id)
    conv.active_specialists = active
    db.add(conv)

    # Mapping for the staggered greetings
    specialist_map = {
        "lex": {"name": "Lex", "pronoun": "him", "topic": "legal situation"},
        "maya": {"name": "Dr. Maya", "pronoun": "her", "topic": "health"},
        "ray": {"name": "Officer Ray", "pronoun": "him", "topic": "safety"},
        "techie": {"name": "Techie", "pronoun": "him", "topic": "technical issues"},
        "mentor": {"name": "Mentor", "pronoun": "them", "topic": "studies"},
        "finance": {"name": "Finance Coach", "pronoun": "him", "topic": "finances"},
        "fitness": {"name": "Fitness Coach", "pronoun": "him", "topic": "fitness"},
    }

    spec_data = specialist_map.get(specialist_id, {"name": spec_info["name"], "pronoun": "them", "topic": "situation"})
    spec_name = spec_data["name"]
    pronoun = spec_data["pronoun"]
    topic = spec_data["topic"]
    user_name = current_user.name or "there"

    # Generate Buddy's 4 intro messages
    buddy_contents = [
        "hey 😊",
        f"i think {spec_name} can explain this better than me",
        f"i gave {pronoun} the context already",
        f"{spec_name}, {user_name} has been worried about their {topic} lately"
    ]

    # Generate Specialist's 3 greeting messages
    spec_contents = [
        f"hey {user_name} 👋",
        "Buddy told me a little about what's going on",
        "can you tell me how long this has been happening?"
    ]

    base_time = datetime.now(timezone.utc)
    messages_created = []

    # Save Buddy's messages
    for idx, content in enumerate(buddy_contents):
        msg = Message(
            conversation_id=conversation_id,
            user_id=current_user.id,
            role="assistant",
            content=content,
            sender_type="buddy",
            created_at=base_time + timedelta(seconds=idx)
        )
        db.add(msg)
        messages_created.append(msg)

    # Save Specialist's messages
    for idx, content in enumerate(spec_contents):
        msg = Message(
            conversation_id=conversation_id,
            user_id=current_user.id,
            role="assistant",
            content=content,
            sender_type=specialist_id,
            created_at=base_time + timedelta(seconds=len(buddy_contents) + idx)
        )
        db.add(msg)
        messages_created.append(msg)

    await db.commit()

    return [MessageResponse.model_validate(m) for m in messages_created]


@router.post("/conversations/{conversation_id}/disconnect-specialist", response_model=list[MessageResponse])
async def disconnect_specialist(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect all specialists from the conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    active = list(conv.active_specialists or [])
    if not active:
        return []

    # Clear active specialists
    conv.active_specialists = []
    db.add(conv)

    # Save Buddy farewell message (but NO system leave message)
    buddy_msg = Message(
        conversation_id=conversation_id,
        user_id=current_user.id,
        role="assistant",
        content="I'm here. We've disconnected the specialist support for now, but let me know if you want to connect them again later!",
        sender_type="buddy"
    )
    db.add(buddy_msg)

    await db.commit()

    return [MessageResponse.model_validate(buddy_msg)]


