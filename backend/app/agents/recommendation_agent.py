"""
Recommendation Agent – generates contextual coping suggestions
when appropriate, based on all prior analysis.
"""

import json
import logging

from openai import AsyncOpenAI

from app.agents.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

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
    """
    Generate contextual coping suggestions based on all agent analyses.

    Returns ``recommendations`` — a list of suggestion strings (possibly empty).
    """
    emotion = state.get("emotion_analysis", {})
    personality = state.get("personality_analysis", {})
    context = state.get("context_analysis", {})
    memories = state.get("memories", [])
    user_message = state.get("user_message", "")

    # Skip recommendations for casual messages
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
