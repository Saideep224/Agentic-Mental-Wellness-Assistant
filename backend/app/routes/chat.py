"""
Chat route – send messages, list conversations, stream responses via SSE.
"""

import json
import uuid
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select, func, and_
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
from app.database import _history_cache, _profile_cache, write_queue
_recent_responses_cache: dict[str, list[str]] = {}
_RESPONSE_CACHE_SIZE = 20
from app.utils.helpers import get_random_human_fallback, get_speculative_transition, normalize_uuid, detect_specialist_action


class MockConversation:
    def __init__(self, id, user_id, title="Temporary Conversation"):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.emotional_tag = "neutral"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

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
    
    prompt = """You are the Title Generator Agent for Buddy, a supportive mental wellness companion.
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
        from app.utils.llm import generate_chat_completion_with_fallback
        title = await generate_chat_completion_with_fallback(
            messages=[
                {"role": "system", "content": prompt.format(history_text=history_text)},
            ],
            temperature=0.7,
            max_tokens=25,
            route_category="SNAPSHOT_GENERATION"
        )
        # Clean title
        title = title.replace('"', '').replace("'", '').replace("`", "").strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title
    except Exception as e:
        logger.error(f"Failed to generate LLM title: {e}")
        return "✨ Soft check-in"


def detect_specialist_recommendation(message: str, agent_analysis: dict, history: list = None) -> str | None:
    """Detect if the message suggests a need for a specialist agent based on cognitive analysis and context."""
    if not agent_analysis:
        return None

    import re

    # 1. Enforce Turn Delay Rules
    # We count user turns in the conversation history to let Buddy chat first.
    user_turns = 0
    if history:
        user_turns = sum(1 for m in history if m.get("role") == "user")

    # The current incoming user message is +1 turn.
    total_user_turns = user_turns + 1

    # 2. Extract semantic classification from LLM-derived agent_analysis
    ctx = agent_analysis.get("context_analysis", {})
    suggested = ctx.get("specialist_recommendation")
    topic = ctx.get("topic")

    # 3. Double-guard: Boundary-aware keyword overrides to fix false keyword routing
    msg_lower = message.lower()
    
    # Check for relationship overrides first (e.g. "broke up", "broken up" should never route to finance)
    is_relationship = False
    if re.search(r'\b(broke\s+up|broken\s+up|split\s+up|dumped|my\s+ex|my\s+boyfriend|my\s+girlfriend|left\s+me|broken\s+heart|heartbreak|had\s+a\s+fight)\b', msg_lower):
        is_relationship = True
        topic = "relationship"
        suggested = "relationship"

    # Fallback keyword matching (only if LLM suggestion is not present)
    if not suggested:
        keywords = {
            "lex": ["legal", "lawyer", "court", "sue", "property dispute", "land dispute", "contract", "police case", "family property", "agreement", "lease", "tenant", "advocate", "litigation"],
            "maya": ["health", "symptom", "pain", "medical", "doctor", "disease", "illness", "headache", "chest pain", "diagnosis", "health anxiety", "sick", "infection", "cough", "fever", "physician"],
            "ray": ["hacked", "stalker", "cyber", "scam", "blackmail", "harass", "threat", "bully", "online safety", "scammed", "stole my account", "compromised", "phishing", "leak", "police", "cop", "fir", "crime", "emergency"],
            "techie": ["code", "bug", "programming", "git", "database error", "broken phone", "windows update", "server down", "software crash", "tech support", "ide", "laptop", "computer", "compiler"],
            "mentor": ["exam", "study", "failing class", "test stress", "academic pressure", "semester", "syllabus", "procrastinating study", "homework", "grades", "school", "college", "university", "midterm"],
            "fitness": ["workout", "exercise", "weight loss", "nutrition", "diet", "gym", "fitness", "calories", "posture", "muscle", "active habits", "cardio", "sleep schedule", "stretching", "running"]
        }
        
        # Match financial keywords carefully (excluding "broke" if it is a breakup)
        finance_keywords = ["money", "budget", "finance", "debt", "loan", "credit card", "bills", "rent", "cost of living", "salary", "student loan", "bankrupt", "expenses", "saving"]
        if "broke" in msg_lower and not is_relationship:
            finance_keywords.append("broke")

        keywords["finance"] = finance_keywords

        for spec_id, words in keywords.items():
            if any(re.search(rf'\b{re.escape(w)}\b', msg_lower) for w in words):
                suggested = spec_id
                if spec_id == "relationship":
                    topic = "relationship"
                break

    # If still no specialist suggestion, return None
    if not suggested:
        return None

    # Map semantic categories to specialist IDs
    category_to_spec = {
        "relationship": "relationship",
        "finance": "finance",
        "legal": "lex",
        "health": "maya",
        "academic": "mentor",
        "tech": "techie",
        "fitness": "fitness"
    }
    spec_id = category_to_spec.get(suggested, suggested)

    # 4. Enforce turns threshold delay
    if spec_id == "relationship" or topic == "relationship":
        # For relationship, require at least 3 total user turns (current + history)
        if total_user_turns < 3:
            logger.info(f"[Specialist Routing] Delayed relationship coach recommendation (turns: {total_user_turns}/3)")
            return None
    else:
        # For other specialists, require at least 2 total user turns
        if total_user_turns < 2:
            logger.info(f"[Specialist Routing] Delayed specialist '{spec_id}' recommendation (turns: {total_user_turns}/2)")
            return None

    # 5. Enforce routing confidence threshold (0.75)
    confidence = agent_analysis.get("detected_emotion_confidence", 1.0)
    if confidence < 0.75:
        logger.info(f"[Specialist Routing] Specialist recommendation '{spec_id}' below confidence threshold: {confidence} < 0.75")
        return None

    return spec_id


async def _get_or_create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
) -> Conversation:
    """Return an existing conversation or create a new one, raising HTTP exceptions on failure."""
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
                logger.warning(f"[DB SELECT] Conversation {conversation_id} not found for user {user_id}. Auto-creating to recover state...")
                conv = Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    title="Buddy Chat",
                    agent_id="buddy",
                    active_specialists=[]
                )
                db.add(conv)
                await db.flush()
            logger.info(f"[DB SELECT] Found conversation: id={conv.id}, title='{conv.title}'")
            return conv
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[DB SELECT ERROR] Failed to fetch conversation {conversation_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error fetching conversation",
            )

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize new conversation thread",
        )


async def _build_conversation_history(
    db: AsyncSession, conversation_id: uuid.UUID, limit: int = 20
) -> list[dict]:
    """Load the last N messages in a conversation as dicts for the agents, with in-memory caching."""
    try:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        history = [
            {
                "role": m.role.value, 
                "content": m.content,
                "agent_analysis": m.agent_analysis or {}
            }
            for m in reversed(messages)
        ]
        # Update in-memory fallback cache
        _history_cache[str(conversation_id)] = history
        return history
    except Exception as e:
        logger.warning(f"[DB FAIL] _build_conversation_history failed: {e}. Falling back to in-memory cache.")
        return _history_cache.get(str(conversation_id), [])


async def _get_emotional_profile_dict(
    db: AsyncSession, user_id: uuid.UUID, user_name: str
) -> dict:
    """Load the emotional profile as a plain dict, with in-memory caching."""
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

    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
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
            
        # Update in-memory fallback cache
        _profile_cache[str(user_id)] = profile_dict
        return profile_dict
    except Exception as e:
        logger.warning(f"[DB FAIL] _get_emotional_profile_dict failed: {e}. Falling back to in-memory cache.")
        return _profile_cache.get(str(user_id), profile_dict)


async def _get_conversation_summary(db: AsyncSession, user_id: str, conversation_id: str) -> str | None:
    """Query the memories table for a conversation summary memory with a 3.0s timeout."""
    try:
        from app.models.memory import Memory
        
        async def _query():
            result = await db.execute(
                select(Memory).where(Memory.user_id == user_id)
            )
            memories = result.scalars().all()
            for m in memories:
                meta = m.metadata_json or {}
                if meta.get("source") == "conversation_summary" and meta.get("conversation_id") == str(conversation_id):
                    return m.memory_summary
            return None

        return await asyncio.wait_for(_query(), timeout=3.0)
    except Exception as e:
        logger.warning(f"Failed to fetch conversation summary (timeout or error): {e}")
    return None


async def summarize_and_store_conversation(db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, history: list[dict]):
    """Summarize older messages in a conversation and store it in the memories table."""
    logger.info(f"Summarizing thread {conversation_id} for user {user_id}")
    
    # We summarize everything except the last 4 messages to preserve immediate context continuity
    messages_to_summarize = history[:-4]
    if not messages_to_summarize:
        return
        
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages_to_summarize])
    
    prompt = f"""You are the Summarization Agent for Buddy, a mental wellness companion.
Summarize the emotional context, key topics discussed, and state of mind of the user in this conversation history snippet.
Keep it extremely concise (under 2-3 sentences). Focus on what triggers, stressors, or breakthrough moments occurred.

Conversation history:
{history_text}

