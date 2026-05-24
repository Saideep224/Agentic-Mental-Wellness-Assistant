"""
LangGraph agent graph – orchestrates the multi-agent pipeline.
Consolidated into a single file to reduce file count and share the OpenAI client.
"""

import json
import logging
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


# ── 1. Router Agent ───────────────────────────────────────────
ROUTER_SYSTEM_PROMPT = """You are the Router Agent for Esona, a supportive mental wellness companion.

Your job is to quickly analyze the user's message and decide:
1. What TYPE of message this is
2. Which specialist agents should be activated

Message types:
- "emotional": The user is sharing feelings, venting, or expressing emotions
- "casual": Small talk, greetings, general conversation
- "crisis": Signs of severe distress, self-harm mentions, or urgent emotional crisis
- "check_in": User checking in, sharing daily updates, routine conversation

Agent activation rules:
- emotion_agent: Activate for emotional, crisis, and check_in messages. Skip for purely casual small talk.
- personality_agent: Activate when the message reveals patterns, overthinking, or personality-related content.
- context_agent: Activate for emotional and crisis messages, or when context would help understand the user better.
- memory_agent: Almost always activate — memories help personalize responses. Only skip for very brief greetings.

For crisis messages, ALWAYS activate ALL agents.

Respond with ONLY a valid JSON object (no markdown, no explanation):
{
    "activate_emotion": true/false,
    "activate_personality": true/false,
    "activate_context": true/false,
    "activate_memory": true/false,
    "message_type": "emotional"|"casual"|"crisis"|"check_in"
}"""

async def router_agent(state: AgentState) -> dict:
    """Analyze the user message and decide which agents to activate."""
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])

    recent_context = ""
    if history:
        last_messages = history[-4:]
        recent_context = "\n".join(
            f"{m['role']}: {m['content'][:200]}" for m in last_messages
        )

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Recent conversation context:\n{recent_context}\n\n"
                        f"Current message: {user_message}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        decision = json.loads(raw)

    except Exception as e:
        logger.warning(f"Router agent failed, activating all agents: {e}")
        decision = {
            "activate_emotion": True,
            "activate_personality": True,
            "activate_context": True,
            "activate_memory": True,
            "message_type": "emotional",
        }

    return {"router_decision": decision}


# ── 2. Emotion Agent ──────────────────────────────────────────
EMOTION_SYSTEM_PROMPT = """You are the Emotion Analysis Agent for Esona, a mental wellness companion.

Your role is to deeply understand what the user is REALLY feeling — not just the surface-level words, but the undertones, the things left unsaid, and the emotional weight behind the message.

You're like a perceptive friend who can read between the lines.

You are analyzing for advanced emotional states, including:
- emotional exhaustion
- loneliness
- overthinking
- emotional numbness
- burnout
- anxiety
- quiet sadness
- social withdrawal
- emotional overwhelm
- crisis (severe risk / self-harm)
- calm
- happy
- neutral

Respond with ONLY a valid JSON object:
{
  "primary_emotion": "the main emotion detected from the list above",
  "secondary_emotion": "an underlying or secondary emotion",
  "intensity": 1 to 10,
  "energy_level": "high|moderate|low",
  "social_state": "seeking|balanced|withdrawn",
  "emotional_stability": "stable|vulnerable|fragile"
}"""

async def emotion_agent(state: AgentState) -> dict:
    """Analyze the emotional content of the user's message."""
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])

    recent_context = ""
    if history:
        last_msgs = history[-6:]
        recent_context = "\n".join(
            f"{m['role']}: {m['content'][:300]}" for m in last_msgs
        )

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": EMOTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Conversation context:\n{recent_context}\n\n"
                        f"Current message to analyze: {user_message}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        analysis = json.loads(raw)

    except Exception as e:
        logger.warning(f"Emotion agent failed: {e}")
        analysis = {
            "primary_emotion": "neutral",
            "secondary_emotion": "none",
            "intensity": 3,
            "energy_level": "moderate",
            "social_state": "balanced",
            "emotional_stability": "stable",
        }

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
    
    primary_em = str(analysis.get("primary_emotion", "neutral")).lower()
    mood_score = 0.5
    for key, val in mood_map.items():
        if key in primary_em:
            mood_score = val
            break

    return {
        "emotion_analysis": analysis,
        "mood_score": mood_score,
        "detected_emotion": analysis.get("primary_emotion", "neutral"),
    }


