import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.buddy_service import buddy_service
from app.services.lawyer_service import lawyer_service
from app.services.doctor_service import doctor_service
from app.services.mentor_service import mentor_service
from app.services.tech_service import tech_service
from app.services.finance_service import finance_service
from app.services.fitness_service import fitness_service

logger = logging.getLogger(__name__)

class AIRouter:
    """Routes message generation to the appropriate specialist or buddy service."""

    async def generate_response(
        self,
        db: AsyncSession,
        user_id: str,
        agent_id: str,
        user_message: str,
        conversation_history: list[dict],
        cog_res: dict,
    ) -> dict:
        logger.info(f"[AIRouter] Routing request for agent_id={agent_id}")

        if agent_id == "buddy":
            return await buddy_service.generate_response(
                db=db,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                cog_res=cog_res
            )
        elif agent_id == "lex":
            return await lawyer_service.generate_response(
                db=db,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                cog_res=cog_res
            )
        elif agent_id == "maya":
            return await doctor_service.generate_response(
                db=db,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                cog_res=cog_res
            )
        elif agent_id == "mentor":
            return await mentor_service.generate_response(
                db=db,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                cog_res=cog_res
            )
        elif agent_id == "techie":
            return await tech_service.generate_response(
                db=db,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                cog_res=cog_res
            )
        elif agent_id == "finance":
            return await finance_service.generate_response(
                db=db,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                cog_res=cog_res
            )
        elif agent_id == "fitness":
            return await fitness_service.generate_response(
                db=db,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                cog_res=cog_res
            )
        else:
            logger.warning(f"[AIRouter] Unknown agent_id={agent_id}, falling back to buddy.")
            return await buddy_service.generate_response(
                db=db,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
                cog_res=cog_res
            )

ai_router = AIRouter()
