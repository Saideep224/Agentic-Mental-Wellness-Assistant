"""
Intent Agent - parses the user's intent, goals, and messaging category.
"""

from typing import Dict, Any

class IntentAgent:
    """
    Logical agent responsible for analyzing:
    - Message Type (casual, emotional, crisis, check_in)
    - Inferred cause
    - Underlying needs
    - Support requested (validation, advice, distraction, listening, encouragement)
    """

    def analyze(self, raw_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract intent details from the single structured Gemini analysis.
        """
        context = raw_analysis.get("context_analysis", {})
        
        return {
            "message_type": raw_analysis.get("message_type", "emotional"),
            "underlying_need": context.get("underlying_need", "to be heard and understood"),
            "what_user_needs": context.get("what_user_needs", "listening"),
            "emotional_triggers": context.get("emotional_triggers", []),
            "inferred_causes": context.get("inferred_causes", [])
        }

intent_agent = IntentAgent()
