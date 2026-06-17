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
    
    # Handle index-based or generic label IDs (e.g., LABEL_0, LABEL_1, etc.)
    if lbl.startswith("label_"):
        idx_str = lbl.replace("label_", "")
        if idx_str.isdigit():
            idx = int(idx_str)
            # Mapping for bhadresh-savani/bert-base-uncased-emotion (6 labels):
            # 0: sadness, 1: joy, 2: love, 3: anger, 4: fear, 5: surprise
            bhadresh_map = {0: "sadness", 1: "joy", 2: "love", 3: "anger", 4: "fear", 5: "surprise"}
            lbl = bhadresh_map.get(idx, lbl)

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

        # Crisis Override Check
        msg_lower = message.lower()
        crisis_keywords = ["want to die", "kill myself", "end my life", "suicide"]
        if any(keyword in msg_lower for keyword in crisis_keywords):
            logger.warning(f"[Crisis Override] Crisis detected in message: '{message}'. Overriding to Crisis classification.")
            await self._save_emotion_log(db, user_id, message, "Crisis", 0.95)
            return {
                "detected_emotion": "Crisis",
                "confidence_score": 0.95
            }

        # 1. Attempt local classification if configured
        if settings.USE_LOCAL_EMOTION_MODEL:
            classifier = get_local_classifier()
            if classifier is not None:
                try:
                    logger.info(f"TEXT SENT TO MENTALBERT (Local): '{message}'")
                    # Run inference locally
                    predictions = classifier(message)
                    logger.info(f"Raw Model Predictions: {predictions}")
                    
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
            logger.info(f"TEXT SENT TO MENTALBERT (LLM Simulator): '{message}'")
            messages = [
                {"role": "system", "content": MENTALBERT_EMOTION_CLASSIFIER_PROMPT},
                {"role": "user", "content": f"User message: {message}"},
            ]
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
            logger.info(f"LLM Raw Output: {raw}")
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
            logger.error(f"Error in classify_emotion_mentalbert: {e}. Falling back to local rule-based simulation.", exc_info=True)
            try:
                from app.services.mentalbert_service import mentalbert_service
                scores = mentalbert_service.predict(message)
                try:
                    import torch
                    if torch.is_tensor(scores):
                        scores = scores.tolist()[0]
                except Exception:
                    pass
                
                emotions = ["happy", "neutral", "stress", "anxiety", "sadness", "frustration", "loneliness"]
                max_idx = scores.index(max(scores)) if scores else 1
                primary = emotions[max_idx].capitalize()
                confidence = max(scores) if scores else 0.5
                
                logger.info(f"[Fallback Simulator] Mapped failed API call to simulated emotion: '{primary}' (confidence: {confidence})")
                await self._save_emotion_log(db, user_id, message, primary, confidence)
                return {"detected_emotion": primary, "confidence_score": confidence}
            except Exception as fallback_err:
                logger.error(f"Fallback simulator also failed: {fallback_err}", exc_info=True)
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
