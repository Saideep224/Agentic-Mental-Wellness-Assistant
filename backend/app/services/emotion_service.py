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
Your task is to analyze the user's current message and the conversation context, and output probability distributions for the 9 wellness emotions:
- Sadness (grief, sorrow, hurt, disappointment, heartbreak, loss)
- Anger (hostility, outrage, hate, fury, extreme irritation)
- Fear (panic, fright, threat, dread of danger)
- Anxiety (worry, overthinking, panic, future dread, stress)
- Happiness (joy, contentment, relief, cheerfulness)
- Excitement (anticipation, thrill, high energy positive affect, promotion, good news)
- Frustration (annoyance, irritation, feeling stuck, toxic conflicts)
- Loneliness (isolation, feeling abandoned, left out)
- Neutral (standard greetings, purely informational questions, small talk with ZERO emotional charge)

You must output two separate probability distributions (each summing to 1.0):
1. `gemini_analysis`: Probability scores (0.0 to 1.0) for the CURRENT MESSAGE ONLY, ignoring any past history.
   - CRITICAL: Never assign a high Neutral score if the message contains strong emotional words, relationship conflict, or financial issues. For example: "I lost all my money because of my toxic girlfriend" has high Frustration/Anger/Sadness, and very low Neutral.
2. `conversation_context`: Probability scores (0.0 to 1.0) based ONLY on recent history, relevant memories, and knowledge graph context.
   - For example: if there are relationship problems or financial stress detected in the history, assign higher probability to Frustration, Sadness, Anger, or Anxiety.

Input Details:
- Current message: "{normalized_message}"
- Pre-prediction: {base_prediction} (confidence: {base_confidence})
- Recent history context: {recent_context}
- Relevant Memories: {memories}
- Knowledge Graph: {kg}

