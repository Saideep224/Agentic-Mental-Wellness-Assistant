"""
LangGraph agent graph – orchestrates the optimized multi-agent pipeline.
Consolidated to use a single Cognitive Analyzer LLM call to prevent 429 rate limits,
and structured with advanced personalization rules.
"""

import json
import logging
import time
from datetime import datetime
from typing import Literal, TypedDict
from zoneinfo import ZoneInfo

from langgraph.graph import StateGraph, END
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_maker
from app.memory.memory_manager import MemoryManager

# Import logical agents and orchestrator
from app.agents.personality_agent import personality_agent
from app.agents.emotion_agent import emotion_agent
from app.agents.behavior_agent import behavior_agent
from app.agents.growth_agent import growth_agent
from app.orchestrator.response_orchestrator import response_orchestrator

logger = logging.getLogger(__name__)

# ── Shared AsyncOpenAI Client ─────────────────────────────────
client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


# ── Typed State ──────────────────────────────────────────────
class AgentState(TypedDict, total=False):
    """
    Full state schema for the Esona multi-agent graph.
    """
    db: AsyncSession
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
    emotional_patterns: dict
    recommendations: list[str]
    response: str
    mood_score: float
    detected_emotion: str

    # New Multi-Agent keys
    personality_agent: dict
    emotion_agent: dict
    behavior_agent: dict
    growth_agent: dict
    memory_extraction: dict
    response_strategy: dict
    orchestrated_prompt_summary: str
    agent_analysis: dict


# ── 1. Structured Multi-Agent Analyzer System Prompt ──────────
MULTI_AGENT_ANALYZER_SYSTEM_PROMPT = """You are the Multi-Agent Cognitive Analysis System for Esona, a mental wellness companion.
Your job is to analyze the user's message and recent conversation history, and produce a structured, deep emotional, behavioral, and growth analysis.

Analyze for the following categories using the four logical agents:
1. PERSONALITY AGENT:
   - confidence_level: high, moderate, low, fluctuating (with brief explanation)
   - communication_style: Intellectualizer, Catastrophizer, Open-processor, Minimizer, Avoider, etc.
   - emotional_openness: open, guarded, avoidant, vulnerable (with brief explanation)
   - introvert_extrovert_tendencies: introvert, extrovert, ambivert (with brief explanation)
2. EMOTION AGENT:
   - primary_emotion: anxiety, sadness, burnout, calm, happy, neutral, loneliness, overthinking, emotional numbness, emotional overwhelm, crisis
   - stress: float between 0.0 (lowest) and 1.0 (highest)
   - anxiety: float between 0.0 (lowest) and 1.0 (highest)
   - sadness: float between 0.0 (lowest) and 1.0 (highest)
   - burnout: float between 0.0 (lowest) and 1.0 (highest)
   - emotional_intensity: integer between 1 and 10
3. BEHAVIOR AGENT:
   - productivity_patterns: productivity indicators, task focus issues, procrastination
   - sleep_issues: sleep disruption, insomnia, late-night sleep, regular sleep
   - procrastination: high, medium, low, none
   - routine_consistency: consistent, erratic, forming habits, none
4. GROWTH AGENT:
   - emotional_improvement: progress indicators, static, regressing emotional trends
   - motivation: high, moderate, low, lacking (intrinsic or extrinsic)
   - self_awareness: high, moderate, low, developing (with brief explanation)
   - mental_growth: trigger identification, reframing, coping skills, none
5. MESSAGE TYPE & ROUTING:
   - Decide if the message is "emotional", "casual", "crisis", or "check_in".
6. SITUATIONAL CONTEXT:
   - emotional_triggers: list of identified triggers (e.g. exams, conflicts, work)
   - inferred_causes: list of potential root causes
   - underlying_need: the deeper, unspoken need behind their words (one sentence)
   - what_user_needs: validation, advice, distraction, listening, encouragement
7. COPING RECOMMENDATIONS:
   - 1 to 3 personalized, highly actionable coping suggestions ONLY if they would be helpful (e.g., for emotional/crisis/check_in states). Keep them specific. Avoid generic platitudes.
8. MEMORY EXTRACTION:
   - We only save memories that represent:
     - Personality traits or preferences (e.g. studies better at night, prefers supportive tone)
     - Emotional state, triggers, or stressors (e.g. gets anxious before exams, lonely on weekends)
     - Burnout indicators or routine patterns.
   - Set "is_meaningful" to false and summary/patterns to null for casual greetings, small talk, filler messages.
   - Set "is_meaningful" to true, provide a concise summary, and behavior patterns for meaningful insights.

Respond with ONLY a valid JSON object matching this schema:
{
  "message_type": "emotional" | "casual" | "crisis" | "check_in",
  "personality_agent": {
    "confidence_level": "string",
    "communication_style": "string",
    "emotional_openness": "string",
    "introvert_extrovert_tendencies": "string"
  },
  "emotion_agent": {
    "primary_emotion": "string",
    "stress": 0.0-1.0,
    "anxiety": 0.0-1.0,
    "sadness": 0.0-1.0,
    "burnout": 0.0-1.0,
    "emotional_intensity": 1-10
  },
  "behavior_agent": {
    "productivity_patterns": "string",
    "sleep_issues": "string",
    "procrastination": "high" | "medium" | "low" | "none",
    "routine_consistency": "string"
  },
  "growth_agent": {
    "emotional_improvement": "string",
    "motivation": "string",
    "self_awareness": "string",
    "mental_growth": "string"
  },
  "context_analysis": {
    "emotional_triggers": ["string"],
    "inferred_causes": ["string"],
    "underlying_need": "string",
    "what_user_needs": "validation" | "advice" | "distraction" | "listening" | "encouragement"
  },
  "recommendations": ["string"],
  "memory_extraction": {
    "is_meaningful": true | false,
    "memory_summary": "string" | null,
    "behavior_patterns": {
      "trigger": "string" | null,
      "stress_level": 1-10 | null,
      "emotion": "string" | null
    } | null
  }
}"""