# ── 3. Personality Agent ──────────────────────────────────────
PERSONALITY_SYSTEM_PROMPT = """You are the Personality Analysis Agent for Esona, a mental wellness companion.

Your role is to understand HOW the user thinks and communicates — their patterns, tendencies, and personality-driven behaviors that shape their emotional experience.

You're looking for:

1. **Overthinking patterns**: Circular reasoning, "what if" spirals, rumination, second-guessing, analysis paralysis. These often show up as long messages, excessive qualifiers ("I know it's stupid but..."), or repeated revisiting of the same topic.

2. **Communication patterns**: 
   - "Intellectualizer": Uses logic to avoid feelings ("Logically I know...")
   - "Minimizer": Downplays their own struggles ("It's not a big deal")
   - "Catastrophizer": Jumps to worst-case scenarios
   - "People-pleaser": Focuses on others' reactions, guilt about their own needs
   - "Avoider": Changes subject, uses humor to deflect
   - "Open-processor": Thinks out loud, comfortable with vulnerability

3. **Social energy**: 
   - "Drained": Socially exhausted, needs alone time
   - "Seeking": Wanting connection, feeling isolated
   - "Balanced": Comfortable with current social level
   - "Overwhelmed": Too much social input

4. **Personality traits**: Pick the most relevant from the message (empathetic, analytical, creative, perfectionist, resilient, sensitive, independent, nurturing, anxious, optimistic, cautious, spontaneous)

5. **Emotional needs**: What this person specifically needs right now based on their personality (e.g., "permission to rest", "validation of feelings", "help breaking the overthinking cycle", "reminder of their strengths")

Respond with ONLY a valid JSON object:
{
    "overthinking_detected": true/false,
    "communication_pattern": "one of the patterns above",
    "social_energy": "drained|seeking|balanced|overwhelmed",
    "personality_traits": ["trait1", "trait2", "trait3"],
    "emotional_needs": ["need1", "need2"]
}"""

async def personality_agent(state: AgentState) -> dict:
    """Analyze personality patterns in the user's message."""
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])
    profile = state.get("emotional_profile", {})

    recent_context = ""
    if history:
        last_msgs = history[-6:]
        recent_context = "\n".join(
            f"{m['role']}: {m['content'][:300]}" for m in last_msgs
        )

    profile_snippet = ""
    if profile:
        profile_snippet = f"\nKnown personality profile: {json.dumps(profile.get('personality_type', {}))}"

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": PERSONALITY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Conversation context:\n{recent_context}\n"
                        f"{profile_snippet}\n\n"
                        f"Current message: {user_message}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        analysis = json.loads(raw)

    except Exception as e:
        logger.warning(f"Personality agent failed: {e}")
        analysis = {
            "overthinking_detected": False,
            "communication_pattern": "open-processor",
            "social_energy": "balanced",
            "personality_traits": ["reflective"],
            "emotional_needs": ["being heard"],
        }

    return {"personality_analysis": analysis}


