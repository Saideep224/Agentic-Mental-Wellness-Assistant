"""
Dashboard / analytics response schemas.
"""

from datetime import date, datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer


class MoodDataPoint(BaseModel):
    """Single mood data point for charts."""
    date: str
    mood_score: float
    emotion: str | None = None


class MoodTrendsResponse(BaseModel):
    """Mood trend data for the last N days."""
    data_points: list[MoodDataPoint]
    average_mood: float
    trend: str = Field(
        description="'improving', 'declining', or 'stable'",
    )


class EmotionalProfileResponse(BaseModel):
    """Full emotional profile for the dashboard."""
    personality_type: dict[str, Any]
    emotional_baseline: dict[str, Any]
    comfort_preferences: dict[str, Any]
    communication_style: dict[str, Any]
    emotional_style: dict[str, Any]
    interests: dict[str, Any]
    stress_triggers: dict[str, Any]
    strengths: dict[str, Any]
    weaknesses: dict[str, Any]
    onboarding_answers: dict[str, Any]
    updated_at: datetime | None = None

    @field_serializer("updated_at")
    def serialize_updated_at(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")


class StressPattern(BaseModel):
    """Individual stress pattern entry."""
    category: str
    value: float
    fullMark: float = 100.0


class StressPatternsResponse(BaseModel):
    """Aggregated stress pattern data."""
    patterns: list[StressPattern]
    current_stress_level: float
    burnout_risk: str = Field(description="'low', 'moderate', or 'high'")


class InsightItem(BaseModel):
    """A single personality / emotional insight."""
    category: str
    insight: str
    confidence: float = Field(ge=0.0, le=1.0)


class InsightsResponse(BaseModel):
    """Personality insights summary."""
    insights: list[InsightItem]
    personality_summary: str
    emotional_tendencies: list[str]
    growth_areas: list[str]


class GrowthInsightItem(BaseModel):
    """A single personal growth observation derived from analytics."""
    icon: str
    category: str
    observation: str
    timeframe: str
    count: Optional[int] = None
    trend: str = Field(
        default="stable",
        description="'rising', 'falling', or 'stable'",
    )


class GrowthInsightsResponse(BaseModel):
    """Collection of personal growth observations for the dashboard."""
    insights: list[GrowthInsightItem]
    generated_at: str
    total_logs: int = 0
    total_memories: int = 0
    has_data: bool = False
