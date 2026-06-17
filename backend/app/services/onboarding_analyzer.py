"""
Service to analyze onboarding responses and build the initial EmotionalProfile.
Uses OpenAI API to parse responses and generate structured personality/emotional insights.
"""

import json
import logging
import uuid
from typing import Any, Dict, List

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.conversation import Message
from app.models.memory import Memory

logger = logging.getLogger(__name__)


async def analyze_onboarding(
    user_id: uuid.UUID,
    answers: List[Dict[str, Any]],
    db: AsyncSession,
) -> UserProfile:
    """
    Analyze 20 onboarding responses using OpenAI and save the resulting
    EmotionalProfile.
    """
    logger.info(f"Analyzing onboarding responses for user: {user_id}")

    # Format answers for the prompt
    formatted_responses = []
    for ans in answers:
        q_id = ans.get("question_id")
        cat = ans.get("category")
        opts = ans.get("selected_answers", [])
        custom = ans.get("custom_answer")
        
        opts_str = ", ".join([f"'{o}'" for o in opts])
        custom_str = f" (Custom answer: '{custom}')" if custom else ""
        formatted_responses.append(
            f"Question {q_id} [{cat}]: Selected [{opts_str}]{custom_str}"
        )

    answers_summary = "\n".join(formatted_responses)

    # Fetch last 50 chat messages from the user/assistant to contextualize the profile
    try:
        messages_result = await db.execute(
            select(Message)
            .where(Message.user_id == user_id)
            .order_by(Message.created_at.desc())
            .limit(50)
        )
        db_messages = messages_result.scalars().all()
        # Sort chronologically
        db_messages = list(reversed(db_messages))
        chat_context = "\n".join([
            f"{'User' if m.role == 'user' else 'Buddy'}: {m.content}"
            for m in db_messages
        ])
    except Exception as e:
        logger.warning(f"Failed to fetch messages for onboarding analysis: {e}")
        chat_context = "No chat history available."

    # Fetch recent memories
    try:
        memories_result = await db.execute(
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
            .limit(15)
        )
        db_memories = memories_result.scalars().all()
        memories_context = "\n".join([
            f"- {mem.memory_content} (Type: {mem.memory_type or 'General'})"
            for mem in db_memories
        ])
    except Exception as e:
        logger.warning(f"Failed to fetch memories for onboarding analysis: {e}")
        memories_context = "No memories available."

    system_prompt = """
    You are an advanced psychological profiling system. Your task is to analyze a user's answers to their onboarding questionnaire, their recent chat history, and their recorded memories to produce a structured, deep emotional and behavioral profile.
    
    The inputs are:
    1. Onboarding answers (from a 25-question onboarding setup or updates).
    2. Recent chat logs with Esona/Buddy.
    3. Recorded memories/observations.

    Analyze these sources comprehensively to generate a cohesive, accurate profile.

    Analyze these answers and output a single JSON object containing exactly these keys:
    - personality_type: containing 'type' (a descriptive name, e.g. "Thoughtful Introvert", "Empathetic Rescuer", etc.), 'description', 'strengths' (list of strings), 'growth_areas' (list of strings), and 'summary' (a brief overview).
    - emotional_baseline: containing 'dominant_emotion' (e.g. calm, overwhelmed, anxious, optimistic), 'tendencies' (list of strings describing their recurring moods), 'stress_level' (a rating between 1 and 10), and 'burnout_risk_assessment' (brief textual assessment).
    - comfort_preferences: containing 'safest_environment' (where they feel emotionally safest), 'escape_mechanisms' (list of things they use to de-stress), and 'mood_boosters' (list of actions/factors that improve their mood).
    - communication_style: containing 'preferred_style' (e.g. warm & friendly, direct & logical, gentle & validating), 'annoyances' (list of communication patterns that annoy them), and 'comfort_support_type' (what they seek when feeling low: practical advice vs validation/listening).
    - reply_style: containing 'reply_style' (one of: "short_funny", "short", "deep_emotional", "casual"), 'likes_humor' (boolean), 'paragraph_preference' (one of: "short", "medium", "long"), 'emoji_usage' (one of: "low", "medium", "high"), 'communication_style' (one of: "casual", "gentle", "direct", "funny"), and 'energy' (one of: "playful", "calm", "thoughtful", "supportive").
    - emotional_summary: containing a descriptive narrative summarizing their current emotional state, baseline, and tendencies.
    - stress_patterns: containing 'stress_triggers' (list of strings) and 'coping_mechanisms' (list of strings).
    - emotional_triggers: containing 'triggers' (list of strings) and 'overthinking_tendency' (high/medium/low).
    - preferred_response_style: containing 'preferred_tone', 'what_helps' (list of strings), and 'what_to_avoid' (list of strings).

    Output ONLY valid JSON. Do not include markdown code block formatting or backticks around the JSON.
    """

    user_prompt = f"""
    Analyze the following user data to generate the structured emotional profile:
    
    ONBOARDING QUESTIONS AND ANSWERS:
    {answers_summary}
    
    RECENT CHAT CONVERSATION HISTORY:
    {chat_context}
    
    RECORDED MEMORIES / KEY OBSERVATIONS:
    {memories_context}
    """

    # Use client to run query
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content or "{}"
        profile_data = json.loads(raw_content)

    except Exception as e:
        logger.error(f"OpenAI profiling failed: {e}", exc_info=True)
        # Fallback profile data in case of error
        profile_data = {
            "personality_type": {
                "type": "Thoughtful Processor",
                "description": "Prefers reflecting internally and values authentic connections.",
                "strengths": ["Self-reflective", "Empathetic listener"],
                "growth_areas": ["Managing overthinking"],
                "summary": "Values quiet reflection and clear, low-pressure support.",
            },
            "emotional_baseline": {
                "dominant_emotion": "neutral",
                "tendencies": ["calm", "reflective"],
                "stress_level": 4.0,
                "burnout_risk_assessment": "Moderate. Keep track of energy level balance.",
            },
            "comfort_preferences": {
                "safest_environment": "Quiet personal space",
                "escape_mechanisms": ["listening to music", "retreating into hobbies"],
                "mood_boosters": ["quiet achievements", "sincere connections"],
            },
            "communication_style": {
                "preferred_style": "gentle & validating",
                "annoyances": ["toxic positivity", "overly formal scripts"],
                "comfort_support_type": "validation & quiet listening",
            },
            "reply_style": {
                "reply_style": "casual",
                "likes_humor": True,
                "paragraph_preference": "short",
                "emoji_usage": "medium",
                "communication_style": "casual",
                "energy": "supportive"
            },
            "emotional_summary": {
                "summary": "Currently in a neutral, calm emotional baseline. Tends to overthink during stress but values self-reflection."
            },
            "stress_patterns": {
                "stress_triggers": ["overwhelming responsibilities", "lack of structure"],
                "coping_mechanisms": ["music", "retreating into a quiet space"]
            },
            "emotional_triggers": {
                "triggers": ["abrupt communication", "high-pressure expectations"],
                "overthinking_tendency": "medium"
            },
            "preferred_response_style": {
                "preferred_tone": "gentle & validating",
                "what_helps": ["validation", "active listening", "calm suggestions"],
                "what_to_avoid": ["toxic positivity", "robotic motivational lines"]
            }
        }

    # Fetch existing profile if any, or create a new one
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)

    # Populate sections
    profile.personality_type = profile_data.get("personality_type", {})
    profile.emotional_style = profile_data.get("emotional_baseline", {})
    profile.interests = profile_data.get("comfort_preferences", {})
    profile.communication_style = profile_data.get("communication_style", {})
    profile.stress_triggers = profile_data.get("emotional_triggers", {})
    profile.strengths = {"strengths": profile_data.get("personality_type", {}).get("strengths", [])}
    profile.weaknesses = {"weaknesses": profile_data.get("personality_type", {}).get("growth_areas", [])}
    profile.onboarding_answers = {"answers": answers}

    # Onboarding Additions
    profile.onboarding_completed = True
    p_type = profile_data.get("personality_type", {}).get("type", "Thoughtful Explorer")
    c_style = profile_data.get("communication_style", {}).get("preferred_style", "Gentle and validating")
    p_strengths = profile_data.get("personality_type", {}).get("strengths", [])
    p_interests = profile_data.get("comfort_preferences", {}).get("escape_mechanisms", [])
    p_triggers = profile_data.get("stress_patterns", {}).get("stress_triggers", [])
    p_motivation = profile_data.get("preferred_response_style", {}).get("what_helps", [])
    
    profile.personality_profile = {
        "type": p_type,
        "communication_style": c_style,
        "strengths": p_strengths,
        "interests": p_interests,
        "stress_triggers": p_triggers,
        "motivation_style": ", ".join(p_motivation) if isinstance(p_motivation, list) else str(p_motivation),
        "reply_style": profile_data.get("reply_style", {
            "reply_style": "casual",
            "likes_humor": True,
            "paragraph_preference": "short",
            "emoji_usage": "medium",
            "communication_style": "casual",
            "energy": "supportive"
        })
    }
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.personality_profile = profile.personality_profile
        user.personality_type = p_type
        user.communication_style = c_style
        user.interests = {"items": p_interests}
        user.onboarding_completed = True

    profile.personality_type_text = p_type
    profile.communication_style_text = c_style

    # Backward compatibility
    profile.emotional_baseline = profile_data.get("emotional_baseline", {})
    profile.comfort_preferences = profile_data.get("comfort_preferences", {})
    profile.emotional_summary = profile_data.get("emotional_summary", {})
    profile.stress_patterns = profile_data.get("stress_patterns", {})
    profile.emotional_triggers = profile_data.get("emotional_triggers", {})
    profile.preferred_response_style = profile_data.get("preferred_response_style", {})

    await db.flush()
    logger.info(f"UserProfile saved successfully for user: {user_id}")
    return profile
