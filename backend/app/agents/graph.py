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

from langgraph.graph import StateGraph, END
from openai import AsyncOpenAI

from app.config import settings
from app.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

# ── Shared AsyncOpenAI Client ─────────────────────────────────
client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


# ── Typed State ──────────────────────────────────────────────
class AgentState(TypedDict, total=False):
    """
    Full state schema for the Esona multi-agent graph.
    """
    user_message: str
    user_id: str
    conversation_history: list[dict]
    emotional_profile: dict
    router_decision: dict
    emotion_analysis: dict
    personality_analysis: dict
    context_analysis: dict
    memories: list[dict]
    emotional_patterns: dict
    recommendations: list[str]
    response: str
    mood_score: float
    detected_emotion: str


# ── 1. Cognitive Analyzer Prompt & Agent ──────────────────────
COGNITIVE_ANALYZER_SYSTEM_PROMPT = """You are the Cognitive Analysis Agent for Esona, a mental wellness companion.
Your job is to analyze the user's message and recent conversation context, and produce a structured, deep emotional, behavioral, and situational analysis.

Analyze for the following categories:
1. Message Type & Routing:
   - Decide if the message is "emotional" (sharing feelings, venting), "casual" (small talk, greetings), "crisis" (self-harm mentions, severe distress), or "check_in" (daily updates).
2. Advanced Emotional State:
   - Detect main and secondary emotions (from: emotional exhaustion, loneliness, overthinking, emotional numbness, burnout, anxiety, quiet sadness, social withdrawal, emotional overwhelm, crisis, calm, happy, neutral).
   - Grade the emotional intensity (1 to 10), energy level (high/moderate/low), social state (seeking/balanced/withdrawn), and emotional stability (stable/vulnerable/fragile).
3. Cognitive & Personality Patterns:
   - Detect if overthinking/rumination is present (true/false).
   - Identify the communication pattern (e.g. Intellectualizer, Minimizer, Catastrophizer, People-pleaser, Avoider, Open-processor).
   - Determine social energy level (drained, seeking, balanced, overwhelmed) and relevant personality traits (empathetic, analytical, creative, perfectionist, sensitive, independent, anxious, optimistic, etc.).
   - Highlight their immediate emotional needs (e.g. "permission to rest", "validation of feelings", "help breaking the overthinking cycle").
4. Situational Context & Triggers:
   - Identify emotional triggers (e.g., workplace conflict, academic pressure, loneliness) and inferred causes of stress.
   - State the underlying need (the deeper, unspoken need behind their words).
   - Select the best response strategy (validation, advice, distraction, listening, encouragement).
5. Actionable Coping Recommendations:
   - Generate 1 to 3 personalized, highly actionable coping suggestions ONLY if they would be helpful (e.g., for emotional/crisis/check_in states). Keep them specific to the user's situation and personality. Avoid generic platitudes.
   - Return an empty list for casual small talk.

Respond with ONLY a valid JSON object matching this schema:
{
  "message_type": "emotional" | "casual" | "crisis" | "check_in",
  "emotion_analysis": {
    "primary_emotion": "main emotion",
    "secondary_emotion": "secondary emotion or none",
    "intensity": 1-10,
    "energy_level": "high" | "moderate" | "low",
    "social_state": "seeking" | "balanced" | "withdrawn",
    "emotional_stability": "stable" | "vulnerable" | "fragile"
  },
  "personality_analysis": {
    "overthinking_detected": true | false,
    "communication_pattern": "pattern name",
    "social_energy": "drained" | "seeking" | "balanced" | "overwhelmed",
    "personality_traits": ["trait1", "trait2"],
    "emotional_needs": ["need1", "need2"]
  },
  "context_analysis": {
    "emotional_triggers": ["trigger1"],
    "inferred_causes": ["cause1"],
    "underlying_need": "deeper need in one sentence",
    "what_user_needs": "validation" | "advice" | "distraction" | "listening" | "encouragement",
    "contextual_insights": "brief insight"
  },
  "recommendations": ["coping recommendation 1", "coping recommendation 2"]
}"""

