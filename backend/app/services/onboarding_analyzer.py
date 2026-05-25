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
from app.models.user_profile import UserProfile

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
        opt = ans.get("selected_option")
        custom = ans.get("custom_text")
        
        custom_str = f" (Custom answer: '{custom}')" if custom else ""
        formatted_responses.append(
            f"Question {q_id} [{cat}]: Selected '{opt}'{custom_str}"
        )

    answers_summary = "\n".join(formatted_responses)

    system_prompt = """
    You are an advanced psychological profiling system. Your task is to analyze a user's answers to a 20-question onboarding questionnaire and produce a structured, deep emotional and behavioral profile.
    
    The questionnaire covers four categories:
    1. Personality & Behavioral Understanding (Q1-Q5)
    2. Emotional State & Stress Analysis (Q6-Q10)
    3. Hobbies & Comfort Zone Understanding (Q11-Q15)
    4. Communication & Response Preference (Q16-Q20)

    Analyze these answers and output a single JSON object containing exactly these keys:
    - personality_type: containing 'type' (a descriptive name, e.g. "Thoughtful Introvert", "Empathetic Rescuer", etc.), 'description', 'strengths' (list of strings), 'growth_areas' (list of strings), and 'summary' (a brief overview).
    - emotional_baseline: containing 'dominant_emotion' (e.g. calm, overwhelmed, anxious, optimistic), 'tendencies' (list of strings describing their recurring moods), 'stress_level' (a rating between 1 and 10), and 'burnout_risk_assessment' (brief textual assessment).
    - comfort_preferences: containing 'safest_environment' (where they feel emotionally safest), 'escape_mechanisms' (list of things they use to de-stress), and 'mood_boosters' (list of actions/factors that improve their mood).
    - communication_style: containing 'preferred_style' (e.g. warm & friendly, direct & logical, gentle & validating), 'annoyances' (list of communication patterns that annoy them), and 'comfort_support_type' (what they seek when feeling low: practical advice vs validation/listening).
    - emotional_summary: containing a descriptive narrative summarizing their current emotional state, baseline, and tendencies.
    - stress_patterns: containing 'stress_triggers' (list of strings) and 'coping_mechanisms' (list of strings).
    - emotional_triggers: containing 'triggers' (list of strings) and 'overthinking_tendency' (high/medium/low).
    - preferred_response_style: containing 'preferred_tone', 'what_helps' (list of strings), and 'what_to_avoid' (list of strings).

    Output ONLY valid JSON. Do not include markdown code block formatting or backticks around the JSON.
    """

    user_prompt = f"""
    Analyze the following user onboarding answers and generate the structured emotional profile:
    
    {answers_summary}
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
