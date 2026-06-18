"""
Emotion Service – handles MentalBERT sequence classification for user emotions
and logs results in the emotion_logs table.
"""

import re
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

MENTALBERT_EMOTION_CLASSIFIER_CONTEXT_PROMPT = """You are an expert psychological emotion classifier fine-tuned on mental health conversations.
Your task is to classify the user's message into a primary emotion and secondary emotion.

Target Emotion Categories:
- Happy (positive affect, contentment, relief, cheerfulness, gratitude)
- Neutral (ONLY for truly neutral messages: standard greetings, purely informational questions, small talk with ZERO emotional charge)
- Stress (overwhelmed, burnout, financial pressure, too much to do, exhaustion, suffering)
- Anxiety (fear, worry, overthinking, panic, dread of the future, uncertainty)
- Sadness (grief, sorrow, hurt, disappointment, feeling low, heartbreak, loss)
- Frustration (anger, annoyance, irritation, resentment, betrayal, toxic relationships)
- Loneliness (isolation, feeling left out, no one to talk to, feeling abandoned)

## CRITICAL RULES:
1. NEVER return Neutral if the message contains ANY of these signals:
   - Strong negative words (toxic, bloody, damn, hate, ruined, suffering, etc.)
   - Relationship conflict (breakup, cheating, toxic partner, fight with gf/bf)
   - Financial distress (lost money, debt, finance issues, can't afford)
   - Emotional pain words (hurt, devastated, broken, hopeless)
   - Profanity or strong expletives used in frustration
   - The word "suffering" alone is enough to return Stress or Sadness
2. Words like "bloody", "toxic", "damm/damn", "lost all my money" = Frustration/Anger, NOT Neutral
3. "suffering from finance issue" = Stress, NOT Neutral
4. If you see relationship + financial stress together, pick the strongest emotion (usually Frustration or Stress)
5. Consider the Keyword-Boosted Pre-Prediction as a strong signal — do not ignore it

Input Details provided:
- Normalized message: {normalized_message}
- Keyword-Boosted Pre-Prediction: {base_prediction} (confidence: {base_confidence})
- Detected Emojis: {emoji_summary}
- Recent history context: {recent_context}
- Past session summary context: {past_summary}
- Relevant Memories: {memories}
- Knowledge Graph: {kg}

Output ONLY a valid JSON object matching this schema:
{{
  "detected_emotion": "Happy" | "Neutral" | "Stress" | "Anxiety" | "Sadness" | "Frustration" | "Loneliness",
  "secondary_emotion": "Happy" | "Neutral" | "Stress" | "Anxiety" | "Sadness" | "Frustration" | "Loneliness" | "None",
  "topic": string,
  "intensity": integer between 1-10,
  "confidence_score": float between 0.0-1.0
}}"""


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


def normalize_stretched_words(text: str) -> str:
    if not text:
        return text
    # Specific common stretched words
    text = re.sub(r'\b(bro)o+\b', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(up)p+\b', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(no)o+\b', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(please)e+\b', r'\1', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(so)o+\b', r'\1', text, flags=re.IGNORECASE)
    
    # General de-stretching for letters:
    # Reduce 3+ 'o' and 'e' to 2 (e.g. goood -> good, pleaseeee -> pleasee)
    text = re.sub(r'([oOeE])\1{2,}', r'\1\1', text)
    # Reduce any other letter repeating 3+ times to 1 (e.g. lll -> l, ppp -> p)
    text = re.sub(r'([a-zA-Z])\1{2,}', r'\1', text)
    return text


def extract_emojis(text: str) -> dict:
    if not text:
        return {}
    target_emojis = ["😭", "💔", "😡", "🥺", "😂", "❤️"]
    counts = {}
    for emo in target_emojis:
        c = text.count(emo)
        if c > 0:
            counts[emo] = c
    return counts