# ── 4. Context Agent ──────────────────────────────────────────
CONTEXT_SYSTEM_PROMPT = """You are the Context Analysis Agent for Esona, a mental wellness companion.

Your role is to understand the SITUATION, CONTEXT, and WHY the user feels the way they do. You look past the words to figure out:

1. **Emotional triggers**: What specific things seem to be causing or amplifying the user's emotional state? (e.g., "workplace conflict", "romantic rejection", "academic pressure", "family expectations", "financial stress", "health anxiety", "loneliness", "identity struggles")

2. **Inferred causes**: Analyze and infer potential root causes behind the message (e.g. "loneliness", "exhaustion", "disappointment", "stress", "emotional burnout", "overthinking").

3. **Underlying need**: What is the deeper, unspoken need? The user might say "I had a bad day" but the underlying need might be "I need someone to acknowledge that my frustrations are valid" or "I need to feel like I'm not alone in struggling."

4. **What the user needs right now**: Pick the MOST appropriate response strategy:
   - "validation": They need to hear that their feelings make sense and are okay
   - "advice": They're actually looking for practical suggestions or a different perspective
   - "distraction": They're emotionally saturated and need a mental break
   - "listening": They just need to be heard — no fixing, no advice, just presence
   - "encouragement": They need a confidence boost or reminder of their capability

5. **Contextual insights**: A brief insight that would help craft the perfect response. For example: "User seems to be comparing themselves to peers," or "This appears to be a recurring pattern around Sunday evenings," or "User is processing grief but isn't ready to name it yet."

Important: Don't make assumptions without evidence. If the message is ambiguous, lean toward "listening" — it's the safest and most respectful default.

Respond with ONLY a valid JSON object:
{
    "emotional_triggers": ["trigger1", "trigger2"],
    "inferred_causes": ["loneliness|exhaustion|disappointment|stress|burnout|overthinking"],
    "underlying_need": "the deeper need in one sentence",
    "what_user_needs": "validation|advice|distraction|listening|encouragement",
    "contextual_insights": "brief contextual insight"
}"""

async def context_agent(state: AgentState) -> dict:
    """Analyze the situational context of the user's message."""
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])
    profile = state.get("emotional_profile", {})

    recent_context = ""
    if history:
        last_msgs = history[-8:]
        recent_context = "\n".join(
            f"{m['role']}: {m['content'][:300]}" for m in last_msgs
        )

    profile_snippet = ""
    if profile:
        comfort = profile.get("comfort_preferences", {})
        if comfort:
            profile_snippet = f"\nUser's comfort preferences: {json.dumps(comfort)}"

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": CONTEXT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Conversation context:\n{recent_context}\n"
                        f"{profile_snippet}\n\n"
                        f"Current message: {user_message}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=400,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        analysis = json.loads(raw)

    except Exception as e:
        logger.warning(f"Context agent failed: {e}")
        analysis = {
            "emotional_triggers": [],
            "inferred_causes": ["exhaustion"],
            "underlying_need": "to be heard and acknowledged",
            "what_user_needs": "listening",
            "contextual_insights": "Unable to determine deeper context — defaulting to empathetic listening.",
        }

    return {"context_analysis": analysis}


# ── 5. Memory Agent ───────────────────────────────────────────
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


# ── 6. Recommendation Agent ───────────────────────────────────
RECOMMENDATION_SYSTEM_PROMPT = """You are the Recommendation Agent for Esona, a mental wellness companion.

Based on the emotional analysis, personality insights, and context, your job is to generate practical, personalized coping suggestions — but ONLY when they would genuinely help.

IMPORTANT RULES:
1. Do NOT recommend things if the user just needs to be heard. Sometimes the best recommendation is none.
2. Never suggest "seek professional help" as a first resort unless there's a crisis.
3. Make suggestions SPECIFIC and ACTIONABLE, not generic platitudes.
4. Match recommendations to the user's personality:
   - For overthinkers: grounding exercises, journaling, time-boxing worries
   - For people-pleasers: boundary-setting exercises, self-compassion practices
   - For avoiders: gentle exposure, breaking tasks into tiny steps
   - For intellectualizers: body-based exercises, emotional labeling
5. Consider social energy: don't suggest social activities for someone who's drained.
6. Maximum 3 recommendations. Quality over quantity.
7. If the message is casual or the user is doing well, return an empty list.

Bad examples (never do these):
- "Try to stay positive!" ← toxic positivity
- "Have you tried therapy?" ← dismissive
- "Everything happens for a reason" ← invalidating
- "Just breathe" ← too generic without context

Good examples:
- "When the overthinking spiral starts, try writing down the three worst things that could happen, then the three most likely things. The gap between them is usually where reality lives."
- "It sounds like your body is carrying a lot of tension from this. A 5-minute body scan might help — just noticing where you're holding stress without trying to fix it."
- "Setting one small boundary this week, even something tiny like saying 'I need 10 minutes' before responding, can start to shift the pattern."

Based on the analysis data provided, return ONLY a JSON array of recommendation strings (or empty array):
["recommendation 1", "recommendation 2"]"""

