"""
Growth Agent - parses and analyzes user's growth, awareness, and motivation.
"""

from typing import Dict, Any

class GrowthAgent:
    """
    Logical agent responsible for analyzing:
    - Emotional improvement
    - Motivation
    - Self-awareness
    - Mental growth
    """

    def analyze(self, raw_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract growth insights from the single structured Gemini analysis.
        """
        data = raw_analysis.get("growth_agent", {})

        # Fallback values if missing
        return {
            "emotional_improvement": data.get("emotional_improvement", "stable"),
            "motivation": data.get("motivation", "moderate"),
            "self_awareness": data.get("self_awareness", "moderate"),
            "mental_growth": data.get("mental_growth", "none detected")
        }

growth_agent = GrowthAgent()
