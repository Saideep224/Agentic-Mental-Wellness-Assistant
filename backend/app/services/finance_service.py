import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.specialist_service import specialist_service

logger = logging.getLogger(__name__)

class FinanceService:
    """Service wrapper for Finance Coach Specialist."""

    async def generate_response(
        self,
        db: AsyncSession,
        user_id: str,
        user_message: str,
        conversation_history: list[dict],
        cog_res: dict,
    ) -> dict:
        logger.info("[FinanceService] Invoking specialist service for Finance Coach")
        return await specialist_service.generate_specialist_response(
            db=db,
            user_id=user_id,
            specialist_id="finance",
            user_message=user_message,
            conversation_history=conversation_history,
            cog_res=cog_res
        )

finance_service = FinanceService()
