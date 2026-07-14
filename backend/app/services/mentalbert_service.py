"""
MentalBERT Service – handles text sequence classification using the local mental/mental-bert-base-uncased model
with a rule-based fallback simulator if the model is not loaded locally.
"""

import logging
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

# Try to import torch and transformers, but do not fail hard if not installed
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    HAS_TORCH_TRANSFORMERS = True
except ImportError:
    HAS_TORCH_TRANSFORMERS = False


# ── Emotion keyword dictionaries ────────────────────────────────────────────
# Phrase-level patterns (checked first, before single words)
EMOTION_PHRASES = {
    "frustration": [
        "lost all my money", "she ruined", "he ruined", "they ruined",
        "toxic relationship", "toxic person", "toxic girl", "toxic guy",
        "broke up", "break up", "broke my heart", "cheated on me",
        "she cheated", "he cheated", "wasted my time", "ruined everything",
        "sick of her", "sick of him", "sick of them", "done with her",
        "done with him", "i hate my", "i hate this", "so unfair",
        "makes me mad", "makes me angry", "makes me furious",
        "can't stand", "fed up", "driving me crazy", "annoying me",
        "pissing me off", "pissed off",
    ],
    "sadness": [
        "broke up with me", "she left me", "he left me", "they left me",
        "lost a friend", "lost my job", "lost everything", "miss her",
        "miss him", "miss them", "crying myself", "feel so empty",
        "feeling empty", "no one cares", "nobody cares", "feel hopeless",
        "feel worthless", "feel like nothing", "broken heart", "heartbroken",
        "grieving", "in grief", "in mourning", "lost someone",
    ],
    "stress": [
        "lost all my money", "financial issue", "finance issue", "money problems",
        "money problem", "can't pay", "can't afford", "can not afford",
        "debt problem", "struggling financially", "financial stress",
        "financial crisis", "running out of money", "no money left",
        "drowning in debt", "behind on bills", "behind on rent",
        "so much to do", "too much work", "overwhelmed with", "burned out",
        "burnt out", "can't keep up", "falling behind", "deadline pressure",
    ],
    "anxiety": [
        "panic attack", "having a panic", "can't breathe", "heart is racing",
        "overthinking everything", "what if everything", "scared of the future",
        "terrified of", "dread the", "worst case scenario",
    ],
    "loneliness": [
        "feel so alone", "completely alone", "all alone", "no one to talk to",
        "nobody to talk to", "nobody understands me", "no one understands me",
        "isolated from", "cut off from", "left out of", "left me out",
        "no friends left", "have no friends",
    ],
}

# Single-word/token patterns (checked after phrase matching)
EMOTION_KEYWORDS = {
    "frustration": [
        # Strong anger words
        "bloody", "damn", "damm", "fuck", "shit", "crap", "toxic", "hate",
        "furious", "livid", "enraged", "outraged", "disgusted", "disgusting",
        "infuriated", "irritated", "irritating", "annoyed", "annoying",
        "frustrated", "frustrating", "mad", "angry", "rage", "hatred",
        "betrayed", "betrayal", "backstabbed", "disrespected",
        "cheated", "lied", "deceived", "manipulated", "manipulative",
        "abusive", "abuse", "controlling", "manipulator", "narcissist",
        # Relationship-conflict words
        "ruined", "destroyed", "wrecked",
    ],
    "sadness": [
        "sad", "sadness", "cry", "crying", "cried", "tears", "weeping",
        "depressed", "depression", "hurt", "pain", "painful", "grief",
        "grieving", "gloomy", "miserable", "misery", "heartbreak",
        "heartbroken", "devastated", "devastation", "shattered",
        "hopeless", "hopelessness", "worthless", "useless", "failure",
        "down", "low", "unhappy", "upset", "disappointed", "disappointment",
        "broken", "empty", "numb", "lost", "alone", "abandoned",
        "rejected", "rejection", "unloved", "unwanted", "insignificant",
        "suffering", "suffer", "suffered", "aching", "aches",
    ],
    "stress": [
        "stress", "stressed", "stressful", "overwhelmed", "overwhelm",
        "exhausted", "exhaustion", "burnout", "burned", "burnt",
        "tired", "fatigue", "drained", "depleted", "overloaded",
        "deadline", "pressure", "behind", "falling", "struggling",
        "swamped", "buried", "suffocating",
        # Financial stress keywords
        "suffering", "finance", "financial", "money", "broke", "debt",
        "loan", "bills", "salary", "income", "afford", "afford",
        "bankruptcy", "bankrupt", "poverty", "poor", "unpaid",
        "eviction", "evicted", "homeless", "starving",
    ],
    "anxiety": [
        "anxious", "anxiety", "worry", "worried", "worrying",
        "panic", "panicking", "scared", "terrified", "terrifying",
        "frightened", "frightening", "fear", "fearful", "afraid",
        "dread", "dreading", "uneasy", "unease", "nervous", "nervousness",
        "overthink", "overthinking", "overthought", "intrusive",
        "catastrophizing", "worst", "dreaded",
    ],
    "loneliness": [
        "lonely", "loneliness", "alone", "isolated", "isolation",
        "abandoned", "excluded", "left out", "invisible", "forgotten",
        "disconnected", "disconnection", "no one", "nobody", "friendless",
        "unwanted", "ostracized",
    ],
    "happy": [
        "happy", "happiness", "joy", "joyful", "excited", "excitement",
        "glad", "cheerful", "delighted", "thrilled", "ecstatic", "elated",
        "pleased", "grateful", "thankful", "blessed", "wonderful",
        "amazing", "great", "fantastic", "excellent", "good", "positive",
        "smile", "smiling", "laugh", "laughing", "love", "loved",
        "enjoying", "enjoy", "fun", "awesome", "brilliant",
    ],
}

