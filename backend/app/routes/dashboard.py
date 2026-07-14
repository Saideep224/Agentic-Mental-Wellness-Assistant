"""Dashboard / My Growth API using canonical Knowing Me completion."""
from datetime import datetime, timedelta, timezone
import logging
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.emotion_log import EmotionLog
from app.models.mood_log import MoodLog
from app.models.onboarding import UserAnswer
from app.models.user_profile import UserProfile
from app.routes.auth import get_current_user
from app.services.onboarding_analyzer import onboarding_analyzer
from app.schemas.dashboard import (
    MoodDataPoint,
    MoodTrendsResponse,
    EmotionalProfileResponse,
    StressPattern,
    StressPatternsResponse,
    InsightItem,
    InsightsResponse,
    GrowthInsightItem,
    GrowthInsightsResponse,
)

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
    
    from app.config import settings
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    if not settings.is_postgres:
        seven_days_ago = seven_days_ago.replace(tzinfo=None)
        
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


@router.get("/emotional-profile")
@router.get("/profile")
async def get_user_profile(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(current_user["id"])
    profile, answer_count = await _canonical_profile(db, user_id)
    completed = answer_count >= 27
    
    # Retrieve onboarding answers list formatted for the frontend
    answers_result = await db.execute(
        select(UserAnswer)
        .where(UserAnswer.user_id == user_id)
        .order_by(UserAnswer.question_id.asc())
    )
    db_answers = answers_result.scalars().all()
    onboarding_answers_list = [
        {
            "question_id": ans.question_id,
            "category": ans.category,
            "selected_answers": ans.selected_answers,
            "custom_answer": ans.custom_answer,
        }
        for ans in db_answers
    ]
    
    if not profile:
        return {"onboarding_completed": completed, "knowing_me_answer_count": answer_count, "personality_profile": {}, "emotional_baseline": {},
                "comfort_preferences": {}, "emotional_style": {}, "stress_triggers": {}, "preferred_response_style": {}, "emotional_summary": {},
                "onboarding_answers": {"answers": onboarding_answers_list}}
    return {"onboarding_completed": completed, "knowing_me_answer_count": answer_count, "personality_profile": profile.personality_profile or {},
            "emotional_baseline": profile.emotional_baseline or {}, "comfort_preferences": profile.comfort_preferences or {},
            "emotional_style": profile.emotional_style or {}, "stress_triggers": profile.stress_triggers or {},
            "preferred_response_style": profile.preferred_response_style or {}, "emotional_summary": profile.emotional_summary or {},
            "onboarding_answers": {"answers": onboarding_answers_list}}


@router.get("/mood-trends", response_model=MoodTrendsResponse)
async def get_dashboard_mood_trends(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(current_user["id"]) if isinstance(current_user, dict) else current_user.id
    
    from app.config import settings
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=15)
    if not settings.is_postgres:
        seven_days_ago = seven_days_ago.replace(tzinfo=None)
        
    result = await db.execute(
        select(EmotionLog)
        .where(EmotionLog.user_id == user_id, EmotionLog.timestamp >= seven_days_ago)
        .order_by(EmotionLog.timestamp.asc())
    )
    logs = list(result.scalars().all())
    
    mood_result = await db.execute(
        select(MoodLog)
        .where(MoodLog.user_id == user_id, MoodLog.created_at >= seven_days_ago)
        .order_by(MoodLog.created_at.asc())
    )
    mood_logs = list(mood_result.scalars().all())
    
    data_points = []
    if mood_logs:
        for ml in mood_logs:
            date_str = ml.created_at.isoformat() if ml.created_at else ""
            data_points.append(
                MoodDataPoint(
                    date=date_str,
                    mood_score=ml.mood_score * 10.0 if ml.mood_score <= 1.0 else ml.mood_score,
                    emotion=ml.detected_emotion
                )
            )
    else:
        for el in logs:
            date_str = el.timestamp.isoformat() if el.timestamp else ""
            score = el.confidence_score
            positive = el.detected_emotion.lower() in {"happy", "joy", "excited", "calm"}
            final_score = score * 10.0 if positive else max(0.5, (1.0 - score) * 10.0)
            data_points.append(
                MoodDataPoint(
                    date=date_str,
                    mood_score=round(final_score, 1),
                    emotion=el.detected_emotion
                )
            )
            
    if data_points:
        avg_mood = round(sum(dp.mood_score for dp in data_points) / len(data_points), 1)
    else:
        avg_mood = 7.0
        
    if len(data_points) >= 2:
        diff = data_points[-1].mood_score - data_points[0].mood_score
        if diff > 1.0:
            trend = "improving"
        elif diff < -1.0:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"
        
    return MoodTrendsResponse(
        data_points=data_points,
        average_mood=avg_mood,
        trend=trend
    )


@router.get("/stress-patterns", response_model=StressPatternsResponse)
async def get_stress_patterns(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(current_user["id"]) if isinstance(current_user, dict) else current_user.id
    
    from app.services.profile_service import profile_service
    status_dict = await profile_service.get_knowing_me_completion(db, user_id)
    if not status_dict["is_complete"]:
        return StressPatternsResponse(patterns=[], current_stress_level=0.0, burnout_risk="low")
        
    result = await db.execute(select(UserAnswer).where(UserAnswer.user_id == user_id))
    answers = {a.question_id: a for a in result.scalars().all()}
    
    overthinking_score = 40.0
    if 10 in answers:
        ans10 = "".join(answers[10].selected_answers or [""]).lower()
        if "overthink" in ans10 or "anxious" in ans10 or "racing" in ans10:
            overthinking_score += 40.0
    if 11 in answers:
        ans11 = "".join(answers[11].selected_answers or [""]).lower()
        if "stress" in ans11 or "future" in ans11 or "to-do" in ans11:
            overthinking_score += 20.0
            
    shutdown_score = 30.0
    if 6 in answers:
        ans6 = "".join(answers[6].selected_answers or [""]).lower()
        if "isolate" in ans6 or "alone" in ans6 or "silent" in ans6:
            shutdown_score += 35.0
    if 12 in answers:
        ans12 = "".join(answers[12].selected_answers or [""]).lower()
        if "shut" in ans12 or "withdraw" in ans12 or "ignore" in ans12:
            shutdown_score += 35.0
            
    social_fatigue = 20.0
    if 24 in answers:
        ans24 = "".join(answers[24].selected_answers or [""]).lower()
        if "low" in ans24 or "empty" in ans24 or "drained" in ans24:
            social_fatigue += 60.0
        elif "medium" in ans24 or "average" in ans24:
            social_fatigue += 30.0
            
    pressure_score = 30.0
    if 3 in answers:
        ans3 = "".join(answers[3].selected_answers or [""]).lower()
        if "studies" in ans3 or "placement" in ans3 or "career" in ans3 or "finance" in ans3:
            pressure_score += 40.0
    if 8 in answers:
        ans8 = "".join(answers[8].selected_answers or [""]).lower()
        if "failure" in ans8 or "expectations" in ans8 or "pressure" in ans8:
            pressure_score += 30.0
            
    patterns = [
        StressPattern(category="Overthinking", value=min(100.0, overthinking_score)),
        StressPattern(category="Emotional Shutdown", value=min(100.0, shutdown_score)),
        StressPattern(category="Social Fatigue", value=min(100.0, social_fatigue)),
        StressPattern(category="Performance Pressure", value=min(100.0, pressure_score))
    ]
    
    current_stress = round(sum(p.value for p in patterns) / len(patterns), 1) if patterns else 0.0
    if current_stress > 70.0:
        risk = "high"
    elif current_stress > 40.0:
        risk = "moderate"
    else:
        risk = "low"
        
    return StressPatternsResponse(
        patterns=patterns,
        current_stress_level=current_stress,
        burnout_risk=risk
    )


@router.get("/insights", response_model=InsightsResponse)
async def get_dashboard_insights(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(current_user["id"]) if isinstance(current_user, dict) else current_user.id
    
    from app.services.profile_service import profile_service
    status_dict = await profile_service.get_knowing_me_completion(db, user_id)
    if not status_dict["is_complete"]:
        return InsightsResponse(insights=[], personality_summary="", emotional_tendencies=[], growth_areas=[])
        
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    
    insights_list = []
    personality_summary = "Your emotional profile is still being generated."
    emotional_tendencies = []
    growth_areas = []
    
    if profile and profile.personality_profile:
        pp = profile.personality_profile
        personality_summary = f"Based on your check-ins, you have a {pp.get('communication_style', 'thoughtful')} style. You deal with challenges like {pp.get('current_challenge', 'general stress')} using coping mechanisms like {', '.join(pp.get('interests', [])) or 'reflection'}."
        
        if pp.get("advice_preference"):
            insights_list.append(
                InsightItem(
                    category="Advice style 🎯",
                    insight=f"Prefers {pp.get('advice_preference')} advice when handling issues.",
                    confidence=0.9
                )
            )
        if pp.get("social_energy"):
            insights_list.append(
                InsightItem(
                    category="Social Energy 🔋",
                    insight=f"Describes social energy lately as {pp.get('social_energy')}.",
                    confidence=0.85
                )
            )
        if pp.get("communication_style"):
            insights_list.append(
                InsightItem(
                    category="Communication 💬",
                    insight=f"Exhibits a {pp.get('communication_style')} style.",
                    confidence=0.8
                )
            )
            
        emotional_tendencies = [
            f"Mind default mode: {pp.get('mind_default_mode', 'reflective')}",
            f"Stress response: {profile.emotional_style.get('stress_response', 'internal processing')}"
        ]
        growth_areas = [
            f"Focus on {pp.get('current_challenge', 'daily stressors')}",
            "Maintain consistent sleep and relaxation patterns"
        ]
        
    return InsightsResponse(
        insights=insights_list,
        personality_summary=personality_summary,
        emotional_tendencies=emotional_tendencies,
        growth_areas=growth_areas
    )


@router.get("/growth-insights", response_model=GrowthInsightsResponse)
async def get_dashboard_growth_insights(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(current_user["id"]) if isinstance(current_user, dict) else current_user.id
    
    from app.services.growth_insights_service import growth_insights_service
    res = await growth_insights_service.generate_insights(db, user_id)
    
    return GrowthInsightsResponse(
        insights=[
            GrowthInsightItem(
                icon=ins.icon,
                category=ins.category,
                observation=ins.observation,
                timeframe=ins.timeframe,
                count=ins.count,
                trend=ins.trend
            )
            for ins in res.insights
        ],
        generated_at=res.generated_at,
        total_logs=res.total_logs,
        total_memories=res.total_memories,
        has_data=len(res.insights) > 0
    )


@router.get("/growth/summary")
async def get_growth_summary(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user_id = uuid.UUID(current_user["id"]) if isinstance(current_user, dict) else current_user.id
    
    from app.services.profile_service import profile_service
    from app.services.growth_insights_service import growth_insights_service
    
    completion = await profile_service.get_knowing_me_completion(db, user_id)
    
    from app.config import settings
    fifteen_days_ago = datetime.now(timezone.utc) - timedelta(days=15)
    if not settings.is_postgres:
        fifteen_days_ago = fifteen_days_ago.replace(tzinfo=None)
        
    result = await db.execute(
        select(EmotionLog)
        .where(EmotionLog.user_id == user_id, EmotionLog.timestamp >= fifteen_days_ago)
        .order_by(EmotionLog.timestamp.asc())
    )
    logs = list(result.scalars().all())
    
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)
    if not settings.is_postgres:
        seven_days_ago = seven_days_ago.replace(tzinfo=None)
        fourteen_days_ago = fourteen_days_ago.replace(tzinfo=None)
        
    recent_week_scores = []
    prior_week_scores = []
    for l in logs:
        score = l.confidence_score
        pos = l.detected_emotion.lower() in {"happy", "joy", "excited", "calm"}
        val = score * 10.0 if pos else max(0.5, (1.0 - score) * 10.0)
        
        ts = l.timestamp
        if not settings.is_postgres and ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)
            
        if ts >= seven_days_ago:
            recent_week_scores.append(val)
        elif ts >= fourteen_days_ago:
            prior_week_scores.append(val)
            
    recent_avg = round(sum(recent_week_scores) / len(recent_week_scores), 1) if recent_week_scores else 7.0
    prior_avg = round(sum(prior_week_scores) / len(prior_week_scores), 1) if prior_week_scores else 7.0
    
    diff = recent_avg - prior_avg
    if diff > 0.5:
        shifting_direction = "rising"
        shifting_text = f"Your average mood rose from {prior_avg} to {recent_avg} over the last week. That's a positive shift!"
    elif diff < -0.5:
        shifting_direction = "falling"
        shifting_text = f"Your average mood fell from {prior_avg} to {recent_avg} compared to the previous week. You might be carrying more weight lately."
    else:
        shifting_direction = "stable"
        shifting_text = "Your emotional patterns have been relatively steady over the last two weeks."
        
    something_is_shifting = {
        "recent_average": recent_avg,
        "prior_average": prior_avg,
        "direction": shifting_direction,
        "observation": shifting_text
    }
    
    profile_res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = profile_res.scalar_one_or_none()
    pp = profile.personality_profile if profile else {}
    
    energy = "BALANCED"
    mind_load = "MEDIUM"
    direction = "STABLE"
    
    sleep = str(profile.emotional_baseline.get("sleep", "") if profile else "").lower()
    if "poor" in sleep or "average" in sleep or "bad" in sleep or "tired" in sleep:
        energy = "LOW"
    elif "good" in sleep or "high" in sleep:
        energy = "HIGH"
        
    challenge = str(pp.get("current_challenge", "")).lower()
    if challenge and any(x in challenge for x in ["exams", "studies", "placement", "career", "finance", "pressure", "overwhelmed"]):
        mind_load = "HIGH"
    elif not challenge or challenge in ["none", "n/a"]:
        mind_load = "LOW"
        
    if shifting_direction == "rising":
        direction = "IMPROVING"
    elif shifting_direction == "falling":
        direction = "UNSETTLED"
        
    if direction == "UNSETTLED" and mind_load == "HIGH":
        desc = "You've been carrying more pressure lately, and studies or uncertainty seem to be taking more space in your thoughts."
    elif direction == "IMPROVING":
        desc = "Things are looking up. You've been finding better pockets of rest and motivation."
    else:
        desc = "You are maintaining a steady, reflective rhythm as you navigate your day-to-day challenges."
        
    inner_weather = {
        "energy": energy,
        "mind_load": mind_load,
        "emotional_direction": direction,
        "description": desc
    }
    
    growth_insights = await growth_insights_service.generate_insights(db, user_id)
    esona_noticed = []
    for idx, ins in enumerate(growth_insights.insights[:3]):
        esona_noticed.append({
            "id": f"notice_{idx}",
            "pattern": ins.category,
            "evidence": ins.observation,
            "dismissed": False
        })
    if not esona_noticed:
        esona_noticed.append({
            "id": "notice_default",
            "pattern": "Reflective Rhythm",
            "evidence": "You value quiet reflection and clear, low-pressure support during stress.",
            "dismissed": False
        })
        
    nodes = []
    links = []
    
    nodes.append({"id": "you", "label": "Self", "type": "user", "weight": 1.0})
    added_nodes = set()
    
    challenge_val = pp.get("current_challenge")
    if challenge_val and challenge_val not in added_nodes:
        added_nodes.add(challenge_val)
        nodes.append({"id": "challenge", "label": challenge_val[:20], "type": "stressor", "weight": 0.8})
        links.append({"source": "you", "target": "challenge"})
        
    interests = pp.get("interests", [])
    for idx, item in enumerate(interests[:3]):
        if item and item not in added_nodes:
            added_nodes.add(item)
            node_id = f"interest_{idx}"
            nodes.append({"id": node_id, "label": item[:20], "type": "theme", "weight": 0.7})
            links.append({"source": "you", "target": node_id})
            
    coping = profile.comfort_preferences.get("coping_mechanisms", []) if profile else []
    for idx, item in enumerate(coping[:2]):
        if item and item not in added_nodes:
            added_nodes.add(item)
            node_id = f"coping_{idx}"
            nodes.append({"id": node_id, "label": item[:20], "type": "coping", "weight": 0.6})
            links.append({"source": "you", "target": node_id})
            
    if len(nodes) <= 1:
        nodes.extend([
            {"id": "calm", "label": "Calm State", "type": "theme", "weight": 0.5},
            {"id": "rest", "label": "Rest Patterns", "type": "coping", "weight": 0.5}
        ])
        links.extend([
            {"source": "you", "target": "calm"},
            {"source": "you", "target": "rest"}
        ])
        
    calm_recommendations = []
    if mind_load == "HIGH":
        calm_recommendations.append("Thought Untangle")
    if energy == "LOW":
        calm_recommendations.append("Sensory Grounding")
    if direction == "UNSETTLED" or not calm_recommendations:
        calm_recommendations.append("Box Breathing")
        
    calm_space = {
        "recommended_exercises": calm_recommendations,
        "mood_boosters": list(pp.get("interests", [])) or ["music", "gaming"]
    }
    
    return {
        "inner_weather": inner_weather,
        "esona_noticed": esona_noticed,
        "emotional_constellation": {
            "nodes": nodes,
            "links": links
        },
        "calm_space": calm_space,
        "something_is_shifting": something_is_shifting,
        "knowing_me_completion": completion
    }
