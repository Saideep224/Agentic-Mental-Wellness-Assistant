"""
Response Agent – the final agent that crafts the actual message
the user will read.

This is the most critical agent in the pipeline. The system prompt
must produce natural, human-like, emotionally adaptive responses.
"""

import json
import logging

from openai import AsyncOpenAI

from app.agents.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

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
    """
    Craft the final response using all analysis from prior agents.

    Returns ``response`` — the message text the user will see.
    """
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])
    profile = state.get("emotional_profile", {})
    emotion = state.get("emotion_analysis", {})
    personality = state.get("personality_analysis", {})
    context = state.get("context_analysis", {})
    memories = state.get("memories", [])
    recommendations = state.get("recommendations", [])
    router = state.get("router_decision", {})

    # Format values for prompt placeholders
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

    # Add recent conversation history for natural continuity
    if history:
        for msg in history[-8:]:
            role = msg.get("role", "user")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": msg["content"]})

    # Add the current message
    messages.append({"role": "user", "content": user_message})

    try:
        kwargs = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800,
        }
        if not settings.GEMINI_API_KEY:
            kwargs["presence_penalty"] = 0.3
            kwargs["frequency_penalty"] = 0.4

        response = await client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Response agent failed: {e}")
        # Dynamic, emotionally natural conversational recovery (avoids raw technical failures)
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
            # Check primary emotion from analysis if we got it but response agent failed
            primary = str(emotion.get("primary_emotion", "neutral")).lower()
            if "exhaust" in primary or "burnout" in primary or "tired" in primary:
                text = "You sound a little mentally tired tonight. What’s been sitting on your mind?"
            elif "lonely" in primary or "withdrawal" in primary or "sad" in primary:
                text = "I want to understand properly. What’s been weighing on you lately?"
            else:
                text = "I think I missed part of what you meant. Want to tell me a little more?"

    return {"response": text}