# Topic/context detection keywords
TOPIC_KEYWORDS = {
    "relationship": [
        "gf", "girlfriend", "bf", "boyfriend", "partner", "spouse",
        "wife", "husband", "ex", "dating", "relationship", "marriage",
        "married", "engaged", "breakup", "divorce", "cheating",
    ],
    "financial": [
        "money", "finance", "financial", "debt", "loan", "salary",
        "income", "bills", "rent", "mortgage", "broke", "bankrupt",
        "afford", "poverty", "job", "career", "unemployed",
    ],
    "academic": [
        "exam", "test", "assignment", "homework", "study", "studying",
        "grade", "college", "university", "school", "class", "professor",
        "teacher", "deadline", "project",
    ],
    "health": [
        "sick", "ill", "illness", "disease", "hospital", "doctor",
        "medicine", "pain", "surgery", "diagnosis", "treatment",
        "symptoms", "fever", "injury",
    ],
    "work": [
        "work", "job", "boss", "manager", "colleague", "office",
        "workplace", "fired", "promotion", "career", "project",
        "meeting", "deadline", "workload",
    ],
}


def _score_text(text_lower: str) -> dict:
    """
    Score text against emotion keyword dictionaries.
    Returns a dict of {emotion: score} where score > 0 means the emotion was detected.
    Multi-word phrases are weighted higher than single-word matches.
    """
    raw_scores = {
        "happy": 0.0,
        "neutral": 0.0,
        "stress": 0.0,
        "anxiety": 0.0,
        "sadness": 0.0,
        "frustration": 0.0,
        "loneliness": 0.0,
    }

    # Phase 1: Phrase matching (weight 0.6 per phrase hit)
    for emotion, phrases in EMOTION_PHRASES.items():
        for phrase in phrases:
            if phrase in text_lower:
                raw_scores[emotion] += 0.6

    # Phase 2: Single keyword matching (weight 0.15 per word hit)
    words_in_text = set(text_lower.split())
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if " " not in kw:
                # single token
                if kw in words_in_text or kw in text_lower:
                    raw_scores[emotion] += 0.15
            else:
                # short phrase in keyword list
                if kw in text_lower:
                    raw_scores[emotion] += 0.3

    return raw_scores