async def cognitive_analyzer_agent(state: AgentState) -> dict:
    """Analyze the user message and generate emotional, personality, and situational context analysis along with recommendations."""
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
                {"role": "system", "content": COGNITIVE_ANALYZER_SYSTEM_PROMPT},
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
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        analysis = json.loads(raw)
        
    except Exception as e:
        logger.warning(f"Cognitive analyzer agent failed, using fallback defaults: {e}")
        analysis = {
            "message_type": "emotional",
            "emotion_analysis": {
                "primary_emotion": "neutral",
                "secondary_emotion": "none",
                "intensity": 3,
                "energy_level": "moderate",
                "social_state": "balanced",
                "emotional_stability": "stable",
            },
            "personality_analysis": {
                "overthinking_detected": False,
                "communication_pattern": "open-processor",
                "social_energy": "balanced",
                "personality_traits": ["reflective"],
                "emotional_needs": ["being heard"],
            },
            "context_analysis": {
                "emotional_triggers": [],
                "inferred_causes": ["exhaustion"],
                "underlying_need": "to be heard and acknowledged",
                "what_user_needs": "listening",
                "contextual_insights": "Unable to determine deeper context — defaulting to empathetic listening.",
            },
            "recommendations": []
        }

    # Extract detected emotion and mood score for DB storage compatibility
    detected_emotion = analysis.get("emotion_analysis", {}).get("primary_emotion", "neutral")
    
    # Calculate mood score
    mood_map = {
        "emotional exhaustion": 0.3,
        "loneliness": 0.35,
        "overthinking": 0.4,
        "emotional numbness": 0.25,
        "burnout": 0.2,
        "anxiety": 0.3,
        "quiet sadness": 0.35,
        "social withdrawal": 0.3,
        "emotional overwhelm": 0.2,
        "crisis": 0.05,
        "calm": 0.75,
        "happy": 0.9,
        "neutral": 0.5
    }
    primary_em = str(detected_emotion).lower()
    mood_score = 0.5
    for key, val in mood_map.items():
        if key in primary_em:
            mood_score = val
            break

    return {
        "router_decision": {"message_type": analysis.get("message_type", "emotional")},
        "emotion_analysis": analysis.get("emotion_analysis", {}),
        "personality_analysis": analysis.get("personality_analysis", {}),
        "context_analysis": analysis.get("context_analysis", {}),
        "recommendations": analysis.get("recommendations", []),
        "detected_emotion": detected_emotion,
        "mood_score": mood_score,
    }


# ── 2. Memory Agent ───────────────────────────────────────────
async def memory_agent(state: AgentState) -> dict:
    """Query SQLite for relevant past memories and retrieve the user's emotional patterns."""
    user_message = state.get("user_message", "")
    user_id = state.get("user_id", "")

    retrieved_memories: list[dict] = []
    patterns: dict = {}

    try:
        mm = MemoryManager()
        results = mm.retrieve_memories(
            user_id=user_id,
            query=user_message,
            n_results=5,
        )
        retrieved_memories = results
        patterns = mm.get_emotional_patterns(user_id)

    except Exception as e:
        logger.warning(f"Memory agent error: {e}")

    return {"memories": retrieved_memories, "emotional_patterns": patterns}


# ── 3. Response Agent ─────────────────────────────────────────
RESPONSE_SYSTEM_PROMPT = """You are Esona, an emotionally adaptive AI companion.

You are NOT a therapist.
You are NOT a robotic assistant.
You are NOT a motivational chatbot.

Your role is to:
- understand emotional nuance
- speak naturally
- sound emotionally aware
- adapt to personality and emotional state
- maintain emotionally realistic conversations

=================================================

CURRENT USER PROFILE:
{profile_data}

CURRENT EMOTIONAL ANALYSIS:
{emotion_analysis}

RECENT EMOTIONAL MEMORY:
{memory_context}

CURRENT MESSAGE:
{user_message}

CURRENT DATE AND TIME:
{current_time}

=================================================

DEEP PERSONALIZATION INSTRUCTIONS:

1. ADDRESS THE USER BY NAME: Use their name (found in `user_name` in the CURRENT USER PROFILE) when starting the response or in a natural validation sentence (e.g., "Hey Sai deep, that sounds really draining," or "I hear you, Sai deep."). Do not repeat it more than once per message to keep it feeling natural and authentic.

2. TAILOR THE SUPPORT STYLE: Look at the `comfort_support_type` and `preferred_style` in the user's profile under `communication_style`. 
   - If they prefer "validation and empathetic listening" or "validation & quiet listening", focus entirely on validating their emotions, matching their tone, and showing presence. Do NOT jump into recommendations or suggestions immediately.
   - If they prefer "practical advice" or the analyzer strategy is "advice", integrate the generated COPING RECOMMENDATIONS smoothly into your response, explaining them in a warm, conversational style.
   - If they prefer "encouragement", highlight their strengths and give them a gentle, realistic boost without toxic positivity.

3. RESPECT COMFORT PREFERENCES & THEMES: Integrate their `safest_environment`, `escape_mechanisms`, or `mood_boosters` where relevant (e.g., "Would retreating into your music help right now?").

4. AVOID ANNOYANCES: Check the user's communication `annoyances` list in the profile. Absolutely DO NOT use any phrasing, tones, or structures listed there.

5. ADAPT TO EMOTIONAL HISTORY: Reference their patterns, dominant emotion, or common triggers from their RECENT EMOTIONAL MEMORY if it helps build continuity (e.g., "I know this trigger has come up before...").

=================================================

IMPORTANT BEHAVIOR RULES:

1. NEVER sound robotic.
2. NEVER expose technical issues.
3. NEVER use generic motivational replies repeatedly.
4. NEVER overuse:
- "everything will be okay"
- "stay strong"
- "take deep breaths"
5. Speak naturally like someone emotionally intelligent.
6. Keep responses concise and human.
7. Match user's emotional energy.

=================================================

RESPONSE STYLE EXAMPLES:

BAD:
"I understand your feelings. Stay strong."

GOOD:
"You sound mentally tired tonight."

BAD:
"Everything will be okay."

GOOD:
"That sounds like it's been sitting with you for a while."

BAD:
"Take deep breaths."

GOOD:
"Want to talk about what’s been draining you lately?"

=================================================

Generate a natural emotionally adaptive response."""

