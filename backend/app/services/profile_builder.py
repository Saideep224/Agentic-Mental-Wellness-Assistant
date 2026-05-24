"""
Service to dynamically rebuild or update a user's EmotionalProfile.
Incorporates recent conversation dynamics to adjust the profile over time.
"""

import json
import logging
import uuid
from typing import Dict, Any

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.emotional_profile import EmotionalProfile
from app.models.conversation import Message, Conversation

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """Handles incremental emotional profile adjustments based on conversation history."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_profile_from_history(self, user_id: uuid.UUID, limit: int = 30) -> EmotionalProfile:
        """
        Loads the last N user messages and the current profile, then uses OpenAI
        to update/refine the EmotionalProfile to reflect recent changes.
        """
        logger.info(f"Dynamically updating emotional profile for user {user_id}")

        # 1. Fetch current profile
        profile_res = await self.db.execute(
            select(EmotionalProfile).where(EmotionalProfile.user_id == user_id)
        )
        profile = profile_res.scalar_one_or_none()
        if not profile:
            raise ValueError("Emotional profile must exist (from onboarding) before updating from history.")

        # 2. Get recent conversation messages
        messages_res = await self.db.execute(
            select(Message)
            .join(Message.conversation)
            .where(
                Conversation.user_id == user_id,
                Message.role == "user",
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        user_messages = messages_res.scalars().all()
        if not user_messages:
            logger.info("No user messages found to update profile. Skipping update.")
            return profile

        messages_text = "\n".join([f"- {m.content}" for m in reversed(user_messages)])

        # 3. Format prompt for OpenAI
        current_profile_json = {
            "personality_type": profile.personality_type,
            "emotional_baseline": profile.emotional_baseline,
            "comfort_preferences": profile.comfort_preferences,
            "communication_style": profile.communication_style,
            "emotional_summary": profile.emotional_summary,
            "stress_patterns": profile.stress_patterns,
            "emotional_triggers": profile.emotional_triggers,
            "preferred_response_style": profile.preferred_response_style,
        }

        system_prompt = """
        You are an advanced psychological profiling system. You are given a user's current emotional profile and their recent conversation messages.
        Your job is to update and refine their profile to reflect any new patterns, shifts in mood, new emotional triggers, or changes in communication styles.
        
        Keep the profile updates natural and realistic. Do not make drastic changes based on a few messages, but adjust indicators like stress levels, dominant emotions, or comfort preferences if a clear pattern emerges.
        
        Return a single JSON object containing exactly these keys:
        - personality_type: containing 'type', 'description', 'strengths' (list of strings), 'growth_areas' (list of strings), and 'summary'.
        - emotional_baseline: containing 'dominant_emotion', 'tendencies' (list of strings), 'stress_level' (float between 1 and 10), and 'burnout_risk_assessment'.
        - comfort_preferences: containing 'safest_environment', 'escape_mechanisms' (list of strings), and 'mood_boosters' (list of strings).
        - communication_style: containing 'preferred_style', 'annoyances' (list of strings), and 'comfort_support_type'.
        - emotional_summary: containing a descriptive narrative summarizing their current emotional state, baseline, and tendencies.
        - stress_patterns: containing 'stress_triggers' (list of strings) and 'coping_mechanisms' (list of strings).
        - emotional_triggers: containing 'triggers' (list of strings) and 'overthinking_tendency' (high/medium/low).
        - preferred_response_style: containing 'preferred_tone', 'what_helps' (list of strings), and 'what_to_avoid' (list of strings).

        Output ONLY valid JSON.
        """

        user_prompt = f"""
        Current Profile:
        {json.dumps(current_profile_json, indent=2)}

        Recent user messages:
        {messages_text}
        
        Generate the updated emotional profile:
        """

        client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

        try:
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )


            raw_content = response.choices[0].message.content or "{}"
            updated_data = json.loads(raw_content)

            # Update profile properties if present in response
            if "personality_type" in updated_data:
                profile.personality_type = updated_data["personality_type"]
            if "emotional_baseline" in updated_data:
                profile.emotional_baseline = updated_data["emotional_baseline"]
            if "comfort_preferences" in updated_data:
                profile.comfort_preferences = updated_data["comfort_preferences"]
            if "communication_style" in updated_data:
                profile.communication_style = updated_data["communication_style"]
            if "emotional_summary" in updated_data:
                profile.emotional_summary = updated_data["emotional_summary"]
            if "stress_patterns" in updated_data:
                profile.stress_patterns = updated_data["stress_patterns"]
            if "emotional_triggers" in updated_data:
                profile.emotional_triggers = updated_data["emotional_triggers"]
            if "preferred_response_style" in updated_data:
                profile.preferred_response_style = updated_data["preferred_response_style"]

            await self.db.flush()
            logger.info(f"EmotionalProfile successfully updated for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to update profile from history: {e}", exc_info=True)

        return profile