class MentalBERTService:
    def __init__(self):
        self.classifier = None
        self.initialized = False
        
    def _initialize_model(self):
        if self.initialized:
            return
        # Load local model only if torch/transformers are installed and enabled
        if HAS_TORCH_TRANSFORMERS and settings.USE_LOCAL_EMOTION_MODEL:
            try:
                logger.info(f"Initializing local MentalBERT pipeline with model: {settings.EMOTION_MODEL_NAME}...")
                from transformers import pipeline
                self.classifier = pipeline(
                    "text-classification",
                    model=settings.EMOTION_MODEL_NAME,
                    return_all_scores=True,
                    device=-1  # CPU by default
                )
                self.initialized = True
                logger.info("Local MentalBERT pipeline loaded successfully.")
                logger.info(f"Model Name: {settings.EMOTION_MODEL_NAME}")
                logger.info(f"Device: {self.classifier.model.device}")
                logger.info(f"Labels mapping (id2label): {self.classifier.model.config.id2label}")
            except Exception as e:
                logger.warning(f"Could not load local MentalBERT pipeline: {e}. Fallback to API simulation will be used.")
                self.initialized = True
        else:
            self.initialized = True

    def predict(self, text: str) -> Any:
        """
        Predict emotion scores for the input text using local MentalBERT model,
        or simulate it using an LLM / rule-based fallback if the local model is not loaded.
        Returns a PyTorch tensor (or list representing the predictions).
        """
        if not self.initialized:
            self._initialize_model()

        if not text or len(text.strip()) == 0:
            mock_probs = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            if HAS_TORCH_TRANSFORMERS:
                import torch
                return torch.tensor([mock_probs])
            return mock_probs

        logger.info(f"TEXT SENT TO MENTALBERT: '{text}'")

        # If local model is initialized, run local transformers pipeline inference
        if self.initialized and self.classifier:
            try:
                results = self.classifier(text)
                logger.info(f"Raw Model Predictions: {results}")
                
                # Map typical 6-class models (sadness, joy, love, anger, fear, surprise) or index-based labels
                # to our 7 wellness categories:
                # 0: happy, 1: neutral, 2: stress, 3: anxiety, 4: sadness, 5: frustration, 6: loneliness
                scores = [0.0] * 7
                raw_dict = {}
                for item in results[0]:
                    label = item["label"].lower().strip()
                    score = float(item["score"])
                    
                    # Handle LABEL_0 style outputs
                    if label.startswith("label_"):
                        idx_str = label.replace("label_", "")
                        if idx_str.isdigit():
                            idx = int(idx_str)
                            # bhadresh-savani indices mapping: 
                            # 0: sadness, 1: joy, 2: love, 3: anger, 4: fear, 5: surprise
                            bhadresh_map = {0: "sadness", 1: "joy", 2: "love", 3: "anger", 4: "fear", 5: "surprise"}
                            label = bhadresh_map.get(idx, label)
                    
                    raw_dict[label] = score

                joy_score = raw_dict.get("joy", 0.0) + raw_dict.get("love", 0.0)
                sadness_score = raw_dict.get("sadness", 0.0)
                anger_score = raw_dict.get("anger", 0.0)
                fear_score = raw_dict.get("fear", 0.0)
                surprise_score = raw_dict.get("surprise", 0.0)
                
                scores[0] = joy_score                       # happy
                scores[1] = max(0.1, surprise_score)         # neutral
                scores[2] = fear_score * 0.6                 # stress
                scores[3] = fear_score                       # anxiety
                scores[4] = sadness_score                    # sadness
                scores[5] = anger_score                      # frustration
                scores[6] = sadness_score * 0.6              # loneliness
                
                # Normalize scores
                total = sum(scores)
                if total > 0:
                    scores = [s / total for s in scores]
                
                logger.info(f"Mapped Wellness Scores: {scores}")
                
                if HAS_TORCH_TRANSFORMERS:
                    import torch
                    return torch.tensor([scores])
                return scores
            except Exception as local_err:
                logger.error(f"Error during local MentalBERT prediction: {local_err}. Using rule-based fallback.")

        # ── Rule-based fallback (expanded keyword system) ──────────────────
        text_lower = text.lower()
        
        # Check crisis override keywords first
        crisis_keywords = [
            "suicide", "self-harm", "kill myself", "want to die", "end my life", 
            "end it all", "hurting myself", "hurt myself", "painful to exist", 
            "sleep forever", "no point in living", "planning to end it", 
            "want to sleep and never wake up", "don't want to exist", "live anymore"
        ]
        if any(keyword in text_lower for keyword in crisis_keywords):
            # 0: happy, 1: neutral, 2: stress, 3: anxiety, 4: sadness, 5: frustration, 6: loneliness
            scores = [0.0, 0.05, 0.15, 0.0, 0.75, 0.0, 0.05]
        else:
            # Run the expanded keyword scoring system
            raw = _score_text(text_lower)
            
            # Map named emotions to index positions
            # 0: happy, 1: neutral, 2: stress, 3: anxiety, 4: sadness, 5: frustration, 6: loneliness
            scores = [
                raw["happy"],
                0.0,             # neutral starts at 0 — must earn its score
                raw["stress"],
                raw["anxiety"],
                raw["sadness"],
                raw["frustration"],
                raw["loneliness"],
            ]
            
            total_emotion_score = sum(scores)
            
            if total_emotion_score < 0.05:
                # Truly no emotion detected — safe to return neutral
                scores[1] = 1.0
            else:
                # Some emotion was detected — give neutral a small base to allow normalization
                scores[1] = 0.02

        # Normalize scores to sum to 1.0
        total = sum(scores)
        if total > 0:
            scores = [s / total for s in scores]

        logger.info(f"[Rule-Based Fallback] Scores: {dict(zip(['happy','neutral','stress','anxiety','sadness','frustration','loneliness'], [round(s,3) for s in scores]))}")

        if HAS_TORCH_TRANSFORMERS:
            import torch
            return torch.tensor([scores])
        else:
            return scores


# Export singleton instance
mentalbert_service = MentalBERTService()
