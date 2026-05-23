"""
Service to track and analyze user mood history.
Analyzes mood scores from messages to detect trends, stress levels, and spikes.
"""

import logging
from typing import Dict, List, Any
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Message, Conversation

logger = logging.getLogger(__name__)


class MoodTracker:
    """Manages the aggregation and analysis of user mood data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_average_mood(self, user_id: uuid.UUID, days: int = 30) -> float:
        """Calculate the average mood score for a user over a period of days."""
        from datetime import datetime, timedelta, timezone
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(func.avg(Message.mood_score))
            .join(Message.conversation)
            .where(
                Message.mood_score.isnot(None),
                Message.created_at >= since,
                Conversation.user_id == user_id,
            )
        )
        val = result.scalar()
        return round(float(val), 2) if val is not None else 0.5

    async def get_mood_swings_detected(self, user_id: uuid.UUID, limit: int = 10) -> bool:
        """
        Check if the user has shown high mood volatility recently.
        If mood changes by > 0.4 between subsequent messages, volatility is high.
        """
        result = await self.db.execute(
            select(Message.mood_score)
            .join(Message.conversation)
            .where(
                Message.mood_score.isnot(None),
                Conversation.user_id == user_id,
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        scores = [float(s) for s in result.scalars().all()]
        if len(scores) < 2:
            return False

        # Calculate difference between consecutive messages
        diffs = [abs(scores[i] - scores[i + 1]) for i in range(len(scores) - 1)]
        avg_diff = sum(diffs) / len(diffs)
        
        # High volatility threshold
        return avg_diff > 0.3
