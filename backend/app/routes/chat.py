"""
Chat route – send messages, list conversations, stream responses via SSE.
"""

import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from jose import JWTError, jwt

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message, MessageRole
from app.models.user_profile import UserProfile
from app.models.chat_history import ChatHistory
from app.models.mood_log import MoodLog
from app.routes.auth import get_current_user
from app.schemas.chat import (
    ChatMessageRequest,
    MessageResponse,
    ConversationResponse,
    ConversationCreateRequest,
    ConversationUpdateRequest,
)
from app.chatbot.pipeline import run_agent_graph
from app.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


def generate_emotional_title(message: str, emotion: str) -> str:
    """Generate a poetic, emotionally meaningful chat title."""
    emotion_lower = (emotion or "").lower()
    
    # Check for specific emotional signatures
    if "exhaust" in emotion_lower or "burnout" in emotion_lower or "tired" in emotion_lower:
        return "🌧 Feeling emotionally drained"
    elif "lone" in emotion_lower or "withdr" in emotion_lower or "solit" in emotion_lower:
        return "🌊 Quiet loneliness tonight"
    elif "overthink" in emotion_lower or "spiral" in emotion_lower or "worry" in emotion_lower:
        return "🌙 Late night overthinking"
    elif "anx" in emotion_lower or "overwhelm" in emotion_lower or "fear" in emotion_lower:
        return "💭 Fear about future"
    elif "sad" in emotion_lower or "melancholy" in emotion_lower or "hurt" in emotion_lower or "grief" in emotion_lower:
        return "🌧 Muted melancholy"
    elif "happy" in emotion_lower or "joy" in emotion_lower or "thrive" in emotion_lower or "excit" in emotion_lower:
        return "☀️ Finding sunshine"
    elif "calm" in emotion_lower or "peace" in emotion_lower:
        return "✨ Safe harbor"
    
    # Fallback to general keywords in message
    msg_lower = message.lower()
    if "sleep" in msg_lower or "night" in msg_lower:
        return "🌙 Late night thoughts"
    elif "work" in msg_lower or "job" in msg_lower or "stud" in msg_lower:
        return "🍂 Stressful day"
    elif "friend" in msg_lower or "people" in msg_lower or "bully" in msg_lower:
        return "💭 Hurting connections"
    
    # Generic emotional fallbacks
    emotion_titles = {
        "anxiety": "🌪 Riding the wave",
        "sadness": "☔ Rain of thoughts",
        "overthinking": "🌀 Spiraling thoughts",
        "burnout": "🍂 Mentally exhausted",
        "loneliness": "🌌 Solitary reflections",
        "neutral": "✨ Soft check-in",
        "happy": "🌱 Small victories",
    }
    return emotion_titles.get(emotion_lower, "💬 Quiet catch-up")


async def generate_chat_title_llm(messages: list[dict]) -> str:
    """Use LLM to generate a short, beautiful, and emotionally resonant title (3-5 words) from messages."""
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages[:4]])
    
    prompt = """You are the Title Generator Agent for Esona, a supportive mental wellness companion.
Analyze the following conversation snippet and generate a short, poetic, and emotionally resonant title (3-5 words).
Do NOT use quotes. Do NOT explain. Use a single relevant emoji at the start.
Keep it under 35 characters.

Example: 🌊 Quiet loneliness tonight
Example: ☀️ Finding sunshine
Example: 🍂 Stressful day
Example: 🌙 Late night thoughts
Example: 💭 Fear about future

Conversation:
{history_text}

Title:"""
    
    try:
        from app.utils.llm import get_chat_client
        client = get_chat_client()
        from app.config import settings
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": prompt.format(history_text=history_text)},
            ],
            temperature=0.7,
            max_tokens=25,
        )
        title = response.choices[0].message.content.strip()
        # Clean title
        title = title.replace('"', '').replace("'", '').replace("`", "").strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title
    except Exception as e:
        logger.error(f"Failed to generate LLM title: {e}")
        return "✨ Soft check-in"