Summary:"""

    try:
        from app.utils.llm import generate_chat_completion_with_fallback
        summary = await generate_chat_completion_with_fallback(
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
            route_category="SNAPSHOT_GENERATION"
        )
        
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
                },
                memory_type="event",
                importance_score=5.0
            )
            logger.info(f"Created conversation summary memory for {conversation_id}")
            
    except Exception as e:
        logger.error(f"Failed to generate and store conversation summary: {e}", exc_info=True)


async def async_save_message(conversation_id, user_id, role, content, emotion_detected=None, mood_score=None, agent_analysis=None, sender_type=None):
    """Asynchronously inserts a message inside a fresh DB session on failure."""
    logger.info(f"[BackgroundWriteQueue] Executing async message save: conversation_id={conversation_id}, role={role}")
    from app.routes.chat import get_db_session
    async with get_db_session() as save_db:
        try:
            # Resolve conversation exists
            result = await save_db.execute(select(Conversation).where(Conversation.id == conversation_id))
            conv = result.scalar_one_or_none()
            if not conv:
                # If conversation was also lost, recreate it first
                conv = Conversation(id=conversation_id, user_id=user_id, title="Recovered Conversation")
                save_db.add(conv)
                await save_db.flush()
                
            msg = Message(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                content=content,
                emotion_detected=emotion_detected,
                mood_score=mood_score,
                agent_analysis=agent_analysis,
                emotional_context=agent_analysis.get("emotion_analysis", {}) if agent_analysis else None,
                sender_type=sender_type
            )
            save_db.add(msg)
            conv.updated_at = datetime.now(timezone.utc)
            save_db.add(conv)
            await save_db.commit()
            logger.info(f"[BackgroundWriteQueue] Async message save successful: message_id={msg.id}")
        except Exception as e:
            logger.error(f"[BackgroundWriteQueue] Async message save failed: {e}", exc_info=True)
            await save_db.rollback()
            raise


async def async_save_mood_log(user_id, mood_score, mood_label, dims):
    """Asynchronously inserts a mood log inside a fresh DB session on failure."""
    logger.info(f"[BackgroundWriteQueue] Executing async mood log save: user_id={user_id}")
    from app.routes.chat import get_db_session
    async with get_db_session() as save_db:
        try:
            mood_log = MoodLog(
                user_id=user_id,
                mood_score=mood_score or 0.5,
                mood_label=mood_label or "neutral",
                detected_emotion=mood_label or "neutral",
                stress=dims.get("stress", 0.3),
                happiness=dims.get("happiness", 0.5),
                sadness=dims.get("sadness", 0.3),
                anxiety=dims.get("anxiety", 0.3),
                motivation=dims.get("motivation", 0.5),
                confidence=dims.get("confidence", 0.5)
            )
            save_db.add(mood_log)
            await save_db.commit()
            logger.info(f"[BackgroundWriteQueue] Async mood log save successful.")
        except Exception as e:
            logger.error(f"[BackgroundWriteQueue] Async mood log save failed: {e}", exc_info=True)
            await save_db.rollback()
            raise


def check_buddy_intervention(message: str, specialist_id: str, specialist_response: str, cog_res: dict) -> tuple[bool, str | None]:
    """
    Checks if Buddy should intervene in a specialist conversation.
    Returns (should_intervene, reason).
    """
    # 1. Direct address
    message_lower = message.lower()
    if "buddy" in message_lower:
        return True, "mention"

    # 2. Confusion
    confusion_keywords = ["confused", "don't understand", "what does that mean", "dont understand", "what do you mean"]
    if any(kw in message_lower for kw in confusion_keywords):
        return True, "confusion"

    # 3. Highly technical terms
    technical_jargon = [
        "jurisdiction", "liability", "compliance", "statute", "remedy",
        "clause", "agreement", "dispute", "physiological", "hydration",
        "baseline", "stress response", "consult a physician", "block",
        "otp", "phishing", "screenshots", "cybercrime portal", "incident log",
        "stack trace", "debug", "error log", "dependency", "framework",
        "backend", "frontend", "runtime", "syntax", "breakpoint",
        "pomodoro", "active recall", "feynman technique", "time-blocking",
        "revision", "syllabus", "budget", "fixed expenses", "variable costs",
        "savings rate", "debt-to-income", "emergency fund", "reps", "sets",
        "progressive overload", "protein intake", "calorie deficit", "workout split"
    ]
    spec_response_lower = specialist_response.lower()
    if any(word in spec_response_lower for word in technical_jargon):
        return True, "technical"

    # 4. Emotional Intensity
    e_data = cog_res.get("emotion_agent", {})
    stress_val = float(e_data.get("stress", 0.0))
    anxiety_val = float(e_data.get("anxiety", 0.0))
    sadness_val = float(e_data.get("sadness", 0.0))
    if stress_val >= 0.7 or anxiety_val >= 0.7 or sadness_val >= 0.7:
        return True, "emotion"

    return False, None


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
            try:
                await db.refresh(conversation)
                await db.refresh(user_msg)
            except Exception:
                pass
            logger.info(f"[DB COMMIT SUCCESS] User message (id={getattr(user_msg, 'id', 'N/A')}) and Conversation (id={getattr(conversation, 'id', 'N/A')}) successfully saved.")
        except Exception as commit_err:
            logger.error(f"[DB COMMIT ERROR] Failed to save conversation/user message to DB: {commit_err}. Queueing async recovery.", exc_info=True)
            await db.rollback()
            await write_queue.add_task(
                async_save_message,
                conversation_id=conversation_id_resolved,
                user_id=current_user.id,
                role=MessageRole.user,
                content=body.message
            )

        # ---------------------------------------------------------------
        # NON-BLOCKING ONBOARDING ROUTING
        # Priority 1: Crisis detection  → bypass onboarding, run pipeline
        # Priority 2: Free-form message → auto-complete, run pipeline
        # Priority 3: Looks like an onboarding answer → save silently,
        #             then STILL run the full agent pipeline (non-blocking)
        # ---------------------------------------------------------------
        if not current_user.onboarding_completed:
            from app.services.onboarding_service import onboarding_service
            profile_res = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
            profile = profile_res.scalar_one_or_none()

            is_crisis = onboarding_service.is_crisis_message(body.message)
            is_free_form = onboarding_service.is_free_form_message(body.message)

            if is_crisis:
                # CRISIS: auto-complete onboarding immediately, fall through to agent pipeline
                logger.warning(f"[ONBOARDING CRISIS] Crisis message detected for user {current_user.id}. Bypassing onboarding.")
                await onboarding_service.auto_complete_onboarding(db, current_user, profile)
                await db.commit()
            elif is_free_form:
                # FREE-FORM: user is having a real conversation, auto-complete onboarding
                logger.info(f"[ONBOARDING FREE-FORM] Free-form message detected. Auto-completing onboarding for user {current_user.id}.")
                await onboarding_service.auto_complete_onboarding(db, current_user, profile)
                await db.commit()
            else:
                # STRUCTURED ANSWER: save silently, but DO NOT block — fall through to pipeline
                if profile:
                    stage = (profile.personality_profile or {}).get("onboarding_stage", 1)
                    try:
                        await onboarding_service.parse_and_save_answer(db, current_user, profile, stage, body.message)
                        await db.commit()
                        logger.info(f"[ONBOARDING SILENT SAVE] Saved answer for stage {stage} for user {current_user.id}.")
                    except Exception as ob_err:
                        logger.warning(f"[ONBOARDING SILENT SAVE] Failed to save onboarding answer: {ob_err}")
                        await db.rollback()
            # Re-read onboarding_completed in case auto_complete_onboarding updated it
            await db.refresh(current_user)


        # 4. Build context for agents
        logger.info(f"[CONTEXT] Loading conversation history for id={conversation_id_resolved}...")
        history = await _build_conversation_history(db, conversation_id_resolved)
        logger.info(f"[CONTEXT] Loaded {len(history)} messages from history.")
        
        logger.info(f"[CONTEXT] Loading user emotional profile...")
        emotional_profile = await _get_emotional_profile_dict(db, current_user.id, current_user.name)
        logger.info(f"[CONTEXT] Profile loaded successfully.")

        # 5. Run agent graph
        logger.info(f"[AI AGENT] Running multi-agent cognitive graph for user message...")

        specialist_id = None
        specialist_response = None
        suggested_specialist = None

        try:
            # Run Esona (Buddy) cognitive graph directly
            result = await run_agent_graph(
                user_message=body.message,
                user_id=str(current_user.id),
                conversation_history=history,
                emotional_profile=emotional_profile,
                conversation_id=conversation_id_resolved,
                db=db,
            )

            logger.info(f"[AI AGENT SUCCESS] Multi-agent processing complete.")
            full_response = result.get("response", "I'm here for you. Could you tell me more?")
            detected_emotion = result.get("detected_emotion", None)
            mood_score = result.get("mood_score", None)
            agent_analysis = result.get("agent_analysis", {})

        except Exception as agent_err:
            logger.error(f"[AI AGENT ERROR] Multi-agent execution failed: {agent_err}. Falling back to randomized human reply.", exc_info=True)
            full_response = get_random_human_fallback()
            detected_emotion = "neutral"
            mood_score = 0.5
            agent_analysis = {}
            result = {}
        
        confidence_score = result.get("detected_emotion_confidence", 1.0)
        e_data = result.get("emotion_agent", {})
        stress_score = e_data.get("stress", 0.0)
        anxiety_score = e_data.get("anxiety", 0.0)
        
        # Update user's message with emotion classification details
        user_msg.emotion = detected_emotion
        user_msg.emotion_score = confidence_score
        user_msg.stress_score = stress_score
        user_msg.anxiety_score = anxiety_score
        user_msg.emotional_context = {"emotion": detected_emotion, "confidence": confidence_score}
        db.add(user_msg)
        
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
                    memory_type=mem_extraction.get("memory_type"),
                    importance_score=mem_extraction.get("importance_score"),
                )
                logger.info(f"[DB INSERT SUCCESS] Memory stored successfully.")
            else:
                logger.info(f"[MEMORY] Skip storing memory: conversation was small talk.")
        except Exception as mem_err:
            logger.error(f"[MEMORY ERROR] Failed to save memory: {mem_err}", exc_info=True)

        # 8. Save assistant messages and mood logs to DB
        logger.info(f"[DB INSERT] Saving AI response and Mood logs to database...")
        logger.info(f"[TYPE LOG] send_message assistant: conversation_id type: {type(conversation_id_resolved)}, value: {conversation_id_resolved}")
        logger.info(f"[TYPE LOG] send_message assistant: user_id type: {type(current_user.id)}, value: {current_user.id}")
        try:
            # 8a. If specialist responded, save specialist message
            if specialist_id and specialist_response:
                spec_msg = Message(
                    conversation_id=conversation_id_resolved,
                    user_id=current_user.id,
                    role=MessageRole.assistant,
                    content=specialist_response,
                    sender_type=specialist_id,
                    emotion=detected_emotion,
                    emotion_score=confidence_score,
                    stress_score=stress_score,
                    anxiety_score=anxiety_score,
                )
                db.add(spec_msg)

            # 8b. Save Buddy message
            assistant_msg = None
            if full_response is not None:
                assistant_msg = Message(
                    conversation_id=conversation_id_resolved,
                    user_id=current_user.id,
                    role=MessageRole.assistant,
                    content=full_response,
                    sender_type="buddy",
                    emotion_detected=detected_emotion,
                    mood_score=mood_score,
                    agent_analysis=agent_analysis,
                    emotion=detected_emotion,
                    emotion_score=confidence_score,
                    stress_score=stress_score,
                    anxiety_score=anxiety_score,
                    emotional_context={"emotion": detected_emotion, "confidence": confidence_score},
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

            # Trigger memory reflection every 10 user messages
            try:
                num_user = sum(1 for m in history if m.get("role") == "user")
                if num_user > 0 and num_user % 10 == 0:
                    logger.info(f"[DB CONTEXT] Triggering memory reflection for user {current_user.id} (user messages: {num_user})...")
                    from app.services.memory_service import memory_service
                    await memory_service.reflect_and_consolidate_memories(db, current_user.id)
            except Exception as ref_err:
                logger.error(f"[REFLECTION ERROR] Reflection failed: {ref_err}", exc_info=True)

            # Commit assistant messages + mood logs
            await db.commit()
            if assistant_msg:
                try:
                    await db.refresh(assistant_msg)
                except Exception:
                    pass
            logger.info(f"[DB COMMIT SUCCESS] AI response and MoodLog saved successfully.")
        except Exception as db_err:
            logger.error(f"[DB COMMIT ERROR] Failed to save assistant message/mood log: {db_err}. Queueing async recovery.", exc_info=True)
            await db.rollback()
            if specialist_id and specialist_response:
                await write_queue.add_task(
                    async_save_message,
                    conversation_id=conversation_id_resolved,
                    user_id=current_user.id,
                    role=MessageRole.assistant,
                    content=specialist_response,
                    sender_type=specialist_id
                )
            if full_response is not None:
                await write_queue.add_task(
                    async_save_message,
                    conversation_id=conversation_id_resolved,
                    user_id=current_user.id,
                    role=MessageRole.assistant,
                    content=full_response,
                    emotion_detected=detected_emotion,
                    mood_score=mood_score,
                    agent_analysis=agent_analysis,
                    sender_type="buddy"
                )
            await write_queue.add_task(
                async_save_mood_log,
                user_id=current_user.id,
                mood_score=mood_score,
                mood_label=detected_emotion,
                dims=result.get("emotion_dimensions", {}) if 'result' in locals() and result else {}
            )

        return {
            "response": full_response,
            "emotionDetected": detected_emotion,
            "moodScore": mood_score,
            "emotionScore": confidence_score,
            "stressScore": stress_score,
            "anxietyScore": anxiety_score,
            "agentAnalysis": agent_analysis,
            "specialistResponse": specialist_response,
            "specialistId": specialist_id,
            "suggestedSpecialist": suggested_specialist,
            "specialistActionEvent": specialist_action_event,
        }

    except Exception as route_err:
        logger.error(f"[API ERROR] Global failure in send_message endpoint: {route_err}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="I encountered an internal server error. Please try again in a moment.",
        )


def classify_message_complexity(message: str) -> str:
    msg = (message or "").lower().strip()
    import re
    msg_clean = re.sub(r"[^\w\s]", "", msg).strip()
    words = msg_clean.split()
    
    # 1. SAFETY_CRITICAL
    crisis_keywords = {
        "want to die", "kill myself", "end my life", "suicide", "self-harm",
        "self harm", "end it all", "hurting myself", "hurt myself", "painful to exist", 
        "sleep forever", "no point in living", "planning to end it", 
        "want to sleep and never wake up", "dont want to exist", "live anymore",
        "end life", "suicidal", "kill me"
    }
    if any(keyword in msg_clean or keyword in msg for keyword in crisis_keywords):
        return "SAFETY_CRITICAL"
        
    # 2. FAST_SOCIAL
    social_words = {
        "hi", "hello", "hey", "hola", "yo", "sup", "buddy", "esona",
        "yes", "no", "ok", "okay", "cool", "nice", "fine", "lol", "lmao",
        "haha", "bro", "dude", "thanks", "thank you", "bye", "goodbye",
        "how are you", "hows it going", "whats up", "what up", "yeah", "yep",
        "agree", "indeed", "good morning", "good night", "sweet dreams", "take care",
        "awesome", "great", "perfect", "understood", "sure", "of course"
    }
    if len(words) <= 3 and (not words or all(w in social_words for w in words)):
        return "FAST_SOCIAL"
        
    # 3. EMOTIONAL_SUPPORT
    emotional_keywords = {
        "tired", "long day", "feeling low", "feel low", "lonely", "feel lonely",
        "stressed", "feel stressed", "cant focus", "cant concentrate", "sad", "feeling sad",
        "not feeling great", "not feeling good", "anxious", "feel anxious", "down", "feeling down",
        "exhausted", "overwhelmed", "worry", "worried", "unhappy", "depressed", "scared", "afraid",
        "angry", "mad", "pissed", "hurt", "crying", "cry", "hate", "stress", "anxiety", "panic"
    }
    if any(w in emotional_keywords for w in words) or (len(words) <= 8 and any(w in emotional_keywords for w in words)):
        return "EMOTIONAL_SUPPORT"
        
    # 4. DEEP_PERSONAL
    deep_keywords = {
        "relationship", "parents", "mom", "dad", "family", "friend", "girlfriend", "boyfriend",
        "future", "career", "life", "meaning", "existential", "pattern", "always do this",
        "childhood", "past", "memory", "reminds me", "scared of", "fear", "dream", "goal",
        "failure", "fail", "regret", "love", "marry", "divorce", "loneliness", "death"
    }
    if any(w in deep_keywords for w in words):
        return "DEEP_PERSONAL"
        
    # Default is NORMAL_CHAT
    return "NORMAL_CHAT"


async def save_chat_response_to_db(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    user_message: str,
    full_response: str,
    detected_emotion: str,
    confidence_score: float,
    stress_score: float,
    anxiety_score: float,
    mood_score: float,
    agent_analysis: dict,
    emotion_dimensions: dict,
    is_first_message: bool,
):
    try:
        async with get_db_session() as db:
            # 1. Update user message emotion details
            user_msg_res = await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.role == MessageRole.user
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            user_msg = user_msg_res.scalar_one_or_none()
            if user_msg:
                user_msg.emotion = detected_emotion
                user_msg.emotion_score = confidence_score
                user_msg.stress_score = stress_score
                user_msg.anxiety_score = anxiety_score
                user_msg.emotional_context = {"emotion": detected_emotion, "confidence": confidence_score}
                db.add(user_msg)

            # 2. Save assistant message
            assistant_msg = Message(
                conversation_id=conversation_id,
                user_id=user_id,
                role=MessageRole.assistant,
                content=full_response,
                sender_type="buddy",
                emotion_detected=detected_emotion,
                mood_score=mood_score,
                agent_analysis=agent_analysis,
                emotion=detected_emotion,
                emotion_score=confidence_score,
                stress_score=stress_score,
                anxiety_score=anxiety_score,
                emotional_context={"emotion": detected_emotion, "confidence": confidence_score},
            )
            db.add(assistant_msg)

            # 3. Save mood log
            mood_log = MoodLog(
                user_id=user_id,
                mood_score=mood_score,
                mood_label=detected_emotion,
                detected_emotion=detected_emotion,
                stress=emotion_dimensions.get("stress", 0.3),
                happiness=emotion_dimensions.get("happiness", 0.5),
                sadness=emotion_dimensions.get("sadness", 0.3),
                anxiety=emotion_dimensions.get("anxiety", 0.3),
                motivation=emotion_dimensions.get("motivation", 0.5),
                confidence=emotion_dimensions.get("confidence", 0.5),
            )
            db.add(mood_log)

            # 4. Update conversation title if needed
            conversation_res = await db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = conversation_res.scalar_one_or_none()
            if conversation:
                conversation.emotional_tag = detected_emotion
                conversation.updated_at = datetime.now(timezone.utc)
                if is_first_message:
                    try:
                        title_msgs = [
                            {"role": "user", "content": user_message},
                            {"role": "assistant", "content": full_response}
                        ]
                        conversation.title = await generate_chat_title_llm(title_msgs)
                    except Exception:
                        conversation.title = generate_emotional_title(user_message, detected_emotion)
                db.add(conversation)

            await db.commit()
            logger.info(f"[BG SAVE SUCCESS] Saved assistant message and logs for conversation_id={conversation_id}")
    except Exception as e:
        logger.error(f"[BG SAVE ERROR] Failed to save message: {e}", exc_info=True)


async def generate_and_persist_sse_response(
    message: str,
    current_user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    history: list[dict],
    emotional_profile: dict,
) -> dict:
    """
    Runs the agent graph, generates the response, updates/saves the chat message,
    mood logs, conversation metadata, and memory asynchronously using a fresh DB session.
    """
    logger.info(f"[SSE PERSIST] Starting background processing for conversation_id={conversation_id}")
    
    async with get_db_session() as db:
        try:
            conversation_res = await db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user_id
                )
            )
            conversation = conversation_res.scalar_one_or_none()

            specialist_id = None
            specialist_response = None
            suggested_specialist = None
            sse_specialist_action_event = None

            # Run Esona (Buddy) cognitive graph directly
            result = await run_agent_graph(
                user_message=message,
                user_id=str(current_user_id),
                conversation_history=history,
                emotional_profile=emotional_profile,
                conversation_id=conversation_id,
                db=db,
            )

            logger.info(f"[SSE AI SUCCESS] Agent processing complete.")
            full_response = result.get("response", "I'm here for you. Could you tell me more?")
            detected_emotion = result.get("detected_emotion", None)
            mood_score = result.get("mood_score", None)
            agent_analysis = result.get("agent_analysis", {})

        except Exception as agent_err:
            logger.error(f"[SSE AI ERROR] Agent graph execution failed: {agent_err}. Falling back to randomized human reply.", exc_info=True)
            full_response = get_random_human_fallback()
            detected_emotion = "neutral"
            mood_score = 0.5
            agent_analysis = {}
            result = {}
            
        confidence_score = result.get("detected_emotion_confidence", 1.0)
        e_data = result.get("emotion_agent", {})
        stress_score = e_data.get("stress", 0.0)
        anxiety_score = e_data.get("anxiety", 0.0)
        
        # Update user's message with emotion details
        try:
            user_msg_res = await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.role == MessageRole.user
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            user_msg = user_msg_res.scalar_one_or_none()
            if user_msg:
                user_msg.emotion = detected_emotion
                user_msg.emotion_score = confidence_score
                user_msg.stress_score = stress_score
                user_msg.anxiety_score = anxiety_score
                user_msg.emotional_context = {"emotion": detected_emotion, "confidence": confidence_score}
                db.add(user_msg)
        except Exception as update_user_msg_err:
            logger.warning(f"Failed to update user message with emotion details: {update_user_msg_err}")

        # If conversation is missing, create a temp mock
        if not conversation:
            try:
                conversation = Conversation(id=conversation_id, user_id=current_user_id, title="New Conversation")
                db.add(conversation)
                await db.flush()
            except Exception as create_err:
                logger.error(f"[SSE DB ERROR] Failed to recreate missing conversation: {create_err}")

        # 3. Update title if first message
        if len(history) <= 1 and conversation:
            try:
                logger.info(f"[SSE TITLE] Generating title for new conversation...")
                title_msgs = [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": full_response}
                ]
                conversation.title = await generate_chat_title_llm(title_msgs)
                logger.info(f"[SSE TITLE SUCCESS] Title set: '{conversation.title}'")
            except Exception as title_err:
                logger.warning(f"[SSE TITLE WARNING] LLM title failed: {title_err}. Falling back to default.")
                conversation.title = generate_emotional_title(message, detected_emotion or "neutral")

        # 4. Save assistant messages and mood logs
        specialist_msg_id = None
        try:
            # 4a. Save specialist message
            if specialist_id and specialist_response:
                spec_msg = Message(
                    conversation_id=conversation_id,
                    user_id=current_user_id,
                    role=MessageRole.assistant,
                    content=specialist_response,
                    sender_type=specialist_id,
                    emotion=detected_emotion,
                    emotion_score=confidence_score,
                    stress_score=stress_score,
                    anxiety_score=anxiety_score,
                )
                db.add(spec_msg)
                await db.flush()
                specialist_msg_id = str(spec_msg.id)

            # 4b. Save Buddy message
            assistant_msg = None
            if full_response is not None:
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    user_id=current_user_id,
                    role=MessageRole.assistant,
                    content=full_response,
                    sender_type="buddy",
                    emotion_detected=detected_emotion,
                    mood_score=mood_score,
                    agent_analysis=agent_analysis,
                    emotion=detected_emotion,
                    emotion_score=confidence_score,
                    stress_score=stress_score,
                    anxiety_score=anxiety_score,
                    emotional_context={"emotion": detected_emotion, "confidence": confidence_score},
                )
                db.add(assistant_msg)

            # Save mood log
            dims = result.get("emotion_dimensions", {})
            mood_log = MoodLog(
                user_id=current_user_id,
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

            if conversation:
                if detected_emotion:
                    conversation.emotional_tag = detected_emotion
                conversation.updated_at = datetime.now(timezone.utc)
                db.add(conversation)

            # 5. Commit everything
            await db.commit()
            logger.info(f"[SSE DB SUCCESS] Background save successful for conversation_id={conversation_id}")
        except Exception as commit_err:
            logger.error(f"[SSE DB COMMIT ERROR] Failed to save background SSE updates: {commit_err}. Queueing async recovery.", exc_info=True)
            await db.rollback()
            if specialist_id and specialist_response:
                await write_queue.add_task(
                    async_save_message,
                    conversation_id=conversation_id,
                    user_id=current_user_id,
                    role=MessageRole.assistant,
                    content=specialist_response,
                    sender_type=specialist_id
                )
            await write_queue.add_task(
                async_save_message,
                conversation_id=conversation_id,
                user_id=current_user_id,
                role=MessageRole.assistant,
                content=full_response,
                emotion_detected=detected_emotion,
                mood_score=mood_score,
                agent_analysis=agent_analysis,
                sender_type="buddy"
            )
            await write_queue.add_task(
                async_save_mood_log,
                user_id=current_user_id,
                mood_score=mood_score,
                mood_label=detected_emotion,
                dims=dims
            )

        return {
            "specialist_response": specialist_response,
            "specialist_id": specialist_id,
            "specialist_message_id": specialist_msg_id,
            "full_response": full_response,
            "detected_emotion": detected_emotion,
            "mood_score": mood_score,
            "emotion_score": confidence_score,
            "stress_score": stress_score,
            "anxiety_score": anxiety_score,
            "agent_analysis": agent_analysis,
            "message_id": str(assistant_msg.id) if (assistant_msg is not None and hasattr(assistant_msg, "id")) else str(uuid.uuid4()),
            "suggested_specialist": suggested_specialist,
            "specialist_action_event": sse_specialist_action_event,
            "agent_result": result,
        }


async def run_background_learning_tasks(
    user_id: uuid.UUID,
    user_message: str,
    assistant_response: str,
    conversation_id: uuid.UUID,
    history: list[dict],
    detected_emotion: str,
    agent_result: dict,
):
    """Runs all non-critical learning and DB writes in the background using a fresh database session."""
    logger.info(f"[BACKGROUND LEARNING] Starting background learning tasks for user_id={user_id}")
    async with get_db_session() as db:
        try:
            # 1. Profile Fact Extraction and update db
            try:
                from app.services.profile_service import profile_service
                await profile_service.extract_and_update_profile_facts(db, user_id, user_message)
                await db.commit()
            except Exception as fact_err:
                logger.error(f"[BACKGROUND] Profile fact extraction failed: {fact_err}")

            # 2. Knowledge Graph Extraction and storage
            try:
                from app.services.knowledge_graph_service import knowledge_graph_service
                profile_context = agent_result.get("emotional_profile", {})
                user_name = profile_context.get("user_name", "User") or "User"
                extracted_graph = await knowledge_graph_service.extract_relationships(user_message, user_name=user_name)
                
                if isinstance(extracted_graph, list):
                    extracted_graph = {
                        "entities": [],
                        "relationships": [],
                        "events": [],
                        "relations": extracted_graph
                    }
                if detected_emotion and detected_emotion != "Neutral":
                    if "events" not in extracted_graph:
                        extracted_graph["events"] = []
                    extracted_graph["events"].append({
                        "event": "current_feeling",
                        "emotion": detected_emotion
                    })
                await knowledge_graph_service.store_graph_data(db, user_id, extracted_graph)
                await db.commit()
            except Exception as kg_err:
                logger.error(f"[BACKGROUND] KG extraction/storage failed: {kg_err}")

            # 3. Memory extraction and storage
            try:
                from app.services.memory_service import memory_service
                mem_extraction = agent_result.get("memory_extraction", {})
                if mem_extraction.get("is_meaningful"):
                    logger.info(f"[BACKGROUND] Storing memory: '{mem_extraction.get('memory_summary', '')[:80]}'...")
                    await memory_service.saveMemory(
                        db=db,
                        user_id=str(user_id),
                        memory_summary=mem_extraction.get("memory_summary"),
                        behavior_patterns=mem_extraction.get("behavior_patterns") or {},
                        memory_type=mem_extraction.get("memory_type"),
                        importance_score=mem_extraction.get("importance_score"),
                    )
                    await db.commit()
            except Exception as mem_err:
                logger.error(f"[BACKGROUND] Memory storage failed: {mem_err}")

            # 4. Memory pruning
            try:
                from app.services.memory_service import memory_service
                await memory_service.prune_expired_memories(db, user_id)
                await db.commit()
            except Exception as prune_err:
                logger.error(f"[BACKGROUND] Memory pruning failed: {prune_err}")

            # 5. Hybrid Gemini Emotion Log generation and db save (updates/overwrites mood logs if needed)
            try:
                from app.services.emotion_service import emotion_service
                await emotion_service.classify_emotion_mentalbert(
                    db=db,
                    user_id=str(user_id),
                    message=user_message,
                    conversation_id=str(conversation_id),
                    history=history,
                    memories=agent_result.get("memories", []),
                    graph_relationships=agent_result.get("graph_relationships", [])
                )
                await db.commit()
            except Exception as gemini_emo_err:
                logger.error(f"[BACKGROUND] Hybrid Gemini Emotion Classifier failed: {gemini_emo_err}")

            # 6. Thread summary check and store
            if len(history) >= 12 and len(history) % 6 == 0:
                try:
                    await summarize_and_store_conversation(db, user_id, conversation_id, history)
                    await db.commit()
                except Exception as sum_err:
                    logger.error(f"[BACKGROUND] Thread summarization failed: {sum_err}")

            # 7. Memory reflection check and reflect
            try:
                num_user = sum(1 for m in history if m.get("role") == "user")
                if num_user > 0 and num_user % 10 == 0:
                    from app.services.memory_service import memory_service
                    await memory_service.reflect_and_consolidate_memories(db, user_id)
                    await db.commit()
            except Exception as ref_err:
                logger.error(f"[BACKGROUND] Memory reflection failed: {ref_err}")
            logger.info(f"[BACKGROUND LEARNING SUCCESS] Finished background learning tasks successfully.")
        except Exception as bg_outer_err:
            logger.error(f"[BACKGROUND OUTER ERROR] Background tasks failed: {bg_outer_err}", exc_info=True)
@router.get("/{conversation_id}/stream")
async def stream_message_sse(
    conversation_id: uuid.UUID,
    message: str,
    token: str,
    background_tasks: BackgroundTasks,
    client_message_id: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    GET endpoint for Server-Sent Events (SSE) streaming of chat responses.
    Allows browsers to connect natively using the standard EventSource API.
    """
    print("CHAT REQUEST RECEIVED")
    logger.info(f"[API SSE] stream_message_sse request received: conversation_id={conversation_id}, client_message_id={client_message_id}")
    
    try:
        # 1. Authenticate token using jwt payload
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
        except Exception as auth_err:
            logger.error(f"[AUTH SSE ERROR] JWT validation failed: {auth_err}")
            raise credentials_exception
 
        # Load user from profiles table
        result = await db.execute(select(User).where(User.id == user_id))
        current_user = result.scalar_one_or_none()
        if current_user is None:
            logger.info(f"[AUTH SSE] User profile not found in DB for user_id={user_id}. Auto-creating...")
            try:
                user_meta = payload.get("user_metadata", {}) if payload else {}
                onboarding_completed_meta = bool(user_meta.get("onboarding_completed", False))
                avatar_url = user_meta.get("avatar_url") or user_meta.get("picture") or None
                
                provider = "credentials"
                if payload:
                    provider = payload.get("app_metadata", {}).get("provider", "credentials")
                    
                github_username = user_meta.get("user_name") if provider == "github" else None
                name = user_meta.get("full_name") or user_meta.get("name") or None
                email = payload.get("email", "")
                
                if email:
                    result_email = await db.execute(select(User).where(User.email == email))
                    existing_user_by_email = result_email.scalar_one_or_none()
                    if existing_user_by_email and existing_user_by_email.id != user_id:
                        logger.warning(f"[AUTH SSE] Conflict detected: email {email} registered under old user_id {existing_user_by_email.id}. Deleting old profile...")
                        await db.delete(existing_user_by_email)
                        await db.flush()
                
                if not name:
                    name = email.split("@")[0] or "Buddy User"
                    
                current_user = User(
                    id=user_id,
                    user_id=user_id,
                    email=email,
                    name=name,
                    avatar_url=avatar_url,
                    provider=provider,
                    github_username=github_username,
                    onboarding_completed=onboarding_completed_meta,
                )
                db.add(current_user)
                await db.commit()
                result = await db.execute(select(User).where(User.id == user_id))
                current_user = result.scalar_one()
                logger.info(f"[AUTH SSE SUCCESS] Auto-created user details: id={current_user.id}, email={current_user.email}")
            except Exception as auto_err:
                logger.error(f"[AUTH SSE ERROR] Failed to auto-create user profile: {auto_err}", exc_info=True)
                await db.rollback()
                raise credentials_exception
        else:
            logger.info(f"[AUTH SSE SUCCESS] Authenticated user details: id={current_user.id}, email={current_user.email}")
 
        # 2. Get the conversation
        conversation = await _get_or_create_conversation(db, current_user.id, conversation_id)
        conversation_id_resolved = conversation.id
 
        # 3. Save the user's message
        logger.info(f"[DB INSERT SSE] Saving User message: conversation_id={conversation_id_resolved}, user_id={current_user.id}")
        existing_user_msg = None
        existing_assistant_msg = None
        try:
            # Deduplicate by client_message_id if provided
            if client_message_id:
                dedup_result = await db.execute(
                    select(Message).where(
                        and_(
                            Message.conversation_id == conversation_id_resolved,
                            Message.role == MessageRole.user,
                        )
                    ).order_by(Message.created_at.desc()).limit(1)
                )
                candidate = dedup_result.scalar_one_or_none()
                if candidate and candidate.emotional_context and candidate.emotional_context.get("client_message_id") == client_message_id:
                    existing_user_msg = candidate
                    logger.info(f"[SSE DEDUP] Duplicate message detected (client_message_id={client_message_id}). Checking for processed response.")
                    
                    # Find assistant response that followed this duplicate user message
                    assist_result = await db.execute(
                        select(Message).where(
                            and_(
                                Message.conversation_id == conversation_id_resolved,
                                Message.role == MessageRole.assistant,
                                Message.created_at >= existing_user_msg.created_at
                            )
                        ).order_by(Message.created_at.asc()).limit(1)
                    )
                    existing_assistant_msg = assist_result.scalar_one_or_none()

            if existing_user_msg:
                user_msg = existing_user_msg
            else:
                user_msg = Message(
                    conversation_id=conversation_id_resolved,
                    user_id=current_user.id,
                    role=MessageRole.user,
                    content=message,
                    emotional_context={"client_message_id": client_message_id} if client_message_id else None,
                )
                db.add(user_msg)
                conversation.updated_at = datetime.now(timezone.utc)
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                await db.refresh(user_msg)
                logger.info(f"[DB COMMIT SSE SUCCESS] Saved user message: {user_msg.id}")
        except Exception as db_msg_err:
            logger.error(f"[DB COMMIT SSE ERROR] Failed to save user message: {db_msg_err}", exc_info=True)
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to save user message")

        # ---------------------------------------------------------------
        # NON-BLOCKING ONBOARDING ROUTING (SSE)
        # ---------------------------------------------------------------
        if not current_user.onboarding_completed:
            from app.services.onboarding_service import onboarding_service
            profile_res = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
            profile = profile_res.scalar_one_or_none()

            is_crisis = onboarding_service.is_crisis_message(message)
            is_free_form = onboarding_service.is_free_form_message(message)

            if is_crisis:
                logger.warning(f"[ONBOARDING SSE CRISIS] Crisis detected for user {current_user.id}. Bypassing onboarding.")
                await onboarding_service.auto_complete_onboarding(db, current_user, profile)
                await db.commit()
            elif is_free_form:
                logger.info(f"[ONBOARDING SSE FREE-FORM] Auto-completing onboarding for user {current_user.id}.")
                await onboarding_service.auto_complete_onboarding(db, current_user, profile)
                await db.commit()
            else:
                if profile:
                    stage = (profile.personality_profile or {}).get("onboarding_stage", 1)
                    try:
                        await onboarding_service.parse_and_save_answer(db, current_user, profile, stage, message)
                        await db.commit()
                        logger.info(f"[ONBOARDING SSE SILENT SAVE] Saved answer for stage {stage}.")
                    except Exception as ob_err:
                        logger.warning(f"[ONBOARDING SSE SILENT SAVE] Failed: {ob_err}")
                        await db.rollback()

        # 4. Event generator for Starlette SSE EventSourceResponse
        async def event_generator() -> AsyncGenerator[dict, None]:
            import asyncio
            import time
            perf_logger = logging.getLogger("ESONA_CHAT_PERF")
            
            trace_id = uuid.uuid4().hex[:8]
            start_time = time.perf_counter()
            logger.info(f"[CHAT PERF][trace={trace_id}] request_received +0ms")

            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "connected",
                    "trace_id": trace_id,
                    "conversation_id": str(conversation_id_resolved),
                }),
            }
            logger.info(f"[CHAT PERF][trace={trace_id}] sse_connected +{int((time.perf_counter() - start_time) * 1000)}ms")

            # Handle replay deduplication directly
            if existing_assistant_msg:
                logger.info(f"[SSE REPLAY] Streaming existing response for trace={trace_id}")
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "status", "stage": "responding"}),
                }
                
                content = existing_assistant_msg.content or ""
                chunk_size = 4
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "chunk",
                            "content": chunk,
                            "conversation_id": str(conversation_id_resolved),
                        }),
                    }
                    await asyncio.sleep(0.005)

                emo = existing_assistant_msg.emotion_detected or "neutral"
                mood = existing_assistant_msg.mood_score or 0.9
                
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "done",
                        "message_id": str(existing_assistant_msg.id),
                        "conversation_id": str(conversation_id_resolved),
                        "emotion_detected": emo,
                        "mood_score": mood,
                        "emotion_score": 1.0,
                        "stress_score": 0.1,
                        "anxiety_score": 0.1,
                        "agent_analysis": {},
                    }),
                }
                
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                perf_logger.info(
                    f"[ESONA_CHAT_PERF] category=REPLAY trace_id={trace_id} total_ms={duration_ms} "
                    f"client_message_id={client_message_id}"
                )
                return

            # Default values to prevent unbound errors
            detected_emotion = "neutral"
            confidence_score = 1.0
            stress_score = 0.1
            anxiety_score = 0.1
            mood_score = 0.9
            user_signal = None
            response_plan = None
            
            # Yield understanding status
            yield {
                "event": "message",
                "data": json.dumps({"type": "status", "stage": "understanding"}),
            }

            # Classify message complexity (FAST_SOCIAL, NORMAL_CHAT, EMOTIONAL_SUPPORT, DEEP_PERSONAL, SAFETY_CRITICAL)
            category = classify_message_complexity(message)
            logger.info(f"[CHAT PERF][trace={trace_id}] complexity_classified +{int((time.perf_counter() - start_time) * 1000)}ms category={category}")

            try:
                # We need a db session to load profile & history
                async with get_db_session() as s_db:
                    p_start = time.perf_counter()
                    from app.services.profile_service import profile_service
                    
                    try:
                        emotional_profile = await _get_emotional_profile_dict(s_db, current_user.id, current_user.name)
                    except Exception as e:
                        logger.warning(f"Failed to load emotional profile: {e}")
                        emotional_profile = {}
                        
                    try:
                        personalization_block = await profile_service.build_personalization_prompt_block(s_db, current_user.id)
                    except Exception as e:
                        logger.warning(f"Failed to load personalization block: {e}")
                        personalization_block = ""
                    profile_context = personalization_block
                    logger.info(f"[CHAT PERF][trace={trace_id}] personalization_complete +{int((time.perf_counter() - start_time) * 1000)}ms duration={int((time.perf_counter() - p_start) * 1000)}ms")

                    # Length Matching Calculations
                    user_words = message.strip().split()
                    length_constraint = ""
                    if len(user_words) <= 3:
                        length_constraint = "Keep response extremely brief (1 short sentence, max 12 words) and conversational."
                    elif len(user_words) <= 7:
                        length_constraint = "Keep response brief (1-2 sentences, max 20 words)."
                    else:
                        length_constraint = "Keep response natural and concise (2-3 sentences, max 35 words)."

                    if category == "SAFETY_CRITICAL":
                        detected_emotion = "Crisis"
                        confidence_score = 0.95
                        mood_score = 0.05
                        stress_score = 0.95
                        anxiety_score = 0.95
                        
                        system_prompt = (
                            "Activate Buddy Crisis Support Protocol. Focus on validating pain, sharing safety hotlines (e.g. Vandrevala Foundation or AASRA), staying grounded, and being direct. Strictly no humor.\n"
                            "Write warm, empathetic, and direct lowercase WhatsApp style texts under 4 sentences."
                        )
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": message}
                        ]

                    elif category == "FAST_SOCIAL":
                        # Bypasses history, memories, graph, and agents logic. Max speed!
                        system_prompt = (
                            "You are Esona (also known as Buddy), a supportive, relatable college friend. "
                            "Strictly adopt the following user personalization guidelines:\n"
                            f"{personalization_block}\n\n"
                            "CRITICAL RESPONSE STYLE CONSTRAINTS:\n"
                            "- Write like a real close friend texting on WhatsApp.\n"
                            "- Write mostly in lowercase, warm, natural, and empathetic.\n"
                            "- Keep response extremely short (1 to 2 sentences max, under 20 words).\n"
                            "- Omit terminal punctuation.\n"
                            "- Use casual abbreviations naturally (like ngl, idk, fr, tbh, bro, 😭, 💀) but do not force them.\n"
                            "- Do NOT use any <reasoning> or <thinking> tags.\n"
                            f"- {length_constraint}\n"
                        )
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": message}
                        ]

                    elif category == "NORMAL_CHAT":
                        # Bypasses heavy agents. Safe GETs for context.
                        history = await _build_conversation_history(s_db, conversation_id_resolved, limit=6)
                        
                        from app.services.emotional_intelligence import build_user_signal, select_response_strategy
                        personalization = emotional_profile.get("personality_profile", {})
                        user_signal = build_user_signal(
                            user_message=message,
                            history=history,
                            personalization=personalization
                        )
                        response_plan = select_response_strategy(user_signal, personalization)

                        from app.agents import memory_agent
                        
                        mem_res = await memory_agent.retrieve_context(s_db, str(current_user.id), message, limit=3)
                        memories = mem_res.get("memories", [])
                        memories_str = "\n".join([f"- User once said: '{m.get('content')}'" for m in memories]) if memories else "None."

                        system_prompt = (
                            "You are Esona (also known as Buddy), a supportive, relatable college friend. "
                            "Strictly adopt the following user personalization guidelines:\n"
                            f"{personalization_block}\n\n"
                            f"Relevant Past Memories:\n{memories_str}\n\n"
                            "CRITICAL RESPONSE STYLE CONSTRAINTS:\n"
                            "- Speak like a supportive friend. Validate their feeling naturally, keeping it warm and conversational.\n"
                            "- Write mostly in lowercase, warm, natural, and empathetic.\n"
                            "- Omit terminal punctuation.\n"
                            "- Do NOT use any <reasoning> or <thinking> tags.\n"
                            f"- {length_constraint}\n"
                        )
                        recent_responses = _recent_responses_cache.get(str(current_user.id), [])
                        if recent_responses:
                            system_prompt += f"\n- Avoid repeating these recent phrases: {recent_responses[-3:]}"

                        messages = [{"role": "system", "content": system_prompt}]
                        for h in history:
                            messages.append({"role": h["role"], "content": h["content"]})
                        messages.append({"role": "user", "content": message})

                    else:
                        # EMOTIONAL_SUPPORT / DEEP_PERSONAL Route
                        # Stage: remembering -> retrieve light context
                        yield {
                            "event": "message",
                            "data": json.dumps({"type": "status", "stage": "remembering"}),
                        }

                        history_limit = 8 if category == "EMOTIONAL_SUPPORT" else 12
                        memory_limit = 5
                        kg_limit = 5 if category == "EMOTIONAL_SUPPORT" else 10

                        from app.agents import memory_agent, personality_agent, emotion_agent, behavior_agent, growth_agent, intent_agent, safety_agent
                        from app.services.emotion_service import emotion_service
                        from app.services.knowledge_graph_service import knowledge_graph_service
                        from app.services.emotional_intelligence import mood_trend_tracker

                        async def timed_history():
                            t = time.perf_counter()
                            res = await _build_conversation_history(s_db, conversation_id_resolved, limit=history_limit)
                            logger.info(f"History Retrieval: {int((time.perf_counter() - t)*1000)}ms")
                            return res

                        async def timed_mem():
                            t = time.perf_counter()
                            res = await memory_agent.retrieve_context(s_db, str(current_user.id), message, limit=memory_limit)
                            logger.info(f"Memory Retrieval: {int((time.perf_counter() - t)*1000)}ms")
                            return res

                        async def timed_kg():
                            t = time.perf_counter()
                            try:
                                res = await knowledge_graph_service.retrieve_relevant_relationships(s_db, current_user.id, message)
                            except Exception as e:
                                logger.warning(f"Failed to retrieve KG: {e}")
                                res = []
                            logger.info(f"Knowledge Graph: {int((time.perf_counter() - t)*1000)}ms")
                            return res

                        async def timed_emotion():
                            t = time.perf_counter()
                            res = await emotion_service.classify_emotion_fast(message)
                            logger.info(f"Emotion Analysis: {int((time.perf_counter() - t)*1000)}ms")
                            return res

                        async def timed_trend():
                            t = time.perf_counter()
                            res = await mood_trend_tracker.get_mood_trend(s_db, current_user.id)
                            logger.info(f"Mood Trend: {int((time.perf_counter() - t)*1000)}ms")
                            return res

                        logger.info("Conversation Started")
                        history_task = asyncio.create_task(timed_history())
                        mem_task = asyncio.create_task(timed_mem())
                        kg_task = asyncio.create_task(timed_kg())
                        emotion_task = asyncio.create_task(timed_emotion())
                        trend_task = asyncio.create_task(timed_trend())

                        history, memories_res, kg_res, emotion_res, emotional_trend = await asyncio.gather(
                            history_task, mem_task, kg_task, emotion_task, trend_task
                        )
                        memories = memories_res.get("memories", [])
                        graph_relationships = [f"- {r.subject} -> {r.predicate} -> {r.object}" for r in kg_res[:kg_limit]]

                        detected_emotion = emotion_res.get("detected_emotion", "Neutral")
                        confidence_score = emotion_res.get("confidence_score", 1.0)
                        blended_scores = emotion_res.get("blended_scores", [0.0]*9)

                        # Stage: thinking
                        yield {
                            "event": "message",
                            "data": json.dumps({"type": "status", "stage": "thinking"}),
                        }

                        # Local agent execution (avoid sequential LLM calls)
                        from app.utils.llm import _local_cognitive_analysis
                        mock_analysis_messages = [
                            {"role": "system", "content": "personality_agent emotion_agent memory_extraction"},
                            {"role": "user", "content": f"Classifier result for current message: {detected_emotion}\nCurrent message to analyze: {message}"}
                        ]
                        raw_analysis = _local_cognitive_analysis(mock_analysis_messages)
                        from app.utils.helpers import safe_json_parse
                        analysis = safe_json_parse(raw_analysis)
                        
                        p_data = personality_agent.analyze(analysis)
                        e_data = emotion_agent.analyze(blended_scores)
                        b_data = behavior_agent.analyze(analysis)
                        g_data = growth_agent.analyze(analysis)
                        i_data = intent_agent.analyze(analysis)
                        s_data = safety_agent.check_safety(analysis, message)
                        
                        from app.services.emotional_intelligence import build_user_signal, select_response_strategy
                        from app.services.reasoning_engine import reasoning_engine
                        
                        personalization = emotional_profile.get("personality_profile", {})
                        
                        # State Machine Transition (V3)
                        prev_stage = reasoning_engine.get_previous_stage(history)
                        detected_emotion = emotion_res.get("detected_emotion", "Neutral")
                        stage = reasoning_engine.transition_stage(prev_stage, message, history, detected_emotion)
                        strategy = reasoning_engine.select_strategy_for_stage(stage, detected_emotion, "low" if detected_emotion != "Crisis" else "crisis")
                        
                        user_signal = {
                            "primary_emotion": detected_emotion,
                            "intensity": emotion_res.get("intensity", 5),
                            "conversation_stage": stage,
                            "emotional_trend": emotional_trend
                        }
                        response_plan = {
                            "conversation_stage": stage,
                            "primary_strategy": strategy,
                            "desired_length": "medium" if detected_emotion != "Neutral" else "short",
                            "tone": "empathetic" if detected_emotion.lower() in ["sadness", "frustration"] else "calming"
                        }
                        
                        tone = response_plan["tone"]
                        
                        # Comfort kit if negative emotions
                        comfort_kit_dict = {}
                        from app.services.recommendation_service import recommendation_service
                        if detected_emotion.lower() in recommendation_service.NEGATIVE_EMOTIONS:
                            try:
                                kit = await recommendation_service.build_comfort_kit(
                                    db=s_db,
                                    user_id=str(current_user.id),
                                    detected_emotion=detected_emotion,
                                    graph_relationships=graph_relationships,
                                    personality_profile=emotional_profile.get("personality_profile", {}),
                                )
                                comfort_kit_dict = {
                                    "emotional_trigger": kit.emotional_trigger,
                                    "interests": kit.interests,
                                    "hobbies": kit.hobbies,
                                    "coping_activities": kit.coping_activities,
                                    "comfort_environment": kit.comfort_environment,
                                    "activity_suggestions": kit.activity_suggestions,
                                    "is_empty": kit.is_empty,
                                }
                            except Exception as e:
                                logger.warning(f"Failed to build comfort kit: {e}")
                                comfort_kit_dict = {"is_empty": True}
                            
                        # Retrieve emotion timeline
                        from app.services.mood_tracker import MoodTracker
                        from zoneinfo import ZoneInfo
                        mt = MoodTracker(s_db)
                        try:
                            emotion_timeline = await mt.retrieve_emotion_timeline(current_user.id, days=7)
                        except Exception as e:
                            logger.warning(f"Failed to retrieve emotion timeline: {e}")
                            emotion_timeline = []
                        
                        # Growth insights check
                        growth_insight = None
                        total_msgs = len([m for m in history if m.get("role") == "user"])
                        if total_msgs > 0 and total_msgs % 15 == 0:
                            try:
                                from app.services.growth_insights_service import growth_insights_service
                                growth_insight = await growth_insights_service.get_top_insight_for_chat(s_db, str(current_user.id))
                            except Exception as e:
                                logger.warning(f"Failed to retrieve growth insight: {e}")
                                growth_insight = None
                        
                        # Build system prompt
                        system_prompt = response_orchestrator.build_final_prompt(
                            user_name=current_user.name,
                            personality_profile=emotional_profile.get("personality_profile", {}),
                            personality=p_data,
                            emotion=e_data,
                            behavior=b_data,
                            growth=g_data,
                            memories=memories,
                            tone=tone,
                            strategy=strategy,
                            current_time_str=datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%A, %B %d, %Y %I:%M %p (IST)'),
                            profile_context=profile_context,
                            detected_emotion=detected_emotion,
                            detected_emotion_confidence=confidence_score,
                            graph_relationships=graph_relationships,
                            comfort_kit=comfort_kit_dict,
                            emotion_timeline=emotion_timeline,
                            growth_insight=growth_insight,
                            message_type="emotional",
                            recent_buddy_responses=_recent_responses_cache.get(str(current_user.id), []),
                        )
                        
                        system_prompt += f"\n\n[LENGTH MATCHING CONSTRAINT]: {length_constraint}"
                        recent_responses = _recent_responses_cache.get(str(current_user.id), [])
                        if recent_responses:
                            system_prompt += f"\n\n[ANTI-REPETITION CONSTRAINT]: Avoid repeating the phrasing, style or starting structures of your recent responses: {recent_responses[-3:]}. Choose a different conversational move (e.g. if you asked a question last time, reflect or validate this time instead of asking another question)."

                        messages = [{"role": "system", "content": system_prompt}]
                        summary = await _get_conversation_summary(s_db, str(current_user.id), str(conversation_id_resolved))
                        if summary:
                            messages.append({
                                "role": "system",
                                "content": f"System Note: Here is a summary of the earlier part of this conversation:\n\"{summary}\"\nUse it for context, but do not repeat it verbatim."
                            })
                            
                        # Rolling summary history threshold: if exceeds 10 messages, send summary + last 4 messages
                        if len(history) > 10:
                            history_to_send = history[-4:]
                        else:
                            history_to_send = history
                            
                        for h in history_to_send:
                            messages.append({"role": h["role"], "content": h["content"]})
                        messages.append({"role": "user", "content": message})

                    # Stage: responding
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "status", "stage": "responding"}),
                    }
                    
                    full_response = ""
                    first_chunk = False
                    logger.info(f"[CHAT PERF][trace={trace_id}] llm_started +{int((time.perf_counter() - start_time) * 1000)}ms")
                    
                    if category in ("SAFETY_CRITICAL", "FAST_SOCIAL"):
                        from app.utils.llm import generate_chat_completion_stream_with_fallback
                        async for chunk in generate_chat_completion_stream_with_fallback(
                            messages, 
                            temperature=0.7, 
                            route_category=category
                        ):
                            if not first_chunk:
                                first_chunk = True
                                logger.info(f"[CHAT PERF][trace={trace_id}] llm_first_chunk +{int((time.perf_counter() - start_time) * 1000)}ms")
                            full_response += chunk
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "chunk",
                                    "content": chunk,
                                    "conversation_id": str(conversation_id_resolved),
                                }),
                            }
                    else:
                        from app.agents.response_agent import response_agent
                        gen_res = await response_agent.generate(
                            messages=messages,
                            temperature=0.7,
                            max_tokens=300,
                            recent_responses=recent_responses,
                            user_signal=user_signal,
                            response_plan=response_plan
                        )
                        full_response = gen_res.get("text", "")
                        
                        # Simulate streaming of full_response in small chunks to the frontend UI
                        chunk_size = 8
                        for i in range(0, len(full_response), chunk_size):
                            chunk = full_response[i:i+chunk_size]
                            if not first_chunk:
                                first_chunk = True
                                logger.info(f"[CHAT PERF][trace={trace_id}] llm_first_chunk +{int((time.perf_counter() - start_time) * 1000)}ms")
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "chunk",
                                    "content": chunk,
                                    "conversation_id": str(conversation_id_resolved),
                                }),
                            }
                            await asyncio.sleep(0.01)

                    # Determine scoring
                    if category in ("SAFETY_CRITICAL", "FAST_SOCIAL", "NORMAL_CHAT"):
                        stress_score = 0.1
                        anxiety_score = 0.1
                        mood_score = 0.9
                        agent_analysis = {"personality_agent": {"communication_style": "casual"}, "intent_agent": {"message_type": "casual"}}
                        emotion_dimensions = {"stress": 0.1, "sadness": 0.1, "anxiety": 0.1, "happiness": 0.9, "motivation": 0.8, "confidence": 0.8}
                    else:
                        stress_score = e_data.get("stress", 0.3)
                        anxiety_score = e_data.get("anxiety", 0.3)
                        sadness_val = e_data.get("sadness", 0.3)
                        burnout_val = e_data.get("burnout", 0.3)
                        mood_score = round(1.0 - (stress_score * 0.2 + anxiety_score * 0.3 + sadness_val * 0.3 + burnout_val * 0.2), 2)
                        mood_score = max(0.05, min(0.95, mood_score))
                        
                        emotion_dimensions = {
                            "stress": stress_score,
                            "anxiety": anxiety_score,
                            "sadness": sadness_val,
                            "burnout": burnout_val,
                            "happiness": round(max(0.0, 1.0 - (sadness_val + stress_score) / 2.0), 2),
                            "motivation": 0.5,
                            "confidence": 0.5
                        }
                        agent_analysis = {
                            "personality_agent": p_data,
                            "emotion_agent": e_data,
                            "behavior_agent": b_data,
                            "growth_agent": g_data,
                            "intent_agent": i_data,
                            "safety_agent": s_data,
                            "retrieved_memories": memories,
                            "response_strategy": {"tone": tone, "strategy": strategy},
                            "conversation_stage": stage,
                        }
                        
                        # Parse internal reasoning from ResponseAgent (V3)
                        if isinstance(gen_res, dict) and gen_res.get("reasoning"):
                            try:
                                from app.utils.helpers import safe_json_parse
                                reasoning_dict = safe_json_parse(gen_res["reasoning"])
                                if reasoning_dict:
                                    agent_analysis["conversation_stage"] = reasoning_dict.get("conversation_stage", stage)
                                    agent_analysis["user_need"] = reasoning_dict.get("user_need", "")
                                    agent_analysis["hidden_emotion"] = reasoning_dict.get("hidden_emotion", "")
                                    agent_analysis["best_strategy"] = reasoning_dict.get("best_strategy", strategy)
                                    agent_analysis["intensity"] = reasoning_dict.get("emotion_intensity", 5)
                                    
                                    # Overwrite detected_emotion and mood_score if model returned a primary emotion in reasoning
                                    if reasoning_dict.get("primary_emotion"):
                                        detected_emotion = reasoning_dict["primary_emotion"]
                            except Exception as parse_err:
                                logger.warning(f"Failed to parse internal reasoning JSON: {parse_err}")

                    # Save response and run background learning tasks async
                    background_tasks.add_task(
                        save_chat_response_to_db,
                        conversation_id=conversation_id_resolved,
                        user_id=current_user.id,
                        user_message=message,
                        full_response=full_response,
                        detected_emotion=detected_emotion,
                        confidence_score=confidence_score,
                        stress_score=stress_score,
                        anxiety_score=anxiety_score,
                        mood_score=mood_score,
                        agent_analysis=agent_analysis,
                        emotion_dimensions=emotion_dimensions,
                        is_first_message=(len(history) == 0 if 'history' in locals() else True),
                    )

                    if category not in ("SAFETY_CRITICAL", "FAST_SOCIAL"):
                        background_tasks.add_task(
                            run_background_learning_tasks,
                            user_id=current_user.id,
                            user_message=message,
                            assistant_response=full_response,
                            conversation_id=conversation_id_resolved,
                            history=history,
                            detected_emotion=detected_emotion,
                            agent_result=agent_analysis,
                        )

                    # Update recent responses cache
                    if full_response:
                        c = _recent_responses_cache.setdefault(str(current_user.id), [])
                        c.append(full_response)
                        if len(c) > _RESPONSE_CACHE_SIZE:
                            _recent_responses_cache[str(current_user.id)] = c[-_RESPONSE_CACHE_SIZE:]

                # Yield final done event
                msg_id = str(uuid.uuid4())
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "done",
                        "message_id": msg_id,
                        "conversation_id": str(conversation_id_resolved),
                        "emotion_detected": detected_emotion,
                        "mood_score": mood_score,
                        "emotion_score": confidence_score,
                        "stress_score": stress_score,
                        "anxiety_score": anxiety_score,
                        "agent_analysis": {},
                    }),
                }
                
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                perf_logger.info(
                    f"[ESONA_CHAT_PERF] category={category} trace_id={trace_id} total_ms={duration_ms} "
                    f"client_message_id={client_message_id}"
                )
                logger.info(f"[CHAT PERF][trace={trace_id}] request_complete +{duration_ms}ms")

            except Exception as inner_err:
                logger.error(f"[SSE STREAM ERROR] Error inside event_generator: {inner_err}", exc_info=True)
                # Emit explicit rollback indicator to the client
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "error",
                        "content": "generation_failed",
                        "rollback": True,
                        "conversation_id": str(conversation_id_resolved),
                    }),
                }
                fallback_excuse = get_random_human_fallback()
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "chunk",
                        "content": fallback_excuse,
                        "conversation_id": str(conversation_id_resolved),
                    }),
                }
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "type": "done",
                        "message_id": str(uuid.uuid4()),
                        "conversation_id": str(conversation_id_resolved),
                        "emotion_detected": "neutral",
                        "mood_score": 0.5,
                        "agent_analysis": {},
                    }),
                }


        # Return the EventSourceResponse immediately
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
    Generate and save a personalized greeting check-in message, time-aware and context-priority-based,
    for the user conversation when they open the chat.
    """
    # 1. Verify conversation exists
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

    # 2. Get message count and messages
    history_res = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(6)
    )
    history_msgs = list(history_res.scalars().all())
    msg_count = len(history_msgs)

    # 3. Fetch onboarding answers and recent emotions
    from app.models.onboarding import UserAnswer
    answers_res = await db.execute(
        select(UserAnswer).where(UserAnswer.user_id == current_user.id)
    )
    onboarding_answers = answers_res.scalars().all()
    onboarding_answers_list = [f"Q: {ans.question_text} | A: {', '.join(ans.selected_answers)} {ans.custom_answer or ''}" for ans in onboarding_answers]
    onboarding_str = "\n".join(onboarding_answers_list) if onboarding_answers_list else "No onboarding answers recorded."

    from app.models.emotion_log import EmotionLog
    emotion_logs_res = await db.execute(
        select(EmotionLog)
        .where(EmotionLog.user_id == current_user.id)
        .order_by(EmotionLog.timestamp.desc())
        .limit(10)
    )
    emotion_logs = emotion_logs_res.scalars().all()
    recent_emotions_list = [f"{log.timestamp.strftime('%Y-%m-%d %H:%M')}: {log.detected_emotion} (confidence: {log.confidence_score})" for log in emotion_logs]
    recent_emotions_str = "\n".join(recent_emotions_list) if recent_emotions_list else "No recent emotion logs."

    # 4. Gather other rich context
    user_name = current_user.name or "friend"
    from app.services.profile_service import profile_service
    personal_profile = await profile_service.get_profile(db, current_user.id)
    
    profession = "unknown"
    goals = []
    interests = []
    stress_triggers = []
    if personal_profile:
        profession = personal_profile.profession or "unknown"
        goals = personal_profile.goals or []
        interests = personal_profile.interests or personal_profile.hobbies or []
        stress_triggers = personal_profile.stress_triggers or []

    # Fetch Knowledge Graph Relations
    from app.services.knowledge_graph_service import knowledge_graph_service
    relations = await knowledge_graph_service.retrieve_relationships(db, current_user.id)
    relations_list = [f"({r.subject}, {r.predicate}, {r.object})" for r in relations[:20]]
    relations_str = "\n".join(relations_list) if relations_list else "No knowledge graph relationships."

    # Fetch Memories (excluding conversation summaries)
    from app.models.memory import Memory
    memory_result = await db.execute(
        select(Memory)
        .where(Memory.user_id == current_user.id)
        .order_by(Memory.created_at.desc())
        .limit(10)
    )
    memories = memory_result.scalars().all()
    memories_list = [
        f"- {m.memory_summary} (Patterns: {m.behavior_patterns})"
        for m in memories
        if (m.metadata_json or {}).get("source") != "conversation_summary"
    ]
    memories_str = "\n".join(memories_list) if memories_list else "No past memories recorded."

    # Fetch last 6 messages
    history_msgs.reverse()  # oldest first
    recent_messages_str = "\n".join(
        f"{m.role}: {m.content}" for m in history_msgs
    ) if history_msgs else "No recent messages."

    # Time-aware calculation (Indian local offset UTC+5:30)
    from datetime import timedelta
    local_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    hour = local_now.hour
    if 5 <= hour < 12:
        time_of_day = "Morning"
    elif 12 <= hour < 17:
        time_of_day = "Afternoon"
    else:
        time_of_day = "Night"

    # Determine message generation path
    is_new_user_first_message = (not current_user.onboarding_completed) and msg_count == 0

    if is_new_user_first_message:
        prompt = f"""You are Buddy, the user's close friend and empathetic wellness companion.
