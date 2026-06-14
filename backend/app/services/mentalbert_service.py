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
        self.tokenizer = None
        self.model = None
        self.initialized = False
        
        # Load local model only if torch/transformers are installed and enabled
        if HAS_TORCH_TRANSFORMERS and settings.USE_LOCAL_EMOTION_MODEL:
            try:
                logger.info("Initializing local MentalBERT model...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    "mental/mental-bert-base-uncased"
                )
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    "mental/mental-bert-base-uncased",
                    num_labels=7  # For our 7 emotion classes
                )
                self.initialized = True
                logger.info("Local MentalBERT model loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load local MentalBERT model: {e}. Fallback to API simulation will be used.")

    def predict(self, text: str) -> Any:
        """
        Predict emotion scores for the input text using local MentalBERT model,
        or simulate it using an LLM / rule-based fallback if the local model is not loaded.
        Returns a PyTorch tensor (or list/dict representing the predictions).
        """
        if not text or len(text.strip()) == 0:
            mock_probs = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            if HAS_TORCH_TRANSFORMERS:
                import torch
                return torch.tensor([mock_probs])
            return mock_probs

        # If local model is initialized, run local PyTorch inference
        if self.initialized and self.model and self.tokenizer:
            try:
                inputs = self.tokenizer(
                    text,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512
                )
                with torch.no_grad():
                    outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1)
                return probs
            except Exception as local_err:
                logger.error(f"Error during local MentalBERT prediction: {local_err}. Using API simulation fallback.")

        # Fallback: rule-based simulation to get accurate scores
        text_lower = text.lower()
        
        # Check crisis override keywords
        crisis_keywords = ["want to die", "kill myself", "end my life", "suicide"]
        if any(keyword in text_lower for keyword in crisis_keywords):
            # 0: happy, 1: neutral, 2: stress, 3: anxiety, 4: sadness, 5: frustration, 6: loneliness
            scores = [0.0, 0.05, 0.15, 0.0, 0.75, 0.0, 0.05]
        # Mapping: 0: happy, 1: neutral, 2: stress, 3: anxiety, 4: sadness, 5: frustration, 6: loneliness
        else:
            scores = [0.1, 0.3, 0.2, 0.2, 0.2, 0.2, 0.2]
            
            if any(w in text_lower for w in ["happy", "good", "great", "smile", "excited", "glad", "relief"]):
                scores = [0.8, 0.1, 0.05, 0.05, 0.0, 0.0, 0.0]
            elif any(w in text_lower for w in ["anxious", "anxiety", "worry", "worried", "panic", "scared"]):
                scores = [0.0, 0.1, 0.3, 0.8, 0.2, 0.1, 0.1]
            elif any(w in text_lower for w in ["stress", "stressed", "overwhelm", "exhausted", "burnout", "tired"]):
                scores = [0.0, 0.1, 0.8, 0.3, 0.2, 0.1, 0.1]
            elif any(w in text_lower for w in ["sad", "sadness", "cry", "hurt", "pain", "down", "unhappy", "depressed", "depression"]):
                scores = [0.0, 0.1, 0.2, 0.2, 0.8, 0.1, 0.2]
            elif any(w in text_lower for w in ["lonely", "loneliness", "alone", "isolated"]):
                scores = [0.0, 0.1, 0.1, 0.2, 0.3, 0.1, 0.8]
            elif any(w in text_lower for w in ["angry", "frustrated", "annoyed", "mad", "hate"]):
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
