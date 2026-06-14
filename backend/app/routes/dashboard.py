"""
Dashboard route – mood trends, emotional profile, stress patterns, insights.
"""

from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.mood_log import MoodLog
from app.routes.auth import get_current_user
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
from app.memory.memory_manager import MemoryManager
from app.services.growth_insights_service import growth_insights_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/mood-trends", response_model=MoodTrendsResponse)
async def get_mood_trends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mood scores over the last 30 days from real MoodLogs."""
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    result = await db.execute(
        select(
            func.date(MoodLog.created_at).label("day"),
            func.avg(MoodLog.mood_score).label("avg_mood"),
            func.max(MoodLog.detected_emotion).label("emotion"),
        )
        .where(
            MoodLog.created_at >= thirty_days_ago,
            MoodLog.user_id == current_user.id,
        )
        .group_by(func.date(MoodLog.created_at))
        .order_by(func.date(MoodLog.created_at).asc())
    )
    rows = result.all()

    data_points = [
        MoodDataPoint(
            date=str(row.day),
            mood_score=round(float(row.avg_mood) * 10, 1),  # Scale to 1-10 for chart
            emotion=row.emotion,
        )
        for row in rows
    ]

    if not data_points:
        return MoodTrendsResponse(
            data_points=[],
            average_mood=5.0,
            trend="stable",
        )

    avg_mood = sum(dp.mood_score for dp in data_points) / len(data_points)

    # Determine trend
    if len(data_points) >= 3:
        recent = [dp.mood_score for dp in data_points[-3:]]
        early = [dp.mood_score for dp in data_points[:3]]
        recent_avg = sum(recent) / len(recent)
        early_avg = sum(early) / len(early)
        if recent_avg - early_avg > 0.5:
            trend = "improving"
        elif early_avg - recent_avg > 0.5:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return MoodTrendsResponse(
        data_points=data_points,
        average_mood=round(avg_mood, 2),
        trend=trend,
    )


@router.get("/emotional-profile", response_model=EmotionalProfileResponse)
async def get_emotional_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's full emotional profile."""
    result = await db.execute(
        select(UserProfile).where(
            UserProfile.user_id == current_user.id
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Emotional profile not found. Please complete onboarding first.",
        )

    return EmotionalProfileResponse(
        personality_type=profile.personality_type,
        emotional_baseline=profile.emotional_baseline,
        comfort_preferences=profile.comfort_preferences,
        communication_style=profile.communication_style,
        emotional_style=profile.emotional_style,
        interests=profile.interests,
        stress_triggers=profile.stress_triggers,
        strengths=profile.strengths,
        weaknesses=profile.weaknesses,
        onboarding_answers=profile.onboarding_answers,
        updated_at=profile.updated_at,
    )


@router.get("/stress-patterns", response_model=StressPatternsResponse)
async def get_stress_patterns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate stress-related data from real MoodLogs."""
    user_id_str = str(current_user.id)

    # Fetch stress statistics
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    async def _avg_stress_for_period(since: datetime) -> float:
        res = await db.execute(
            select(func.avg(MoodLog.stress))
            .where(
                MoodLog.stress.isnot(None),
                MoodLog.created_at >= since,
                MoodLog.user_id == current_user.id,
            )
        )
        val = res.scalar()
        return round(float(val) * 100, 1) if val is not None else 0.0

    stress_7d = await _avg_stress_for_period(seven_days_ago)
    stress_14d = await _avg_stress_for_period(fourteen_days_ago)
    stress_30d = await _avg_stress_for_period(thirty_days_ago)

    # Check triggers from Memory or UserProfile
    common_triggers = ["work", "sleep", "relationships"]
    try:
        profile_res = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
        prof = profile_res.scalar_one_or_none()
        if prof and prof.stress_triggers:
            triggers_data = prof.stress_triggers.get("triggers", [])
            if triggers_data:
                common_triggers = triggers_data
    except Exception as e:
        logger.warning(f"Failed to read triggers from UserProfile: {e}")

    try:
        mm = MemoryManager()
        patterns_data = await mm.get_emotional_patterns(db, user_id_str)
        triggers = patterns_data.get("common_triggers", [])
        if triggers:
            common_triggers = triggers
    except Exception as e:
        logger.warning(f"Failed to get triggers from MemoryManager: {e}")

    # Fallback to zeros if no data is present
    has_logs_res = await db.execute(select(func.count(MoodLog.id)).where(MoodLog.user_id == current_user.id))
    logs_count = has_logs_res.scalar() or 0

    if logs_count == 0:
        return StressPatternsResponse(
            patterns=[],
            current_stress_level=0.0,
            burnout_risk="low",
        )

    # Fetch average emotional dimensions
    avg_res = await db.execute(
        select(
            func.avg(MoodLog.stress).label("stress"),
            func.avg(MoodLog.happiness).label("happiness"),
            func.avg(MoodLog.sadness).label("sadness"),
            func.avg(MoodLog.anxiety).label("anxiety"),
            func.avg(MoodLog.motivation).label("motivation"),
            func.avg(MoodLog.confidence).label("confidence"),
        ).where(MoodLog.user_id == current_user.id)
    )
    row = avg_res.fetchone()

    stress_val = round(float(row.stress) * 100, 1) if row and row.stress is not None else 0.0
    happiness_val = round(float(row.happiness) * 100, 1) if row and row.happiness is not None else 0.0
    sadness_val = round(float(row.sadness) * 100, 1) if row and row.sadness is not None else 0.0
    anxiety_val = round(float(row.anxiety) * 100, 1) if row and row.anxiety is not None else 0.0
    motivation_val = round(float(row.motivation) * 100, 1) if row and row.motivation is not None else 0.0
    confidence_val = round(float(row.confidence) * 100, 1) if row and row.confidence is not None else 0.0

    patterns = [
        StressPattern(category="Stress", value=stress_val),
        StressPattern(category="Happiness", value=happiness_val),
        StressPattern(category="Sadness", value=sadness_val),
        StressPattern(category="Anxiety", value=anxiety_val),
        StressPattern(category="Motivation", value=motivation_val),
        StressPattern(category="Confidence", value=confidence_val),
    ]

    # Burnout risk assessment
    if stress_7d > 70.0:
        burnout = "high"
    elif stress_7d > 40.0:
        burnout = "moderate"
    else:
        burnout = "low"

    return StressPatternsResponse(
        patterns=patterns,
        current_stress_level=stress_7d,
        burnout_risk=burnout,
    )


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Personality insights summary derived from UserProfile & chat counts."""
    result = await db.execute(
        select(UserProfile).where(
            UserProfile.user_id == current_user.id
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return InsightsResponse(
            insights=[],
            personality_summary="Complete onboarding to get your personality insights.",
            emotional_tendencies=[],
            growth_areas=[],
        )

    # Check conversation count for dynamic logic
    count_res = await db.execute(
        select(func.count(MoodLog.id)).where(MoodLog.user_id == current_user.id)
    )
    chat_count = count_res.scalar() or 0

    personality = profile.personality_type or {}
    baseline = profile.emotional_style or {}
    communication = profile.communication_style or {}
    strengths = profile.strengths.get("strengths", []) if profile.strengths else []
    weaknesses = profile.weaknesses.get("weaknesses", []) if profile.weaknesses else []

    insights: list[InsightItem] = []

    if chat_count == 0:
        # Onboarding recommendations
        personality_summary = "Onboarding completed! Chat with Esona to begin analyzing your profile."
        insights.append(InsightItem(
            category="Recommendation",
            insight="Welcome to Esona! Try sending a simple greeting in the Chat tab to start your emotional wellness journey.",
            confidence=1.0
        ))
        emotional_tendencies = ["Setting baseline"]
        growth_areas = ["Onboarding complete"]
    elif chat_count < 3:
        # Partial insights
        personality_summary = f"Partial insights are active. Esona has parsed {chat_count} chat exchanges. Keep talking to generate advanced AI analytics!"
        
        if personality.get("type"):
            insights.append(InsightItem(
                category="Initial Personality Indicator",
                insight=f"You might be a {personality['type']}. We are refining this analysis.",
                confidence=0.5
            ))
        
        emotional_tendencies = baseline.get("tendencies", [])[:1] or ["Refining baseline"]
        growth_areas = ["Continue chatting"]
    else:
        # Advanced insights
        personality_summary = personality.get(
            "summary",
            "Your personality profile is being built as we get to know you better."
        )
        
        if personality.get("type"):
            insights.append(InsightItem(
                category="Personality Profile 🧠",
                insight=f"Personality Type: {personality['type']}. {personality.get('description', '')}",
                confidence=0.9
            ))

        if baseline.get("dominant_emotion"):
            insights.append(InsightItem(
                category="Emotional Style 💭",
                insight=f"Your dominant emotional style is {baseline['dominant_emotion']}.",
                confidence=0.85
            ))

        if communication.get("preferred_style"):
            insights.append(InsightItem(
                category="Communication Style 🗣️",
                insight=f"Preferred Communication Mode: {communication['preferred_style']}.",
                confidence=0.88
            ))

        for strength in strengths[:2]:
            insights.append(InsightItem(
                category="Strengths ✨",
                insight=f"Strength: {strength}",
                confidence=0.80
            ))

        for weakness in weaknesses[:2]:
            insights.append(InsightItem(
                category="Growth Areas 🌱",
                insight=f"Growth Target: {weakness}",
                confidence=0.75
            ))

        emotional_tendencies = baseline.get("tendencies", [])
        growth_areas = weaknesses

    return InsightsResponse(
        insights=insights,
        personality_summary=personality_summary,
        emotional_tendencies=emotional_tendencies,
        growth_areas=growth_areas,
    )


@router.get("/growth-insights", response_model=GrowthInsightsResponse)
async def get_growth_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Personal Growth Insights – aggregates emotion frequencies, memory topic patterns,
    positive-mood correlations, and knowledge-graph triples into human-readable observations.
    Derived entirely from existing data; no new LLM calls are made.
    """
    try:
        result = await growth_insights_service.generate_insights(
            db=db,
            user_id=str(current_user.id),
            days=30,
        )

        return GrowthInsightsResponse(
            insights=[
                GrowthInsightItem(
                    icon=item.icon,
                    category=item.category,
                    observation=item.observation,
                    timeframe=item.timeframe,
                    count=item.count,
                    trend=item.trend,
                )
                for item in result.insights
            ],
            generated_at=result.generated_at,
            total_logs=result.total_logs,
            total_memories=result.total_memories,
            has_data=len(result.insights) > 0,
        )
    except Exception as exc:
        logger.error(f"get_growth_insights failed for user {current_user.id}: {exc}", exc_info=True)
        from datetime import datetime, timezone
        return GrowthInsightsResponse(
            insights=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
            has_data=False,
        )
