"""
Router Agent – first agent in the pipeline.

Analyzes the user message to decide which downstream agents should
be activated and classifies the message type.
"""

import json
import logging

from openai import AsyncOpenAI

from app.agents.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

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
    """
    Analyze the user message and decide which agents to activate.

    Returns a partial state update with ``router_decision``.
    """
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])

    # Build a concise context snippet for the router
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

        # Parse JSON from the response, stripping markdown fences if present
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
