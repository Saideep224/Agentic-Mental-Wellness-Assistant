"""
Memory Agent - retrieves relevant user memories and aggregates emotional patterns.
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory_service import memory_service
from app.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

def get_memory_priority(content: str, memory_type: str | None) -> int:
    content_lower = content.lower()
    mtype_lower = (memory_type or "").lower()
    
    # Priority 5: Crisis, Trauma, Panic attacks
    if any(k in content_lower for k in ["die", "suicide", "kill myself", "end my life", "panic attack", "trauma", "abuse", "grief", "death", "passed away"]):
        return 5
    if any(k in mtype_lower for k in ["crisis", "trauma", "panic"]):
        return 5
        
    # Priority 4: Family, Relationships
    if any(k in content_lower for k in ["girlfriend", "boyfriend", "wife", "husband", "partner", "mom", "dad", "mother", "father", "sister", "brother", "family", "relationship", "married", "blocked me", "broke up"]):
        return 4
    if any(k in mtype_lower for k in ["family", "relationship"]):
        return 4
        
    # Priority 3: Career, Exams
    if any(k in content_lower for k in ["exam", "study", "job", "career", "interview", "office", "placement", "boss", "work", "college", "school"]):
        return 3
    if any(k in mtype_lower for k in ["career", "exam", "work"]):
        return 3
        
    # Priority 2: Interests
    if any(k in content_lower for k in ["hobby", "game", "gaming", "music", "guitar", "gym", "fitness", "movie", "book", "read"]):
        return 2
    if any(k in mtype_lower for k in ["interest", "hobby"]):
        return 2
        
    # Priority 1: Small preferences
    return 1


class MemoryAgent:
    """
    Logical agent responsible for:
    - Recalling semantically relevant context
    - Fetching current user mood trends & patterns
    """

    def __init__(self) -> None:
        self.mm = MemoryManager()

    async def retrieve_context(self, db: AsyncSession, user_id: str, query: str, limit: int = 5) -> Dict[str, Any]:
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
                limit=limit + 3,  # Fetch slightly more to rank them
            )
            # Prioritize memories by similarity distance
            retrieved_memories = [
                {
                    "content": m.memory_summary,
                    "memory_type": m.memory_type,
                    "importance_score": m.importance_score,
                    "metadata": m.metadata_json,
                    "distance": 0.0
                }
                for m in mem_objs
            ]
            
            # Sort retrieved memories by category priority, then by importance_score
            retrieved_memories.sort(
                key=lambda x: (get_memory_priority(x["content"], x["memory_type"]), x.get("importance_score") or 0.0),
                reverse=True
            )
            
            # Limit to top 4 to prevent prompt token bloat
            retrieved_memories = retrieved_memories[:4]
            
            patterns = await self.mm.get_emotional_patterns(db, user_id)
            logger.info(f"[MemoryAgent] Successfully recalled {len(retrieved_memories)} ranked memories for user {user_id}")
        except Exception as e:
            logger.warning(f"[MemoryAgent] Recall failed: {e}", exc_info=True)

        return {
            "memories": retrieved_memories,
            "emotional_patterns": patterns
        }

memory_agent = MemoryAgent()