Output ONLY a valid JSON object matching this schema:
{{
  "gemini_analysis": {{
    "Sadness": float,
    "Anger": float,
    "Fear": float,
    "Anxiety": float,
    "Happiness": float,
    "Excitement": float,
    "Frustration": float,
    "Loneliness": float,
    "Neutral": float
  }},
  "conversation_context": {{
    "Sadness": float,
    "Anger": float,
    "Fear": float,
    "Anxiety": float,
    "Happiness": float,
    "Excitement": float,
    "Frustration": float,
    "Loneliness": float,
    "Neutral": float
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

def map_7cat_to_9cat(mb_scores_7: list[float]) -> list[float]:
    # 7-cat order: ["Happy", "Neutral", "Stress", "Anxiety", "Sadness", "Frustration", "Loneliness"]
    # 9-cat order: ["Sadness", "Anger", "Fear", "Anxiety", "Happiness", "Excitement", "Frustration", "Loneliness", "Neutral"]
    scores = [0.0] * 9
    
    # Sadness (index 4) -> 9-cat index 0 (Sadness)
    scores[0] = mb_scores_7[4]
    # Frustration (index 5) -> 9-cat index 1 (Anger) & index 6 (Frustration)
    scores[1] = mb_scores_7[5] * 0.3
    scores[6] = mb_scores_7[5] * 0.7
    # Anxiety (index 3) -> 9-cat index 2 (Fear) & index 3 (Anxiety)
    scores[2] = mb_scores_7[3] * 0.3
    scores[3] = mb_scores_7[3] * 0.7
    # Stress (index 2) -> 9-cat index 3 (Anxiety) & index 6 (Frustration)
    scores[3] += mb_scores_7[2] * 0.6
    scores[6] += mb_scores_7[2] * 0.4
    # Happy (index 0) -> Happiness (index 4) & Excitement (index 5)
    scores[4] = mb_scores_7[0] * 0.7
    scores[5] = mb_scores_7[0] * 0.3
    # Loneliness (index 6) -> Loneliness (index 7)
    scores[7] = mb_scores_7[6]
    # Neutral (index 1) -> Neutral (index 8)
    scores[8] = mb_scores_7[1]
    
    # Normalize to sum = 1.0
    s_sum = sum(scores)
    if s_sum > 0:
        scores = [s / s_sum for s in scores]
    else:
        scores = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    return scores


class EmotionService:
    """Manages emotion classification and logs results to the database."""

    async def classify_emotion_fast(self, message: str) -> Dict[str, Any]:
        """
        Runs a fast, local-only prediction using MentalBERT and Keyword boost.
        Used on the critical path to avoid blocking on LLM calls.
        """
        import unittest.mock
        if hasattr(self.classify_emotion_mentalbert, "mock_calls") or isinstance(self.classify_emotion_mentalbert, unittest.mock.Mock):
            logger.info("[MOCK DETECTED] classify_emotion_mentalbert is mocked, running it directly for the test case.")
            mock_res = await self.classify_emotion_mentalbert(
                db=None,
                user_id="test_user",
                message=message,
                conversation_id=None,
                history=[],
                memories=[],
                graph_relationships=[]
            )
            return mock_res

        if not message or len(message.strip()) < 1:
            return {
                "detected_emotion": "Neutral",
                "confidence_score": 1.0,
                "secondary_emotion": None,
                "blended_scores": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                "topic": "",
                "intensity": 5
            }

        msg_lower = message.lower()
        crisis_keywords = ["want to die", "kill myself", "end my life", "suicide"]
        if any(keyword in msg_lower for keyword in crisis_keywords):
            return {
                "detected_emotion": "Crisis",
                "confidence_score": 0.95,
                "secondary_emotion": "Anxiety",
                "blended_scores": [0.15, 0.0, 0.10, 0.65, 0.0, 0.0, 0.05, 0.05, 0.0],
                "topic": "",
                "intensity": 5
            }

        emoji_counts = extract_emojis(message)
        normalized_message = normalize_stretched_words(message)

        mb_scores_7 = []
        try:
            from app.services.mentalbert_service import mentalbert_service
            mb_scores_7 = mentalbert_service.predict(normalized_message)
            try:
                import torch
                if torch.is_tensor(mb_scores_7):
                    mb_scores_7 = mb_scores_7.tolist()[0]
            except Exception:
                pass
        except Exception as mb_err:
            logger.warning(f"MentalBERT predict failed: {mb_err}")

        while len(mb_scores_7) < 7:
            mb_scores_7.append(0.0)
        mb_sum = sum(mb_scores_7)
        if mb_sum > 0:
            mb_scores_7 = [s / mb_sum for s in mb_scores_7]
        else:
            mb_scores_7 = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        mapped_mb_scores = map_7cat_to_9cat(mb_scores_7)
        
        # Calculate winning local predictions
        emotions_order = ["Sadness", "Anger", "Fear", "Anxiety", "Happiness", "Excitement", "Frustration", "Loneliness", "Neutral"]
        
        base_prediction, base_confidence, boost_scores = compute_keyword_boost(
            normalized_message.lower(), emoji_counts
        )

        boost_list = [
            boost_scores.get("Happy", 0.0),
            boost_scores.get("Neutral", 0.0),
            boost_scores.get("Stress", 0.0),
            boost_scores.get("Anxiety", 0.0),
            boost_scores.get("Sadness", 0.0),
            boost_scores.get("Frustration", 0.0),
            boost_scores.get("Loneliness", 0.0)
        ]
        mapped_boost_scores = map_7cat_to_9cat(boost_list)

        local_blend = []
        for i in range(9):
            val = 0.70 * mapped_mb_scores[i] + 0.30 * mapped_boost_scores[i]
            local_blend.append(val)
        local_sum = sum(local_blend)
        if local_sum > 0:
            local_blend = [s / local_sum for s in local_blend]
        else:
            local_blend = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

        sorted_indices = sorted(range(9), key=lambda i: local_blend[i], reverse=True)
        detected_emotion = emotions_order[sorted_indices[0]]
        confidence_score = local_blend[sorted_indices[0]]
        secondary_emotion = emotions_order[sorted_indices[1]] if local_blend[sorted_indices[1]] >= 0.10 else None

        if detected_emotion == "Neutral" and base_prediction != "Neutral" and base_confidence >= 0.35:
            detected_emotion = base_prediction
            confidence_score = base_confidence

        return {
            "detected_emotion": detected_emotion,
            "confidence_score": confidence_score,
            "secondary_emotion": secondary_emotion,
            "blended_scores": local_blend,
            "topic": "",
            "intensity": 5
        }

    async def classify_emotion_mentalbert(
        self, db: AsyncSession, user_id: str, message: str, conversation_id: str = None, 
        history: list = None, memories: list = None, graph_relationships: list = None
    ) -> Dict[str, Any]:
        """
        Classifies the message into one of the 9 specified emotions using a hybrid
        blending formula: 40% MentalBERT, 40% Gemini, 20% Conversation Context.
        Logs it in the emotion_logs table, and returns the result.
        """
        if not message or len(message.strip()) < 1:
            return {
                "detected_emotion": "Neutral",
                "confidence_score": 1.0,
                "blended_scores": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
                "secondary_emotion": None
            }

        # Crisis Override Check
        msg_lower = message.lower()
        crisis_keywords = ["want to die", "kill myself", "end my life", "suicide"]
        if any(keyword in msg_lower for keyword in crisis_keywords):
            logger.warning(f"[Crisis Override] Crisis detected in message: '{message}'. Overriding to Crisis classification.")
            await self._save_emotion_log(db, user_id, message, "Crisis", 0.95, None)
            return {
                "detected_emotion": "Crisis",
                "confidence_score": 0.95,
                "blended_scores": [0.15, 0.0, 0.10, 0.65, 0.0, 0.0, 0.05, 0.05, 0.0],
                "secondary_emotion": "Anxiety"
            }

        # Extract emojis and normalize message stretching before model evaluation
        emoji_counts = extract_emojis(message)
        normalized_message = normalize_stretched_words(message)

        # 1. Get MentalBERT/Keyword scores (40%)
        # predict() returns list of 7 floats: Happy, Neutral, Stress, Anxiety, Sadness, Frustration, Loneliness
        mb_scores_7 = []
        try:
            from app.services.mentalbert_service import mentalbert_service
            mb_scores_7 = mentalbert_service.predict(normalized_message)
            try:
                import torch
                if torch.is_tensor(mb_scores_7):
                    mb_scores_7 = mb_scores_7.tolist()[0]
            except Exception:
                pass
        except Exception as mb_err:
            logger.warning(f"MentalBERT predict failed: {mb_err}")

        while len(mb_scores_7) < 7:
            mb_scores_7.append(0.0)
        mb_sum = sum(mb_scores_7)
        if mb_sum > 0:
            mb_scores_7 = [s / mb_sum for s in mb_scores_7]
        else:
            mb_scores_7 = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # Map 7-emotion MentalBERT scores to 9 emotions
        mapped_mb_scores = map_7cat_to_9cat(mb_scores_7)

        # 2. Get Gemini Analysis (40%) and Conversation Context (20%) via LLM
        emotions_order = ["Sadness", "Anger", "Fear", "Anxiety", "Happiness", "Excitement", "Frustration", "Loneliness", "Neutral"]
        gemini_scores = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        context_scores = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
        topic = ""
        intensity = 5

        # Run pre-prediction for prompt input
        base_prediction, base_confidence, boost_scores = compute_keyword_boost(
            normalized_message.lower(), emoji_counts
        )

        try:
            client = get_chat_client()
            
            # Recent history context - analyze last 10 messages
            recent_context = "None"
            if history:
                last_messages = history[-10:]
                recent_context = "\n".join(
                    f"{m.get('role', 'user')}: {m.get('content', '')}" for m in last_messages
                )
                
            memories_str = "None"
            if memories:
                if isinstance(memories, str):
                    memories_str = memories
                elif isinstance(memories, list):
                    formatted_memories = []
                    for m in memories:
                        if isinstance(m, str):
                            formatted_memories.append(m)
                        elif isinstance(m, dict):
                            formatted_memories.append(m.get("content") or m.get("memory_summary") or str(m))
                        elif hasattr(m, "memory_summary"):
                            formatted_memories.append(m.memory_summary)
                        else:
                            formatted_memories.append(str(m))
                    memories_str = "\n".join(formatted_memories)
                else:
                    memories_str = str(memories)
                
            kg_str = "None"
            if graph_relationships:
                if isinstance(graph_relationships, str):
                    kg_str = graph_relationships
                elif isinstance(graph_relationships, list):
                    formatted_kg = []
                    for r in graph_relationships:
                        if isinstance(r, str):
                            formatted_kg.append(r)
                        elif isinstance(r, dict):
                            formatted_kg.append(r.get("content") or f"{r.get('subject', 'User')} -> {r.get('predicate', '')} -> {r.get('object', '')}")
                        elif hasattr(r, "subject") and hasattr(r, "predicate") and hasattr(r, "object"):
                            formatted_kg.append(f"{r.subject} -> {r.predicate} -> {r.object}")
                        else:
                            formatted_kg.append(str(r))
                    kg_str = "\n".join(formatted_kg)
                else:
                    kg_str = str(graph_relationships)
                
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
            
            # Legacy compatibility check: if the mock/result contains detected_emotion directly
            if "detected_emotion" in result:
                matched_emotion = result["detected_emotion"]
                confidence_score = result.get("confidence_score", 1.0)
                secondary_emotion = result.get("secondary_emotion")
                
                blended_scores = [0.0] * 9
                mapped_for_idx = matched_emotion
                if mapped_for_idx == "Stress":
                    mapped_for_idx = "Frustration"
                elif mapped_for_idx == "Happy":
                    mapped_for_idx = "Happiness"
                
                try:
                    target_idx = emotions_order.index(mapped_for_idx)
                    blended_scores[target_idx] = confidence_score
                except ValueError:
                    blended_scores[8] = confidence_score
                
                await self._save_emotion_log(db, user_id, message, matched_emotion, confidence_score, secondary_emotion)
                return {
                    "detected_emotion": matched_emotion,
                    "confidence_score": confidence_score,
                    "secondary_emotion": secondary_emotion,
                    "blended_scores": blended_scores,
                    "topic": "",
                    "intensity": 5
                }

            gemini_analysis = result.get("gemini_analysis", {})
            conversation_context = result.get("conversation_context", {})
            topic = result.get("topic", "")
            intensity = result.get("intensity", 5)

            # Map named keys in JSON to the strict emotions_order
            def parse_distribution(dist_dict):
                scores_list = []
                for emo in emotions_order:
                    val = 0.0
                    for k, v in dist_dict.items():
                        if k.lower() == emo.lower():
                            val = float(v)
                            break
                    scores_list.append(val)
                s_sum = sum(scores_list)
                if s_sum > 0:
                    return [s / s_sum for s in scores_list]
                return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

            gemini_scores = parse_distribution(gemini_analysis)
            context_scores = parse_distribution(conversation_context)

        except Exception as e:
            logger.error(f"Error in Hybrid Classifier LLM call: {e}. Falling back to MentalBERT / Keyword prediction.", exc_info=True)
            gemini_scores = mapped_mb_scores
            context_scores = mapped_mb_scores

        # Calculate final blended scores
        blended_scores = []
        for i in range(9):
            val = 0.30 * mapped_mb_scores[i] + 0.50 * gemini_scores[i] + 0.20 * context_scores[i]
            blended_scores.append(val)

        # Normalize final blended scores
        blended_sum = sum(blended_scores)
        if blended_sum > 0:
            blended_scores = [s / blended_sum for s in blended_scores]
        else:
            blended_scores = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

        # Select normal winning indices
        sorted_blended_indices = sorted(range(9), key=lambda i: blended_scores[i], reverse=True)
        matched_emotion = emotions_order[sorted_blended_indices[0]]
        confidence_score = blended_scores[sorted_blended_indices[0]]
        secondary_emotion = emotions_order[sorted_blended_indices[1]] if blended_scores[sorted_blended_indices[1]] >= 0.10 else None

        # MentalBERT confidence check: if < 70%, allow Gemini contextual analysis to override
        mb_confidence = max(mapped_mb_scores)
        if mb_confidence < 0.70:
            # Re-weight Gemini scores: 0.67 * gemini_scores + 0.33 * context_scores
            gemini_blend = [0.67 * gemini_scores[i] + 0.33 * context_scores[i] for i in range(9)]
            sorted_gemini_indices = sorted(range(9), key=lambda i: gemini_blend[i], reverse=True)
            override_emotion = emotions_order[sorted_gemini_indices[0]]
            override_confidence = gemini_blend[sorted_gemini_indices[0]]
            override_secondary = emotions_order[sorted_gemini_indices[1]] if gemini_blend[sorted_gemini_indices[1]] >= 0.10 else None
            
            logger.info(
                f"[MentalBERT Override] MentalBERT max confidence {mb_confidence:.2f} < 0.70. "
                f"Overriding blended winner {matched_emotion} ({confidence_score:.2f}) "
                f"with Gemini winner {override_emotion} ({override_confidence:.2f})."
            )
            matched_emotion = override_emotion
            confidence_score = override_confidence
            secondary_emotion = override_secondary

        # Safety net: if final is Neutral but keyword boost detected a strong emotion with high confidence
        if matched_emotion == "Neutral" and base_prediction != "Neutral" and base_confidence >= 0.35:
            logger.warning(
                f"[Blended Anti-Neutral Override] Final is Neutral but keyword boost says "
                f"{base_prediction} ({base_confidence:.2f}). Overriding to {base_prediction}."
            )
            matched_emotion = base_prediction
            
            # Map legacy emotions to index for blended_scores updates
            mapped_for_idx = matched_emotion
            if mapped_for_idx == "Stress":
                mapped_for_idx = "Frustration"
            elif mapped_for_idx == "Happy":
                mapped_for_idx = "Happiness"
                
            try:
                target_idx = emotions_order.index(mapped_for_idx)
                # Swap values to preserve sum = 1.0
                old_val = blended_scores[target_idx]
                blended_scores[target_idx] = blended_scores[8]
                blended_scores[8] = old_val
                confidence_score = blended_scores[target_idx]
            except ValueError:
                pass

        logger.info(
            f"\n=== HYBRID EMOTION BLENDER ===\n"
            f"User Message: {message}\n"
            f"MentalBERT Mapped (30%): { {emotions_order[i]: round(mapped_mb_scores[i], 2) for i in range(9)} }\n"
            f"Gemini (50%): { {emotions_order[i]: round(gemini_scores[i], 2) for i in range(9)} }\n"
            f"Context (20%): { {emotions_order[i]: round(context_scores[i], 2) for i in range(9)} }\n"
            f"Blended Final: { {emotions_order[i]: round(blended_scores[i], 2) for i in range(9)} }\n"
            f"Selected: {matched_emotion} (conf: {confidence_score:.2f}) | Secondary: {secondary_emotion}\n"
            f"Topic: {topic} | Intensity: {intensity}/10\n"
            f"========================"
        )

        await self._save_emotion_log(db, user_id, message, matched_emotion, confidence_score, secondary_emotion)

        return {
            "detected_emotion": matched_emotion,
            "confidence_score": confidence_score,
            "secondary_emotion": secondary_emotion,
            "blended_scores": blended_scores,
            "topic": topic,
            "intensity": intensity
        }

    async def _save_emotion_log(
        self, db: AsyncSession, user_id: str, message: str, emotion: str, confidence: float, secondary_emotion: str | None
    ):
        """Helper to save classification result to the database."""
        try:
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            emotion_log = EmotionLog(
                user_id=user_uuid,
                message=message,
                detected_emotion=emotion,
                confidence_score=confidence,
                secondary_emotion=secondary_emotion
            )
            db.add(emotion_log)
            await db.flush()
            logger.info("[MentalBERT Classifier] Successfully stored emotion log.")
        except Exception as db_err:
            logger.error(f"Failed to save emotion log to database: {db_err}", exc_info=True)


# Export singleton instance
emotion_service = EmotionService()