async def cognitive_analyzer_agent(state: AgentState) -> dict:
    """Run the single structured Gemini analysis call to populate logical agents and context."""
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])
    profile = state.get("emotional_profile", {})

    recent_context = ""
    if history:
        last_messages = history[-6:]
        recent_context = "\n".join(
            f"{m['role']}: {m['content'][:300]}" for m in last_messages
        )

    profile_snippet = ""
    if profile:
        profile_snippet = f"\nUser Profile:\n{json.dumps(profile, indent=2)}"

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": MULTI_AGENT_ANALYZER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"User Profile details:\n{profile_snippet}\n\n"
                        f"Recent conversation history:\n{recent_context}\n\n"
                        f"Current message to analyze: {user_message}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        analysis = json.loads(raw)
    except Exception as e:
        logger.warning(f"Multi-agent cognitive analyzer failed, using fallback: {e}", exc_info=True)
        analysis = {
            "message_type": "emotional",
            "personality_agent": {
                "confidence_level": "moderate",
                "communication_style": "casual",
                "emotional_openness": "neutral",
                "introvert_extrovert_tendencies": "ambivert"
            },
            "emotion_agent": {
                "primary_emotion": "neutral",
                "stress": 0.3,
                "anxiety": 0.3,
                "sadness": 0.3,
                "burnout": 0.3,
                "emotional_intensity": 5
            },
            "behavior_agent": {
                "productivity_patterns": "none detected",
                "sleep_issues": "none detected",
                "procrastination": "low",
                "routine_consistency": "stable"
            },
            "growth_agent": {
                "emotional_improvement": "stable",
                "motivation": "moderate",
                "self_awareness": "moderate",
                "mental_growth": "none detected"
            },
            "context_analysis": {
                "emotional_triggers": [],
                "inferred_causes": ["exhaustion"],
                "underlying_need": "to be heard and acknowledged",
                "what_user_needs": "listening"
            },
            "recommendations": [],
            "memory_extraction": {
                "is_meaningful": False,
                "memory_summary": None,
                "behavior_patterns": None
            }
        }

    # Execute logical agents to format their states
    p_data = personality_agent.analyze(analysis)
    e_data = emotion_agent.analyze(analysis)
    b_data = behavior_agent.analyze(analysis)
    g_data = growth_agent.analyze(analysis)

    detected_emotion = e_data.get("primary_emotion", "neutral")
    
    # Calculate mood score (0.0 to 1.0)
    stress_val = e_data.get("stress", 0.3)
    anxiety_val = e_data.get("anxiety", 0.3)
    sadness_val = e_data.get("sadness", 0.3)
    burnout_val = e_data.get("burnout", 0.3)
    mood_score = round(1.0 - (stress_val * 0.2 + anxiety_val * 0.3 + sadness_val * 0.3 + burnout_val * 0.2), 2)
    mood_score = max(0.05, min(0.95, mood_score))

    # Populate backward-compatible keys
    emotion_dimensions = {
        "stress": stress_val,
        "anxiety": anxiety_val,
        "sadness": sadness_val,
        "burnout": burnout_val,
        "happiness": round(max(0.0, 1.0 - (sadness_val + stress_val) / 2.0), 2),
        "motivation": 0.8 if "high" in str(g_data.get("motivation")).lower() else (0.2 if "low" in str(g_data.get("motivation")).lower() else 0.5),
        "confidence": 0.8 if "high" in str(p_data.get("confidence_level")).lower() else (0.2 if "low" in str(p_data.get("confidence_level")).lower() else 0.5)
    }

    personality_analysis = {
        "overthinking_detected": "overthink" in str(p_data.get("communication_style")).lower() or stress_val > 0.7,
        "communication_pattern": p_data.get("communication_style", "casual"),
        "social_energy": b_data.get("routine_consistency", "stable"),
        "personality_traits": [p_data.get("introvert_extrovert_tendencies", "ambivert")],
        "emotional_needs": [p_data.get("emotional_openness", "neutral")]
    }

    logger.info(f"[ANALYSIS] Single Gemini analysis completed: type={analysis.get('message_type')}, primary_emotion={detected_emotion}, mood={mood_score}")

    return {
        "router_decision": {"message_type": analysis.get("message_type", "emotional")},
        "personality_agent": p_data,
        "emotion_agent": e_data,
        "behavior_agent": b_data,
        "growth_agent": g_data,
        "memory_extraction": analysis.get("memory_extraction", {}),
        "emotion_analysis": e_data,
        "emotion_dimensions": emotion_dimensions,
        "personality_analysis": personality_analysis,
        "context_analysis": analysis.get("context_analysis", {}),
        "recommendations": analysis.get("recommendations", []),
        "detected_emotion": detected_emotion,
        "mood_score": mood_score,
    }


