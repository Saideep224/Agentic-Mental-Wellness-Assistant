"""
Dashboard route – mood trends, emotional profile, stress patterns, insights.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.conversation import Message, MessageRole
from app.models.emotional_profile import EmotionalProfile
from app.routes.auth import get_current_user
from app.schemas.dashboard import (
    MoodDataPoint,
    MoodTrendsResponse,
    EmotionalProfileResponse,
    StressPattern,
    StressPatternsResponse,
    InsightItem,
    InsightsResponse,
)
from app.services.mood_tracker import MoodTracker
from app.memory.memory_manager import MemoryManager

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/mood-trends", response_model=MoodTrendsResponse)
async def get_mood_trends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mood scores over the last 30 days from conversation messages."""
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    result = await db.execute(
        select(
            func.date(Message.created_at).label("day"),
            func.avg(Message.mood_score).label("avg_mood"),
            func.max(Message.emotion_detected).label("emotion"),
        )
        .join(
            # We need to join through conversation to filter by user
            Message.conversation,
        )
        .where(
            Message.mood_score.isnot(None),
            Message.created_at >= thirty_days_ago,
            Message.conversation.has(user_id=current_user.id),
        )
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at).asc())
    )
    rows = result.all()

    data_points = [
        MoodDataPoint(
            date=str(row.day),
            mood_score=round(float(row.avg_mood), 2),
            emotion=row.emotion,
        )
        for row in rows
    ]

    avg_mood = (
        sum(dp.mood_score for dp in data_points) / len(data_points)
        if data_points
        else 0.5
    )

    # Determine trend
    if len(data_points) >= 3:
        recent = [dp.mood_score for dp in data_points[-3:]]
        early = [dp.mood_score for dp in data_points[:3]]
        recent_avg = sum(recent) / len(recent)
        early_avg = sum(early) / len(early)
        if recent_avg - early_avg > 0.1:
            trend = "improving"
        elif early_avg - recent_avg > 0.1:
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
        select(EmotionalProfile).where(
            EmotionalProfile.user_id == current_user.id
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
        updated_at=profile.updated_at,
    )


@router.get("/stress-patterns", response_model=StressPatternsResponse)
async def get_stress_patterns(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate stress-related data from messages and memory."""
    user_id_str = str(current_user.id)

    # Gather stress data from recent messages
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    async def _avg_stress_for_period(since: datetime) -> float:
        res = await db.execute(
            select(func.avg(Message.mood_score))
            .join(Message.conversation)
            .where(
                Message.mood_score.isnot(None),
                Message.created_at >= since,
                Message.conversation.has(user_id=current_user.id),
            )
        )
        val = res.scalar()
        # Invert mood_score to stress: high mood = low stress
        return round(1.0 - (float(val) if val else 0.5), 2)

    stress_7d = await _avg_stress_for_period(seven_days_ago)
    stress_14d = await _avg_stress_for_period(fourteen_days_ago)
    stress_30d = await _avg_stress_for_period(thirty_days_ago)

    # Try to get triggers from memory
    try:
        mm = MemoryManager()
        patterns_data = mm.get_emotional_patterns(user_id_str)
        common_triggers = patterns_data.get("common_triggers", ["work", "sleep", "relationships"])
    except Exception:
        common_triggers = ["work", "sleep", "relationships"]

    patterns = [
        StressPattern(period="Last 7 days", stress_level=stress_7d, common_triggers=common_triggers[:3]),
        StressPattern(period="Last 14 days", stress_level=stress_14d, common_triggers=common_triggers[:3]),
        StressPattern(period="Last 30 days", stress_level=stress_30d, common_triggers=common_triggers[:3]),
    ]

    # Burnout risk assessment
    if stress_7d > 0.7:
        burnout = "high"
    elif stress_7d > 0.4:
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
    """Personality insights summary derived from the emotional profile."""
    result = await db.execute(
        select(EmotionalProfile).where(
            EmotionalProfile.user_id == current_user.id
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

    # Extract insights from profile data
    insights: list[InsightItem] = []
    personality = profile.personality_type or {}
    baseline = profile.emotional_baseline or {}
    communication = profile.communication_style or {}

    if personality.get("type"):
        insights.append(InsightItem(
            category="Personality",
            insight=f"Your personality type is {personality['type']}. {personality.get('description', '')}",
            confidence=0.85,
        ))

    if baseline.get("dominant_emotion"):
        insights.append(InsightItem(
            category="Emotional Baseline",
            insight=f"Your emotional baseline tends toward {baseline['dominant_emotion']}.",
            confidence=0.80,
        ))

    if communication.get("preferred_style"):
        insights.append(InsightItem(
            category="Communication",
            insight=f"You prefer {communication['preferred_style']} communication.",
            confidence=0.82,
        ))

    if personality.get("strengths"):
        for strength in personality["strengths"][:3]:
            insights.append(InsightItem(
                category="Strength",
                insight=strength,
                confidence=0.78,
            ))

    emotional_tendencies = baseline.get("tendencies", [])
    if not emotional_tendencies and baseline.get("dominant_emotion"):
        emotional_tendencies = [baseline["dominant_emotion"]]

    growth_areas = personality.get("growth_areas", [])
    if not growth_areas:
        growth_areas = ["Self-awareness", "Emotional regulation"]

    personality_summary = personality.get(
        "summary",
        "Your personality profile is being built as we get to know you better.",
    )

    return InsightsResponse(
        insights=insights,
        personality_summary=personality_summary,
        emotional_tendencies=emotional_tendencies,
        growth_areas=growth_areas,
    )