This is the very first time you are meeting the user, and they have not completed their onboarding questionnaire yet.
Generate a warm, friendly, and natural welcome message introducing yourself as Buddy, and invite them to share a bit about themselves so you can get to know them.
Keep it extremely casual, Gen Z texting style, lowercase, using emojis.
You MUST split your thoughts using the delimiter " ||| " (with spaces around it) into exactly 2 or 3 parts.
Do not exceed 3 parts.
DO NOT use the name of the user as you don't know it yet.

Example: "hey 👋 ||| i'm Buddy ||| before we start, i'd love to get to know you a little better 😊"

Response:"""
    else:
        should_generate = False
        if msg_count == 0:
            should_generate = True
        else:
            last_msg = history_msgs[-1]  # The newest one
            if last_msg.role == MessageRole.assistant:
                last_msg_time = last_msg.created_at
                if last_msg_time.tzinfo is None:
                    last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)
                time_diff = datetime.now(timezone.utc) - last_msg_time
                if time_diff.total_seconds() > 4 * 3600:
                    should_generate = True

        if not should_generate:
            return {
                "response": "",
                "emotionDetected": history_msgs[-1].emotion_detected or "neutral",
                "moodScore": history_msgs[-1].mood_score or 0.5,
            }

        prompt = f"""You are Buddy, the user's close friend and empathetic wellness companion.
