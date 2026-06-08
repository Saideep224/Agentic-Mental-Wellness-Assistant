"""
Onboarding Service – manages the step-by-step conversational onboarding flow
for new users inside the chat, parsing and saving answers permanently.
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.memory import Memory
from app.utils.llm import get_chat_client

logger = logging.getLogger(__name__)

ONBOARDING_QUESTIONS = {
    1: "Hey there! I'm Esona, your AI wellness companion. I'd love to get to know you a bit so I can be the best buddy possible. First, what should I call you? 😊",
    2: "Nice to meet you! How old are you?",
    3: "Got it! And what do you do? (School Student, College Student, Working Professional, or Other?)",
    4: "How would you like me to talk to you? You can choose from:\n- Friendly Friend\n- Supportive Listener\n- Motivational Coach\n- Honest and Direct",
    5: "What are your hobbies and interests? (like Gaming, Sports, Anime, Reading, Music, Coding, or anything else!)",
    6: "What are you currently working towards? (like Placements, Exams, Fitness, Business, or Mental Wellness?)",
    7: "What usually stresses you out? (like Exams, Deadlines, Relationships, Loneliness, Family Issues?)",
    8: "Is there anything else important you want me to remember about you?",
}

ONBOARDING_PARSER_PROMPT = """You are an Onboarding Information Extractor. Your task is to extract the answer for a specific onboarding question from the user's message.

Onboarding Question Type: {question_type}
Question Asked: {question_text}
User Message: {user_message}

Instructions:
1. Extract the clean answer value appropriate for the question type.
2. Return a JSON object containing the parsed information.

Expected output formats based on Type:
- identity: {{"name": "extracted name or nickname"}}
- age: {{"age": int or string}}
- profession: {{"profession": "School Student" | "College Student" | "Working Professional" | "Other"}}
- style: {{"communication_style": "Friendly Friend" | "Supportive Listener" | "Motivational Coach" | "Honest and Direct"}}
- interests: {{"interests": ["interest1", "interest2", ...]}} (extract hobbies)
- goals: {{"goals": ["goal1", "goal2", ...]}} (extract goals)
- triggers: {{"stress_triggers": ["trigger1", "trigger2", ...]}} (extract stressors)
- important_info: {{"important_info": "extracted important details" | null}}

Output ONLY valid JSON.
"""


class OnboardingService:
    """Orchestrates natural chat-based onboarding."""

    def get_question(self, stage: int) -> str:
        """Get the question string for a given onboarding stage."""
        return ONBOARDING_QUESTIONS.get(stage, "How can I help you today?")

    async def parse_and_save_answer(
        self, db: AsyncSession, user: User, profile: UserProfile, stage: int, message: str
    ) -> bool:
        """
        Parses the user's reply using LLM extraction, updates the profile database record,
        and advances the onboarding stage. Returns True if successfully parsed.
        """
        question_types = {
            1: "identity",
            2: "age",
            3: "profession",
            4: "style",
            5: "interests",
            6: "goals",
            7: "triggers",
            8: "important_info"
        }
        
        q_type = question_types.get(stage)
        q_text = self.get_question(stage)
        
        try:
            client = get_chat_client()
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": ONBOARDING_PARSER_PROMPT.format(
                        question_type=q_type,
                        question_text=q_text,
                        user_message=message
                    )}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            
            logger.info(f"[Onboarding Parser] Parsed stage {stage} response: {parsed}")
            
            # Save parsed values to user_personality (UserProfile)
            profile_data = dict(profile.personality_profile or {})
            
            if stage == 1:
                name = parsed.get("name", message.strip())
                user.name = name
                profile_data["name"] = name
            elif stage == 2:
                age = parsed.get("age", message.strip())
                profile_data["age"] = age
            elif stage == 3:
                prof = parsed.get("profession", "Other")
                profile_data["profession"] = prof
            elif stage == 4:
                style = parsed.get("communication_style", "Friendly Friend")
                profile.communication_style = {"preferred_style": style}
                user.communication_style = style
            elif stage == 5:
                interests_list = parsed.get("interests", [message.strip()])
                profile.interests = {"hobbies": interests_list}
                user.interests = {"items": interests_list}
            elif stage == 6:
                goals_list = parsed.get("goals", [message.strip()])
                profile_data["goals"] = goals_list
            elif stage == 7:
                triggers_list = parsed.get("stress_triggers", [message.strip()])
                profile.stress_triggers = {"triggers": triggers_list}
            elif stage == 8:
                info = parsed.get("important_info", message.strip())
                if info and info.lower() != "none" and info.lower() != "nothing":
                    profile_data["important_info"] = info
                    # Save as long term profile memory
                    from app.services.memory_service import memory_service
                    await memory_service.saveMemory(
                        db=db,
                        user_id=str(user.id),
                        memory_summary=f"User wants AI to remember: {info}",
                        behavior_patterns={
                            "memory_type": "profile",
                            "importance_score": 9,
                            "source": "conversational_onboarding"
                        }
                    )
            
            # Save onboarding answers raw list
            ans_history = list(profile.onboarding_answers.get("answers", []))
            ans_history.append({
                "question_id": stage,
                "question_text": q_text,
                "user_answer": message
            })
            profile.onboarding_answers = {"answers": ans_history}

            # Update personality profile block
            profile_data["onboarding_stage"] = stage + 1
            profile.personality_profile = profile_data
            
            db.add(profile)
            db.add(user)
            await db.flush()
            
            # If onboarding completed (finished stage 8)
            if stage >= 8:
                await self.finalize_profile(db, user, profile)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to parse onboarding answer for stage {stage}: {e}", exc_info=True)
            # Safe recovery fallback: increment stage and store raw answer
            profile_data = dict(profile.personality_profile or {})
            profile_data["onboarding_stage"] = stage + 1
            profile.personality_profile = profile_data
            db.add(profile)
            await db.flush()
            return False

    async def finalize_profile(self, db: AsyncSession, user: User, profile: UserProfile):
        """Compiles conversational onboarding answers to initialize personality metrics."""
        logger.info(f"Finalizing onboarding profiling for user: {user.id}")
        
        answers = profile.onboarding_answers.get("answers", [])
        answers_str = "\n".join([
            f"Q: {ans.get('question_text')}\nA: {ans.get('user_answer')}" for ans in answers
        ])
        
        system_prompt = """You are an advanced psychological profiling system.
