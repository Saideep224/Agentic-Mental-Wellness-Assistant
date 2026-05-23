"""
Memory Agent – retrieves relevant past memories and stores new emotional data.
"""

import logging

from app.agents.state import AgentState
from app.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


async def memory_agent(state: AgentState) -> dict:
    """
    Query SQLite for relevant past memories and retrieve the user's emotional patterns.

    Returns ``memories`` (list of relevant past entries) and ``emotional_patterns`` (dict).
    """
    user_message = state.get("user_message", "")
    user_id = state.get("user_id", "")

    retrieved_memories: list[dict] = []
    patterns: dict = {}

    try:
        mm = MemoryManager()

        # Retrieve memories related to the current message
        results = mm.retrieve_memories(
            user_id=user_id,
            query=user_message,
            n_results=5,
        )
        retrieved_memories = results

        # Retrieve user's recurring emotional patterns
        patterns = mm.get_emotional_patterns(user_id)

    except Exception as e:
        logger.warning(f"Memory agent error: {e}")
        # Memory failures are non-critical — we continue without them

    return {"memories": retrieved_memories, "emotional_patterns": patterns}