async def _get_or_create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
) -> Conversation:
    """Return an existing conversation or create a new one."""
    if conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conv

    conv = Conversation(user_id=user_id, title="New Conversation")
    db.add(conv)
    await db.flush()
    await db.refresh(conv)
    return conv


async def _build_conversation_history(
    db: AsyncSession, conversation_id: uuid.UUID, limit: int = 20
) -> list[dict]:
    """Load the last N messages in a conversation as dicts for the agents."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return [
        {"role": m.role.value, "content": m.content}
        for m in reversed(messages)
    ]


async def _get_emotional_profile_dict(
    db: AsyncSession, user_id: uuid.UUID, user_name: str
) -> dict:
    """Load the emotional profile as a plain dict (empty dict if none)."""
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    profile_dict = {
        "user_name": user_name,
        "personality_type": {},
        "emotional_baseline": {},
        "comfort_preferences": {},
        "communication_style": {},
        "emotional_summary": {},
        "stress_patterns": {},
        "emotional_triggers": {},
        "preferred_response_style": {},
        "emotional_style": {},
        "interests": {},
        "stress_triggers": {},
        "strengths": {},
        "weaknesses": {},
        "onboarding_answers": {},
        "personality_profile": {},
    }
    
    if profile is not None:
        profile_dict.update({
            "personality_type": profile.personality_type or {},
            "emotional_baseline": profile.emotional_baseline or {},
            "comfort_preferences": profile.comfort_preferences or {},
            "communication_style": profile.communication_style or {},
            "emotional_summary": profile.emotional_summary or {},
            "stress_patterns": profile.stress_patterns or {},
            "emotional_triggers": profile.emotional_triggers or {},
            "preferred_response_style": profile.preferred_response_style or {},
            "emotional_style": profile.emotional_style or {},
            "interests": profile.interests or {},
            "stress_triggers": profile.stress_triggers or {},
            "strengths": profile.strengths or {},
            "weaknesses": profile.weaknesses or {},
            "onboarding_answers": profile.onboarding_answers or {},
            "personality_profile": profile.personality_profile or {},
        })
        
    return profile_dict


async def summarize_and_store_conversation(db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, history: list[dict]):
    """Summarize older messages in a conversation and store it in the memories table."""
    logger.info(f"Summarizing thread {conversation_id} for user {user_id}")
    
    # We summarize everything except the last 4 messages to preserve immediate context continuity
    messages_to_summarize = history[:-4]
    if not messages_to_summarize:
        return
        
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages_to_summarize])
    
    prompt = f"""You are the Summarization Agent for Esona, a mental wellness companion.
Summarize the emotional context, key topics discussed, and state of mind of the user in this conversation history snippet.
Keep it extremely concise (under 2-3 sentences). Focus on what triggers, stressors, or breakthrough moments occurred.

Conversation history:
{history_text}

