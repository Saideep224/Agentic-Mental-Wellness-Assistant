"""
Dashboard / analytics response schemas.
"""

from datetime import date, datetime, timezone
from typing import Any

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
    period: str
    stress_level: float
    common_triggers: list[str]


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
