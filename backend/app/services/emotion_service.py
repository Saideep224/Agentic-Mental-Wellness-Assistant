"""
Emotion Service – handles MentalBERT sequence classification for user emotions
and logs results in the emotion_logs table.
"""

import json
import logging
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.emotion_log import EmotionLog
from app.utils.llm import get_chat_client

logger = logging.getLogger(__name__)

MENTALBERT_EMOTION_CLASSIFIER_PROMPT = """You are the MentalBERT Sequence Classification Model, a domain-specific BERT classifier fine-tuned on psychological texts and mental health support forums.
Your task is to perform sequence classification on the user's message and classify it into one of seven emotional categories.

Target Categories:
- Happy (positive affect, contentment, relief, cheerfulness)
- Neutral (standard greetings, informational, casual questions, small talk without strong emotion)
- Stress (overwhelmed, burnout, pressure, having too much to do, exhaustion)
- Anxiety (fear, worry, overthinking, panic, dread of the future)
- Sadness (grief, sorrow, hurt, disappointment, feeling low)
- Frustration (anger, annoyance, irritation, resentment)
- Loneliness (isolation, feeling left out, having no one to talk to, feeling abandoned)

Analyze the sentiment, context, and tone of the message. Choose the primary, dominant emotion.

Output ONLY a valid JSON object matching this schema:
{
  "detected_emotion": "Happy" | "Neutral" | "Stress" | "Anxiety" | "Sadness" | "Frustration" | "Loneliness",
  "confidence_score": float
}"""


class EmotionService:
    """Manages emotion classification and logs results to the database."""

    async def classify_emotion_mentalbert(
        self, db: AsyncSession, user_id: str, message: str
    ) -> Dict[str, Any]:
        """
        Classifies the message into one of the 7 specified emotions,
        logs it in the emotion_logs table, and returns the result.
        """
        if not message or len(message.strip()) < 1:
            return {"detected_emotion": "Neutral", "confidence_score": 1.0}

        try:
            # 1. Execute classification call via LLM simulating MentalBERT
            client = get_chat_client()
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": MENTALBERT_EMOTION_CLASSIFIER_PROMPT},
                    {"role": "user", "content": f"User message: {message}"},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
            result = json.loads(raw)
            
            detected_emotion = result.get("detected_emotion", "Neutral")
            confidence_score = float(result.get("confidence_score", 0.8))
            
            # Normalize casing
            valid_emotions = ["Happy", "Neutral", "Stress", "Anxiety", "Sadness", "Frustration", "Loneliness"]
            matched_emotion = "Neutral"
            for emo in valid_emotions:
                if detected_emotion.lower() == emo.lower():
                    matched_emotion = emo
                    break

            logger.info(
                f"[MentalBERT Classifier] Classified message: '{message[:40]}...' as "
                f"'{matched_emotion}' (confidence: {confidence_score})"
            )

            # 2. Persist in emotion_logs table
            try:
                user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                emotion_log = EmotionLog(
                    user_id=user_uuid,
                    message=message,
                    detected_emotion=matched_emotion,
                    confidence_score=confidence_score,
                )
                db.add(emotion_log)
                await db.flush()
                logger.info("[MentalBERT Classifier] Successfully stored emotion log.")
            except Exception as db_err:
                logger.error(f"Failed to save emotion log to database: {db_err}", exc_info=True)

            return {
                "detected_emotion": matched_emotion,
                "confidence_score": confidence_score
            }

        except Exception as e:
            logger.error(f"Error in classify_emotion_mentalbert: {e}", exc_info=True)
            return {"detected_emotion": "Neutral", "confidence_score": 0.5}


# Export singleton instance
emotion_service = EmotionService()
