"""
Emotion Agent – detects emotional content, stress, and mood from the message.
"""

import json
import logging

from openai import AsyncOpenAI

from app.agents.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

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
    """
    Analyze the emotional content of the user's message.

    Returns ``emotion_analysis``, ``mood_score``, and ``detected_emotion``.
    """
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

    # Map primary emotion and energy level to numeric mood score (0.0 to 1.0)
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