# ── Keyword Boost Tables ────────────────────────────────────────────────────
ANGER_WORDS = [
    "hate", "toxic", "bloody", "damn", "damm", "fuck", "shit", "annoyed", "furious",
    "ruined", "cheated", "betrayed", "lied", "deceived", "manipulated", "abusive",
    "disgusting", "disgusted", "enraged", "outraged", "livid", "infuriated",
    "fed up", "sick of", "can't stand", "pissed", "rage", "wasted my time",
]
SAD_WORDS = [
    "breakup", "broke up", "heartbroken", "heartbreak", "alone", "cry", "crying",
    "lost", "hurt", "suffering", "suffer", "devastated", "hopeless", "worthless",
    "depressed", "depression", "grief", "grieving", "miserable", "empty", "numb",
    "abandoned", "rejected", "unloved", "shattered", "broken", "miss her", "miss him",
]
STRESS_WORDS = [
    "stress", "stressed", "overwhelmed", "exhausted", "burnout", "tired", "pressure",
    "finance", "financial", "money", "debt", "loan", "bills", "salary", "afford",
    "suffering", "struggling", "swamped", "deadline", "overloaded", "behind",
    "bankrupt", "broke", "poverty", "eviction", "lost all",
]
ANXIETY_WORDS = [
    "anxious", "anxiety", "worry", "worried", "panic", "scared", "terrified",
    "fear", "afraid", "dread", "nervous", "overthinking", "uneasy", "frightened",
]
LONELY_WORDS = [
    "lonely", "loneliness", "isolated", "isolation", "abandoned", "no one",
    "nobody", "alone", "excluded", "forgotten", "disconnected", "friendless",
]
HAPPY_WORDS = [
    "happy", "joy", "excited", "glad", "cheerful", "thrilled", "grateful",
    "blessed", "wonderful", "amazing", "great", "fantastic", "love", "smile",
]


def compute_keyword_boost(
    text_lower: str, emoji_counts: dict
) -> tuple[str, float, dict]:
    """
    Compute a keyword-boosted emotion score and return:
    (best_emotion, best_score, all_scores_dict)
    This runs BEFORE the LLM call so the LLM has a strong signal.
    """
    scores = {
        "Happy": 0.0,
        "Neutral": 0.0,
        "Stress": 0.0,
        "Anxiety": 0.0,
        "Sadness": 0.0,
        "Frustration": 0.0,
        "Loneliness": 0.0,
    }

    # Phrase-level matches (higher weight)
    anger_phrases = [
        "lost all my money", "toxic girl", "toxic guy", "toxic person",
        "sick of her", "sick of him", "she ruined", "he ruined",
        "wasted my time", "ruined everything", "pissed off", "fed up",
        "cheated on me", "she cheated", "he cheated",
    ]
    sad_phrases = [
        "broke up", "broke my heart", "broken heart", "feel so empty",
        "no one cares", "nobody cares", "lost everything", "feel hopeless",
    ]
    stress_phrases = [
        "financial issue", "finance issue", "money problem", "lost all my money",
        "can't afford", "can not afford", "struggling financially", "running out of money",
        "behind on bills", "so much to do", "overwhelmed with",
    ]

    for phrase in anger_phrases:
        if phrase in text_lower:
            scores["Frustration"] += 0.5
    for phrase in sad_phrases:
        if phrase in text_lower:
            scores["Sadness"] += 0.5
    for phrase in stress_phrases:
        if phrase in text_lower:
            scores["Stress"] += 0.5

    # Single keyword matches
    words = set(text_lower.split())
    for w in ANGER_WORDS:
        if w in words or w in text_lower:
            scores["Frustration"] += 0.2
    for w in SAD_WORDS:
        if w in words or w in text_lower:
            scores["Sadness"] += 0.2
    for w in STRESS_WORDS:
        if w in words or w in text_lower:
            scores["Stress"] += 0.2
    for w in ANXIETY_WORDS:
        if w in words or w in text_lower:
            scores["Anxiety"] += 0.2
    for w in LONELY_WORDS:
        if w in words or w in text_lower:
            scores["Loneliness"] += 0.2
    for w in HAPPY_WORDS:
        if w in words or w in text_lower:
            scores["Happy"] += 0.2

    # Emoji boosts
    scores["Sadness"] += (emoji_counts.get("😭", 0) * 0.4) + (emoji_counts.get("💔", 0) * 0.5)
    scores["Frustration"] += emoji_counts.get("😡", 0) * 0.4
    scores["Anxiety"] += emoji_counts.get("🥺", 0) * 0.3
    scores["Happy"] += (emoji_counts.get("😂", 0) * 0.3) + (emoji_counts.get("❤️", 0) * 0.3)

    # Only give Neutral a score if NO other emotion was detected
    total_emotion = sum(v for k, v in scores.items() if k != "Neutral")
    scores["Neutral"] = 0.1 if total_emotion < 0.1 else 0.0

    # Pick winner
    best_emotion = max(scores, key=lambda e: scores[e])
    best_score = min(1.0, scores[best_emotion])

    logger.info(
        f"[KeywordBoost] Scores: { {k: round(v, 2) for k, v in scores.items()} } "
        f"→ best={best_emotion} ({best_score:.2f})"
    )
    return best_emotion, best_score, scores


