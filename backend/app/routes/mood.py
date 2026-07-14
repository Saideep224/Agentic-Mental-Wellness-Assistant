"""
Mood and Music API routes – mood average calculation and song suggestions.
"""

import logging
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.mood_log import MoodLog
from app.models.emotion_log import EmotionLog
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Mood & Music"])


@router.get("/mood/average")
async def get_mood_average(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Query the average mood score from mood_logs (or emotion_logs fallback) for the last 10 messages."""
    user_id = uuid.UUID(current_user["id"]) if isinstance(current_user, dict) else current_user.id
    
    result = await db.execute(
        select(MoodLog)
        .where(MoodLog.user_id == user_id)
        .order_by(MoodLog.created_at.desc())
        .limit(10)
    )
    logs = result.scalars().all()
    if not logs:
        # Fallback to check if there are any emotion_logs
        emo_res = await db.execute(
            select(EmotionLog)
            .where(EmotionLog.user_id == user_id)
            .order_by(EmotionLog.timestamp.desc())
            .limit(10)
        )
        emo_logs = emo_res.scalars().all()
        if not emo_logs:
            return {"average_mood": 0.5, "count": 0}
        
        # Map emotions to approximate mood scores
        mood_map = {
            "happy": 0.85, "joy": 0.85, "excited": 0.9, "neutral": 0.5,
            "sad": 0.2, "sadness": 0.2, "lonely": 0.2, "loneliness": 0.2,
            "anxious": 0.35, "anxiety": 0.35, "stress": 0.4, "stressed": 0.4,
            "anger": 0.3, "angry": 0.3, "crisis": 0.1
        }
        total_score = 0.0
        for el in emo_logs:
            total_score += mood_map.get(el.detected_emotion.lower(), 0.5)
        return {"average_mood": total_score / len(emo_logs), "count": len(emo_logs)}

    avg_mood = sum(l.mood_score for l in logs) / len(logs)
    return {"average_mood": avg_mood, "count": len(logs)}


@router.get("/music/suggested-songs")
async def get_suggested_songs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Suggest songs and genres based on the user's average mood score over the last 10 messages."""
    user_id = uuid.UUID(current_user["id"]) if isinstance(current_user, dict) else current_user.id
    
    result = await db.execute(
        select(MoodLog)
        .where(MoodLog.user_id == user_id)
        .order_by(MoodLog.created_at.desc())
        .limit(10)
    )
    logs = result.scalars().all()
    
    if not logs:
        # Fallback to check if there are any emotion_logs
        emo_res = await db.execute(
            select(EmotionLog)
            .where(EmotionLog.user_id == user_id)
            .order_by(EmotionLog.timestamp.desc())
            .limit(10)
        )
        emo_logs = emo_res.scalars().all()
        if emo_logs:
            mood_map = {
                "happy": 0.85, "joy": 0.85, "excited": 0.9, "neutral": 0.5,
                "sad": 0.2, "sadness": 0.2, "lonely": 0.2, "loneliness": 0.2,
                "anxious": 0.35, "anxiety": 0.35, "stress": 0.4, "stressed": 0.4,
                "anger": 0.3, "angry": 0.3, "crisis": 0.1
            }
            avg_mood = sum(mood_map.get(el.detected_emotion.lower(), 0.5) for el in emo_logs) / len(emo_logs)
        else:
            avg_mood = 0.5
    else:
        avg_mood = sum(l.mood_score for l in logs) / len(logs)
        
    if avg_mood < 0.35:
        # Sadness/Loneliness
        return {
            "genre": "Acoustic & Soft Indie",
            "songs": ["Holocene - Bon Iver", "Skinny Love - Birdy", "All I Want - Kodaline", "Saturn - Sleeping At Last"],
            "mood_type": "sadness"
        }
    elif avg_mood < 0.60:
        # Anxiety/Stress
        return {
            "genre": "Calming Ambient & Lo-Fi Beats",
            "songs": ["Weightless - Marconi Union", "Gymnopedie No. 1 - Satie", "Sunset Lover - Petit Biscuit", "Departure - Lofi Beats"],
            "mood_type": "anxiety"
        }
    else:
        # Happy/Energetic
        return {
            "genre": "Upbeat Pop & Motivation",
            "songs": ["Happy - Pharrell Williams", "Good Vibrations - Beach Boys", "Can't Stop the Feeling - Timberlake", "Levitating - Dua Lipa"],
            "mood_type": "happy"
        }