Your task is to generate a highly personalized, warm, and natural first greeting message (check-in) for the user.
Every session check-in must feel unique, caring, and reflect that you remember their life, goals, and interests.

=== TIME-AWARE RULES ===
Current time of day is: {time_of_day}
- Morning (5am-12pm): Include a morning-oriented friendly greeting like "good morning ☀️" or "morning!".
- Afternoon (12pm-5pm): Use a casual greeting like "hey 👋" or "hey there".
- Night (5pm-5am): Check in with something like "still awake? 😭" or "long day?" or "hey, how was your day?" depending on the context.

=== CONTEXT PRIORITY ORDER ===
You must check the user's context and select the highest priority topic available:
1. Active Emotional Concerns: If recent messages, emotions, or memories show they are going through a tough time (e.g. breakup, high anxiety, loneliness, sadness), ask how they are holding up today.
2. Recent Discussions: If they recently mentioned a specific event, exam, meeting, or project, ask how it went.
3. Goals: Reference one of their goals (e.g., finding an internship, coding, learning Japanese, fitness) and ask for updates.
4. Hobbies/Interests: Ask about one of their hobbies or interests (e.g. video editing, gaming, anime) in a friendly way.
5. General Greeting: If no specific context exists, just check in on how their day is going.

=== BEHAVIOR RULES ===
1. NEVER introduce yourself (DO NOT say "I'm Buddy" or "Hi, I'm Buddy" or "Hi, I'm Esona"). The user already knows you.
2. Speak like a close friend texting — informal, lowercase-friendly, warm, using natural emojis.
3. STRICT LENGTH LIMIT: Under no circumstances exceed 2 short messages.
4. You MUST split your thoughts using the delimiter " ||| " (with spaces around it) into exactly 1 or 2 parts. Each part should be a single short line.
5. Do NOT ask generic robotic assistant questions like "How can I help you today?".

