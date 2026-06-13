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


_local_classifier = None


def get_local_classifier():
    """Helper to lazily load the local emotion classifier pipeline."""
    global _local_classifier
    if _local_classifier is not None:
        return _local_classifier

    try:
        from transformers import pipeline
        logger.info(f"Loading local emotion classifier pipeline: {settings.EMOTION_MODEL_NAME}...")
        _local_classifier = pipeline(
            "text-classification",
            model=settings.EMOTION_MODEL_NAME,
            device=-1  # CPU by default
        )
        logger.info("Local emotion classifier pipeline loaded successfully.")
        return _local_classifier
    except Exception as e:
        logger.warning(
            f"Failed to load local emotion model '{settings.EMOTION_MODEL_NAME}': {e}. "
            f"Falling back to API-based classification."
        )
        return None


def map_model_label_to_wellness_emotion(label: str) -> str:
    """Maps typical text classification model labels to the 7 supported wellness emotions."""
    lbl = label.lower().strip()
    
    # Supported categories: anxiety, stress, sadness, frustration, happiness, neutral, loneliness
    if lbl in ["joy", "love", "happiness", "happy", "relief"]:
        return "Happy"
    elif lbl in ["fear", "anxiety", "anxious", "panic", "worry", "dread"]:
        return "Anxiety"
    elif lbl in ["sadness", "sad", "grief", "sorrow", "low", "disappointment"]:
        return "Sadness"
    elif lbl in ["anger", "frustration", "frustrated", "annoyance", "irritation", "resentment"]:
        return "Frustration"
    elif lbl in ["stress", "stressed", "overwhelmed", "burnout", "pressure"]:
        return "Stress"
    elif lbl in ["loneliness", "lonely", "isolated", "isolation"]:
        return "Loneliness"
    else:
        return "Neutral"


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

        # 1. Attempt local classification if configured
        if settings.USE_LOCAL_EMOTION_MODEL:
            classifier = get_local_classifier()
            if classifier is not None:
                try:
                    # Run inference locally
                    predictions = classifier(message)
                    if predictions and len(predictions) > 0:
                        pred = predictions[0]
                        detected_label = pred.get("label", "Neutral")
                        confidence_score = float(pred.get("score", 0.8))
                        
                        matched_emotion = map_model_label_to_wellness_emotion(detected_label)
                        
                        logger.info(
                            f"[Local MentalBERT] Classified message: '{message[:40]}...' as "
                            f"'{matched_emotion}' (confidence: {confidence_score})"
                        )
                        
                        await self._save_emotion_log(db, user_id, message, matched_emotion, confidence_score)
                        
                        return {
                            "detected_emotion": matched_emotion,
                            "confidence_score": confidence_score
                        }
                except Exception as local_err:
                    logger.error(f"Local emotion classification failed: {local_err}. Falling back to LLM.", exc_info=True)

        # 2. Fallback: Execute classification call via LLM simulating MentalBERT
        try:
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
                f"[MentalBERT API Simulator] Classified message: '{message[:40]}...' as "
                f"'{matched_emotion}' (confidence: {confidence_score})"
            )

            await self._save_emotion_log(db, user_id, message, matched_emotion, confidence_score)

            return {
                "detected_emotion": matched_emotion,
                "confidence_score": confidence_score
            }

        except Exception as e:
            logger.error(f"Error in classify_emotion_mentalbert: {e}", exc_info=True)
            return {"detected_emotion": "Neutral", "confidence_score": 0.5}

    async def _save_emotion_log(
        self, db: AsyncSession, user_id: str, message: str, emotion: str, confidence: float
    ):
        """Helper to save classification result to the database."""
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            emotion_log = EmotionLog(
                user_id=user_uuid,
                message=message,
                detected_emotion=emotion,
                confidence_score=confidence,
            )
            db.add(emotion_log)
            await db.flush()
            logger.info("[MentalBERT Classifier] Successfully stored emotion log.")
        except Exception as db_err:
            logger.error(f"Failed to save emotion log to database: {db_err}", exc_info=True)


# Export singleton instance
emotion_service = EmotionService()
