"""Dashboard / My Growth API using canonical Knowing Me completion."""
from datetime import datetime, timedelta, timezone
import logging
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.emotion_log import EmotionLog
from app.models.onboarding import UserAnswer
from app.models.user_profile import UserProfile
from app.routes.auth import get_current_user
from app.services.onboarding_analyzer import onboarding_analyzer

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


async def _canonical_profile(db: AsyncSession, user_id: uuid.UUID):
    count_result = await db.execute(select(func.count(func.distinct(UserAnswer.question_id))).where(UserAnswer.user_id == user_id))
    answer_count = int(count_result.scalar() or 0)
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    pp = (profile.personality_profile or {}) if profile else {}
    needs_v2 = not profile or not profile.onboarding_completed or not pp or "age" not in pp or "gender" not in pp or "communication_style" not in pp
    if answer_count >= 27 and needs_v2:
        await onboarding_analyzer.analyze_onboarding_answers(db, user_id)
        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
    return profile, answer_count


@router.get("/stats")
async def get_dashboard_stats(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(current_user["id"])
    profile, answer_count = await _canonical_profile(db, user_id)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(select(EmotionLog).where(EmotionLog.user_id == user_id, EmotionLog.timestamp >= seven_days_ago).order_by(EmotionLog.timestamp.asc()))
    logs = list(result.scalars().all())
    mood_data = []
    for log in logs:
        score = float(log.confidence_score or 0.5)
        emotion = str(log.detected_emotion or "Neutral")
        positive = emotion.lower() in {"happy", "happiness", "excited", "excitement", "calm", "joy"}
        mood_data.append({"date": log.timestamp.isoformat() if log.timestamp else None, "mood": round(score if positive else max(0.05, 1.0 - score), 2)})
    completed = answer_count >= 27
    personality = (profile.personality_profile or {}) if profile else {}
    emotional = (profile.emotional_baseline or {}) if profile else {}
    style = (profile.preferred_response_style or {}) if profile else {}
    return {"user": {"name": personality.get("name") or current_user.get("name") or "Friend", "email": current_user.get("email")},
            "onboarding_completed": completed, "knowing_me_answer_count": answer_count, "knowing_me_total": 27,
            "mood_data": mood_data, "emotional_state": emotional, "personality": personality,
            "communication_style": style, "interests": personality.get("interests", []),
            "emotional_insights": {"current_challenge": personality.get("current_challenge"), "support_need": personality.get("primary_support_need"),
                "emotional_openness": personality.get("emotional_openness"), "social_energy": personality.get("social_energy"),
                "desired_change": personality.get("desired_change"), "sleep": emotional.get("sleep"),
                "life_satisfaction": emotional.get("life_satisfaction")} if completed else {}}


@router.get("/profile")
async def get_user_profile(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(current_user["id"])
    profile, answer_count = await _canonical_profile(db, user_id)
    completed = answer_count >= 27
    if not profile:
        return {"onboarding_completed": completed, "knowing_me_answer_count": answer_count, "personality_profile": {}, "emotional_baseline": {},
                "comfort_preferences": {}, "emotional_style": {}, "stress_triggers": {}, "preferred_response_style": {}, "emotional_summary": {}}
    return {"onboarding_completed": completed, "knowing_me_answer_count": answer_count, "personality_profile": profile.personality_profile or {},
            "emotional_baseline": profile.emotional_baseline or {}, "comfort_preferences": profile.comfort_preferences or {},
            "emotional_style": profile.emotional_style or {}, "stress_triggers": profile.stress_triggers or {},
            "preferred_response_style": profile.preferred_response_style or {}, "emotional_summary": profile.emotional_summary or {}}
