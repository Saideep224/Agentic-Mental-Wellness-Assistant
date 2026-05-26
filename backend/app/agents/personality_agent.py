"""
Personality Agent - parses and analyzes user's personality traits.
"""

from typing import Dict, Any

class PersonalityAgent:
    """
    Logical agent responsible for analyzing:
    - Confidence level
    - Communication style
    - Emotional openness
    - Introvert/extrovert tendencies
    """
    
    def analyze(self, raw_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract personality insights from the single structured Gemini analysis.
        """
        data = raw_analysis.get("personality_agent", {})
        
        # Fallback values if missing
        return {
            "confidence_level": data.get("confidence_level", "moderate"),
            "communication_style": data.get("communication_style", "casual"),
            "emotional_openness": data.get("emotional_openness", "neutral"),
            "introvert_extrovert_tendencies": data.get("introvert_extrovert_tendencies", "ambivert")
        }

personality_agent = PersonalityAgent()
