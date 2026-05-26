"""
Emotion Agent - parses and analyzes user's current emotional state.
"""

from typing import Dict, Any

class EmotionAgent:
    """
    Logical agent responsible for analyzing:
    - Stress
    - Anxiety
    - Sadness
    - Burnout
    - Emotional intensity
    - Primary/dominant emotion
    """

    def analyze(self, raw_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract emotional insights from the single structured Gemini analysis.
        """
        data = raw_analysis.get("emotion_agent", {})

        # Fallback values if missing
        return {
            "primary_emotion": data.get("primary_emotion", "neutral"),
            "stress": float(data.get("stress", 0.3)),
            "anxiety": float(data.get("anxiety", 0.3)),
            "sadness": float(data.get("sadness", 0.3)),
            "burnout": float(data.get("burnout", 0.3)),
            "emotional_intensity": int(data.get("emotional_intensity", 5))
        }

emotion_agent = EmotionAgent()
