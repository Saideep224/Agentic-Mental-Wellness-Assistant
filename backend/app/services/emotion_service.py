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

HYBRID_EMOTION_CLASSIFIER_PROMPT = """You are an expert psychological emotion classifier fine-tuned on mental health conversations.
Your task is to analyze the user's current message and the conversation context, and output probability distributions for the 7 wellness emotions:
- Happy (positive affect, contentment, relief, cheerfulness, gratitude)
- Neutral (standard greetings, purely informational questions, small talk with ZERO emotional charge)
- Stress (overwhelmed, burnout, financial pressure, too much to do, exhaustion, suffering)
- Anxiety (fear, worry, overthinking, panic, dread of the future, uncertainty)
- Sadness (grief, sorrow, hurt, disappointment, feeling low, heartbreak, loss)
- Frustration (anger, annoyance, irritation, resentment, betrayal, toxic relationships)
- Loneliness (isolation, feeling left out, no one to talk to, feeling abandoned)

You must output two separate probability distributions (each summing to 1.0):
1. `gemini_analysis`: Probability scores (0.0 to 1.0) for the CURRENT MESSAGE ONLY, ignoring any past history.
   - CRITICAL: Never assign a high Neutral score if the message contains strong emotional words, relationship conflict, or financial issues. For example: "I lost all my money because of my toxic girlfriend" has high Frustration and Sadness, and very low Neutral.
2. `conversation_context`: Probability scores (0.0 to 1.0) based ONLY on recent history, relevant memories, and knowledge graph context.
   - For example: if there are relationship problems or financial stress detected in the history, assign higher probability to Frustration, Stress, or Sadness.

Input Details:
- Current message: "{normalized_message}"
- Pre-prediction: {base_prediction} (confidence: {base_confidence})
- Recent history context: {recent_context}
- Relevant Memories: {memories}
- Knowledge Graph: {kg}

Output ONLY a valid JSON object matching this schema:
{{
  "gemini_analysis": {{
    "Happy": float,
    "Neutral": float,
    "Stress": float,
    "Anxiety": float,
    "Sadness": float,
    "Frustration": float,
    "Loneliness": float
  }},
  "conversation_context": {{
    "Happy": float,
    "Neutral": float,
    "Stress": float,
    "Anxiety": float,
    "Sadness": float,
    "Frustration": float,
    "Loneliness": float
  }},
  "topic": string,
  "intensity": integer between 1-10
}}
"""


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
        Classifies the message into one of the 7 specified emotions using a hybrid
        blending formula: 40% MentalBERT, 40% Gemini, 20% Conversation Context.
        Logs it in the emotion_logs table, and returns the result.
        """
        if not message or len(message.strip()) < 1:
            return {
                "detected_emotion": "Neutral",
                "confidence_score": 1.0,
                "blended_scores": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            }

        # Crisis Override Check
        msg_lower = message.lower()
        crisis_keywords = ["want to die", "kill myself", "end my life", "suicide"]
        if any(keyword in msg_lower for keyword in crisis_keywords):
            logger.warning(f"[Crisis Override] Crisis detected in message: '{message}'. Overriding to Crisis classification.")
            await self._save_emotion_log(db, user_id, message, "Crisis", 0.95)
            return {
                "detected_emotion": "Crisis",
                "confidence_score": 0.95,
                "blended_scores": [0.0, 0.05, 0.15, 0.0, 0.75, 0.0, 0.05]
            }

        # Extract emojis and normalize message stretching before model evaluation
        emoji_counts = extract_emojis(message)
        normalized_message = normalize_stretched_words(message)

        # 1. Get MentalBERT/Keyword scores (40%)
        # predict() returns list of 7 floats: Happy, Neutral, Stress, Anxiety, Sadness, Frustration, Loneliness
        mb_scores = []
        try:
            from app.services.mentalbert_service import mentalbert_service
            mb_scores = mentalbert_service.predict(normalized_message)
            try:
                import torch
                if torch.is_tensor(mb_scores):
                    mb_scores = mb_scores.tolist()[0]
            except Exception:
                pass
        except Exception as mb_err:
            logger.warning(f"MentalBERT predict failed: {mb_err}")

        # Ensure it has exactly 7 elements and sums to 1.0
        while len(mb_scores) < 7:
            mb_scores.append(0.0)
        mb_sum = sum(mb_scores)
        if mb_sum > 0:
            mb_scores = [s / mb_sum for s in mb_scores]
        else:
            mb_scores = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # 2. Get Gemini Analysis (40%) and Conversation Context (20%) via LLM
        emotions_order = ["Happy", "Neutral", "Stress", "Anxiety", "Sadness", "Frustration", "Loneliness"]
        gemini_scores = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        context_scores = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        topic = ""
        intensity = 5

        # Run pre-prediction for prompt input
        base_prediction, base_confidence, boost_scores = compute_keyword_boost(
            normalized_message.lower(), emoji_counts
        )

        try:
            client = get_chat_client()
            
            # Recent history context
            recent_context = "None"
            if history:
                last_messages = history[-6:]
                recent_context = "\n".join(
                    f"{m.get('role', 'user')}: {m.get('content', '')}" for m in last_messages
                )
                
            memories_str = "None"
            if memories:
                memories_str = "\n".join(memories)
                
            kg_str = "None"
            if graph_relationships:
                kg_str = "\n".join(graph_relationships)
                
            prompt = HYBRID_EMOTION_CLASSIFIER_PROMPT.format(
                normalized_message=normalized_message,
                base_prediction=base_prediction,
                base_confidence=round(base_confidence, 2),
                recent_context=recent_context,
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
            
            gemini_analysis = result.get("gemini_analysis", {})
            conversation_context = result.get("conversation_context", {})
            topic = result.get("topic", "")
            intensity = result.get("intensity", 5)

            # Map named keys in JSON to the strict emotions_order
            def parse_distribution(dist_dict):
                scores_list = []
                for emo in emotions_order:
                    # try case-insensitive match
                    val = 0.0
                    for k, v in dist_dict.items():
                        if k.lower() == emo.lower():
                            val = float(v)
                            break
                    scores_list.append(val)
                s_sum = sum(scores_list)
                if s_sum > 0:
                    return [s / s_sum for s in scores_list]
                return [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]

            gemini_scores = parse_distribution(gemini_analysis)
            context_scores = parse_distribution(conversation_context)

        except Exception as e:
            logger.error(f"Error in Hybrid Classifier LLM call: {e}. Falling back to MentalBERT / Keyword prediction.", exc_info=True)
            # fallback uses MentalBERT scores as both Gemini and context source
            gemini_scores = mb_scores
            context_scores = mb_scores

        # Calculate final blended scores
        blended_scores = []
        for i in range(7):
            val = 0.40 * mb_scores[i] + 0.40 * gemini_scores[i] + 0.20 * context_scores[i]
            blended_scores.append(val)

        # Normalize final blended scores
        blended_sum = sum(blended_scores)
        if blended_sum > 0:
            blended_scores = [s / blended_sum for s in blended_scores]
        else:
            blended_scores = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # Select final winning emotion
        max_idx = blended_scores.index(max(blended_scores))
        matched_emotion = emotions_order[max_idx]
        confidence_score = blended_scores[max_idx]

        # Safety net: if final is Neutral but keyword boost detected a strong emotion with high confidence
        if matched_emotion == "Neutral" and base_prediction != "Neutral" and base_confidence >= 0.35:
            logger.warning(
                f"[Blended Anti-Neutral Override] Final is Neutral but keyword boost says "
                f"{base_prediction} ({base_confidence:.2f}). Overriding to {base_prediction}."
            )
            # Re-distribute scores to give base_prediction the top score
            matched_emotion = base_prediction
            target_idx = emotions_order.index(matched_emotion)
            # Swap values to preserve sum = 1.0
            old_val = blended_scores[target_idx]
            blended_scores[target_idx] = blended_scores[1]
            blended_scores[1] = old_val
            confidence_score = blended_scores[target_idx]

        logger.info(
            f"\n=== HYBRID EMOTION BLENDER ===\n"
            f"User Message: {message}\n"
            f"MentalBERT (40%): { {emotions_order[i]: round(mb_scores[i], 2) for i in range(7)} }\n"
            f"Gemini (40%): { {emotions_order[i]: round(gemini_scores[i], 2) for i in range(7)} }\n"
            f"Context (20%): { {emotions_order[i]: round(context_scores[i], 2) for i in range(7)} }\n"
            f"Blended Final: { {emotions_order[i]: round(blended_scores[i], 2) for i in range(7)} }\n"
            f"Selected: {matched_emotion} (conf: {confidence_score:.2f})\n"
            f"Topic: {topic} | Intensity: {intensity}/10\n"
            f"========================"
        )

        await self._save_emotion_log(db, user_id, message, matched_emotion, confidence_score)

        return {
            "detected_emotion": matched_emotion,
            "confidence_score": confidence_score,
            "blended_scores": blended_scores,
            "topic": topic,
            "intensity": intensity
        }

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

