"""
LangGraph agent graph – orchestrates the multi-agent pipeline.

Flow:
  START → router_agent
      → conditional fan-out to analysis agents
          (emotion, personality, context, memory)
      → recommendation_agent
      → response_agent
  → END
"""

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.router_agent import router_agent
from app.agents.emotion_agent import emotion_agent
from app.agents.personality_agent import personality_agent
from app.agents.context_agent import context_agent
from app.agents.memory_agent import memory_agent
from app.agents.recommendation_agent import recommendation_agent
from app.agents.response_agent import response_agent

logger = logging.getLogger(__name__)


# ── Pass-through nodes for skipped agents ─────────────────────

async def skip_emotion(state: AgentState) -> dict:
    """No-op when the emotion agent is skipped."""
    return {
        "emotion_analysis": {
            "primary_emotion": "neutral",
            "secondary_emotion": "none",
            "intensity": 0.2,
            "stress_level": 0.2,
            "burnout_risk": False,
            "mood_classification": "neutral",
        },
        "mood_score": 0.5,
        "detected_emotion": "neutral",
    }


async def skip_personality(state: AgentState) -> dict:
    """No-op when the personality agent is skipped."""
    return {
        "personality_analysis": {
            "overthinking_detected": False,
            "communication_pattern": "open-processor",
            "social_energy": "balanced",
            "personality_traits": [],
            "emotional_needs": [],
        }
    }


async def skip_context(state: AgentState) -> dict:
    """No-op when the context agent is skipped."""
    return {
        "context_analysis": {
            "emotional_triggers": [],
            "underlying_need": "general conversation",
            "what_user_needs": "listening",
            "contextual_insights": "Casual interaction — no deep context needed.",
        }
    }


async def skip_memory(state: AgentState) -> dict:
    """No-op when the memory agent is skipped."""
    return {"memories": []}


# ── Merge node (collects parallel outputs before recommendations) ──

async def merge_analyses(state: AgentState) -> dict:
    """
    Identity node used as a synchronization barrier after
    the parallel analysis fan-out.  Returns no new state.
    """
    return {}


# ── Conditional routing helpers ───────────────────────────────

def route_emotion(state: AgentState) -> str:
    """Decide whether to run or skip the emotion agent."""
    decision = state.get("router_decision", {})
    return "emotion_agent" if decision.get("activate_emotion", True) else "skip_emotion"


def route_personality(state: AgentState) -> str:
    decision = state.get("router_decision", {})
    return "personality_agent" if decision.get("activate_personality", True) else "skip_personality"


def route_context(state: AgentState) -> str:
    decision = state.get("router_decision", {})
    return "context_agent" if decision.get("activate_context", True) else "skip_context"


def route_memory(state: AgentState) -> str:
    decision = state.get("router_decision", {})
    return "memory_agent" if decision.get("activate_memory", True) else "skip_memory"


# ── Build the graph ──────────────────────────────────────────

def build_graph() -> StateGraph:
    """Construct and compile the Esona agent graph."""

    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("router_agent", router_agent)
    graph.add_node("emotion_agent", emotion_agent)
    graph.add_node("personality_agent", personality_agent)
    graph.add_node("context_agent", context_agent)
    graph.add_node("memory_agent", memory_agent)
    graph.add_node("skip_emotion", skip_emotion)
    graph.add_node("skip_personality", skip_personality)
    graph.add_node("skip_context", skip_context)
    graph.add_node("skip_memory", skip_memory)
    graph.add_node("merge_analyses", merge_analyses)
    graph.add_node("recommendation_agent", recommendation_agent)
    graph.add_node("response_agent", response_agent)

    # Entry point
    graph.set_entry_point("router_agent")

    # Router fans out in parallel to all analysis dimensions
    graph.add_conditional_edges(
        "router_agent",
        route_emotion,
        {"emotion_agent": "emotion_agent", "skip_emotion": "skip_emotion"},
    )
    graph.add_conditional_edges(
        "router_agent",
        route_personality,
        {"personality_agent": "personality_agent", "skip_personality": "skip_personality"},
    )
    graph.add_conditional_edges(
        "router_agent",
        route_context,
        {"context_agent": "context_agent", "skip_context": "skip_context"},
    )
    graph.add_conditional_edges(
        "router_agent",
        route_memory,
        {"memory_agent": "memory_agent", "skip_memory": "skip_memory"},
    )

    # All analysis paths converge at the merge_analyses synchronization barrier
    graph.add_edge("emotion_agent", "merge_analyses")
    graph.add_edge("skip_emotion", "merge_analyses")
    graph.add_edge("personality_agent", "merge_analyses")
    graph.add_edge("skip_personality", "merge_analyses")
    graph.add_edge("context_agent", "merge_analyses")
    graph.add_edge("skip_context", "merge_analyses")
    graph.add_edge("memory_agent", "merge_analyses")
    graph.add_edge("skip_memory", "merge_analyses")

    # Merge → recommendation → response → END
    graph.add_edge("merge_analyses", "recommendation_agent")
    graph.add_edge("recommendation_agent", "response_agent")
    graph.add_edge("response_agent", END)

    return graph


# Compile once at module level
_compiled_graph = build_graph().compile()


async def run_agent_graph(
    user_message: str,
    user_id: str,
    conversation_history: list[dict],
    emotional_profile: dict,
) -> dict:
    """
    Execute the full agent pipeline and return the final state.

    Parameters
    ----------
    user_message : str
        The current user message.
    user_id : str
        UUID string of the authenticated user.
    conversation_history : list[dict]
        Recent messages as ``[{"role": "user"|"assistant", "content": "..."}]``.
    emotional_profile : dict
        The user's emotional profile from the database.

    Returns
    -------
    dict
        The final AgentState with ``response``, ``detected_emotion``,
        ``mood_score``, and all intermediate analyses.
    """
    initial_state: AgentState = {
        "user_message": user_message,
        "user_id": user_id,
        "conversation_history": conversation_history,
        "emotional_profile": emotional_profile,
        "router_decision": {},
        "emotion_analysis": {},
        "personality_analysis": {},
        "context_analysis": {},
        "memories": [],
        "recommendations": [],
        "response": "",
        "mood_score": 0.5,
        "detected_emotion": "neutral",
    }

    try:
        result = await _compiled_graph.ainvoke(initial_state)
        return result
    except Exception as e:
        logger.error(f"Agent graph execution failed: {e}", exc_info=True)
        return {
            **initial_state,
            "response": (
                "Hey, I hit a bump trying to think that through. "
                "Can you say that again? I want to give you a proper response."
            ),
        }
