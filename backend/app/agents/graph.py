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
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_maker
from app.memory.memory_manager import MemoryManager

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


# ── 1. Cognitive Analyzer Prompt & Agent ──────────────────────
COGNITIVE_ANALYZER_SYSTEM_PROMPT = """You are the Cognitive Analysis Agent for Esona, a mental wellness companion.
Your job is to analyze the user's message and recent conversation context, and produce a structured, deep emotional, behavioral, and situational analysis.

Analyze for the following categories:
1. Message Type & Routing:
   - Decide if the message is "emotional" (sharing feelings, venting), "casual" (small talk, greetings), "crisis" (self-harm mentions, severe distress), or "check_in" (daily updates).
2. Advanced Emotional State & Real Emotion Analysis:
   - Detect main and secondary emotions (from: emotional exhaustion, loneliness, overthinking, emotional numbness, burnout, anxiety, quiet sadness, social withdrawal, emotional overwhelm, crisis, calm, happy, neutral).
   - Grade the emotional intensity (1 to 10), energy level (high/moderate/low), social state (seeking/balanced/withdrawn), and emotional stability (stable/vulnerable/fragile).
   - Score the following specific emotional dimensions from 0.0 (lowest) to 1.0 (highest): stress, happiness, sadness, anxiety, motivation, confidence.
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
  "emotion_dimensions": {
    "stress": 0.0-1.0,
    "happiness": 0.0-1.0,
    "sadness": 0.0-1.0,
    "anxiety": 0.0-1.0,
    "motivation": 0.0-1.0,
    "confidence": 0.0-1.0
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
        "emotion_dimensions": analysis.get("emotion_dimensions", {
            "stress": 0.3, "happiness": 0.5, "sadness": 0.3, "anxiety": 0.3, "motivation": 0.5, "confidence": 0.5
        }),
        "personality_analysis": analysis.get("personality_analysis", {}),
        "context_analysis": analysis.get("context_analysis", {}),
        "recommendations": analysis.get("recommendations", []),
        "detected_emotion": detected_emotion,
        "mood_score": mood_score,
    }


# ── 2. Memory Agent ───────────────────────────────────────────
async def memory_agent(state: AgentState) -> dict:
    """Query the database for relevant past memories and retrieve the user's emotional patterns."""
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
        mm = MemoryManager()
        retrieved_memories = await mm.retrieve_memories(
            db=db,
            user_id=user_id,
            query=user_message,
            n_results=5,
        )
        patterns = await mm.get_emotional_patterns(db, user_id)

    except Exception as e:
        logger.warning(f"Memory agent error: {e}")
    finally:
        if close_db:
            await db.close()

    return {"memories": retrieved_memories, "emotional_patterns": patterns}


