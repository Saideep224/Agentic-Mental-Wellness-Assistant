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
from app.database import _history_cache, _profile_cache, write_queue
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
            "ray": ["hacked", "stalker", "cyber", "scam", "blackmail", "harass", "threat", "bully", "online safety", "scammed", "stole my account", "compromised", "phishing", "leak", "police"],
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
                logger.error(f"[DB SELECT] Conversation {conversation_id} not found for user {user_id}.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
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
            
        # Dynamically load / restore onboarding & profile facts from Supabase (crucial for personalization persistence)
        try:
            from app.services.profile_service import profile_service
            p_data = await profile_service.get_personalization_data(db, user_id)
            if p_data and "raw" in p_data:
                profile_dict["personality_profile"] = p_data["raw"]
        except Exception as p_err:
            logger.warning(f"Failed to fetch consolidated personalization data: {p_err}")

        # Update in-memory fallback cache
        _profile_cache[str(user_id)] = profile_dict
        return profile_dict
    except Exception as e:
        logger.warning(f"[DB FAIL] _get_emotional_profile_dict failed: {e}. Falling back to in-memory cache.")
        return _profile_cache.get(str(user_id), profile_dict)


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

        # --- Intent-based specialist routing ---
        current_specialists: list = list(conversation.active_specialists or [])

        # Extract pending specialist from last assistant message
        pending_specialist = None
        if history:
            for msg in reversed(history):
                if msg.get("role") == "assistant":
                    analysis = msg.get("agent_analysis", {})
                    pending_specialist = analysis.get("suggested_specialist")
                    break

        specialist_action, action_target = detect_specialist_action(body.message, current_specialists, pending_specialist)
        specialist_action_event = None
        if specialist_action == "invite" and action_target:
            if action_target not in current_specialists:
                current_specialists.append(action_target)
                conversation.active_specialists = current_specialists
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                specialist_action_event = {"action": "invited", "specialist_id": action_target}
                logger.info(f"[SPECIALIST INTENT] Invited specialist '{action_target}' to conversation {conversation_id_resolved}")
        elif specialist_action == "remove" and action_target:
            if action_target in current_specialists:
                current_specialists.remove(action_target)
                conversation.active_specialists = current_specialists
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                specialist_action_event = {"action": "removed", "specialist_id": action_target}
                logger.info(f"[SPECIALIST INTENT] Removed specialist '{action_target}' from conversation {conversation_id_resolved}")
        # --- End intent-based routing ---

        specialist_id = None
        if conversation.agent_id and conversation.agent_id != "buddy":
            specialist_id = conversation.agent_id
        elif conversation.active_specialists:
            specialist_id = conversation.active_specialists[0]

        specialist_response = None
        suggested_specialist = None

        try:
            if specialist_id:
                # 1. Run preprocessing (cog analyzer + memory) to extract shared context
                from app.chatbot.pipeline import preprocessing_node
                initial_state = {
                    "user_message": body.message,
                    "user_id": str(current_user.id),
                    "conversation_id": str(conversation_id_resolved),
                    "conversation_history": history,
                    "emotional_profile": emotional_profile,
                    "db": db,
                    "router_decision": {},
                    "emotion_analysis": {},
                    "personality_analysis": {},
                    "context_analysis": {},
                    "memories": [],
                    "recommendations": [],
                    "comfort_kit": {},
                    "response": "",
                    "mood_score": 0.5,
                    "detected_emotion": "neutral",
                    "personality_agent": {},
                    "emotion_agent": {},
                    "behavior_agent": {},
                    "growth_agent": {},
                    "intent_agent": {},
                    "safety_agent": {},
                    "memory_extraction": {},
                    "response_strategy": {},
                    "orchestrated_prompt_summary": "",
                    "agent_analysis": {},
                }
                cog_res = await preprocessing_node(initial_state)
                
                # 2. Invoke the specialist agent via AI Router
                from app.services.ai_router import ai_router
                spec_res = await ai_router.generate_response(
                    db=db,
                    user_id=str(current_user.id),
                    agent_id=specialist_id,
                    user_message=body.message,
                    conversation_history=history,
                    cog_res=cog_res
                )
                specialist_response = spec_res["response"]

                # Check Buddy Intervention
                should_intervene, reason = check_buddy_intervention(body.message, specialist_id, specialist_response, cog_res)

                if should_intervene:
                    # 3. Inject specialist response into Buddy's graph as system note and dialog turn
                    if reason == "technical":
                        system_note = f"System Note: The specialist {specialist_id} just advised: '{specialist_response}'. The user needs a quick translation. Generate a short, casual, friend-like translation or explanation (e.g. 'he means the property papers 😭' or similar). Keep it under 15 words, lowercase, informal, using emojis like a close friend. Do NOT introduce the specialist or say you connected them (you already did). Just briefly add your emotional support."
                    else:
                        system_note = f"System Note: The specialist {specialist_id} just advised: '{specialist_response}'. Empathize with the user, act as the emotional anchor, and translate any complex concepts. Do NOT introduce the specialist or say you connected them (you already did). Just briefly add your emotional support."
                    
                    updated_history = history + [
                        {"role": "system", "content": system_note},
                        {"role": "assistant", "content": specialist_response, "sender_type": specialist_id}
                    ]

                    # Run Buddy graph with specialist injected
                    result = await run_agent_graph(
                        user_message=body.message,
                        user_id=str(current_user.id),
                        conversation_history=updated_history,
                        emotional_profile=emotional_profile,
                        conversation_id=conversation_id_resolved,
                        db=db,
                    )
                else:
                    # Buddy remains silent
                    result = {
                        "response": None,
                        "detected_emotion": cog_res.get("detected_emotion", "neutral"),
                        "detected_emotion_confidence": cog_res.get("detected_emotion_confidence", 1.0),
                        "mood_score": cog_res.get("mood_score", 0.5),
                        "emotion_agent": cog_res.get("emotion_agent", {}),
                        "emotion_dimensions": cog_res.get("emotion_dimensions", {}),
                        "agent_analysis": {},
                    }
            else:
                # No specialist active, run normal Buddy graph
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

            # Check if Buddy should recommend a specialist (only on Buddy chat, when no specialist is active)
            if not specialist_id and conversation.agent_id == "buddy":
                suggested_specialist = detect_specialist_recommendation(body.message, agent_analysis, history)
                if suggested_specialist:
                    from app.agents.specialist_registry import SPECIALIST_REGISTRY
                    spec_info = SPECIALIST_REGISTRY[suggested_specialist]
                    if suggested_specialist == "ray":
                        rec_suffix = "\n\nOfficer Ray can help with reporting, cybercrime and complaint procedures. want me to bring him in?"
                    else:
                        rec_suffix = f"\n\nI think {spec_info['name']} may be able to explain the {spec_info['role'].lower()} side of this situation. Would you like me to connect you?"
                    full_response += rec_suffix
                    agent_analysis["suggested_specialist"] = suggested_specialist

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

            # --- Intent-based specialist routing (SSE path) ---
            current_specialists: list = list((conversation.active_specialists if conversation else None) or [])

            # Extract pending specialist from last assistant message
            pending_specialist = None
            if history:
                for msg in reversed(history):
                    if msg.get("role") == "assistant":
                        analysis = msg.get("agent_analysis", {})
                        pending_specialist = analysis.get("suggested_specialist")
                        break

            specialist_action, action_target = detect_specialist_action(message, current_specialists, pending_specialist)
            sse_specialist_action_event = None
            if conversation:
                if specialist_action == "invite" and action_target:
                    if action_target not in current_specialists:
                        current_specialists.append(action_target)
                        conversation.active_specialists = current_specialists
                        db.add(conversation)
                        await db.commit()
                        await db.refresh(conversation)
                        sse_specialist_action_event = {"action": "invited", "specialist_id": action_target}
                        logger.info(f"[SSE SPECIALIST INTENT] Invited specialist '{action_target}' to conversation {conversation_id}")
                elif specialist_action == "remove" and action_target:
                    if action_target in current_specialists:
                        current_specialists.remove(action_target)
                        conversation.active_specialists = current_specialists
                        db.add(conversation)
                        await db.commit()
                        await db.refresh(conversation)
                        sse_specialist_action_event = {"action": "removed", "specialist_id": action_target}
                        logger.info(f"[SSE SPECIALIST INTENT] Removed specialist '{action_target}' from conversation {conversation_id}")
            # --- End intent-based routing ---

            specialist_id = None
            if conversation:
                if conversation.agent_id and conversation.agent_id != "buddy":
                    specialist_id = conversation.agent_id
                elif conversation.active_specialists:
                    specialist_id = conversation.active_specialists[0]

            specialist_response = None
            suggested_specialist = None

            if specialist_id:
                # 1. Run preprocessing (cog analyzer + memory) to extract shared context
                from app.chatbot.pipeline import preprocessing_node
                initial_state = {
                    "user_message": message,
                    "user_id": str(current_user_id),
                    "conversation_id": str(conversation_id),
                    "conversation_history": history,
                    "emotional_profile": emotional_profile,
                    "db": db,
                    "router_decision": {},
                    "emotion_analysis": {},
                    "personality_analysis": {},
                    "context_analysis": {},
                    "memories": [],
                    "recommendations": [],
                    "comfort_kit": {},
                    "response": "",
                    "mood_score": 0.5,
                    "detected_emotion": "neutral",
                    "personality_agent": {},
                    "emotion_agent": {},
                    "behavior_agent": {},
                    "growth_agent": {},
                    "intent_agent": {},
                    "safety_agent": {},
                    "memory_extraction": {},
                    "response_strategy": {},
                    "orchestrated_prompt_summary": "",
                    "agent_analysis": {},
                }
                cog_res = await preprocessing_node(initial_state)
                
                # 2. Invoke the specialist agent via AI Router
                from app.services.ai_router import ai_router
                spec_res = await ai_router.generate_response(
                    db=db,
                    user_id=str(current_user_id),
                    agent_id=specialist_id,
                    user_message=message,
                    conversation_history=history,
                    cog_res=cog_res
                )
                specialist_response = spec_res["response"]

                # Check Buddy Intervention
                should_intervene, reason = check_buddy_intervention(message, specialist_id, specialist_response, cog_res)

                if should_intervene:
                    # 3. Inject specialist response into Buddy's graph as system note and dialog turn
                    if reason == "technical":
                        system_note = f"System Note: The specialist {specialist_id} just advised: '{specialist_response}'. The user needs a quick translation. Generate a short, casual, friend-like translation or explanation (e.g. 'he means the property papers 😭' or similar). Keep it under 15 words, lowercase, informal, using emojis like a close friend. Do NOT introduce the specialist or say you connected them (you already did). Just briefly add your emotional support."
                    else:
                        system_note = f"System Note: The specialist {specialist_id} just advised: '{specialist_response}'. Empathize with the user, act as the emotional anchor, and translate any complex concepts. Do NOT introduce the specialist or say you connected them (you already did). Just briefly add your emotional support."
                    
                    updated_history = history + [
                        {"role": "system", "content": system_note},
                        {"role": "assistant", "content": specialist_response, "sender_type": specialist_id}
                    ]

                    # Run Buddy graph with specialist injected
                    result = await run_agent_graph(
                        user_message=message,
                        user_id=str(current_user_id),
                        conversation_history=updated_history,
                        emotional_profile=emotional_profile,
                        conversation_id=conversation_id,
                        db=db,
                    )
                else:
                    # Buddy remains silent
                    result = {
                        "response": None,
                        "detected_emotion": cog_res.get("detected_emotion", "neutral"),
                        "detected_emotion_confidence": cog_res.get("detected_emotion_confidence", 1.0),
                        "mood_score": cog_res.get("mood_score", 0.5),
                        "emotion_agent": cog_res.get("emotion_agent", {}),
                        "emotion_dimensions": cog_res.get("emotion_dimensions", {}),
                        "agent_analysis": {},
                    }
            else:
                # No specialist active, run normal Buddy graph
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

            # Check if Buddy should recommend a specialist
            if not specialist_id and conversation and conversation.agent_id == "buddy":
                suggested_specialist = detect_specialist_recommendation(message, agent_analysis, history)
                if suggested_specialist:
                    from app.agents.specialist_registry import SPECIALIST_REGISTRY
                    spec_info = SPECIALIST_REGISTRY[suggested_specialist]
                    if suggested_specialist == "ray":
                        rec_suffix = "\n\nOfficer Ray can help with reporting, cybercrime and complaint procedures. want me to bring him in?"
                    else:
                        rec_suffix = f"\n\nI think {spec_info['name']} may be able to explain the {spec_info['role'].lower()} side of this situation. Would you like me to connect you?"
                    full_response += rec_suffix
                    agent_analysis["suggested_specialist"] = suggested_specialist

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

        # 6. Save memory in background if meaningful
        try:
            from app.services.memory_service import memory_service
            mem_extraction = result.get("memory_extraction", {})
            if mem_extraction.get("is_meaningful"):
                logger.info(f"[SSE MEMORY] Storing memory: '{mem_extraction.get('memory_summary', '')[:80]}'...")
                await memory_service.saveMemory(
                    db=db,
                    user_id=str(current_user_id),
                    memory_summary=mem_extraction.get("memory_summary"),
                    behavior_patterns=mem_extraction.get("behavior_patterns") or {},
                    memory_type=mem_extraction.get("memory_type"),
                    importance_score=mem_extraction.get("importance_score"),
                )
                await db.commit()
                logger.info(f"[SSE MEMORY SUCCESS] Memory stored successfully.")
        except Exception as mem_err:
            logger.error(f"[SSE MEMORY ERROR] Failed to save memory: {mem_err}", exc_info=True)

        # 7. Thread summary trigger if needed
        if len(history) >= 12 and len(history) % 6 == 0:
            try:
                await summarize_and_store_conversation(db, current_user_id, conversation_id, history)
                await db.commit()
            except Exception as sum_err:
                logger.error(f"[SSE SUMMARIZATION ERROR] Summarization trigger failed: {sum_err}", exc_info=True)

        # 8. Memory reflection trigger
        try:
            num_user = sum(1 for m in history if m.get("role") == "user")
            if num_user > 0 and num_user % 10 == 0:
                logger.info(f"[SSE REFLECTION] Triggering memory reflection for user {current_user_id} (user messages: {num_user})...")
                from app.services.memory_service import memory_service
                await memory_service.reflect_and_consolidate_memories(db, current_user_id)
                await db.commit()
        except Exception as ref_err:
            logger.error(f"[SSE REFLECTION ERROR] Reflection failed: {ref_err}", exc_info=True)

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
        }


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

        # ---------------------------------------------------------------
        # NON-BLOCKING ONBOARDING ROUTING (SSE)
        # Priority 1: Crisis → bypass, run full pipeline
        # Priority 2: Free-form → auto-complete, run full pipeline
        # Priority 3: Structured answer → save silently, run pipeline
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
                # Short structured answer — save silently, continue to pipeline
                if profile:
                    stage = (profile.personality_profile or {}).get("onboarding_stage", 1)
                    try:
                        await onboarding_service.parse_and_save_answer(db, current_user, profile, stage, message)
                        await db.commit()
                        logger.info(f"[ONBOARDING SSE SILENT SAVE] Saved answer for stage {stage}.")
                    except Exception as ob_err:
                        logger.warning(f"[ONBOARDING SSE SILENT SAVE] Failed: {ob_err}")
                        await db.rollback()
            # Re-read so the pipeline sees updated onboarding_completed
            await db.refresh(current_user)


        # 4. Build context
        logger.info(f"[CONTEXT SSE] Loading history and emotional profile...")
        history = await _build_conversation_history(db, conversation_id_resolved)
        emotional_profile = await _get_emotional_profile_dict(db, current_user.id, current_user.name)
 
        # 5. Event generator for Starlette SSE EventSourceResponse
        async def event_generator() -> AsyncGenerator[dict, None]:
            logger.info("[EVENT GENERATOR] Stream generator started.")
            
            # Yield speculative transition immediately
            speculative_chunk = get_speculative_transition(message)
            logger.info(f"[SSE STREAM] Yielding speculative transition: '{speculative_chunk}'")
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "placeholder",
                    "content": speculative_chunk,
                    "conversation_id": str(conversation_id_resolved),
                }),
            }
            # Short yield pause
            await asyncio.sleep(0.05)
            
            try:
                persist_task = asyncio.create_task(
                    generate_and_persist_sse_response(
                        message=message,
                        current_user_id=current_user.id,
                        conversation_id=conversation_id_resolved,
                        history=history,
                        emotional_profile=emotional_profile,
                    )
                )
                try:
                    persisted = await asyncio.shield(persist_task)
                except asyncio.CancelledError:
                    logger.warning(
                        "[SSE DISCONNECT] Client disconnected while AI/save task was running. "
                        "Persistence task remains shielded for conversation_id=%s",
                        conversation_id_resolved,
                    )
                    raise
 
                full_response = persisted["full_response"]
                detected_emotion = persisted["detected_emotion"]
                mood_score = persisted["mood_score"]
                agent_analysis = persisted["agent_analysis"]
                msg_id = persisted["message_id"]
                emotion_score = persisted.get("emotion_score", 1.0)
                stress_score = persisted.get("stress_score", 0.0)
                anxiety_score = persisted.get("anxiety_score", 0.0)
                specialist_response = persisted.get("specialist_response")
                specialist_id = persisted.get("specialist_id")
                specialist_msg_id = persisted.get("specialist_message_id")
                suggested_specialist = persisted.get("suggested_specialist")
                sse_specialist_action = persisted.get("specialist_action_event")

                # Emit specialist_action event so the frontend can update the UI
                if sse_specialist_action:
                    logger.info(f"[SSE STREAM] Yielding specialist_action event: {sse_specialist_action}")
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "specialist_action",
                            "action": sse_specialist_action["action"],
                            "specialist_id": sse_specialist_action["specialist_id"],
                            "conversation_id": str(conversation_id_resolved),
                        }),
                    }
                    await asyncio.sleep(0.03)

                # If specialist response is active, stream it first
                if specialist_response and specialist_id:
                    logger.info(f"[SSE STREAM] Yielding specialist '{specialist_id}' response text chunks...")
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "specialist_start",
                            "specialist_id": specialist_id,
                            "conversation_id": str(conversation_id_resolved),
                        }),
                    }
                    await asyncio.sleep(0.05)

                    chunk_size = 12
                    for i in range(0, len(specialist_response), chunk_size):
                        chunk = specialist_response[i : i + chunk_size]
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "specialist_chunk",
                                "content": chunk,
                                "specialist_id": specialist_id,
                                "conversation_id": str(conversation_id_resolved),
                            }),
                        }
                        await asyncio.sleep(0.02)

                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "specialist_done",
                            "specialist_id": specialist_id,
                            "message_id": specialist_msg_id,
                            "conversation_id": str(conversation_id_resolved),
                        }),
                    }
                    await asyncio.sleep(0.1)

                # Yield Buddy chunks
                if full_response is not None:
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
                        "emotion_score": emotion_score,
                        "stress_score": stress_score,
                        "anxiety_score": anxiety_score,
                        "agent_analysis": agent_analysis,
                        "suggested_specialist": suggested_specialist,
                    }),
                }
 
            except Exception as gen_err:
                logger.error(f"[SSE STREAM ERROR] Error inside event_generator: {gen_err}", exc_info=True)
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

    # 3. Handle non-onboarded users
    if not current_user.onboarding_completed:
        if msg_count == 0:
            logger.info(f"[FIRST MESSAGE] New user {current_user.id}. Sending welcome + onboarding intro.")
            reply = "hey 👋 ||| i'm Buddy ||| before we start, i'd love to get to know you a little better 😊"
            assistant_msg = Message(
                conversation_id=conversation.id,
                user_id=current_user.id,
                role=MessageRole.assistant,
                content=reply,
                emotion_detected="neutral",
                mood_score=0.5,
                agent_analysis={}
            )
            db.add(assistant_msg)
            conversation.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return {
                "response": reply,
                "emotionDetected": "neutral",
                "moodScore": 0.5,
            }
        else:
            # Already has onboarding history, return the first message
            history_msgs.reverse()
            first_msg = history_msgs[0]
            return {
                "response": first_msg.content,
                "emotionDetected": first_msg.emotion_detected or "neutral",
                "moodScore": first_msg.mood_score or 0.5,
            }

    # 4. Handle onboarded users
    # Check if this is a new session (msg_count == 0 OR (last_msg is assistant AND > 4 hours old))
    should_generate = False
    if msg_count == 0:
        should_generate = True
    else:
        last_msg = history_msgs[0]  # Since it's ordered by desc, the first one is the newest
        if last_msg.role == "assistant":
            last_msg_time = last_msg.created_at
            if last_msg_time.tzinfo is None:
                last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)
            time_diff = datetime.now(timezone.utc) - last_msg_time
            if time_diff.total_seconds() > 4 * 3600:
                should_generate = True

    if not should_generate:
        return {
            "response": "",
            "emotionDetected": "neutral",
            "moodScore": 0.5,
        }

    # 5. Gather rich context for dynamic personalized check-in
    user_name = current_user.name or "friend"
    
    # Fetch UserPersonalProfile data
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

    # 6. Build LLM prompt
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
1. Active Emotional Concerns: If recent messages or memories show they are going through a tough time (e.g. breakup, high anxiety, loneliness), ask how they are holding up today.
2. Recent Discussions: If they recently mentioned a specific event, exam, meeting, or project, ask how it went.
3. Goals: Reference one of their goals (e.g., finding an internship, coding, learning Japanese, fitness) and ask for updates.
4. Hobbies/Interests: Ask about one of their hobbies or interests (e.g. video editing, gaming, anime) in a friendly way.
5. General Greeting: If no specific context exists, just check in on how their day is going.

=== BEHAVIOR RULES ===
1. NEVER introduce yourself (DO NOT say "I'm Buddy" or "Hi, I'm Buddy" or "Hi, I'm Esona"). The user already knows you.
2. Speak like a close friend texting — informal, lowercase-friendly, warm, using natural emojis.
3. STRICT LENGTH LIMIT: Under no circumstances exceed 2 short messages.
4. You MUST split your thoughts using the delimiter " ||| " (with spaces around it) into exactly 1 or 2 parts. Each part should be a single short line.
   - Example 1: "hey {user_name} 👋 ||| how's the Esona project going?"
   - Example 2: "still awake? 😭 ||| how did that meeting go?"
   - Example 3: "good morning ☀️ ||| how are you holding up after yesterday?"
5. Do NOT ask generic robotic assistant questions like "How can I help you today?".

USER DETAILS:
- Name: {user_name}
- Profession: {profession}
- Goals: {goals}
- Hobbies/Interests: {interests}
- Stress Triggers: {stress_triggers}
- Recent Memories:
{memories_str}
- Knowledge Graph Relationships:
{relations_str}
- Recent Conversation Messages:
{recent_messages_str}

Response:"""

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

