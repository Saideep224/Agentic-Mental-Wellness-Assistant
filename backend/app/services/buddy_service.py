import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.response_agent import response_agent

logger = logging.getLogger(__name__)

class BuddyService:
    """Service wrapper for Esona's main emotional support agent (Buddy)."""

    async def generate_response(
        self,
        db: AsyncSession,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
        cog_res: dict,
    ) -> dict:
        logger.info("[BuddyService] Delegating to response_agent")
        # Buddy's response is normally run as part of the langgraph pipeline, 
        # but this service provides a clean wrapper matching the specialist services interface.
        from app.chatbot.pipeline import run_agent_graph
        result = await run_agent_graph(
            user_message=user_message,
            user_id=user_id,
            conversation_history=conversation_history,
            emotional_profile=cog_res.get("emotional_profile"),
            conversation_id=cog_res.get("conversation_id"),
            db=db,
        )
        return result

buddy_service = BuddyService()
