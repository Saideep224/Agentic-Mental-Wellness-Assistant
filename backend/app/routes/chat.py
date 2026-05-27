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
    logger.info(f"[CHAT FLOW] _get_or_create_conversation called: user_id={user_id}, conversation_id={conversation_id}")
    if conversation_id:
        try:
            logger.info(f"[DB SELECT] Querying conversations for id={conversation_id}...")
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            conv = result.scalar_one_or_none()
            if conv is None:
                logger.error(f"[DB SELECT] Conversation {conversation_id} not found for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
            logger.info(f"[DB SELECT] Found conversation: id={conv.id}, title='{conv.title}'")
            return conv
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"[DB SELECT ERROR] Failed to fetch conversation {conversation_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Database select query failed")

    try:
        logger.info(f"[DB INSERT] Creating new Conversation entry for user_id={user_id}...")
        conv = Conversation(user_id=user_id, title="New Conversation")
        db.add(conv)
        await db.flush()
        await db.refresh(conv)
        logger.info(f"[DB INSERT] Created conversation: id={conv.id}, title='{conv.title}'")
        return conv
    except Exception as e:
        logger.error(f"[DB INSERT ERROR] Failed to create new conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create new conversation in DB")


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
            select(Memory).where(Memory.user_id == user_id)
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
    logger.info(f"[API] send_message request received: conversation_id={body.conversation_id}, message_len={len(body.message) if body.message else 0}")
    logger.info(f"[AUTH STEP] Authenticated user details: id={current_user.id}, email={current_user.email}")
    
    try:
        # 1. Get or create conversation
        conversation = await _get_or_create_conversation(
            db, current_user.id, body.conversation_id
        )
        conversation_id_resolved = conversation.id

        # 2. Save the user's message
        logger.info(f"[DB INSERT] Instantiating user Message: conversation_id={conversation_id_resolved}, user_id={current_user.id}")
        logger.info(f"[TYPE LOG] send_message user: conversation_id type: {type(conversation_id_resolved)}, value: {conversation_id_resolved}")
        logger.info(f"[TYPE LOG] send_message user: user_id type: {type(current_user.id)}, value: {current_user.id}")
        user_msg = Message(
            conversation_id=conversation_id_resolved,
            user_id=current_user.id,
            role=MessageRole.user,
            content=body.message,
        )
        db.add(user_msg)
        conversation.updated_at = datetime.now(timezone.utc)
        
        # 3. Commit immediately before calling the AI/agents to satisfy Task 4
        logger.info(f"[DB COMMIT] Saving User message and Conversation to the database...")
        try:
            await db.commit()
            await db.refresh(conversation)
            await db.refresh(user_msg)
            logger.info(f"[DB COMMIT SUCCESS] User message (id={user_msg.id}) and Conversation (id={conversation.id}) successfully saved.")
        except Exception as commit_err:
            logger.error(f"[DB COMMIT ERROR] Failed to save conversation/user message to DB: {commit_err}", exc_info=True)
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to persist user message in the database")

        # 4. Build context for agents
        logger.info(f"[CONTEXT] Loading conversation history for id={conversation_id_resolved}...")
        history = await _build_conversation_history(db, conversation_id_resolved)
        logger.info(f"[CONTEXT] Loaded {len(history)} messages from history.")
        
        logger.info(f"[CONTEXT] Loading user emotional profile...")
        emotional_profile = await _get_emotional_profile_dict(db, current_user.id, current_user.name)
        logger.info(f"[CONTEXT] Profile loaded successfully.")

        # 5. Run agent graph
        logger.info(f"[AI AGENT] Running multi-agent cognitive graph for user message...")
        try:
            result = await run_agent_graph(
                user_message=body.message,
                user_id=str(current_user.id),
                conversation_history=history,
                emotional_profile=emotional_profile,
                conversation_id=conversation_id_resolved,
                db=db,
            )
            logger.info(f"[AI AGENT SUCCESS] Multi-agent processing complete.")
        except Exception as agent_err:
            logger.error(f"[AI AGENT ERROR] Multi-agent execution failed: {agent_err}", exc_info=True)
            raise HTTPException(status_code=500, detail="I encountered an error trying to process that. Could you try again?")

        full_response = result.get("response", "I'm here for you. Could you tell me more?")
        detected_emotion = result.get("detected_emotion", None)
        mood_score = result.get("mood_score", None)
        agent_analysis = result.get("agent_analysis", {})
        
        # Log memory retrieval details
        retrieved_memories = result.get("memories", [])
        logger.info(f"[MEMORY] Retrieved {len(retrieved_memories)} relevant memories for user.")

        # 6. Update conversation title from first message using LLM
        if len(history) <= 1:
            try:
                logger.info(f"[TITLE GENERATION] Generating title for new conversation...")
                title_msgs = [
                    {"role": "user", "content": body.message},
                    {"role": "assistant", "content": full_response}
                ]
                conversation.title = await generate_chat_title_llm(title_msgs)
                logger.info(f"[TITLE GENERATION SUCCESS] Poetic title set: '{conversation.title}'")
            except Exception as title_err:
                logger.warning(f"[TITLE GENERATION WARNING] LLM title failed: {title_err}. Falling back to default.")
                conversation.title = generate_emotional_title(body.message, detected_emotion or "neutral")
            
            # Save the title update
            db.add(conversation)

        # 7. Store memories if meaningful
        try:
            from app.services.memory_service import memory_service
            mem_extraction = result.get("memory_extraction", {})
            if mem_extraction.get("is_meaningful"):
                logger.info(f"[DB INSERT] Storing memory: '{mem_extraction.get('memory_summary', '')[:80]}'...")
                await memory_service.saveMemory(
                    db=db,
                    user_id=str(current_user.id),
                    memory_summary=mem_extraction.get("memory_summary"),
                    behavior_patterns=mem_extraction.get("behavior_patterns") or {},
                )
                logger.info(f"[DB INSERT SUCCESS] Memory stored successfully.")
            else:
                logger.info(f"[MEMORY] Skip storing memory: conversation was small talk.")
        except Exception as mem_err:
            logger.error(f"[MEMORY ERROR] Failed to save memory: {mem_err}", exc_info=True)

        # 8. Save assistant message and mood logs to DB
        logger.info(f"[DB INSERT] Saving AI response and Mood logs to database...")
        logger.info(f"[TYPE LOG] send_message assistant: conversation_id type: {type(conversation_id_resolved)}, value: {conversation_id_resolved}")
        logger.info(f"[TYPE LOG] send_message assistant: user_id type: {type(current_user.id)}, value: {current_user.id}")
        try:
            assistant_msg = Message(
                conversation_id=conversation_id_resolved,
                user_id=current_user.id,
                role=MessageRole.assistant,
                content=full_response,
                emotion_detected=detected_emotion,
                mood_score=mood_score,
                agent_analysis=agent_analysis,
                emotional_context=agent_analysis.get("emotion_analysis", {}),
            )
            db.add(assistant_msg)

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
            
            # Update conversation emotional_tag
            if detected_emotion:
                conversation.emotional_tag = detected_emotion
            conversation.updated_at = datetime.now(timezone.utc)
            db.add(conversation)

            # Trigger conversation summarization if message count >= 12
            if len(history) >= 12 and len(history) % 6 == 0:
                try:
                    logger.info(f"[DB CONTEXT] Triggering conversation summarization...")
                    await summarize_and_store_conversation(db, current_user.id, conversation_id_resolved, history)
                except Exception as sum_err:
                    logger.error(f"[SUMMARIZATION ERROR] Summarization trigger failed: {sum_err}", exc_info=True)

            # Commit assistant message + mood logs
            await db.commit()
            await db.refresh(assistant_msg)
            logger.info(f"[DB COMMIT SUCCESS] AI response (id={assistant_msg.id}) and MoodLog saved successfully.")
        except Exception as db_err:
            logger.error(f"[DB COMMIT ERROR] Failed to save assistant message/mood log: {db_err}", exc_info=True)
            await db.rollback()

        return {
            "response": full_response,
            "emotionDetected": detected_emotion,
            "moodScore": mood_score,
            "agentAnalysis": agent_analysis,
        }

    except Exception as route_err:
        logger.error(f"[API ERROR] Global failure in send_message endpoint: {route_err}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="I encountered an internal server error. Please try again in a moment.",
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
    logger.info(f"[API SSE] stream_message_sse request received: conversation_id={conversation_id}, message_len={len(message) if message else 0}")
    
    try:
        # 1. Authenticate token using the new shared validation logic
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
        try:
            logger.info("[AUTH SSE] Decoding and verifying token...")
            from app.routes.auth import decode_and_verify_token
            payload = decode_and_verify_token(token)
            user_id_str: str | None = payload.get("sub")
            if user_id_str is None:
                logger.error("[AUTH SSE] Sub claim is missing from JWT payload.")
                raise credentials_exception
            user_id = uuid.UUID(user_id_str)
            logger.info(f"[AUTH SSE] Decoded user_id: {user_id}")
        except Exception as auth_err:
            logger.error(f"[AUTH SSE ERROR] JWT validation failed: {auth_err}")
            raise credentials_exception

        # Load user from profiles table
        result = await db.execute(select(User).where(User.id == user_id))
        current_user = result.scalar_one_or_none()
        if current_user is None:
            logger.error(f"[AUTH SSE ERROR] User profile not found in DB for user_id={user_id}")
            raise credentials_exception
        logger.info(f"[AUTH SSE SUCCESS] Authenticated user details: id={current_user.id}, email={current_user.email}")

        # 2. Get the conversation
        conversation = await _get_or_create_conversation(db, current_user.id, conversation_id)
        conversation_id_resolved = conversation.id

        # 3. Save the user's message
        logger.info(f"[DB INSERT SSE] Saving User message: conversation_id={conversation_id_resolved}, user_id={current_user.id}")
        logger.info(f"[TYPE LOG] stream_message_sse user: conversation_id type: {type(conversation_id_resolved)}, value: {conversation_id_resolved}")
        logger.info(f"[TYPE LOG] stream_message_sse user: user_id type: {type(current_user.id)}, value: {current_user.id}")
        try:
            user_msg = Message(
                conversation_id=conversation_id_resolved,
                user_id=current_user.id,
                role=MessageRole.user,
                content=message,
            )
            db.add(user_msg)
            conversation.updated_at = datetime.now(timezone.utc)
            db.add(conversation)
            
            # Commit the user's message and conversation BEFORE starting stream execution (satisfies Task 4)
            await db.commit()
            await db.refresh(conversation)
            await db.refresh(user_msg)
            logger.info(f"[DB COMMIT SSE SUCCESS] User message (id={user_msg.id}) and Conversation resolved.")
        except Exception as db_msg_err:
            logger.error(f"[DB COMMIT SSE ERROR] Failed to save user message: {db_msg_err}", exc_info=True)
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to save user message")

        # 4. Build context
        logger.info(f"[CONTEXT SSE] Loading history and emotional profile...")
        history = await _build_conversation_history(db, conversation_id_resolved)
        emotional_profile = await _get_emotional_profile_dict(db, current_user.id, current_user.name)

        # 5. Event generator for Starlette SSE EventSourceResponse
        async def event_generator() -> AsyncGenerator[dict, None]:
            logger.info("[EVENT GENERATOR] Stream generator started.")
            try:
                # Execute agents Graph
                logger.info(f"[AI AGENT SSE] Executing agent pipeline graph...")
                result = await run_agent_graph(
                    user_message=message,
                    user_id=str(current_user.id),
                    conversation_history=history,
                    emotional_profile=emotional_profile,
                    conversation_id=conversation_id_resolved,
                    db=None,  # We pass None because we'll use a separate session for saving
                )
                logger.info(f"[AI AGENT SSE SUCCESS] Pipeline graph execution complete.")

                full_response = result.get("response", "I'm here for you. Could you tell me more?")
                detected_emotion = result.get("detected_emotion", None)
                mood_score = result.get("mood_score", None)
                agent_analysis = result.get("agent_analysis", {})

                # Save assistant message & mood log inside a separate DB context to prevent connection locks
                logger.info(f"[DB INSERT SSE ASSISTANT] Saving assistant response outside the request context...")
                async with get_db_session() as save_db:
                    try:
                        # Store memory
                        mem_extraction = result.get("memory_extraction", {})
                        if mem_extraction.get("is_meaningful"):
                            logger.info(f"[DB INSERT SSE MEMORY] Storing memory: '{mem_extraction.get('memory_summary', '')[:80]}'...")
                            from app.services.memory_service import memory_service
                            await memory_service.saveMemory(
                                db=save_db,
                                user_id=str(current_user.id),
                                memory_summary=mem_extraction.get("memory_summary"),
                                behavior_patterns=mem_extraction.get("behavior_patterns") or {},
                            )
                            logger.info("[DB INSERT SSE MEMORY SUCCESS] Memory saved successfully.")
                    except Exception as mem_err:
                        logger.error(f"[MEMORY SSE ERROR] Failed to store memory: {mem_err}", exc_info=True)

                    try:
                        logger.info(f"[TYPE LOG] stream_message_sse assistant: conversation_id type: {type(conversation_id_resolved)}, value: {conversation_id_resolved}")
                        logger.info(f"[TYPE LOG] stream_message_sse assistant: user_id type: {type(current_user.id)}, value: {current_user.id}")
                        assistant_msg = Message(
                            conversation_id=conversation_id_resolved,
                            user_id=current_user.id,
                            role=MessageRole.assistant,
                            content=full_response,
                            emotion_detected=detected_emotion,
                            mood_score=mood_score,
                            agent_analysis=agent_analysis,
                            emotional_context=agent_analysis.get("emotion_analysis", {}),
                        )
                        save_db.add(assistant_msg)

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
                        
                        # Update conversation tag/title
                        stmt = select(Conversation).where(Conversation.id == conversation_id_resolved)
                        conv_res = await save_db.execute(stmt)
                        db_conv = conv_res.scalar_one_or_none()
                        if db_conv:
                            if detected_emotion:
                                db_conv.emotional_tag = detected_emotion
                            db_conv.updated_at = datetime.now(timezone.utc)
                            if len(history) <= 1:
                                try:
                                    logger.info(f"[TITLE GENERATION SSE] Generating title...")
                                    title_msgs = [
                                        {"role": "user", "content": message},
                                        {"role": "assistant", "content": full_response}
                                    ]
                                    db_conv.title = await generate_chat_title_llm(title_msgs)
                                except Exception:
                                    db_conv.title = generate_emotional_title(message, detected_emotion or "neutral")
                                save_db.add(db_conv)
                        
                        # Trigger summarization
                        if len(history) >= 12 and len(history) % 6 == 0:
                            try:
                                logger.info(f"[DB CONTEXT SSE] Triggering summarization...")
                                await summarize_and_store_conversation(save_db, current_user.id, conversation_id_resolved, history)
                            except Exception as sum_err:
                                logger.error(f"[SUMMARIZATION SSE ERROR] Summarization trigger failed: {sum_err}", exc_info=True)

                        await save_db.commit()
                        await save_db.refresh(assistant_msg)
                        msg_id = str(assistant_msg.id)
                        logger.info(f"[DB COMMIT SSE ASSISTANT SUCCESS] Saved assistant response (id={msg_id}) and MoodLog.")
                    except Exception as sse_db_err:
                        logger.error(f"[DB COMMIT SSE ASSISTANT ERROR] Failed to save assistant message/mood log: {sse_db_err}", exc_info=True)
                        await save_db.rollback()
                        msg_id = ""

                # Yield chunks
                logger.info(f"[SSE STREAM] Yielding response text chunks...")
                chunk_size = 12
                for i in range(0, len(full_response), chunk_size):
                    chunk = full_response[i : i + chunk_size]
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "chunk",
                            "content": chunk,
                            "conversation_id": str(conversation_id_resolved),
                        }),
                    }
                    await asyncio.sleep(0.03)

                # Yield done event
                logger.info(f"[SSE STREAM] Yielding final 'done' event.")
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "done",
                        "message_id": msg_id,
                        "conversation_id": str(conversation_id_resolved),
                        "emotion_detected": detected_emotion,
                        "mood_score": mood_score,
                        "agent_analysis": agent_analysis,
                    }),
                }

            except Exception as gen_err:
                logger.error(f"[SSE STREAM ERROR] Error inside event_generator: {gen_err}", exc_info=True)
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "type": "error",
                        "content": "I encountered an error trying to process that. Could you try again?",
                    }),
                }

        # Return the EventSourceResponse
        return EventSourceResponse(event_generator())

    except Exception as route_err:
        logger.error(f"[API ERROR] Global failure in stream_message_sse endpoint: {route_err}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="I encountered an internal server error initializing the chat stream.",
        )


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
        .where(Memory.user_id == current_user.id)
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
    logger.info(f"[TYPE LOG] generate_first_message: conversation_id type: {type(conversation.id)}, value: {conversation.id}")
    logger.info(f"[TYPE LOG] generate_first_message: user_id type: {type(current_user.id)}, value: {current_user.id}")
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