Summary:"""

    try:
        from app.utils.llm import get_chat_client
        client = get_chat_client()
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        summary = response.choices[0].message.content.strip()
        
        # Check if a summary already exists in Memory table
        from app.models.memory import Memory
        from app.services.memory_service import memory_service
        
        result = await db.execute(
            select(Memory).where(Memory.user_id == str(user_id))
        )
        memories = result.scalars().all()
        existing_memory = None
        for m in memories:
            meta = m.metadata_json or {}
            if meta.get("source") == "conversation_summary" and meta.get("conversation_id") == str(conversation_id):
                existing_memory = m
                break
                
        if existing_memory:
            # Update summary
            existing_memory.memory_summary = summary
            existing_memory.created_at = datetime.now(timezone.utc)
            # Shallow copy to trigger SA change tracking
            existing_memory.behavior_patterns = {
                **(existing_memory.behavior_patterns or {}),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            logger.info(f"Updated conversation summary memory for {conversation_id}")
        else:
            # Create a new memory entry
            await memory_service.saveMemory(
                db=db,
                user_id=str(user_id),
                memory_summary=summary,
                behavior_patterns={
                    "source": "conversation_summary",
                    "conversation_id": str(conversation_id),
                    "emotion": "neutral",
                    "stress_level": 3
                }
            )
            logger.info(f"Created conversation summary memory for {conversation_id}")
            
    except Exception as e:
        logger.error(f"Failed to generate and store conversation summary: {e}", exc_info=True)


@router.post("/message")
async def send_message(
    body: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a user message and receive the response as JSON (non-streaming fallback).
    """
    # 1. Get or create conversation
    conversation = await _get_or_create_conversation(
        db, current_user.id, body.conversation_id
    )

    # 2. Save the user's message
    user_msg = Message(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role=MessageRole.user,
        content=body.message,
    )
    db.add(user_msg)
    
    # Save to chat_history
    chat_user = ChatHistory(
        user_id=current_user.id,
        role="user",
        message=body.message,
        emotion_score=None,
    )
    db.add(chat_user)
    conversation.updated_at = datetime.now(timezone.utc)
    
    await db.flush()
    logger.info(f"[CHAT] User message saved (user={current_user.id}, conv={conversation.id})")

    # 3. Build context for agents
    history = await _build_conversation_history(db, conversation.id)
    emotional_profile = await _get_emotional_profile_dict(db, current_user.id, current_user.name)

    # 4. Run agent graph
    try:
        result = await run_agent_graph(
            user_message=body.message,
            user_id=str(current_user.id),
            conversation_history=history,
            emotional_profile=emotional_profile,
            conversation_id=conversation.id,
            db=db,
        )

        full_response = result.get("response", "I'm here for you. Could you tell me more?")
        detected_emotion = result.get("detected_emotion", None)
        mood_score = result.get("mood_score", None)
        agent_analysis = result.get("agent_analysis", {})
        logger.info(f"[CHAT] Gemini response generated (user={current_user.id}, emotion={detected_emotion}, mood={mood_score})")

        # Log memory retrieval status
        retrieved_memories = result.get("memories", [])
        if retrieved_memories:
            logger.info(f"[MEMORY] Retrieved {len(retrieved_memories)} relevant memories for user {current_user.id}")
        else:
            logger.info(f"[MEMORY] No relevant memories found for user {current_user.id}")

        # Update conversation title from first message using LLM
        if len(history) <= 1:
            try:
                title_msgs = [
                    {"role": "user", "content": body.message},
                    {"role": "assistant", "content": full_response}
                ]
                conversation.title = await generate_chat_title_llm(title_msgs)
            except Exception:
                conversation.title = generate_emotional_title(body.message, detected_emotion or "neutral")
            await db.flush()

        # Store memory using structured output from single analyzer call
        try:
            from app.services.memory_service import memory_service
            mem_extraction = result.get("memory_extraction", {})
            if mem_extraction.get("is_meaningful"):
                await memory_service.saveMemory(
                    db=db,
                    user_id=str(current_user.id),
                    memory_summary=mem_extraction.get("memory_summary"),
                    behavior_patterns=mem_extraction.get("behavior_patterns") or {},
                )
                logger.info(f"[MEMORY] Memory saved for user {current_user.id}: '{mem_extraction.get('memory_summary', '')[:80]}'")
            else:
                logger.info(f"[MEMORY] Skipped (small talk / not meaningful) for user {current_user.id}")
        except Exception as mem_err:
            logger.error(f"Failed to process and store memory: {mem_err}", exc_info=True)

        # Save assistant message to DB
        assistant_msg = Message(
            conversation_id=conversation.id,
            user_id=current_user.id,
            role=MessageRole.assistant,
            content=full_response,
            emotion_detected=detected_emotion,
            mood_score=mood_score,
            agent_analysis=agent_analysis,
            emotional_context=agent_analysis.get("emotion_analysis", {}),
        )
        db.add(assistant_msg)

        # Save to chat_history
        chat_assistant = ChatHistory(
            user_id=current_user.id,
            role="assistant",
            message=full_response,
            emotion_score=mood_score,
        )
        db.add(chat_assistant)

        # Save mood log
        dims = result.get("emotion_dimensions", {})
        mood_log = MoodLog(
            user_id=current_user.id,
            mood_score=mood_score or 0.5,
            mood_label=detected_emotion or "neutral",
            detected_emotion=detected_emotion or "neutral",
            stress=dims.get("stress", 0.3),
            happiness=dims.get("happiness", 0.5),
            sadness=dims.get("sadness", 0.3),
            anxiety=dims.get("anxiety", 0.3),
            motivation=dims.get("motivation", 0.5),
            confidence=dims.get("confidence", 0.5),
        )
        db.add(mood_log)
        
        # Also update conversation emotional_tag
        if detected_emotion:
            conversation.emotional_tag = detected_emotion
        conversation.updated_at = datetime.now(timezone.utc)

        # Trigger conversation summarization if message count >= 12
        if len(history) >= 12 and len(history) % 6 == 0:
            try:
                await summarize_and_store_conversation(db, current_user.id, conversation.id, history)
            except Exception as sum_err:
                logger.error(f"Summarization trigger failed: {sum_err}", exc_info=True)

        await db.commit()
        logger.info(f"[CHAT] Assistant response + mood log saved (user={current_user.id}, conv={conversation.id})")

        return {
            "response": full_response,
            "emotionDetected": detected_emotion,
            "moodScore": mood_score,
            "agentAnalysis": agent_analysis,
        }

    except Exception as e:
        logger.error(f"Agent graph error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="I encountered an error trying to process that. Could you try again?",
        )


