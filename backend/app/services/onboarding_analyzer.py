"""Deterministic Knowing Me analyzer using all 27 answers."""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.onboarding import UserAnswer
from app.models.user_profile import UserProfile
from app.models.knowledge_graph import KnowledgeGraphRelation
from app.services.profile_service import profile_service, invalidate_profile_caches

logger = logging.getLogger(__name__)


def _value(answer: UserAnswer) -> Any:
    selected = list(answer.selected_answers or [])
    custom = (answer.custom_answer or "").strip()
    if custom and (not selected or any(str(x).lower() in {"other", "custom", "other (please specify)"} for x in selected)): return custom
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
            "age": _text(amap.get(27)),
            "profession": _text(amap.get(1)),
            "field_of_work": _text(amap.get(2)),
            "university": "",
            "student_year": "",
            "gender": _text(amap.get(26)),
            "name": "",
            "current_challenge": _text(amap.get(3)),
            "advice_preference": _text(amap.get(4)),
            "primary_support_need": _text(amap.get(5)),
            "interests": _list(amap.get(16)) + _list(amap.get(17)),
            "hobbies": _list(amap.get(19)),
            "goals": _list(amap.get(5)),
            "communication_style": _text(amap.get(21)),
            "social_energy": _text(amap.get(24)),
            "confidence_style": _text(amap.get(7)),
            "emotional_openness": _text(amap.get(25)),
            "desired_change": _text(amap.get(25))
        }
        emotional_baseline = {
            "sleep": _text(amap.get(11)),
            "life_satisfaction": _text(amap.get(15)),
            "emotional_openness": _text(amap.get(25)),
            "confidence": _text(amap.get(7))
        }
        emotional_style = {
            "stress_response": _text(amap.get(12)),
            "overwhelm_pattern": _text(amap.get(8)),
            "criticism_response": _text(amap.get(22)),
            "social_energy": _text(amap.get(24))
        }
        comfort_preferences = {
            "coping_mechanisms": _list(amap.get(20)),
            "support_system": _text(amap.get(23)),
            "comfort_preference": _text(amap.get(18)),
            "primary_support_need": _text(amap.get(5))
        }
        stress_triggers = {
            "current_challenge": _text(amap.get(3)),
            "triggers": _list(amap.get(8)),
            "overwhelm_pattern": _text(amap.get(12))
        }
        preferred_response_style = {
            "advice_preference": _text(amap.get(4)),
            "communication_style": _text(amap.get(21)),
            "age_calibration": _text(amap.get(27)),
            "tone_rule": "Match this user's own preferred communication style and emotional openness."
        }
        emotional_summary = {
            "current_challenge": _text(amap.get(3)),
            "support_need": _text(amap.get(5)),
            "stress_response": _text(amap.get(12)),
            "comfort_preference": _text(amap.get(18)),
            "desired_change": _text(amap.get(25))
        }

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
        profile.personality_type = {"social_energy": personality_profile["social_energy"], "confidence_style": personality_profile["confidence_style"], "emotional_openness": personality_profile["emotional_openness"]}
        profile.updated_at = datetime.now(timezone.utc)

        await profile_service.update_profile(db, user_id, {
            "age": _text(amap.get(27)),
            "profession": _text(amap.get(1)),
            "field_of_work": _text(amap.get(2)),
            "university": "",
            "student_year": "",
            "gender": _text(amap.get(26)),
            "name": "",
            "current_challenge": _text(amap.get(3)),
            "advice_preference": _text(amap.get(4)),
            "primary_support_need": _text(amap.get(5)),
            "interests": _list(amap.get(16)) + _list(amap.get(17)),
            "hobbies": _list(amap.get(19)),
            "goals": _list(amap.get(5)),
            "stress_triggers": _list(amap.get(8)),
            "coping_mechanisms": _list(amap.get(20)),
            "support_system": _text(amap.get(23)),
            "sleep_habits": _text(amap.get(11))
        })

        await db.execute(delete(KnowledgeGraphRelation).where(KnowledgeGraphRelation.user_id == user_id, KnowledgeGraphRelation.predicate.like("knowing_me_%")))
        graph_fields = {
            1: "profession", 2: "field", 3: "challenge", 4: "advice_preference", 5: "support_need",
            6: "tiring_day_response", 7: "self_description", 8: "energy_drainer", 9: "upset_texting_style",
            10: "mind_default_mode", 11: "sleep_habit", 12: "first_stress_response", 13: "mood_speed_trigger",
            14: "exhaustion_frequency", 15: "weather_emotion", 16: "interest", 17: "interest", 18: "safest_environment",
            19: "hobby", 20: "coping_mechanism", 21: "communication_style", 22: "annoying_replies", 23: "low_support_method",
            24: "social_battery_state", 25: "wished_understanding", 26: "gender", 27: "age"
        }
        for qid, predicate in graph_fields.items():
            for item in _list(amap.get(qid)):
                if item.strip():
                    db.add(KnowledgeGraphRelation(user_id=user_id, subject="User", predicate=f"knowing_me_{predicate}", object=item[:255], confidence=1.0))

        invalidate_profile_caches(user_id)
        await db.commit()
        return {"personality_profile": personality_profile, "emotional_baseline": emotional_baseline, "comfort_preferences": comfort_preferences,
                "emotional_style": emotional_style, "stress_triggers": stress_triggers, "preferred_response_style": preferred_response_style,
                "emotional_summary": emotional_summary, "onboarding_completed": completed, "answer_count": len(amap)}


onboarding_analyzer = OnboardingAnalyzer()


async def analyze_onboarding(user_id, answers=None, db: AsyncSession | None = None) -> Dict[str, Any]:
    """Backward-compatible service entrypoint used by onboarding routes and service exports.

    The canonical analyzer reads the persisted answers from the database. ``answers`` is
    accepted only to preserve the historical call signature; saved UserAnswer rows remain
    the single source of truth.
    """
    if db is None:
        raise ValueError("A database session is required for onboarding analysis")
    return await onboarding_analyzer.analyze_onboarding_answers(db, user_id)
