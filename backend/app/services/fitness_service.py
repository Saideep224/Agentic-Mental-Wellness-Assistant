import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.specialist_service import specialist_service

logger = logging.getLogger(__name__)

class FitnessService:
    """Service wrapper for Fitness Coach Specialist."""

    async def generate_response(
        self,
        db: AsyncSession,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
        cog_res: dict,
    ) -> dict:
        logger.info("[FitnessService] Invoking specialist service for Fitness Coach")
        return await specialist_service.generate_specialist_response(
            db=db,
            user_id=user_id,
            specialist_id="fitness",
            user_message=user_message,
            conversation_history=conversation_history,
            cog_res=cog_res
        )

fitness_service = FitnessService()