async def response_agent(state: AgentState) -> dict:
    """Craft the final response using all analysis from prior agents."""
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])
    profile = state.get("emotional_profile", {})
    emotion = state.get("emotion_analysis", {})
    personality = state.get("personality_analysis", {})
    context = state.get("context_analysis", {})
    memories = state.get("memories", [])
    recommendations = state.get("recommendations", [])

    profile_data_str = json.dumps(profile) if profile else "No profile data yet."
    emotion_analysis_str = json.dumps({
        "emotion": emotion,
        "personality": personality,
        "context": context,
        "recommendations": recommendations,
    }, indent=2)
    
    patterns = state.get("emotional_patterns", {})
    patterns_str = ""
    if patterns:
        patterns_str = (
            f"User Emotional Patterns:\n"
            f"- Dominant Emotion: {patterns.get('dominant_emotion', 'unknown')}\n"
            f"- Average Stress Level: {patterns.get('average_stress', 'unknown')}\n"
            f"- Common Triggers/Themes: {', '.join(patterns.get('common_triggers', []))}\n\n"
        )

    memory_snippets = [m.get("content", "") for m in memories if m.get("content")]
    history_str = " | ".join(memory_snippets) if memory_snippets else "No relevant past memories."
    memory_context_str = f"{patterns_str}Recent Emotional History:\n{history_str}"

    tz_name = time.tzname[0] if hasattr(time, 'tzname') else 'local time'
    current_time_str = f"{datetime.now().strftime('%A, %B %d, %Y %I:%M %p')} ({tz_name})"

    formatted_system_prompt = RESPONSE_SYSTEM_PROMPT.replace("{profile_data}", profile_data_str) \
                                                    .replace("{emotion_analysis}", emotion_analysis_str) \
                                                    .replace("{memory_context}", memory_context_str) \
                                                    .replace("{user_message}", user_message) \
                                                    .replace("{current_time}", current_time_str)

    messages = [{"role": "system", "content": formatted_system_prompt}]

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
        if not settings.GEMINI_API_KEY and not settings.USE_UNCLOSEAI:
            kwargs["presence_penalty"] = 0.3
            kwargs["frequency_penalty"] = 0.4

        response = await client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Response agent failed: {e}")
        msg_lower = user_message.lower()
        if "insecure" in msg_lower or "security" in msg_lower or "doubt" in msg_lower:
            text = "That kind of insecurity can quietly drain someone after a while. What usually triggers it for you?"
        elif "lonely" in msg_lower or "alone" in msg_lower or "isolated" in msg_lower:
            text = "I want to understand properly. What’s been weighing on you lately?"
        elif "tired" in msg_lower or "exhaust" in msg_lower or "burnout" in msg_lower:
            text = "You sound a little mentally tired tonight. What’s been sitting on your mind?"
        elif "low" in msg_lower or "sad" in msg_lower or "depressed" in msg_lower:
            text = "You sound like you’ve been carrying a lot internally lately."
        else:
            primary = str(emotion.get("primary_emotion", "neutral")).lower()
            if "exhaust" in primary or "burnout" in primary or "tired" in primary:
                text = "You sound a little mentally tired tonight. What’s been sitting on your mind?"
            elif "lonely" in primary or "withdrawal" in primary or "sad" in primary:
                text = "I want to understand properly. What’s been weighing on you lately?"
            else:
                text = "I think I missed part of what you meant. Want to tell me a little more?"

    return {"response": text}


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
) -> dict:
    """Execute the full agent pipeline and return the final state."""
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