# ── 2. Memory Agent ───────────────────────────────────────────
async def memory_agent(state: AgentState) -> dict:
    """Query the database for relevant memories and user patterns."""
    user_message = state.get("user_message", "")
    user_id = state.get("user_id", "")

    retrieved_memories: list[dict] = []
    patterns: dict = {}

    db = state.get("db")
    close_db = False
    if db is None:
        db = async_session_maker()
        close_db = True

    try:
        from app.services.memory_service import memory_service
        mm = MemoryManager()
        mem_objs = await memory_service.retrieveRelevantMemories(
            db=db,
            user_id=user_id,
            query=user_message,
            limit=5,
        )
        retrieved_memories = [
            {
                "content": m.memory_summary,
                "metadata": m.metadata_json,
                "distance": 0.0
            }
            for m in mem_objs
        ]
        logger.info(f"[MEMORY] Retrieved {len(retrieved_memories)} memories for user {user_id}")
        patterns = await mm.get_emotional_patterns(db, user_id)
    except Exception as e:
        logger.warning(f"[MEMORY] Memory agent error: {e}", exc_info=True)
    finally:
        if close_db:
            await db.close()

    return {"memories": retrieved_memories, "emotional_patterns": patterns}


# ── 3. Response Agent ─────────────────────────────────────────
async def response_agent(state: AgentState) -> dict:
    """Use the Response Orchestrator to generate final orchestrated prompt and response."""
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])
    profile = state.get("emotional_profile", {})
    memories = state.get("memories", [])

    personality_profile = profile.get("personality_profile", {})
    user_name = profile.get("user_name", "friend")

    # Call Orchestrator to decide Tone and Strategy
    orchestrated = response_orchestrator.determine_tone_and_strategy(
        personality=state.get("personality_agent", {}),
        emotion=state.get("emotion_agent", {}),
        behavior=state.get("behavior_agent", {}),
        growth=state.get("growth_agent", {})
    )
    tone = orchestrated["tone"]
    strategy = orchestrated["strategy"]

    # Format Current Time
    ist_tz = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(ist_tz)
    current_time_str = current_time_ist.strftime('%A, %B %d, %Y %I:%M %p (IST)')

    # Compile Final Orchestrated System Prompt
    system_prompt = response_orchestrator.build_final_prompt(
        user_name=user_name,
        personality_profile=personality_profile,
        personality=state.get("personality_agent", {}),
        emotion=state.get("emotion_agent", {}),
        behavior=state.get("behavior_agent", {}),
        growth=state.get("growth_agent", {}),
        memories=memories,
        tone=tone,
        strategy=strategy,
        current_time_str=current_time_str
    )

    # Prompt Summary for Live Debug Panel
    prompt_summary = f"[Tone: {tone.upper()} | Strategy: {strategy}]\nSystem prompt length: {len(system_prompt)} chars."

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-8:]:
            role = msg.get("role", "user")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        kwargs = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800,
        }
        response = await client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Response agent generation failed: {e}", exc_info=True)
        # Fallback text
        text = "I'm here for you. ||| Things sound a bit heavy right now... ||| What's on your mind?"

    # Assemble structured developer debug payload
    agent_analysis = {
        "personality_agent": state.get("personality_agent", {}),
        "emotion_agent": state.get("emotion_agent", {}),
        "behavior_agent": state.get("behavior_agent", {}),
        "growth_agent": state.get("growth_agent", {}),
        "retrieved_memories": memories,
        "response_strategy": {
            "tone": tone,
            "strategy": strategy
        },
        "orchestrated_prompt_summary": prompt_summary,
        # Keep backward compatible fields in agent_analysis
        "emotion_analysis": state.get("emotion_analysis", {}),
        "personality_analysis": state.get("personality_analysis", {}),
        "context_analysis": state.get("context_analysis", {}),
        "recommendations": state.get("recommendations", [])
    }

    return {
        "response": text,
        "agent_analysis": agent_analysis,
        "response_strategy": orchestrated
    }