def boost_local_predictions(predictions: Any, emoji_counts: dict) -> tuple[str, float]:
    scores = {
        "Happy": 0.0,
        "Neutral": 0.0,
        "Stress": 0.0,
        "Anxiety": 0.0,
        "Sadness": 0.0,
        "Frustration": 0.0,
        "Loneliness": 0.0
    }
    
    pred_list = []
    if isinstance(predictions, dict):
        pred_list = [predictions]
    elif isinstance(predictions, list):
        if len(predictions) > 0 and isinstance(predictions[0], list):
            pred_list = predictions[0]
        else:
            pred_list = predictions
            
    for pred in pred_list:
        matched = map_model_label_to_wellness_emotion(pred.get("label", ""))
        scores[matched] = max(scores[matched], float(pred.get("score", 0.0)))
        
    sadness_boost = (emoji_counts.get("😭", 0) * 0.4) + (emoji_counts.get("💔", 0) * 0.5)
    frustration_boost = emoji_counts.get("😡", 0) * 0.4
    anxiety_boost = emoji_counts.get("🥺", 0) * 0.3
    happy_boost = (emoji_counts.get("😂", 0) * 0.3) + (emoji_counts.get("❤️", 0) * 0.3)
    
    scores["Sadness"] += sadness_boost
    scores["Frustration"] += frustration_boost
    scores["Anxiety"] += anxiety_boost
    scores["Happy"] += happy_boost
    
    total_boost = sadness_boost + frustration_boost + anxiety_boost + happy_boost
    if total_boost > 0:
        scores["Neutral"] = max(0.0, scores["Neutral"] - total_boost)
        
    best_emotion = "Neutral"
    best_score = 0.0
    for emo, score in scores.items():
        if score > best_score:
            best_score = score
            best_emotion = emo
            
    best_score = min(1.0, best_score)
    return best_emotion, best_score


async def _get_conversation_summary(db: AsyncSession, user_id: str, conversation_id: str) -> str | None:
    try:
        from app.models.memory import Memory
        from sqlalchemy import select
        result = await db.execute(
            select(Memory).where(Memory.user_id == (uuid.UUID(user_id) if isinstance(user_id, str) else user_id))
        )
        memories = result.scalars().all()
        for m in memories:
            meta = m.metadata_json or {}
            if meta.get("source") == "conversation_summary" and meta.get("conversation_id") == str(conversation_id):
                return m.memory_summary
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch conversation summary in emotion service: {e}")
    return None


