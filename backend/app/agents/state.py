"""
Shared typed state for the LangGraph agent pipeline.

Every agent function reads from and writes to subsets of this state.
LangGraph merges partial updates automatically.
"""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """
    Full state schema for the Esona multi-agent graph.

    Fields marked with ``total=False`` are optional – agents only
    return the keys they care about.
    """

    # ── Inputs (set once at the start) ───────────────────────
    user_message: str
    user_id: str
    conversation_history: list[dict]
    emotional_profile: dict

    # ── Router output ────────────────────────────────────────
    router_decision: dict
    # Expected shape:
    # {
    #   "activate_emotion": bool,
    #   "activate_personality": bool,
    #   "activate_context": bool,
    #   "activate_memory": bool,
    #   "message_type": "emotional" | "casual" | "crisis" | "check_in",
    # }

    # ── Analysis agent outputs ───────────────────────────────
    emotion_analysis: dict
    # {
    #   "primary_emotion": str,
    #   "secondary_emotion": str,
    #   "intensity": float (0-1),
    #   "stress_level": float (0-1),
    #   "burnout_risk": bool,
    #   "mood_classification": str,
    # }

    personality_analysis: dict
    # {
    #   "overthinking_detected": bool,
    #   "communication_pattern": str,
    #   "social_energy": str,
    #   "personality_traits": list[str],
    #   "emotional_needs": list[str],
    # }

    context_analysis: dict
    # {
    #   "emotional_triggers": list[str],
    #   "underlying_need": str,
    #   "what_user_needs": "validation"|"advice"|"distraction"|"listening"|"encouragement",
    #   "contextual_insights": str,
    # }

    memories: list[dict]
    emotional_patterns: dict
    recommendations: list[str]

    # ── Final outputs ────────────────────────────────────────
    response: str
    mood_score: float
    detected_emotion: str
