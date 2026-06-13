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
from app.services.profile_service import profile_service

logger = logging.getLogger(__name__)

ONBOARDING_QUESTIONS = {
    1: "Hey there! I'm Esona, your AI wellness companion. I'd love to get to know you a bit so I can be the best buddy possible. First, what should I call you? 😊",
    2: "Nice to meet you! How old are you?",
    3: "Got it! And what do you do?\n- School Student\n- College Student\n- Working Professional\n- Other",
    4: "Which year are you currently in?",
    5: "What are your hobbies and interests? (like Gaming, Sports, Anime, Reading, Music, Coding, or anything else!)",
    6: "What are your current goals?",
    7: "What usually stresses you out?",
    8: "What helps you feel better when stressed?",
    9: "Who do you usually talk to when you need support?",
    10: "How would you like me to talk to you? You can choose from:\n- Friendly Friend\n- Supportive Listener\n- Motivational Coach\n- Direct and Honest",
    11: "How is your sleep generally?\n- Good\n- Average\n- Poor",
}

ONBOARDING_PARSER_PROMPT = """You are an Onboarding Information Extractor. Your task is to extract the answer for a specific onboarding question from the user's message.

Onboarding Question Type: {question_type}
Question Asked: {question_text}
User Message: {user_message}

Instructions:
1. Extract the clean answer value appropriate for the question type.
2. Return a JSON object containing the parsed information.

Expected output formats based on Type:
- name: {{"name": "extracted name or nickname"}}
- age: {{"age": int or string}}
- profession: {{"profession": "School Student" | "College Student" | "Working Professional" | "Other"}}
- student_year: {{"student_year": "extracted year (e.g. 1st year, Sophomore, etc)"}}
- interests: {{"interests": ["interest1", "interest2", ...], "hobbies": ["hobby1", "hobby2", ...]}} (extract hobbies and interests as separate lists if possible, or same lists)
- goals: {{"goals": ["goal1", "goal2", ...]}}
- triggers: {{"stress_triggers": ["trigger1", "trigger2", ...]}}
- coping: {{"coping_mechanisms": ["coping1", "coping2", ...]}}
- support: {{"support_system": "extracted support system"}}
- style: {{"communication_style": "Friendly Friend" | "Supportive Listener" | "Motivational Coach" | "Direct and Honest"}}
- sleep: {{"sleep_habits": "Good" | "Average" | "Poor"}}

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
            1: "name",
            2: "age",
            3: "profession",
            4: "student_year",
            5: "interests",
            6: "goals",
            7: "triggers",
            8: "coping",
            9: "support",
            10: "style",
            11: "sleep"
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
            
            # Save parsed values to user_personality (UserProfile) and new UserPersonalProfile table
            profile_data = dict(profile.personality_profile or {})
            
            if stage == 1:
                name = parsed.get("name", message.strip())
                user.name = name
                profile_data["name"] = name
                await profile_service.update_profile(db, user.id, {"name": name})
            elif stage == 2:
                age = parsed.get("age", message.strip())
                profile_data["age"] = age
                await profile_service.update_profile(db, user.id, {"age": age})
            elif stage == 3:
                prof = parsed.get("profession", "Other")
                profile_data["profession"] = prof
                is_student = prof in ["School Student", "College Student"]
                if not is_student:
                    profile_data["student_year"] = "N/A"
                    await profile_service.update_profile(db, user.id, {
                        "profession": prof,
                        "student_year": "N/A"
                    })
                else:
                    await profile_service.update_profile(db, user.id, {"profession": prof})
            elif stage == 4:
                year = parsed.get("student_year", message.strip())
                profile_data["student_year"] = year
                await profile_service.update_profile(db, user.id, {"student_year": year})
            elif stage == 5:
                interests_list = parsed.get("interests", [message.strip()])
                hobbies_list = parsed.get("hobbies", [message.strip()])
                profile.interests = {"hobbies": hobbies_list + interests_list}
                user.interests = {"items": hobbies_list + interests_list}
                await profile_service.update_profile(db, user.id, {
                    "interests": interests_list,
                    "hobbies": hobbies_list
                })
            elif stage == 6:
                goals_list = parsed.get("goals", [message.strip()])
                profile_data["goals"] = goals_list
                await profile_service.update_profile(db, user.id, {"goals": goals_list})
            elif stage == 7:
                triggers_list = parsed.get("stress_triggers", [message.strip()])
                profile.stress_triggers = {"triggers": triggers_list}
                await profile_service.update_profile(db, user.id, {"stress_triggers": triggers_list})
            elif stage == 8:
                coping_list = parsed.get("coping_mechanisms", [message.strip()])
                await profile_service.update_profile(db, user.id, {"coping_mechanisms": coping_list})
            elif stage == 9:
                support = parsed.get("support_system", message.strip())
                await profile_service.update_profile(db, user.id, {"support_system": support})
            elif stage == 10:
                style = parsed.get("communication_style", "Friendly Friend")
                profile.communication_style = {"preferred_style": style}
                user.communication_style = style
                await profile_service.update_profile(db, user.id, {"communication_style": style})
            elif stage == 11:
                sleep = parsed.get("sleep_habits", "Average")
                await profile_service.update_profile(db, user.id, {"sleep_habits": sleep})
            
            # Determine next stage
            is_student = profile_data.get("profession") in ["School Student", "College Student"]
            if stage == 3 and not is_student:
                next_stage = 5
            else:
                next_stage = stage + 1

            profile_data["onboarding_stage"] = next_stage
            profile.personality_profile = profile_data
            
            # Save onboarding answers raw list
            ans_history = list(profile.onboarding_answers.get("answers", []))
            ans_history.append({
                "question_id": stage,
                "question_text": q_text,
                "user_answer": message
            })
            profile.onboarding_answers = {"answers": ans_history}
            
            db.add(profile)
            db.add(user)
            await db.flush()
            
            # If onboarding completed (finished stage 11 or skipped remaining to 12)
            if next_stage > 11:
                await self.finalize_profile(db, user, profile)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to parse onboarding answer for stage {stage}: {e}", exc_info=True)
            # Safe recovery fallback
            profile_data = dict(profile.personality_profile or {})
            is_student = profile_data.get("profession") in ["School Student", "College Student"]
            if stage == 3 and not is_student:
                next_stage = 5
            else:
                next_stage = stage + 1
            profile_data["onboarding_stage"] = next_stage
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
