"""
Agent state schema — TypedDict used by the LangGraph StateGraph.

Defines the full state that flows through the multi-agent pipeline:
cognitive_analyzer_agent → memory_agent → response_agent.
"""

from typing import TypedDict
from sqlalchemy.ext.asyncio import AsyncSession


class AgentState(TypedDict, total=False):
    """
    Full state schema for the Esona multi-agent graph.
    """
    db: AsyncSession
    conversation_id: str
    user_message: str
    user_id: str
    conversation_history: list[dict]
    emotional_profile: dict
    router_decision: dict
    emotion_analysis: dict
    emotion_dimensions: dict
    personality_analysis: dict
    context_analysis: dict
    memories: list[dict]
    graph_relationships: list[str]
    emotional_patterns: dict
    recommendations: list[str]
    response: str
    mood_score: float
    detected_emotion: str
    detected_emotion_confidence: float

    # Multi-Agent keys
    personality_agent: dict
    emotion_agent: dict
    behavior_agent: dict
    growth_agent: dict
    intent_agent: dict
    safety_agent: dict
    memory_extraction: dict
    response_strategy: dict
    orchestrated_prompt_summary: str
    agent_analysis: dict
