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


class MentalBERTService:
    def __init__(self):
        self.classifier = None
        self.initialized = False
        
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

    def predict(self, text: str) -> Any:
        """
        Predict emotion scores for the input text using local MentalBERT model,
        or simulate it using an LLM / rule-based fallback if the local model is not loaded.
        Returns a PyTorch tensor (or list representing the predictions).
        """
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
                logger.error(f"Error during local MentalBERT prediction: {local_err}. Using API simulation fallback.")

        # Fallback: rule-based simulation to get accurate scores
        text_lower = text.lower()
        
        # Check crisis override keywords
        crisis_keywords = [
            "suicide", "self-harm", "kill myself", "want to die", "end my life", 
            "end it all", "hurting myself", "hurt myself", "painful to exist", 
            "sleep forever", "no point in living", "planning to end it", 
            "want to sleep and never wake up", "don't want to exist", "live anymore"
        ]
        if any(keyword in text_lower for keyword in crisis_keywords):
            # 0: happy, 1: neutral, 2: stress, 3: anxiety, 4: sadness, 5: frustration, 6: loneliness
            scores = [0.0, 0.05, 0.15, 0.0, 0.75, 0.0, 0.05]
        # Mapping: 0: happy, 1: neutral, 2: stress, 3: anxiety, 4: sadness, 5: frustration, 6: loneliness
        else:
            scores = [0.1, 0.3, 0.2, 0.2, 0.2, 0.2, 0.2]
            
            if any(w in text_lower for w in ["happy", "good", "great", "smile", "excited", "glad", "relief", "joy", "cheerful"]):
                scores = [0.8, 0.1, 0.05, 0.05, 0.0, 0.0, 0.0]
            elif any(w in text_lower for w in ["anxious", "anxiety", "worry", "worried", "panic", "scared", "terrified", "frightened", "fear", "afraid"]):
                scores = [0.0, 0.1, 0.3, 0.8, 0.2, 0.1, 0.1]
            elif any(w in text_lower for w in ["stress", "stressed", "overwhelm", "exhausted", "burnout", "tired", "busy", "pressure"]):
                scores = [0.0, 0.1, 0.8, 0.3, 0.2, 0.1, 0.1]
            elif any(w in text_lower for w in ["sad", "sadness", "cry", "hurt", "pain", "down", "unhappy", "depressed", "depression", "grief", "gloomy"]):
                scores = [0.0, 0.1, 0.2, 0.2, 0.8, 0.1, 0.2]
            elif any(w in text_lower for w in ["lonely", "loneliness", "alone", "isolated", "isolation", "abandoned"]):
                scores = [0.0, 0.1, 0.1, 0.2, 0.3, 0.1, 0.8]
            elif any(w in text_lower for w in ["angry", "frustrated", "annoyed", "mad", "hate", "furious", "irritated", "rage", "pissed"]):
                scores = [0.0, 0.1, 0.2, 0.1, 0.1, 0.8, 0.1]

        # Normalize scores to sum to 1.0
        total = sum(scores)
        if total > 0:
            scores = [s / total for s in scores]

        if HAS_TORCH_TRANSFORMERS:
            import torch
            return torch.tensor([scores])
        else:
            return scores


# Export singleton instance
mentalbert_service = MentalBERTService()
