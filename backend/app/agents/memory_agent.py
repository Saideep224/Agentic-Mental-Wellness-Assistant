"""
Memory Agent - retrieves relevant user memories and aggregates emotional patterns.
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import memory_service
from app.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class MemoryAgent:
    """
    Logical agent responsible for:
    - Recalling semantically relevant context
    - Fetching current user mood trends & patterns
    """

    def __init__(self) -> None:
        self.mm = MemoryManager()

    async def retrieve_context(self, db: AsyncSession, user_id: str, query: str, limit: int = 3) -> Dict[str, Any]:
        """
        Recall relevant memories and pull emotional patterns for LLM context enrichment.
        """
        retrieved_memories: List[Dict[str, Any]] = []
        patterns: Dict[str, Any] = {}

        try:
            mem_objs = await memory_service.retrieveRelevantMemories(
                db=db,
                user_id=user_id,
                query=query,
                limit=limit,
            )
            # Prioritize memories by similarity distance
            retrieved_memories = [
                {
                    "content": m.memory_summary,
                    "metadata": m.metadata_json,
                    "distance": 0.0
                }
                for m in mem_objs
            ]
            
            patterns = await self.mm.get_emotional_patterns(db, user_id)
            logger.info(f"[MemoryAgent] Successfully recalled {len(retrieved_memories)} memories for user {user_id}")
        except Exception as e:
            logger.warning(f"[MemoryAgent] Recall failed: {e}", exc_info=True)

        return {
            "memories": retrieved_memories,
            "emotional_patterns": patterns
        }

memory_agent = MemoryAgent()
