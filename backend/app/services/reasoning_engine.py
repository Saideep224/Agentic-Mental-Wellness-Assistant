"""
Conversation Reasoning Engine - tracks conversation stages, determines strategies,
and manages the state machine transitions for Esona V3.
"""

import logging
from typing import Dict, Any, List
from app.models.conversation import MessageRole

logger = logging.getLogger(__name__)

STAGES = ["Greeting", "Listening", "Exploring", "Understanding", "Helping", "Reflection", "Closure"]

STRATEGIES = [
    "Comfort", "Explore", "Clarify", "Encourage", "Celebrate", 
    "Ground", "Reframe", "Reflect", "Problem Solve", "Listen Only", "Crisis Support"
]

class ConversationReasoningEngine:
    """Tracks state transitions and performs emotional reasoning alignment."""

    def get_previous_stage(self, history: List[Dict[str, Any]]) -> str:
        """Scan chat history to find the last assistant message stage."""
        if not history:
            return "Greeting"
            
        for msg in reversed(history):
            role = msg.get("role")
            if role in (MessageRole.assistant, "assistant"):
                analysis = msg.get("agent_analysis") or {}
                if isinstance(analysis, dict) and "conversation_stage" in analysis:
                    stage = analysis["conversation_stage"]
                    if stage in STAGES:
                        return stage
        return "Greeting"

    def transition_stage(self, prev_stage: str, user_message: str, history: List[Dict[str, Any]], primary_emotion: str) -> str:
        """Determines the next conversation stage based on state machine transition rules."""
        msg_lower = user_message.lower().strip()
        word_count = len(msg_lower.split())

        # Reset rules: If the user says hello again or introduces a new topic after closure
        if prev_stage in ("Reflection", "Closure") and any(w in msg_lower for w in ["hey", "hello", "hi", "btw", "also", "guess what"]):
            return "Listening"

        # 1. Greeting
        if prev_stage == "Greeting":
            if word_count <= 3 and any(w in msg_lower for w in ["hi", "hey", "hello", "yo", "sup", "morning"]):
                return "Greeting"
            return "Listening"

        # 2. Listening
        elif prev_stage == "Listening":
            # If user shares emotional words or details, move to Exploring
            if primary_emotion.capitalize() not in ("Neutral", "Happy") or word_count > 5:
                return "Exploring"
            return "Listening"

        # 3. Exploring
        elif prev_stage == "Exploring":
            # If we've asked/explored for a couple of turns, move to Understanding
            user_turns = sum(1 for m in history if m.get("role") == "user")
            if user_turns >= 3:
                return "Understanding"
            return "Exploring"

        # 4. Understanding
        elif prev_stage == "Understanding":
            # Once we validate them, move to Helping (solutions/reframing)
            return "Helping"

        # 5. Helping
        elif prev_stage == "Helping":
            # After brainstorming, check reflection
            return "Reflection"

        # 6. Reflection
        elif prev_stage == "Reflection":
            return "Closure"

        # 7. Closure
        elif prev_stage == "Closure":
            if any(w in msg_lower for w in ["thanks", "thank you", "bye", "goodnight", "ok"]):
                return "Closure"
            return "Listening"

        return "Listening"

    def select_strategy_for_stage(self, stage: str, primary_emotion: str, risk_level: str) -> str:
        """Returns the best conversational strategy aligned with the current stage."""
        if risk_level == "crisis":
            return "Crisis Support"

        stage_strategies = {
            "Greeting": "Comfort",
            "Listening": "Listen Only",
            "Exploring": "Explore",
            "Understanding": "Reflect",
            "Helping": "Reframe" if primary_emotion.capitalize() in ("Stress", "Anxiety", "Frustration") else "Problem Solve",
            "Reflection": "Encourage",
            "Closure": "Comfort"
        }

        # Override based on emotion
        if stage == "Helping" and primary_emotion.capitalize() == "Happy":
            return "Celebrate"
        if stage == "Exploring" and primary_emotion.capitalize() == "Anxiety":
            return "Ground"

        return stage_strategies.get(stage, "Comfort")

reasoning_engine = ConversationReasoningEngine()
