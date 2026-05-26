"""
Memory Service – handles memory analysis, extraction of behavioral/emotional insights,
and persistence in Supabase (PostgreSQL/SQLite) database.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.memory import Memory
from app.agents.graph import client
from app.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

MEMORY_ANALYZER_SYSTEM_PROMPT = """You are the Memory Extraction Agent for Esona, a mental wellness companion.
Your task is to analyze the user's latest message and extract meaningful emotional or behavioral insights.

We only save memories that represent:
- Personality traits or preferences (e.g. user prefers supportive tone, user studies better at night)
- Emotional state, triggers, or stressors (e.g. user feels stressed before exams, user feels lonely on weekends)
- Burnout indicators or focus/sleep/procrastination routines.

Ignore casual small talk, basic greetings, empty statements, or generic messages that contain no personal emotional/behavioral substance (e.g. "hey", "how are you", "tell me a joke", "cool", "whats up").

If the message contains meaningful emotional or behavioral insights:
- Set "is_meaningful" to true.
- Provide a concise "memory_summary" summarizing the key insight.
- Provide "behavior_patterns" as a JSON object containing keys like "trigger", "stress_level" (1-10), "dominant_emotion", and any other relevant fields.

If the message does not contain meaningful substance:
- Set "is_meaningful" to false.
- Set "memory_summary" to null.
- Set "behavior_patterns" to null.

Output ONLY a valid JSON object matching this schema:
{
  "is_meaningful": true | false,
  "memory_summary": "concise description of insight" | null,
  "behavior_patterns": {
    "trigger": "trigger description" | null,
    "stress_level": 1-10 | null,
    "dominant_emotion": "detected emotion" | null
  } | null
}"""


class MemoryService:
    """
    Service for analyzing emotional meaning, behavior pattern extraction,
    and automatic memory persistence.
    """

    def __init__(self) -> None:
        self.memory_manager = MemoryManager()

    async def analyze_memory_importance(
        self, user_message: str, history_context: str = ""
    ) -> Dict[str, Any]:
        """
        Analyze the user message to extract meaningful emotional/behavioral insights.
        Returns a dict containing 'is_meaningful', 'memory_summary', and 'behavior_patterns'.
        """
        if not user_message or len(user_message.strip()) < 3:
            return {"is_meaningful": False, "memory_summary": None, "behavior_patterns": None}

        try:
            prompt_content = f"User message: {user_message}"
            if history_context:
                prompt_content = f"Context:\n{history_context}\n\nUser message: {user_message}"

            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": MEMORY_ANALYZER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_content},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Error in analyze_memory_importance: {e}", exc_info=True)
            return {"is_meaningful": False, "memory_summary": None, "behavior_patterns": None}

    async def save_memory(
        self, db: AsyncSession, user_id: str, memory_summary: str, behavior_patterns: Dict[str, Any]
    ) -> Optional[Memory]:
        """
        Saves a memory to the database and handles embedding generation automatically.
        """
        try:
            # Ensure patterns dict is mutable and sanitized
            patterns = dict(behavior_patterns or {})

            # Generate and embed vector representation of the memory_summary
            embedding = self.memory_manager._get_embedding(memory_summary)
            if embedding:
                patterns["embedding"] = embedding

            memory = Memory(
                user_id=user_id,
                memory_summary=memory_summary,
                behavior_patterns=patterns,
            )
            db.add(memory)
            await db.flush()

            logger.info(f"Memory saved successfully for user {user_id}: '{memory_summary}'")
            return memory
        except Exception as e:
            logger.error(f"Memory save failed for user {user_id}: {e}", exc_info=True)
            return None

    async def retrieve_relevant_memories(
        self, db: AsyncSession, user_id: str, query: str, limit: int = 5
    ) -> List[Memory]:
        """
        Retrieve relevant memories for a user using vector cosine similarity or lexical fallback.
        """
        try:
            # Load user memories
            result = await db.execute(
                select(Memory).where(Memory.user_id == user_id)
            )
            rows = result.scalars().all()
            if not rows:
                return []

            # Generate query embedding
            query_vector = self.memory_manager._get_embedding(query)
            if not query_vector:
                # Fallback lexical matching
                logger.debug("Falling back to lexical keyword matching for memories")
                query_words = set(query.lower().split())
                matches = []
                for mem in rows:
                    content_words = set(mem.memory_summary.lower().split())
                    overlap = len(query_words.intersection(content_words))
                    score = overlap / max(len(query_words), 1)
                    matches.append((mem, score))
                matches.sort(key=lambda x: x[1], reverse=True)
                return [m[0] for m in matches if m[1] > 0][:limit]

            # Vector similarity search
            matches = []
            for mem in rows:
                db_vector = mem.embedding_json
                similarity = 0.0
                if db_vector and len(db_vector) == len(query_vector):
                    similarity = sum(q * d for q, d in zip(query_vector, db_vector))
                else:
                    # Lexical fallback for this specific row if no embedding is available
                    content_words = set(mem.memory_summary.lower().split())
                    overlap = len(set(query.lower().split()).intersection(content_words))
                    similarity = overlap / max(len(query.lower().split()), 1)
                matches.append((mem, similarity))

            matches.sort(key=lambda x: x[1], reverse=True)
            return [m[0] for m in matches][:limit]
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}", exc_info=True)
            return []

    # --- Reusable aliases matching camelCase requirements ---
    async def analyzeMemoryImportance(
        self, user_message: str, history_context: str = ""
    ) -> Dict[str, Any]:
        return await self.analyze_memory_importance(user_message, history_context)

    async def saveMemory(
        self, db: AsyncSession, user_id: str, memory_summary: str, behavior_patterns: Dict[str, Any]
    ) -> Optional[Memory]:
        return await self.save_memory(db, user_id, memory_summary, behavior_patterns)

    async def retrieveRelevantMemories(
        self, db: AsyncSession, user_id: str, query: str, limit: int = 5
    ) -> List[Memory]:
        return await self.retrieve_relevant_memories(db, user_id, query, limit)


# Export standard singleton instance
memory_service = MemoryService()
