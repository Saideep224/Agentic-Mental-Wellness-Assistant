"""Deterministic Knowing Me analyzer using all 27 answers."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.onboarding import UserAnswer
from app.models.user_profile import UserProfile
from app.services.profile_service import profile_service, invalidate_profile_caches

logger = logging.getLogger(__name__)


def _value(answer: UserAnswer) -> Any:
    selected = list(answer.selected_answers or [])
    custom = (answer.custom_answer or "").strip()
    if custom and (not selected or any(str(x).lower() in {"other", "custom", "other (please specify)"} for x in selected)):
        return custom
    if custom and answer.question_id in {1, 7}: return custom
    if len(selected) == 1: return selected[0]
    return selected or custom


def _text(value: Any) -> str:
    return ", ".join(map(str, value)) if isinstance(value, list) else str(value or "")


def _list(value: Any) -> List[str]:
    if not value: return []
    return [str(x) for x in value] if isinstance(value, list) else [str(value)]


class OnboardingAnalyzer:
    async def analyze_onboarding_answers(self, db: AsyncSession, user_id) -> Dict[str, Any]:
        result = await db.execute(select(UserAnswer).where(UserAnswer.user_id == user_id).order_by(UserAnswer.question_id))
        answers = list(result.scalars().all())
        amap = {a.question_id: _value(a) for a in answers}
        completed = len(amap) >= 27

        personality_profile = {
            "age": _text(amap.get(1)), "profession": _text(amap.get(2)),
            "field_of_work": _text(amap.get(3)), "university": _text(amap.get(4)),
            "student_year": _text(amap.get(5)), "gender": _text(amap.get(6)),
            "name": _text(amap.get(7)), "current_challenge": _text(amap.get(8)),
            "advice_preference": _text(amap.get(9)), "primary_support_need": _text(amap.get(10)),
            "interests": _list(amap.get(11)), "hobbies": _list(amap.get(12)), "goals": _list(amap.get(13)),
            "communication_style": _text(amap.get(17)), "social_energy": _text(amap.get(19)),
            "confidence_style": _text(amap.get(20)), "emotional_openness": _text(amap.get(21)),
            "desired_change": _text(amap.get(27)),
        }
        emotional_baseline = {"sleep": _text(amap.get(18)), "life_satisfaction": _text(amap.get(26)),
                              "emotional_openness": _text(amap.get(21)), "confidence": _text(amap.get(20))}
        emotional_style = {"stress_response": _text(amap.get(22)), "overwhelm_pattern": _text(amap.get(23)),
                           "criticism_response": _text(amap.get(24)), "social_energy": _text(amap.get(19))}
        comfort_preferences = {"coping_mechanisms": _list(amap.get(15)), "support_system": _text(amap.get(16)),
                               "comfort_preference": _text(amap.get(25)), "primary_support_need": _text(amap.get(10))}
        stress_triggers = {"current_challenge": _text(amap.get(8)), "triggers": _list(amap.get(14)),
                           "overwhelm_pattern": _text(amap.get(23))}
        preferred_response_style = {"advice_preference": _text(amap.get(9)),
                                    "communication_style": _text(amap.get(17)),
                                    "age_calibration": _text(amap.get(1)),
                                    "tone_rule": "Match this user's own preferred communication style and emotional openness."}
        emotional_summary = {"current_challenge": _text(amap.get(8)), "support_need": _text(amap.get(10)),
                             "stress_response": _text(amap.get(22)), "comfort_preference": _text(amap.get(25)),
                             "desired_change": _text(amap.get(27))}

        profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()
        if not profile:
            profile = UserProfile(user_id=user_id, user_email="")
            db.add(profile)
        profile.personality_profile = personality_profile
        profile.emotional_baseline = emotional_baseline
        profile.comfort_preferences = comfort_preferences
        profile.emotional_style = emotional_style
        profile.stress_triggers = stress_triggers
        profile.preferred_response_style = preferred_response_style
        profile.emotional_summary = emotional_summary
        profile.onboarding_answers = {str(k): v for k, v in amap.items()}
        profile.onboarding_completed = completed
        profile.interests = {"items": personality_profile["interests"], "hobbies": personality_profile["hobbies"]}
        profile.communication_style = {"preferred_style": personality_profile["communication_style"]}
        profile.personality_type = {"social_energy": personality_profile["social_energy"],
                                    "confidence_style": personality_profile["confidence_style"],
                                    "emotional_openness": personality_profile["emotional_openness"]}
        profile.updated_at = datetime.now(timezone.utc)

        await profile_service.update_profile(db, user_id, {
            "age": amap.get(1), "profession": amap.get(2), "field_of_work": amap.get(3),
            "university": amap.get(4), "student_year": amap.get(5), "gender": amap.get(6), "name": amap.get(7),
            "current_challenge": amap.get(8), "advice_preference": amap.get(9), "primary_support_need": amap.get(10),
            "interests": _list(amap.get(11)), "hobbies": _list(amap.get(12)), "goals": _list(amap.get(13)),
            "stress_triggers": _list(amap.get(14)), "coping_mechanisms": _list(amap.get(15)),
            "support_system": amap.get(16), "communication_style": amap.get(17), "sleep_habits": amap.get(18),
        })
        invalidate_profile_caches(user_id)
        await db.commit()
        return {"personality_profile": personality_profile, "emotional_baseline": emotional_baseline,
                "comfort_preferences": comfort_preferences, "emotional_style": emotional_style,
                "stress_triggers": stress_triggers, "preferred_response_style": preferred_response_style,
                "emotional_summary": emotional_summary, "onboarding_completed": completed, "answer_count": len(amap)}


onboarding_analyzer = OnboardingAnalyzer()