async def recommendation_agent(state: AgentState) -> dict:
    """Generate contextual coping suggestions based on all agent analyses."""
    emotion = state.get("emotion_analysis", {})
    personality = state.get("personality_analysis", {})
    context = state.get("context_analysis", {})
    memories = state.get("memories", [])
    user_message = state.get("user_message", "")

    router = state.get("router_decision", {})
    if router.get("message_type") == "casual":
        return {"recommendations": []}

    analysis_summary = json.dumps({
        "user_message": user_message[:500],
        "emotion": emotion,
        "personality": personality,
        "context": context,
        "relevant_past_patterns": [m.get("content", "")[:100] for m in memories[:3]],
    }, indent=2)

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": RECOMMENDATION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Analysis data:\n{analysis_summary}",
                },
            ],
            temperature=0.4,
            max_tokens=500,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        recommendations = json.loads(raw)

        if not isinstance(recommendations, list):
            recommendations = []

    except Exception as e:
        logger.warning(f"Recommendation agent failed: {e}")
        recommendations = []

    return {"recommendations": recommendations}


# ── 7. Response Agent ─────────────────────────────────────────
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

6. Responses should feel:
- calm
- understanding
- emotionally realistic
- conversational
- adaptive

7. If user sounds emotionally low:
- gently explore emotion
- avoid instantly giving advice
- prioritize emotional understanding first

8. Keep responses concise and human.

9. Match user's emotional energy.

10. Avoid therapist-like scripting.

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

    formatted_system_prompt = RESPONSE_SYSTEM_PROMPT.replace("{profile_data}", profile_data_str) \
                                                    .replace("{emotion_analysis}", emotion_analysis_str) \
                                                    .replace("{memory_context}", memory_context_str) \
                                                    .replace("{user_message}", user_message)

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


# ── Pass-through nodes for skipped agents ─────────────────────
async def skip_emotion(state: AgentState) -> dict:
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
    return {
        "context_analysis": {
            "emotional_triggers": [],
            "underlying_need": "general conversation",
            "what_user_needs": "listening",
            "contextual_insights": "Casual interaction — no deep context needed.",
        }
    }

async def skip_memory(state: AgentState) -> dict:
    return {"memories": []}

async def merge_analyses(state: AgentState) -> dict:
    return {}


# ── Conditional routing helpers ───────────────────────────────
def route_emotion(state: AgentState) -> str:
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


# ── Build the compiled graph ──────────────────────────────────
def build_graph() -> StateGraph:
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

    # Router conditional splits
    graph.add_conditional_edges("router_agent", route_emotion, {"emotion_agent": "emotion_agent", "skip_emotion": "skip_emotion"})
    graph.add_conditional_edges("router_agent", route_personality, {"personality_agent": "personality_agent", "skip_personality": "skip_personality"})
    graph.add_conditional_edges("router_agent", route_context, {"context_agent": "context_agent", "skip_context": "skip_context"})
    graph.add_conditional_edges("router_agent", route_memory, {"memory_agent": "memory_agent", "skip_memory": "skip_memory"})

    # Merging
    graph.add_edge("emotion_agent", "merge_analyses")
    graph.add_edge("skip_emotion", "merge_analyses")
    graph.add_edge("personality_agent", "merge_analyses")
    graph.add_edge("skip_personality", "merge_analyses")
    graph.add_edge("context_agent", "merge_analyses")
    graph.add_edge("skip_context", "merge_analyses")
    graph.add_edge("memory_agent", "merge_analyses")
    graph.add_edge("skip_memory", "merge_analyses")

    # Final chain
    graph.add_edge("merge_analyses", "recommendation_agent")
    graph.add_edge("recommendation_agent", "response_agent")
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
