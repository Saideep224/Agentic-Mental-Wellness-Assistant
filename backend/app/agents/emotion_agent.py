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

    def analyze(self, raw_analysis: Any) -> Dict[str, Any]:
        """
        Extract emotional insights from the single structured Gemini analysis,
        or from the raw MentalBERT probability tensor/list.
        """
        probs_list = []
        try:
            import torch
            if torch.is_tensor(raw_analysis):
                probs_list = raw_analysis.tolist()[0]
        except Exception:
            pass

        if not probs_list:
            if isinstance(raw_analysis, list):
                probs_list = raw_analysis
            elif isinstance(raw_analysis, dict) and "emotion_agent" in raw_analysis:
                data = raw_analysis.get("emotion_agent", {})
                return {
                    "primary_emotion": data.get("primary_emotion", "neutral"),
                    "stress": float(data.get("stress", 0.3)),
                    "anxiety": float(data.get("anxiety", 0.3)),
                    "sadness": float(data.get("sadness", 0.3)),
                    "burnout": float(data.get("burnout", 0.3)),
                    "emotional_intensity": int(data.get("emotional_intensity", 5))
                }
            else:
                probs_list = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        # Support both 7-emotion legacy lists and 9-emotion hybrid lists
        if len(probs_list) == 9:
            emotions = ["sadness", "anger", "fear", "anxiety", "happy", "excitement", "frustration", "loneliness", "neutral"]
            max_idx = probs_list.index(max(probs_list))
            primary = emotions[max_idx]
            
            stress = float(probs_list[emotions.index("frustration")]) # Map frustration to stress
            anxiety = float(probs_list[emotions.index("anxiety")])
            sadness = float(probs_list[emotions.index("sadness")])
            burnout = float((stress + sadness) / 2.0)
        else:
            # Map list: 0: happy, 1: neutral, 2: stress, 3: anxiety, 4: sadness, 5: frustration, 6: loneliness
            while len(probs_list) < 7:
                probs_list.append(0.0)

            emotions = ["happy", "neutral", "stress", "anxiety", "sadness", "frustration", "loneliness"]
            max_idx = probs_list.index(max(probs_list))
            primary = emotions[max_idx]
            
            stress = float(probs_list[2])
            anxiety = float(probs_list[3])
            sadness = float(probs_list[4])
            burnout = float((stress + sadness) / 2.0)
        
        return {
            "primary_emotion": primary,
            "stress": round(stress, 2),
            "anxiety": round(anxiety, 2),
            "sadness": round(sadness, 2),
            "burnout": round(burnout, 2),
            "emotional_intensity": int(max(1, min(10, int(max(probs_list) * 10))))
        }

emotion_agent = EmotionAgent()
