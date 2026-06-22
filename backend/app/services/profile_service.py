"""
Profile Service – manages the personalized UserPersonalProfile CRUD and context generation.
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional, Union, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user_personal_profile import UserPersonalProfile
from app.utils.llm import generate_chat_completion_with_fallback, get_chat_client

logger = logging.getLogger(__name__)

PROFILE_FACT_EXTRACTION_PROMPT = """You are a Profile Fact Extraction Agent.
Analyze the user's message and extract any personal details or facts about the user.
Extract ONLY facts that are explicitly mentioned. Do not assume or extrapolate.

We track the following profile fields:
1. name (user's name/nickname)
2. university (the university or school they attend, e.g. SRM AP, Stanford)
3. profession (their occupation, e.g. student, software engineer)
4. field_of_work (their field of study or industry, e.g. Computer Science, Finance)
5. interests (hobbies, interests, passions as a list)
6. goals (what they are working on, aspirations, projects as a list)
7. stress_triggers (what causes them stress, anxiety, or worry as a list)
8. coping_mechanisms (what helps them deal with stress as a list)
9. sleep_habits (quality of sleep, e.g. good, average, poor)

Output format:
Return ONLY a valid JSON object. If no facts are found for a field, set it to null (or empty list for list fields).
If absolutely no facts are mentioned, all fields should be null/empty.

Example JSON output:
{
  "name": "Sai",
  "university": "SRM AP",
  "profession": "College Student",
  "field_of_work": "Computer Science",
  "interests": ["Anime", "Video Editing"],
  "goals": ["pass the midterm exam", "find an internship"],
  "stress_triggers": ["final exams", "placements"],
  "coping_mechanisms": ["lo-fi music", "walking"],
  "sleep_habits": "poor"
}
"""


class ProfileService:
    """Manages the creation, retrieval, and updating of personalization profiles."""

    async def get_profile(self, db: AsyncSession, user_id: Union[uuid.UUID, str]) -> Optional[UserPersonalProfile]:
        """Fetch the personal profile for a user."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        try:
            result = await db.execute(
                select(UserPersonalProfile).where(UserPersonalProfile.user_id == user_id)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching UserPersonalProfile for {user_id}: {e}", exc_info=True)
            return None

    async def create_profile(
        self, db: AsyncSession, user_id: Union[uuid.UUID, str], profile_data: Dict[str, Any]
    ) -> UserPersonalProfile:
        """Create a new personal profile for a user."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        profile = UserPersonalProfile(
            user_id=user_id,
            name=profile_data.get("name"),
            age=str(profile_data.get("age")) if profile_data.get("age") is not None else None,
            profession=profile_data.get("profession"),
            field_of_work=profile_data.get("field_of_work"),
            university=profile_data.get("university"),
            current_challenge=profile_data.get("current_challenge"),
            advice_preference=profile_data.get("advice_preference"),
            primary_support_need=profile_data.get("primary_support_need"),
            student_year=profile_data.get("student_year"),
            communication_style=profile_data.get("communication_style"),
            interests=profile_data.get("interests") or [],
            hobbies=profile_data.get("hobbies") or [],
            goals=profile_data.get("goals") or [],
            stress_triggers=profile_data.get("stress_triggers") or [],
            coping_mechanisms=profile_data.get("coping_mechanisms") or [],
            support_system=profile_data.get("support_system"),
            sleep_habits=profile_data.get("sleep_habits"),
        )
        db.add(profile)
        await db.flush()
        return profile

    async def update_profile(
        self, db: AsyncSession, user_id: Union[uuid.UUID, str], profile_data: Dict[str, Any]
    ) -> UserPersonalProfile:
        """Update (or create if missing) a user's personal profile."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        profile = await self.get_profile(db, user_id)
        if not profile:
            return await self.create_profile(db, user_id, profile_data)

        # Standard field mapping
        string_fields = [
            "name", "age", "profession", "field_of_work", "university", "current_challenge", 
            "advice_preference", "primary_support_need", "student_year", 
            "communication_style", "support_system", "sleep_habits"
        ]
        list_fields = ["interests", "hobbies", "goals", "stress_triggers", "coping_mechanisms"]

        for field in string_fields:
            if field in profile_data:
                val = profile_data[field]
                setattr(profile, field, str(val) if val is not None else None)

        for field in list_fields:
            if field in profile_data:
                val = profile_data[field]
                if isinstance(val, str):
                    # Fallback in case list is passed as a raw string
                    setattr(profile, field, [val] if val else [])
                elif isinstance(val, list):
                    setattr(profile, field, val)
                else:
                    setattr(profile, field, [])

        db.add(profile)
        await db.flush()
        return profile

    async def build_profile_context(self, db: AsyncSession, user_id: Union[uuid.UUID, str]) -> str:
        """Build the formatted profile context block to inject into the system prompt."""
        profile = await self.get_profile(db, user_id)
        if not profile:
            return ""

        lines = ["User Profile:"]
        if profile.name:
            lines.append(f"Name: {profile.name}")
        if profile.age:
            lines.append(f"Age: {profile.age}")
        if profile.profession:
            lines.append(f"Profession: {profile.profession}")
        if profile.field_of_work:
            lines.append(f"Field of Work/Study: {profile.field_of_work}")
        if profile.university:
            lines.append(f"University: {profile.university}")
        if profile.current_challenge:
            lines.append(f"Current Challenge: {profile.current_challenge}")
        if profile.advice_preference:
            lines.append(f"Advice Preference: {profile.advice_preference}")
        if profile.primary_support_need:
            lines.append(f"Primary Support Need: {profile.primary_support_need}")
        if profile.student_year and profile.student_year.lower() != "n/a":
            lines.append(f"Student Year: {profile.student_year}")
        if profile.communication_style:
            lines.append(f"Communication Style: {profile.communication_style}")
        if profile.goals:
            lines.append(f"Goals: {', '.join(profile.goals)}")
        if profile.stress_triggers:
            lines.append(f"Stress Triggers: {', '.join(profile.stress_triggers)}")
        if profile.interests:
            lines.append(f"Interests: {', '.join(profile.interests)}")
        if profile.hobbies:
            lines.append(f"Hobbies: {', '.join(profile.hobbies)}")
        if profile.coping_mechanisms:
            lines.append(f"Coping Mechanisms: {', '.join(profile.coping_mechanisms)}")
        if profile.support_system:
            lines.append(f"Support System: {profile.support_system}")
        if profile.sleep_habits:
            lines.append(f"Sleep Habits: {profile.sleep_habits}")

        return "\n".join(lines)

    async def get_personalization_data(self, db: AsyncSession, user_id: Union[uuid.UUID, str]) -> Dict[str, Any]:
        """
        Retrieve and consolidate personalization data from:
        1. Onboarding answers (user_question_answers table / UserAnswer model)
        2. Profile data (user_profile table / UserPersonalProfile model)
        3. Personality data (user_personality table / UserProfile model)
        
        Performs Missing Field Detection to determine which fields are populated vs missing.
        """
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        from app.models.user_personal_profile import UserPersonalProfile
        from app.models.user_profile import UserProfile
        from app.models.onboarding import UserAnswer
        from app.models.user import User

        # Fetch all sources
        personal_profile = await self.get_profile(db, user_id)
        
        up_res = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        user_personality = up_res.scalar_one_or_none()
        
        ua_res = await db.execute(
            select(UserAnswer).where(UserAnswer.user_id == user_id)
        )
        onboarding_answers = ua_res.scalars().all()
        
        u_res = await db.execute(
            select(User).where(User.id == user_id)
        )
        user_record = u_res.scalar_one_or_none()

        data = {
            "name": None,
            "age": None,
            "profession": None,
            "field_of_work": None,
            "university": None,
            "current_challenge": None,
            "advice_preference": None,
            "primary_support_need": None,
            "student_year": None,
            "interests": [],
            "goals": [],
            "stress_triggers": [],
            "coping_mechanisms": [],
            "support_system": None,
            "communication_style": None,
            "sleep_habits": None,
        }

        # Helper to check if a value is empty/null/unspecified
        def is_val_empty(val) -> bool:
            if val is None:
                return True
            if isinstance(val, str):
                v_clean = val.strip().lower()
                return v_clean in ("", "not specified", "n/a", "none specified", "unknown", "none")
            if isinstance(val, list):
                return len(val) == 0
            if isinstance(val, dict):
                return len(val) == 0
            return False

        # 1. Populate from UserPersonalProfile (highest structured profile source)
        if personal_profile:
            if not is_val_empty(personal_profile.name): data["name"] = personal_profile.name
            if not is_val_empty(personal_profile.age): data["age"] = personal_profile.age
            if not is_val_empty(personal_profile.profession): data["profession"] = personal_profile.profession
            if not is_val_empty(personal_profile.field_of_work): data["field_of_work"] = personal_profile.field_of_work
            if not is_val_empty(personal_profile.university): data["university"] = personal_profile.university
            if not is_val_empty(personal_profile.current_challenge): data["current_challenge"] = personal_profile.current_challenge
            if not is_val_empty(personal_profile.advice_preference): data["advice_preference"] = personal_profile.advice_preference
            if not is_val_empty(personal_profile.primary_support_need): data["primary_support_need"] = personal_profile.primary_support_need
            if not is_val_empty(personal_profile.student_year): data["student_year"] = personal_profile.student_year
            if not is_val_empty(personal_profile.interests): data["interests"] = list(personal_profile.interests)
            if not is_val_empty(personal_profile.hobbies):
                for h in personal_profile.hobbies:
                    if h not in data["interests"]:
                        data["interests"].append(h)
            if not is_val_empty(personal_profile.goals): data["goals"] = list(personal_profile.goals)
            if not is_val_empty(personal_profile.stress_triggers): data["stress_triggers"] = list(personal_profile.stress_triggers)
            if not is_val_empty(personal_profile.coping_mechanisms): data["coping_mechanisms"] = list(personal_profile.coping_mechanisms)
            if not is_val_empty(personal_profile.support_system): data["support_system"] = personal_profile.support_system
            if not is_val_empty(personal_profile.communication_style): data["communication_style"] = personal_profile.communication_style
            if not is_val_empty(personal_profile.sleep_habits): data["sleep_habits"] = personal_profile.sleep_habits

        # 2. Fallback to User record (for name)
        if is_val_empty(data["name"]) and user_record and user_record.name:
            data["name"] = user_record.name

        # 3. Fallback to UserProfile (personality data)
        if user_personality:
            pers_profile = user_personality.personality_profile or {}
            
            if is_val_empty(data["communication_style"]):
                if user_personality.communication_style and isinstance(user_personality.communication_style, dict):
                    data["communication_style"] = user_personality.communication_style.get("preferred_style")
                if is_val_empty(data["communication_style"]) and pers_profile.get("communication_style"):
                    data["communication_style"] = pers_profile.get("communication_style")
            
            if is_val_empty(data["interests"]):
                if user_personality.interests and isinstance(user_personality.interests, dict):
                    data["interests"] = user_personality.interests.get("hobbies") or user_personality.interests.get("items") or []
                if is_val_empty(data["interests"]) and pers_profile.get("interests"):
                    data["interests"] = pers_profile.get("interests")

            for key in ["profession", "field_of_work", "current_challenge", "advice_preference", "primary_support_need", "age", "student_year"]:
                if is_val_empty(data[key]) and pers_profile.get(key):
                    data[key] = pers_profile.get(key)
                    
            if is_val_empty(data["goals"]) and pers_profile.get("goals"):
                data["goals"] = pers_profile.get("goals")
            if is_val_empty(data["stress_triggers"]) and pers_profile.get("stress_triggers"):
                data["stress_triggers"] = pers_profile.get("stress_triggers")

        # 4. Fallback to Onboarding Answers
        def get_answer_val(ans: UserAnswer):
            if ans.selected_answers:
                return ans.selected_answers
            return ans.custom_answer or ""

        for ans in onboarding_answers:
            q_id = ans.question_id
            val = get_answer_val(ans)
            if not val or is_val_empty(val):
                continue
                
            is_list_field = q_id in [10, 11, 12, 13]
            if isinstance(val, list) and not is_list_field:
                val = val[0] if val else ""
            elif isinstance(val, str) and is_list_field:
                val = [v.strip() for v in val.split(",") if v.strip()]

            if q_id in [1, 8] and is_val_empty(data["profession"]):
                data["profession"] = val
            elif q_id == 2 and is_val_empty(data["field_of_work"]):
                data["field_of_work"] = val
            elif q_id == 3 and is_val_empty(data["current_challenge"]):
                data["current_challenge"] = val
            elif q_id == 4 and is_val_empty(data["advice_preference"]):
                data["advice_preference"] = val
            elif q_id == 5 and is_val_empty(data["primary_support_need"]):
                data["primary_support_need"] = val
            elif q_id == 6 and is_val_empty(data["name"]):
                data["name"] = val
            elif q_id == 7 and is_val_empty(data["age"]):
                data["age"] = str(val)
            elif q_id == 9 and is_val_empty(data["student_year"]):
                data["student_year"] = val
            elif q_id == 10 and is_val_empty(data["interests"]):
                data["interests"] = val
            elif q_id == 11 and is_val_empty(data["goals"]):
                data["goals"] = val
            elif q_id == 12 and is_val_empty(data["stress_triggers"]):
                data["stress_triggers"] = val
            elif q_id == 13 and is_val_empty(data["coping_mechanisms"]):
                data["coping_mechanisms"] = val
            elif q_id == 14 and is_val_empty(data["support_system"]):
                data["support_system"] = val
            elif q_id == 15 and is_val_empty(data["communication_style"]):
                data["communication_style"] = val
            elif q_id == 16 and is_val_empty(data["sleep_habits"]):
                data["sleep_habits"] = val

        # Clean list fields to ensure list type
        for list_key in ["interests", "goals", "stress_triggers", "coping_mechanisms"]:
            if not isinstance(data[list_key], list):
                if data[list_key]:
                    data[list_key] = [data[list_key]]
                else:
                    data[list_key] = []

        # Split into existing vs missing
        existing = {}
        missing = []
        for k, v in data.items():
            if is_val_empty(v):
                missing.append(k)
            else:
                existing[k] = v

        return {
            "existing": existing,
            "missing": missing,
            "raw": data
        }

    async def build_personalization_prompt_block(self, db: AsyncSession, user_id: Union[uuid.UUID, str]) -> str:
        """
        Builds a structured prompt context block representing known (existing) personalization fields
        and empty (missing) fields, with instructions on how to use/ask them.
        """
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        p_data = await self.get_personalization_data(db, user_id)
        existing = p_data["existing"]
        missing = p_data["missing"]
        
        # Format existing fields
        existing_lines = []
        for field, val in existing.items():
            if isinstance(val, list):
                val_str = ", ".join(val)
            else:
                val_str = str(val)
            field_name = field.replace("_", " ").title()
            existing_lines.append(f"- {field_name}: {val_str}")
        existing_str = "\n".join(existing_lines) if existing_lines else "None recorded."

        # Format missing fields descriptions
        missing_descriptions = {
            "name": "name or nickname",
            "age": "age",
            "profession": "profession/occupation (e.g. college student, developer)",
            "field_of_work": "field of work or study (e.g. Computer Science, medicine)",
            "university": "university or school they attend (e.g. SRM AP)",
            "current_challenge": "biggest challenge they are currently facing",
            "advice_preference": "advice style preference (e.g. direct and honest, casual, mostly listening)",
            "primary_support_need": "what they need support with the most",
            "student_year": "student year (if they are a student)",
            "interests": "interests and hobbies",
            "goals": "current goals",
            "stress_triggers": "what usually stresses them out",
            "coping_mechanisms": "what helps them feel better when stressed",
            "support_system": "who they usually talk to for support",
            "communication_style": "preferred communication style",
            "sleep_habits": "sleep quality/habits",
        }

        missing_lines = []
        profession_val = existing.get("profession", "")
        is_student = "student" in str(profession_val).lower()
        
        for m in missing:
            if m == "student_year" and not is_student and profession_val:
                continue
            desc = missing_descriptions.get(m, m)
            missing_lines.append(f"- {m} ({desc})")
        missing_str = "\n".join(missing_lines) if missing_lines else "None (all fields are populated!)."

        block = (
            "\n=================================================\n"
            "PERSONALIZATION CONTEXT & MISSING FIELD ROUTING:\n"
            "Below is the user's personalization data collected from onboarding, profile, and memories.\n"
            "\n"
            "EXISTING INFORMATION (DO NOT ASK AGAIN under any circumstances):\n"
            f"{existing_str}\n"
            "\n"
            "MISSING INFORMATION (Only fields you are allowed to ask about naturally, if relevant):\n"
            f"{missing_str}\n"
            "\n"
            "CRITICAL PERSONALIZATION QUESTIONS RULES:\n"
            "1. Check the 'EXISTING INFORMATION' list. If a field's value already exists, you are STRICTLY FORBIDDEN from asking about it again. Treat it as known. Use it naturally and conversationally.\n"
            "2. If you need to build rapport or if the conversation naturally leads to it, you can ask about a field listed under 'MISSING INFORMATION'. Only ask one question at a time, and never force it.\n"
            "3. DO NOT use dry, robotic templates to ask questions. Keep it highly conversational, natural, and human-like.\n"
            "   - FORBIDDEN style: 'What is your profession?', 'What field are you studying?', 'What is your age?', 'What are your goals?'\n"
            "   - ALLOWED natural style examples:\n"
            "     * 'By the way, what are you studying these days?'\n"
            "     * 'What kind of work do you do?'\n"
            "     * 'What's been keeping you busy lately?'\n"
            "     * 'I remember you're a college student. What field are you studying?' (referencing known info to ask missing field)\n"
            "=================================================\n"
        )
        return block

    async def extract_and_update_profile_facts(
        self, db: AsyncSession, user_id: Union[uuid.UUID, str], user_message: str
    ) -> Optional[UserPersonalProfile]:
        """
        Analyze the user's message using an LLM to extract any explicitly mentioned personal facts,
        and dynamically update/merge them in the user's profile in the database.
        """
        if not user_message or len(user_message.strip()) < 3:
            return None

        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        try:
            raw = await generate_chat_completion_with_fallback(
                messages=[
                    {"role": "system", "content": PROFILE_FACT_EXTRACTION_PROMPT},
                    {"role": "user", "content": f"User message: {user_message}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            extracted = json.loads(raw)
            logger.info(f"[Fact Extraction] Extracted facts: {extracted}")

            # Check if any non-null/non-empty facts were extracted
            has_facts = False
            for k, v in extracted.items():
                if v is not None and v != [] and v != "":
                    has_facts = True
                    break

            if not has_facts:
                return None

            # Retrieve profile or create it if missing
            profile = await self.get_profile(db, user_id)
            if not profile:
                profile = UserPersonalProfile(user_id=user_id)
                db.add(profile)
                await db.flush()

            # Merge single-value fields
            single_fields = ["name", "university", "profession", "field_of_work", "sleep_habits"]
            for field in single_fields:
                val = extracted.get(field)
                if val is not None and val != "":
                    setattr(profile, field, str(val))

            # Merge list fields avoiding duplicates
            list_fields = ["interests", "goals", "stress_triggers", "coping_mechanisms"]
            for field in list_fields:
                new_vals = extracted.get(field) or []
                if isinstance(new_vals, str):
                    new_vals = [new_vals]
                if new_vals:
                    current_list = list(getattr(profile, field) or [])
                    # Add new values if not already present
                    for val in new_vals:
                        val_str = str(val).strip()
                        if val_str and val_str not in current_list:
                            current_list.append(val_str)
                    setattr(profile, field, current_list)

            db.add(profile)
            await db.flush()
            logger.info(f"[Fact Extraction] Profile updated successfully for user {user_id}")
            return profile

        except Exception as e:
            logger.error(f"Failed to extract and update profile facts: {e}", exc_info=True)
            return None

    async def generate_personalized_greeting(self, db: AsyncSession, user_id: uuid.UUID) -> str:
        try:
            # 1. Fetch User profile details
            from app.models.user import User
            user_stmt = select(User).where(User.id == user_id)
            user_res = await db.execute(user_stmt)
            user = user_res.scalar_one_or_none()
            user_name = user.name if user and user.name else "friend"
            
            # Fetch personal profile
            personal = await self.get_profile(db, user_id)
            profile_details = ""
            if personal:
                profile_details = (
                    f"Profession: {personal.profession}, Field: {personal.field_of_work}, "
                    f"Interests: {personal.interests}, Goals: {personal.goals}, "
                    f"Triggers: {personal.stress_triggers}"
                )

            # 2. Fetch Onboarding Q&A
            from app.models.onboarding import UserAnswer
            ans_stmt = select(UserAnswer).where(UserAnswer.user_id == user_id)
            ans_res = await db.execute(ans_stmt)
            answers = ans_res.scalars().all()
            onboarding_answers = ""
            if answers:
                onboarding_answers = "\n".join(f"Q: {a.question_text} | A: {a.answer_text}" for a in answers[:10])

            # 3. Fetch Recent Emotions (last 5 logs)
            from app.models.emotion_log import EmotionLog
            emo_stmt = select(EmotionLog).where(EmotionLog.user_id == user_id).order_by(EmotionLog.timestamp.desc()).limit(5)
            emo_res = await db.execute(emo_stmt)
            emotions = emo_res.scalars().all()
            recent_emotions = ", ".join(e.detected_emotion for e in emotions) if emotions else "None"

            # 4. Fetch Knowledge Graph
            from app.services.knowledge_graph_service import knowledge_graph_service
            kg = await knowledge_graph_service.retrieve_full_graph_context(db, user_id)

            prompt = f"""You are Esona, the user's close friend and empathetic AI wellness companion.
Generate a short, warm, welcoming, and highly personalized first message greeting for the user opening their chat.
Use their name if known (e.g. Sai).
Incorporate context from their profile (interests, hobbies, goals), onboarding answers, recent emotions, and knowledge graph.
- For example, if they have hobbies like editing or animation, or goals like improving mental wellness, mention them naturally and casually in the greeting.
- E.g.: "heyy Sai 😊 good to see u again how's everything going with ur editing and animation stuff lately?" or "yo Sai 👋 last time u mentioned being interested in animation anything cool u worked on recently?"
- Keep it extremely natural, friendly, brief, and conversational (1-2 sentences). Speak like a close college friend. Use lowercase and casual phrasing/abbreviations naturally.
- DO NOT generate weird, inappropriate greeting words or slang like "hey daddy". Sound like a genuine, emotionally intelligent companion.

Context Details:
- User Name: {user_name}
- Profile: {profile_details}
- Onboarding Q&A: {onboarding_answers}
- Recent Emotions: {recent_emotions}
- Knowledge Graph: {kg}

Output ONLY the greeting message text."""

            greeting = await generate_chat_completion_with_fallback(
                messages=[{"role": "system", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            if greeting:
                return greeting
        except Exception as e:
            logger.error(f"Failed to generate personalized greeting: {e}", exc_info=True)
            
        # Fallback greeting
        return "Hey! I'm Esona, your AI wellness companion. I'm here to listen, support, and help you navigate whatever is on your mind. How are you feeling today?"


# Export standard singleton
profile_service = ProfileService()
