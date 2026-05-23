"""
Context Agent – understands situational context, triggers, and what the user actually needs.
"""

import json
import logging

from openai import AsyncOpenAI

from app.agents.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

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
    """
    Analyze the situational context of the user's message.

    Returns ``context_analysis``.
    """
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