Analyze the user's conversational onboarding answers and compile a structured emotional and personality profile.

Output ONLY a single JSON object matching this schema:
{
  "personality_type": {
    "type": "Descriptive Type (e.g. Creative Thinker)",
    "description": "Short explanation",
    "strengths": ["strength1", "strength2"],
    "growth_areas": ["growth1", "growth2"],
    "summary": "Short summary of user's mindset"
  },
  "emotional_baseline": {
    "dominant_emotion": "calm" | "neutral" | "anxious" | "stressed" | "overwhelmed",
    "tendencies": ["mood description"],
    "stress_level": 1.0-10.0,
    "burnout_risk_assessment": "assessment text"
  },
  "comfort_preferences": {
    "safest_environment": "description",
    "escape_mechanisms": ["music", "gaming", "etc"],
    "mood_boosters": ["factors"]
  },
  "reply_style": {
    "reply_style": "short_funny" | "short" | "deep_emotional" | "casual",
    "likes_humor": true | false,
    "paragraph_preference": "short" | "medium" | "long",
    "emoji_usage": "low" | "medium" | "high",
    "communication_style": "casual" | "gentle" | "direct" | "funny",
    "energy": "playful" | "calm" | "thoughtful" | "supportive"
  }
}"""

        try:
            client = get_chat_client()
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User answers:\n{answers_str}"}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            profile_data = json.loads(raw)
            
            # Save data
            profile.personality_type = profile_data.get("personality_type", {})
            profile.emotional_baseline = profile_data.get("emotional_baseline", {})
            profile.comfort_preferences = profile_data.get("comfort_preferences", {})
            profile.emotional_style = profile_data.get("emotional_baseline", {})
            profile.strengths = {"strengths": profile_data.get("personality_type", {}).get("strengths", [])}
            profile.weaknesses = {"weaknesses": profile_data.get("personality_type", {}).get("growth_areas", [])}
            
            p_type = profile_data.get("personality_type", {}).get("type", "Thoughtful Explorer")
            c_style = user.communication_style or "Friendly Friend"
            p_interests = profile.interests.get("hobbies", [])
            p_triggers = profile.stress_triggers.get("triggers", [])
            
            profile.personality_profile = {
                "type": p_type,
                "communication_style": c_style,
                "strengths": profile.strengths.get("strengths", []),
                "interests": p_interests,
                "stress_triggers": p_triggers,
                "motivation_style": "Empathetic check-ins",
                "reply_style": profile_data.get("reply_style", {
                    "reply_style": "casual",
                    "likes_humor": True,
                    "paragraph_preference": "short",
                    "emoji_usage": "medium",
                    "communication_style": "casual",
                    "energy": "supportive"
                })
            }
            
            # Update user tables
            user.personality_profile = profile.personality_profile
            user.personality_type = p_type
            user.communication_style = c_style
            user.onboarding_completed = True
            
            profile.onboarding_completed = True
            
            logger.info(f"[Onboarding finalized] Successfully compiled profile for {user.id}")
            
        except Exception as e:
            logger.error(f"Failed to compile profile during onboarding finalization: {e}", exc_info=True)
            # Minimal fallback setup to prevent locking user out
            user.onboarding_completed = True
            profile.onboarding_completed = True
            
        db.add(profile)
        db.add(user)
        await db.flush()


# Export standard singleton
onboarding_service = OnboardingService()