@router.get("/{conversation_id}/stream")
async def stream_message_sse(
    conversation_id: uuid.UUID,
    message: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GET endpoint for Server-Sent Events (SSE) streaming of chat responses.
    Allows browsers to connect natively using the standard EventSource API.
    """
    # 1. Authenticate token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    current_user = result.scalar_one_or_none()
    if current_user is None:
        raise credentials_exception

    # 2. Get the conversation
    conversation = await _get_or_create_conversation(db, current_user.id, conversation_id)

    # 3. Save the user's message
    user_msg = Message(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role=MessageRole.user,
        content=message,
    )
    db.add(user_msg)
    
    # Save to chat_history
    chat_user = ChatHistory(
        user_id=current_user.id,
        role="user",
        message=message,
        emotion_score=None,
    )
    db.add(chat_user)
    conversation.updated_at = datetime.now(timezone.utc)
    
    await db.flush()
    logger.info(f"[CHAT] User message saved via SSE (user={current_user.id}, conv={conversation.id})")

    # 4. Build context
    history = await _build_conversation_history(db, conversation.id)
    emotional_profile = await _get_emotional_profile_dict(db, current_user.id, current_user.name)

    await db.commit()

    # 5. Event generator
    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            result = await run_agent_graph(
                user_message=message,
                user_id=str(current_user.id),
                conversation_history=history,
                emotional_profile=emotional_profile,
                conversation_id=conversation.id,
                db=db,
            )

            full_response = result.get("response", "I'm here for you. Could you tell me more?")
            detected_emotion = result.get("detected_emotion", None)
            mood_score = result.get("mood_score", None)
            agent_analysis = result.get("agent_analysis", {})
            logger.info(f"[CHAT] Gemini response generated via SSE (user={current_user.id}, emotion={detected_emotion}, mood={mood_score})")

            # Log memory retrieval
            retrieved_memories = result.get("memories", [])
            if retrieved_memories:
                logger.info(f"[MEMORY] Retrieved {len(retrieved_memories)} memories for SSE user {current_user.id}")
            else:
                logger.info(f"[MEMORY] No relevant memories for SSE user {current_user.id}")

            # Save assistant message & store memory
            async with get_db_session() as save_db:
                # Store memory
                try:
                    from app.services.memory_service import memory_service
                    mem_extraction = result.get("memory_extraction", {})
                    if mem_extraction.get("is_meaningful"):
                        await memory_service.saveMemory(
                            db=save_db,
                            user_id=str(current_user.id),
                            memory_summary=mem_extraction.get("memory_summary"),
                            behavior_patterns=mem_extraction.get("behavior_patterns") or {},
                        )
                        logger.info(f"[MEMORY] Memory saved via SSE for user {current_user.id}: '{mem_extraction.get('memory_summary', '')[:80]}'")
                    else:
                        logger.info(f"[MEMORY] Skipped (small talk) for SSE user {current_user.id}")
                except Exception as mem_err:
                    logger.error(f"Failed to process and store memory in stream: {mem_err}", exc_info=True)

                assistant_msg = Message(
                    conversation_id=conversation.id,
                    user_id=current_user.id,
                    role=MessageRole.assistant,
                    content=full_response,
                    emotion_detected=detected_emotion,
                    mood_score=mood_score,
                    agent_analysis=agent_analysis,
                    emotional_context=agent_analysis.get("emotion_analysis", {}),
                )
                save_db.add(assistant_msg)

                # Save to chat_history
                chat_assistant = ChatHistory(
                    user_id=current_user.id,
                    role="assistant",
                    message=full_response,
                    emotion_score=mood_score,
                )
                save_db.add(chat_assistant)

                # Save mood log
                dims = result.get("emotion_dimensions", {})
                mood_log = MoodLog(
                    user_id=current_user.id,
                    mood_score=mood_score or 0.5,
                    mood_label=detected_emotion or "neutral",
                    detected_emotion=detected_emotion or "neutral",
                    stress=dims.get("stress", 0.3),
                    happiness=dims.get("happiness", 0.5),
                    sadness=dims.get("sadness", 0.3),
                    anxiety=dims.get("anxiety", 0.3),
                    motivation=dims.get("motivation", 0.5),
                    confidence=dims.get("confidence", 0.5),
                )
                save_db.add(mood_log)
                
                # Also update conversation emotional_tag and title
                stmt = select(Conversation).where(Conversation.id == conversation.id)
                conv_res = await save_db.execute(stmt)
                db_conv = conv_res.scalar_one_or_none()
                if db_conv:
                    if detected_emotion:
                        db_conv.emotional_tag = detected_emotion
                    db_conv.updated_at = datetime.now(timezone.utc)
                    if len(history) <= 1:
                        try:
                            title_msgs = [
                                {"role": "user", "content": message},
                                {"role": "assistant", "content": full_response}
                            ]
                            db_conv.title = await generate_chat_title_llm(title_msgs)
                        except Exception:
                            db_conv.title = generate_emotional_title(message, detected_emotion or "neutral")

                # Trigger conversation summarization if message count >= 12
                if len(history) >= 12 and len(history) % 6 == 0:
                    try:
                        await summarize_and_store_conversation(save_db, current_user.id, conversation.id, history)
                    except Exception as sum_err:
                        logger.error(f"Summarization trigger failed: {sum_err}", exc_info=True)

                await save_db.commit()
                await save_db.refresh(assistant_msg)
                msg_id = str(assistant_msg.id)
                logger.info(f"[CHAT] SSE assistant response + mood log saved (user={current_user.id}, conv={conversation.id})")

            # Stream chunks
            chunk_size = 12
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i : i + chunk_size]
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "chunk",
                        "content": chunk,
                        "conversation_id": str(conversation.id),
                    }),
                }
                await asyncio.sleep(0.03)

            # Final done event
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "done",
                    "message_id": msg_id,
                    "conversation_id": str(conversation.id),
                    "emotion_detected": detected_emotion,
                    "mood_score": mood_score,
                    "agent_analysis": agent_analysis,
                }),
            }

        except Exception as e:
            logger.error(f"SSE stream error: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({
                    "type": "error",
                    "content": "I encountered an error trying to process that. Could you try again?",
                }),
            }

    return EventSourceResponse(event_generator())


@router.post("/conversations/{conversation_id}/first-message")
async def generate_first_message(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate and save a personalized first greeting message in an empty conversation,
    based on the user's personality profile, mood patterns, and past memories.
    """
    # 1. Verify conversation exists and is empty
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
        
    msg_count_res = await db.execute(
        select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    )
    msg_count = msg_count_res.scalar() or 0
    if msg_count > 0:
        # Conversation is not empty, return the first message already in it
        first_msg_res = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(1)
        )
        first_msg = first_msg_res.scalar_one_or_none()
        if first_msg:
            return {
                "response": first_msg.content,
                "emotionDetected": first_msg.emotion_detected,
                "moodScore": first_msg.mood_score,
            }
            
    # 2. Gather context
    # Profile
    profile = await _get_emotional_profile_dict(db, current_user.id, current_user.name)
    user_name = current_user.name or "friend"
    personality_str = json.dumps(profile.get("personality_profile", {}))
    interests_str = json.dumps(profile.get("interests", {}))
    
    # Recent Mood logs
    mood_result = await db.execute(
        select(MoodLog)
        .where(MoodLog.user_id == current_user.id)
        .order_by(MoodLog.created_at.desc())
        .limit(5)
    )
    mood_logs = mood_result.scalars().all()
    recent_moods = [f"Mood: {m.detected_emotion} (score: {m.mood_score}, stress: {m.stress})" for m in mood_logs]
    recent_moods_str = "\n".join(recent_moods) if recent_moods else "No recent mood logs."
    
    # Recent Memories
    from app.models.memory import Memory
    memory_result = await db.execute(
        select(Memory)
        .where(Memory.user_id == str(current_user.id))
        .order_by(Memory.created_at.desc())
        .limit(5)
    )
    memories = memory_result.scalars().all()
    memories_list = [f"- {m.memory_summary} (Patterns: {m.behavior_patterns})" for m in memories if m.metadata_json.get("source") != "conversation_summary"]
    memories_str = "\n".join(memories_list) if memories_list else "No past memories recorded."

    # Preferred texting style
    reply_style = profile.get("personality_profile", {}).get("reply_style", {})
    style_preference = (
        f"Paragraph preference: {reply_style.get('paragraph_preference', 'short')}, "
        f"Emoji usage: {reply_style.get('emoji_usage', 'medium')}, "
        f"Tone: {reply_style.get('communication_style', 'gentle')}"
    )

    # 3. Create prompt
    prompt = f"""You are Esona, a deeply supportive, emotionally intelligent AI wellness companion for students.
Your job is to generate a personalized first greeting message (opening check-in) for the user.
Avoid repeating the exact same message every time. Be creative, casual, warm, and mirror a human texting style.

============================================
USER PROFILE & CONTEXT:
- Name: {user_name}
- Personality: {personality_str}
- Interests: {interests_str}
- Style Preference: {style_preference}
- Recent Mood Logs:
{recent_moods_str}
- Relevant Memories / Past Context:
{memories_str}

============================================
BEHAVIOR & GREETING VARIATION RULES:
1. Make your greeting feel natural, warm, and highly personalized.
2. DO NOT sound like a therapy assistant. Ban robotic templates ("I understand...", "How can I help you today?").
3. Choose one of the following variation themes depending on context:
   - "Supportive Check-in": If recent mood logs show high stress/anxiety/sadness, check in on how they are feeling now.
   - "Continuation Check-in": If memories exist, reference a topic they discussed recently (e.g. studies, exams, sleep, a friend) naturally.
   - "Warm Opening": If there are no recent stress triggers or memories, greet them warmly, reference one of their interests, and ask how their day is going.
4. You MUST split your response into 2 to 3 separate human-like thoughts using the delimiter " ||| " (with spaces around it).

First Message:"""

    # 4. Generate first message
    try:
        from app.utils.llm import generate_chat_completion_with_fallback
        raw_response = await generate_chat_completion_with_fallback(
            messages=[{"role": "system", "content": prompt}],
            temperature=0.75,
            max_tokens=300
        )
    except Exception as e:
        logger.error(f"Failed to generate personalized first message: {e}", exc_info=True)
        raw_response = f"Hey {user_name}! 👋 ||| Just checking in to see how you're doing today. ||| What's on your mind?"

    # 5. Save message to DB
    assistant_msg = Message(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role=MessageRole.assistant,
        content=raw_response,
        emotion_detected="neutral",
        mood_score=0.5,
        agent_analysis={}
    )
    db.add(assistant_msg)
    
    # Update conversation's updated_at
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    
    return {
        "response": raw_response,
        "emotionDetected": "neutral",
        "moodScore": 0.5,
    }


def get_db_session():
    """Standalone session context for saving messages outside the request lifecycle."""
    from app.database import async_session_maker
    return async_session_maker()



# Conversation CRUD endpoints moved to app.routes.conversations