# ── Build the compiled graph ──────────────────────────────────
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Add optimized nodes
    graph.add_node("cognitive_analyzer_agent", cognitive_analyzer_agent)
    graph.add_node("memory_agent", memory_agent)
    graph.add_node("response_agent", response_agent)

    # Entry point
    graph.set_entry_point("cognitive_analyzer_agent")

    # Linear workflow chain
    graph.add_edge("cognitive_analyzer_agent", "memory_agent")
    graph.add_edge("memory_agent", "response_agent")
    graph.add_edge("response_agent", END)

    return graph


# Compile module-level compiled graph
_compiled_graph = build_graph().compile()


async def run_agent_graph(
    user_message: str,
    user_id: str,
    conversation_history: list[dict],
    emotional_profile: dict,
    db: AsyncSession | None = None,
) -> dict:
    """Execute the full agent pipeline and return the final state."""
    initial_state: AgentState = {
        "user_message": user_message,
        "user_id": user_id,
        "conversation_history": conversation_history,
        "emotional_profile": emotional_profile,
        "db": db,
        "router_decision": {},
        "emotion_analysis": {},
        "personality_analysis": {},
        "context_analysis": {},
        "memories": [],
        "recommendations": [],
        "response": "",
        "mood_score": 0.5,
        "detected_emotion": "neutral",
        "personality_agent": {},
        "emotion_agent": {},
        "behavior_agent": {},
        "growth_agent": {},
        "memory_extraction": {},
        "response_strategy": {},
        "orchestrated_prompt_summary": "",
        "agent_analysis": {},
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