USER DETAILS:
- Name: {user_name}
- Profession: {profession}
- Goals: {goals}
- Hobbies/Interests: {interests}
- Stress Triggers: {stress_triggers}
- Onboarding Answers:
{onboarding_str}
- Recent Emotions:
{recent_emotions_str}
- Recent Memories:
{memories_str}
- Knowledge Graph Relationships:
{relations_str}
- Recent Conversation Messages:
{recent_messages_str}

Response:"""

    if is_new_user_first_message:
        raw_response = "hey 👋 ||| i'm Buddy ||| before we start, i'd love to get to know you a little better 😊"
    else:
        try:
            from app.utils.llm import generate_chat_completion_with_fallback
            raw_response = await generate_chat_completion_with_fallback(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.75,
                max_tokens=150
            )
        except Exception as e:
            logger.error(f"Failed to generate personalized first message: {e}", exc_info=True)
            raw_response = f"hey {user_name} 👋 ||| just wanted to check in and see how you're doing today."

    # 7. Save greeting to DB
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


from pydantic import BaseModel

class DebugEmotionRequest(BaseModel):
    text: str


@router.post("/debug/emotion")
async def debug_emotion(body: DebugEmotionRequest, db: AsyncSession = Depends(get_db)):
    """
    Temporary debug endpoint to test MentalBERT classification.
    """
    try:
        from app.services.emotion_service import emotion_service
        # Generate a dummy user ID for logging/saving
        dummy_user_id = str(uuid.uuid4())
        res = await emotion_service.classify_emotion_mentalbert(db, dummy_user_id, body.text)
        
        detected_emotion = res.get("detected_emotion", "Neutral")
        confidence = res.get("confidence_score", 1.0)
        
        return {
            "mentalbert_prediction": detected_emotion,
            "confidence": confidence,
            "final_emotion": detected_emotion
        }
    except Exception as e:
        logger.error(f"Debug emotion classification failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Emotion classification failed: {str(e)}"
        )