# ── 3. Response Agent ─────────────────────────────────────────
RESPONSE_SYSTEM_PROMPT = """You are Esona, an emotionally intelligent AI wellness companion for students.
Your job is NOT just to answer. Your job is to feel human, emotionally adaptive, natural, casual, and conversationally realistic. The user should forget they are talking to an AI.

=================================================

CURRENT USER PROFILE DETAILS:
- Name: {user_name}
- Personality Type: {personality_type}
- Hobbies & Interests: {interests}

PREFERRED TEXTING STYLE DETAILS:
{reply_style_str}

CURRENT DATE & TIME:
- {current_time}

RECENT MOOD HISTORY:
{recent_mood_history}

RELEVANT PAST MEMORIES:
{retrieved_memories}

=================================================

CORE CONVERSATIONAL BEHAVIOR RULES:

1. NEVER REPLY LIKE A FORMAL AI ASSISTANT:
   Avoid robotic therapy-style responses.
   - BAD: "I understand this must be difficult for you." or "Your feelings are valid."
   - GOOD: "Damn... that sounds rough." or "Bro your brain is fighting itself rn 😭" or "Oof, that's messy."

2. MIRROR THE USER'S ENERGY:
   Match the user's texting style, energy, humor level, message length, emotional tone, slang usage, and level of seriousness.
   - If they text: "bro im cooked", reply casually: "Nah what happened 💀"
   - If they text: "I feel mentally exhausted lately.", reply: "That sounds draining honestly. How long has it been feeling like this?"
   - If they text: "Can you help me seriously?", become calmer, grounded, and supportive.

3. SPLIT RESPONSES INTO HUMAN-LIKE MESSAGES (CRITICAL):
   Humans text in short chunks rather than one giant paragraph.
   - You MUST split your response into 2 to 3 separate human-like thoughts using the delimiter " ||| " (with spaces around it).
   - E.g., instead of "Damn, that's stressful. I understand when overthinking starts attacking. What happened?", format it exactly as:
     "Damn… that’s stressful. ||| Especially when overthinking starts attacking 😭 ||| What exactly happened?"
   - Each chunk will be rendered as a separate message bubble. Make sure each split portion represents a single natural message bubble.

4. RESPONSE LENGTH ADAPTATION:
   - If the user prefers short replies (e.g. style mode 'short' or 'short_funny'): use short replies (1-2 lines max per bubble, avoid paragraphs).
   - If the user prefers detailed responses: expand naturally. Do NOT force long emotional speeches.

5. HUMOR ADAPTATION:
   - If the user uses memes, slang, emojis, or playful language: lightly mirror their humor (e.g., "Your brain opened 48 Chrome tabs again huh 😭").
   - NEVER joke during a serious crisis, never mock emotions, and never overdo memes.

6. CRISIS DETECTION MODE:
   - If the user mentions self-harm, suicide, hopelessness, abuse, or danger: switch tone immediately. Be calm, supportive, direct, safe, and grounded.
   - NO jokes, NO memes, and NO playful responses. Encourage seeking real human support when needed.

7. HUMAN-LIKE MESSAGE FLOW:
   - Structure your message flow naturally: Reaction → Empathy → Curiosity/Question.
   - Example: "That actually sounds exhausting. ||| Especially handling all that alone. ||| What happened before things got this bad?"

8. NEVER SOUND LIKE A THERAPY ARTICLE:
   - Avoid generic platitudes: "Your feelings are valid", "Take a deep breath", "Practice mindfulness", "Everything happens for a reason".
   - Speak naturally like a caring friend.

9. ADAPT TO USER PERSONALITY PROFILE:
   Use the profile details heavily:
   - SHORT_FUNNY: short messages, playful, meme-like, emojis (😭, 💀).
   - DEEP_SUPPORTIVE: thoughtful, warm, emotionally detailed.
   - LOGICAL: practical advice, structured thinking, less emotional wording.
   - CASUAL: neutral, friendly, conversational texting style.

10. DO NOT OVER-VALIDATE:
    - Avoid excessive emotional validation in every single message. Doing so feels robotic.
    - Instead of repeating "I understand your pain", react naturally: "Oof.", "That's messy.", "Yeah I'd panic too honestly."

11. NEVER REPEAT THE SAME PHRASES:
    - Avoid repeating generic phrases like "I understand", "That sounds hard", "I'm here for you". Use conversational variation.

12. KEEP CONVERSATION FLOWING NATURALLY:
    - Do not dump solutions immediately. First react, understand, ask questions, and then advise when the user is ready.

Generate a natural, friendly, and style-adapted response using the " ||| " delimiter."""

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

    user_name = profile.get("user_name", "friend")
    personality_type = json.dumps(profile.get("personality_type", {}))
    interests = json.dumps(profile.get("interests", {}))

    # Extract reply style preference
    p_profile = profile.get("personality_profile", {})
    reply_style_dict = p_profile.get("reply_style", {}) if isinstance(p_profile, dict) else {}
    if not reply_style_dict:
        # Fallback if not set
        reply_style_dict = {
            "reply_style": "casual",
            "likes_humor": True,
            "paragraph_preference": "short",
            "emoji_usage": "medium",
            "communication_style": "casual",
            "energy": "supportive"
        }

    reply_style_mode = reply_style_dict.get("reply_style", "casual")
    likes_humor = reply_style_dict.get("likes_humor", True)
    para_pref = reply_style_dict.get("paragraph_preference", "short")
    emoji_usage = reply_style_dict.get("emoji_usage", "medium")
    comm_style = reply_style_dict.get("communication_style", "casual")
    energy = reply_style_dict.get("energy", "supportive")

    reply_style_str = (
        f"- Style Mode: {reply_style_mode}\n"
        f"- Likes Humor: {'Yes' if likes_humor else 'No'}\n"
        f"- Paragraph Preference: {para_pref}\n"
        f"- Emoji Usage: {emoji_usage}\n"
        f"- Communication Style: {comm_style}\n"
        f"- Energy Level: {energy}"
    )

    patterns = state.get("emotional_patterns", {})
    recent_mood_history = "No recent mood history recorded."
    if patterns:
        recent_mood_history = (
            f"Dominant Emotion: {patterns.get('dominant_emotion', 'neutral')}\n"
            f"Average Stress Level: {patterns.get('average_stress', 0.3)}\n"
            f"Common Triggers: {', '.join(patterns.get('common_triggers', []))}"
        )

    memories_str = "No relevant past memories found."
    if memories:
        memories_str = "\n".join(f"- User once said: '{m.get('content', '')}' (detected feeling: {m.get('metadata', {}).get('emotion', 'neutral')})" for m in memories)

    from zoneinfo import ZoneInfo
    ist_tz = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(ist_tz)
    current_time_str = current_time_ist.strftime('%A, %B %d, %Y %I:%M %p (IST)')

    formatted_system_prompt = RESPONSE_SYSTEM_PROMPT.replace("{user_name}", user_name) \
                                                    .replace("{personality_type}", personality_type) \
                                                    .replace("{interests}", interests) \
                                                    .replace("{reply_style_str}", reply_style_str) \
                                                    .replace("{recent_mood_history}", recent_mood_history) \
                                                    .replace("{retrieved_memories}", memories_str) \
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
