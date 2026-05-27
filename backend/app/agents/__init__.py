"""
Multi-agent system for emotionally adaptive responses.

Agents are data extractors that parse the single cognitive analysis JSON.
The actual LLM pipeline lives in app.chatbot.pipeline.
"""

from app.agents.personality_agent import personality_agent
from app.agents.emotion_agent import emotion_agent
from app.agents.behavior_agent import behavior_agent
from app.agents.growth_agent import growth_agent

__all__ = [
    "personality_agent",
    "emotion_agent",
    "behavior_agent",
    "growth_agent",
]