class EmotionService:
    """Manages emotion classification and logs results to the database."""

    async def classify_emotion_mentalbert(
        self, db: AsyncSession, user_id: str, message: str, conversation_id: str = None, 
        history: list = None, memories: list = None, graph_relationships: list = None
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

        # Extract emojis and normalize message stretching before model evaluation
        emoji_counts = extract_emojis(message)
        normalized_message = normalize_stretched_words(message)

        raw_predictions = None

        # 1. Keyword-Boosted Pre-Prediction (always runs, fast, no API calls)
        base_prediction, base_confidence, boost_scores = compute_keyword_boost(
            normalized_message.lower(), emoji_counts
        )

        # 2. Attempt local MentalBERT model (if configured)
        if settings.USE_LOCAL_EMOTION_MODEL:
            classifier = get_local_classifier()
            if classifier is not None:
                try:
                    logger.info(f"TEXT SENT TO MENTALBERT (Local): '{normalized_message}'")
                    raw_predictions = classifier(normalized_message)
                    
                    if raw_predictions and len(raw_predictions) > 0:
                        local_emotion, local_confidence = boost_local_predictions(raw_predictions, emoji_counts)
                        # Override base_prediction if local model is more confident
                        if local_confidence > base_confidence:
                            base_prediction = local_emotion
                            base_confidence = local_confidence
                except Exception as local_err:
                    logger.error(f"Local emotion classification failed: {local_err}. Using keyword-boost prediction.", exc_info=True)

        # 3. Execute Context Resolver via LLM
        try:
            client = get_chat_client()
            
            # Emoji context string
            if emoji_counts:
                emoji_summary = ", ".join(f"{emo} (count: {count})" for emo, count in emoji_counts.items())
            else:
                emoji_summary = "None"
                
            # Recent history context
            recent_context = "None"
            if history:
                last_messages = history[-6:]
                recent_context = "\n".join(
                    f"{m.get('role', 'user')}: {m.get('content', '')}" for m in last_messages
                )
                
            # Past session summary
            past_summary = "None"
            if conversation_id and db:
                past_summary = await _get_conversation_summary(db, user_id, conversation_id) or "None"
                
            memories_str = "None"
            if memories:
                memories_str = "\n".join(memories)
                
            kg_str = "None"
            if graph_relationships:
                kg_str = "\n".join(graph_relationships)
                
            prompt = MENTALBERT_EMOTION_CLASSIFIER_CONTEXT_PROMPT.format(
                normalized_message=normalized_message,
                base_prediction=base_prediction,
                base_confidence=round(base_confidence, 2),
                emoji_summary=emoji_summary,
                recent_context=recent_context,
                past_summary=past_summary,
                memories=memories_str,
                kg=kg_str
            )
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"User message: {message}"},
            ]
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
            result = json.loads(raw)
            
            detected_emotion = result.get("detected_emotion", "Neutral")
            confidence_score = float(result.get("confidence_score", 0.8))
            secondary_emotion = result.get("secondary_emotion", "None")
            topic = result.get("topic", "")
            intensity = result.get("intensity", 5)
            
            # Normalize casing
            valid_emotions = ["Happy", "Neutral", "Stress", "Anxiety", "Sadness", "Frustration", "Loneliness"]
            matched_emotion = "Neutral"
            for emo in valid_emotions:
                if detected_emotion.lower() == emo.lower():
                    matched_emotion = emo
                    break

            # Safety net: if LLM returned Neutral but keyword boost found a strong emotion, override
            if matched_emotion == "Neutral" and base_prediction != "Neutral" and base_confidence >= 0.3:
                logger.warning(
                    f"[Anti-Neutral Override] LLM returned Neutral but keyword boost says "
                    f"{base_prediction} ({base_confidence:.2f}). Overriding to {base_prediction}."
                )
                matched_emotion = base_prediction
                confidence_score = max(confidence_score, base_confidence)

            logger.info(
                f"\n=== MENTALBERT DEBUG ===\n"
                f"User Message: {message}\n"
                f"Keyword-Boost Pre-Prediction: {base_prediction} (conf: {base_confidence:.2f})\n"
                f"Raw MentalBERT Scores: {raw_predictions if raw_predictions else 'N/A (keyword-boost only)'}\n"
                f"LLM Selected Emotion: {matched_emotion} (conf: {confidence_score:.2f})\n"
                f"Secondary Emotion: {secondary_emotion}\n"
                f"Topic: {topic}\n"
                f"Intensity: {intensity}/10\n"
                f"Final Stored Emotion: {matched_emotion}\n"
                f"========================"
            )

            await self._save_emotion_log(db, user_id, message, matched_emotion, confidence_score)

            return {
                "detected_emotion": matched_emotion,
                "confidence_score": confidence_score
            }

        except Exception as e:
            logger.error(f"Error in Context Resolver LLM: {e}. Falling back to base prediction or rule-based simulation.", exc_info=True)
            if base_prediction != "Unknown (Using LLM context inference)":
                await self._save_emotion_log(db, user_id, message, base_prediction, base_confidence)
                return {"detected_emotion": base_prediction, "confidence_score": base_confidence}
                
            try:
                from app.services.mentalbert_service import mentalbert_service
                scores = mentalbert_service.predict(normalized_message)
                try:
                    import torch
                    if torch.is_tensor(scores):
                        scores = scores.tolist()[0]
                except Exception:
                    pass
                
                # Apply emoji boosts to rule-based fallback list
                # 0: happy, 1: neutral, 2: stress, 3: anxiety, 4: sadness, 5: frustration, 6: loneliness
                sadness_boost = (emoji_counts.get("😭", 0) * 0.4) + (emoji_counts.get("💔", 0) * 0.5)
                frustration_boost = emoji_counts.get("😡", 0) * 0.4
                anxiety_boost = emoji_counts.get("🥺", 0) * 0.3
                happy_boost = (emoji_counts.get("😂", 0) * 0.3) + (emoji_counts.get("❤️", 0) * 0.3)
                
                if len(scores) >= 7:
                    scores[0] += happy_boost
                    scores[2] += sadness_boost * 0.3
                    scores[3] += anxiety_boost
                    scores[4] += sadness_boost
                    scores[5] += frustration_boost
                    
                    total_boost = sadness_boost + frustration_boost + anxiety_boost + happy_boost
                    if total_boost > 0:
                        scores[1] = max(0.0, scores[1] - total_boost)
                
                emotions = ["happy", "neutral", "stress", "anxiety", "sadness", "frustration", "loneliness"]
                max_idx = scores.index(max(scores)) if scores else 1
                primary = emotions[max_idx].capitalize()
                confidence = min(1.0, max(scores) if scores else 0.5)
                
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

