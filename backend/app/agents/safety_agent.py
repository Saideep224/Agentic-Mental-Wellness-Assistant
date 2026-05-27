"""
Safety Agent - checks message content and emotional tags for self-harm or crisis patterns.
"""

from typing import Dict, Any

class SafetyAgent:
    """
    Logical agent responsible for:
    - Scanning user inputs for crisis keywords
    - Checking if message_type is flagged as crisis
    - Recommending activation of safe crisis response protocol
    """

    def check_safety(self, raw_analysis: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """
        Scan and evaluate if user message represents an active crisis.
        """
        message_type = raw_analysis.get("message_type", "")
        emotion_data = raw_analysis.get("emotion_agent", {})
        primary_emotion = emotion_data.get("primary_emotion", "")
        
        # Keyword triggers
        crisis_words = ["suicide", "self-harm", "kill myself", "want to die", "end my life", "end it all"]
        msg_lower = user_message.lower()
        has_crisis_word = any(word in msg_lower for word in crisis_words)

        is_crisis = (
            message_type == "crisis"
            or primary_emotion == "crisis"
            or has_crisis_word
        )

        return {
            "is_safe": not is_crisis,
            "crisis_detected": is_crisis,
            "safety_action": "crisis_protocol" if is_crisis else "none"
        }

safety_agent = SafetyAgent()
