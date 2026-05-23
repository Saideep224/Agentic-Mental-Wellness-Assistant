"""
Personality Agent – detects communication patterns, overthinking, and personality traits.
"""

import json
import logging

from openai import AsyncOpenAI

from app.agents.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

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
    """
    Analyze personality patterns in the user's message.

    Returns ``personality_analysis``.
    """
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
