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
from app.utils.llm import get_chat_client
from app.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


MEMORY_ANALYZER_SYSTEM_PROMPT = """You are the Memory Extraction Agent for Esona, a mental wellness companion.
Your task is to analyze the user's latest message and extract meaningful emotional or behavioral insights, including relationship entities, goals, exams, jobs, and stress triggers.

We only save memories that represent:
- Personality traits or preferences (e.g. user prefers supportive tone, user studies better at night)
- Emotional state, triggers, or stressors (e.g. user feels stressed before exams, user feels lonely on weekends)
- Burnout indicators or focus/sleep/procrastination routines.
- Key relationship entities mentioned (e.g., "Reshma" (girlfriend/crush), "Mom", "Dad", "best friend", "brother").
- Key upcoming or past events with dates or contexts (e.g., "job interview next Tuesday", "exam on Friday").

Ignore casual small talk, basic greetings, empty statements, or generic messages that contain no personal emotional/behavioral substance (e.g. "hey", "how are you", "tell me a joke", "cool", "whats up").

If the message contains meaningful emotional or behavioral insights:
- Set "is_meaningful" to true.
- Provide a concise "memory_summary" summarizing the key insight.
- Provide "behavior_patterns" as a JSON object containing keys like "trigger", "stress_level" (1-10), "dominant_emotion", "relationship_entities" (list of name strings, e.g. ["Reshma", "Mom"]), and "events" (list of event/date strings, e.g. ["exam on friday"]).

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
    "dominant_emotion": "detected emotion" | null,
    "relationship_entities": ["name1", "name2"] | null,
    "events": ["event description with date"] | null
  } | null
}"""

MEMORY_REFLECTION_PROMPT = """You are the Memory Reflection Agent for Esona.
Your task is to analyze all the user's recorded memories and consolidate them into a single, structured summary of the user's current life context, personality, and concerns.

Consolidate the memories into a clean, bulleted list of facts grouped under:
- What the user is interested in / hobbies.
- Where they are studying or working.
- What they are currently concerned about or working on (e.g. internships, projects).
- What often stresses them out or triggers their anxiety.

Do NOT include specific one-off venting messages unless they represent a pattern. Keep it concise, factual, and direct.
Example format:
User is:
- Interested in AI and coding
- Studying Computer Science at SRM AP
- Concerned about internship placement and GPA
- Often stressed by upcoming exam deadlines and public speaking

Output ONLY the bulleted list.
"""


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

            client = get_chat_client()
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
        self,
        db: AsyncSession,
        user_id: str,
        memory_summary: str,
        behavior_patterns: Dict[str, Any],
        memory_type: Optional[str] = None,
        importance_score: Optional[float] = None,
    ) -> Optional[Memory]:
        """
        Saves a memory to the database and handles embedding generation automatically.
        """
        try:
            import uuid
            # Ensure patterns dict is mutable and sanitized
            patterns = dict(behavior_patterns or {})

            # Extract memory_type and importance_score from patterns or parameters
            resolved_type = memory_type or patterns.pop("memory_type", None)
            resolved_importance = importance_score or patterns.pop("importance_score", None)

            # Map legacy values
            if resolved_importance is None and "importance_level" in patterns:
                resolved_importance = float(patterns.pop("importance_level")) * 2.0  # Scale 1-5 to 1-10
            
            if resolved_type is None:
                if patterns.get("source") == "conversation_summary":
                    resolved_type = "event"
                else:
                    resolved_type = "emotion" # default fallback
            
            if resolved_importance is None:
                resolved_importance = 5.0 # default fallback

            # Generate and embed vector representation of the memory_summary
            embedding = await self.memory_manager._get_embedding(memory_summary)
            if embedding:
                patterns["embedding"] = embedding

            user_uuid = uuid.UUID(str(user_id)) if isinstance(user_id, (str, uuid.UUID)) else user_id

            memory = Memory(
                user_id=user_uuid,
                memory_summary=memory_summary,
                memory_type=resolved_type,
                importance_score=float(resolved_importance),
                behavior_patterns=patterns,
            )
            db.add(memory)
            await db.flush()

            logger.info(f"Memory saved successfully for user {user_id}: '{memory_summary}' [Type: {resolved_type}, Importance: {resolved_importance}]")
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
            query_vector = await self.memory_manager._get_embedding(query)
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

            # Vector similarity search with confidence scoring and decay priority
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
                
                # Apply decay priority and confidence weighting
                patterns = mem.behavior_patterns
                if isinstance(patterns, str):
                    try:
                        import json
                        patterns = json.loads(patterns)
                    except Exception:
                        patterns = {}
                if not isinstance(patterns, dict):
                    patterns = {}
                decay_priority = patterns.get("decay_priority", 3)
                importance = mem.importance_score if mem.importance_score is not None else float(patterns.get("importance_level", 3.0))
                
                # Confidence score is base similarity + importance boost + decay preservation
                # Core memories (decay_priority=5) get a permanent boost
                # Temporary memories (decay_priority=1) lose relevance easily if similarity isn't very high
                boost = (importance * 0.025) + (decay_priority * 0.02)
                final_score = similarity + boost
                
                matches.append((mem, final_score))

            matches.sort(key=lambda x: x[1], reverse=True)
            return [m[0] for m in matches][:limit]
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}", exc_info=True)
            return []

    async def prune_expired_memories(self, db: AsyncSession, user_id: str) -> int:
        """
        Prunes (deletes) expired temporary memories for a user based on importance_score / decay_priority.
        Rules:
        - decay_priority = 1 or importance_score < 4 (very low/temporary): Delete if older than 3 days.
        - decay_priority = 2 or importance_score < 6 (low/medium): Delete if older than 14 days.
        - decay_priority = 3 or importance_score < 8 (medium/high): Delete if older than 30 days.
        - decay_priority >= 4 or importance_score >= 8 (core/permanent): Never delete.
        Returns the number of deleted memories.
        """
        try:
            import uuid
            from datetime import datetime, timezone, timedelta
            user_uuid = uuid.UUID(str(user_id)) if isinstance(user_id, (str, uuid.UUID)) else user_id

            # Retrieve all memories for the user
            result = await db.execute(
                select(Memory).where(Memory.user_id == user_uuid)
            )
            memories = result.scalars().all()
            now = datetime.now(timezone.utc)
            deleted_count = 0

            for mem in memories:
                # Resolve importance and decay priority
                patterns = mem.behavior_patterns
                if isinstance(patterns, str):
                    try:
                        import json
                        patterns = json.loads(patterns)
                    except Exception:
                        patterns = {}
                if not isinstance(patterns, dict):
                    patterns = {}
                imp = mem.importance_score if mem.importance_score is not None else float(patterns.get("importance_level", 5.0))
                decay = patterns.get("decay_priority")
                if decay is None:
                    # Infer decay from importance
                    if imp >= 8:
                        decay = 5
                    elif imp >= 6:
                        decay = 3
                    elif imp >= 4:
                        decay = 2
                    else:
                        decay = 1

                # Calculate age
                age = now - mem.created_at.replace(tzinfo=timezone.utc) if mem.created_at.tzinfo is None else now - mem.created_at

                # Pruning rules
                should_delete = False
                if decay == 1 or imp < 4:
                    if age > timedelta(days=3):
                        should_delete = True
                elif decay == 2 or imp < 6:
                    if age > timedelta(days=14):
                        should_delete = True
                elif decay == 3 or imp < 8:
                    if age > timedelta(days=30):
                        should_delete = True

                if should_delete:
                    await db.delete(mem)
                    deleted_count += 1

            if deleted_count > 0:
                await db.flush()
                logger.info(f"Pruned {deleted_count} expired memories for user {user_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to prune expired memories for user {user_id}: {e}", exc_info=True)
            return 0

    async def reflect_and_consolidate_memories(self, db: AsyncSession, user_id: str) -> Optional[Memory]:
        """
        Gathers all stored memories for a user, calls the LLM to consolidate them into a structured
        reflection summary of their life context, personality, and concerns, deletes any older reflection
        memory, and saves the new one.
        """
        try:
            import uuid
            user_uuid = uuid.UUID(str(user_id)) if isinstance(user_id, (str, uuid.UUID)) else user_id

            # 1. Retrieve all stored memories (excluding previous reflections to avoid self-reinforcing loops)
            result = await db.execute(
                select(Memory).where(
                    Memory.user_id == user_uuid,
                    Memory.memory_type != "reflection"
                )
            )
            memories = result.scalars().all()
            
            # Skip if there are fewer than 5 memories (not enough context to reflect on)
            if len(memories) < 5:
                logger.info(f"Skipping memory reflection for user {user_id}: only {len(memories)} memories present (min 5).")
                return None

            # 2. Format memories for prompt
            formatted_memories = []
            for m in memories:
                formatted_memories.append(f"- {m.memory_summary}")
            memories_text = "\n".join(formatted_memories)

            # 3. Call LLM to consolidate
            client = get_chat_client()
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": MEMORY_REFLECTION_PROMPT},
                    {"role": "user", "content": f"User's memories:\n{memories_text}"}
                ],
                temperature=0.3,
            )
            reflection_content = response.choices[0].message.content.strip()

            if not reflection_content or len(reflection_content) < 10:
                logger.warning(f"Consolidated memory reflection was too short or empty. Skipping.")
                return None

            # 4. Delete existing reflections to keep only the newest one
            delete_res = await db.execute(
                select(Memory).where(
                    Memory.user_id == user_uuid,
                    Memory.memory_type == "reflection"
                )
            )
            old_reflections = delete_res.scalars().all()
            for old in old_reflections:
                await db.delete(old)
            if old_reflections:
                await db.flush()
                logger.info(f"Deleted {len(old_reflections)} older memory reflection(s) for user {user_id}")

            # 5. Save the new reflection summary
            new_reflection = await self.save_memory(
                db=db,
                user_id=str(user_id),
                memory_summary=reflection_content,
                behavior_patterns={"source": "reflection", "decay_priority": 5},
                memory_type="reflection",
                importance_score=9.0
            )
            logger.info(f"Successfully consolidated memories into reflection summary for user {user_id}")
            return new_reflection

        except Exception as e:
            logger.error(f"Failed to consolidate and reflect memories for user {user_id}: {e}", exc_info=True)
            return None

    async def rebuild_memories_from_history(self, db: AsyncSession, user_id: Any) -> List[Memory]:
        """
        Rebuild user memories from past chat messages if user memories are missing.
        """
        import uuid
        user_uuid = uuid.UUID(str(user_id)) if isinstance(user_id, (str, uuid.UUID)) else user_id
        
        REBUILD_MEMORIES_PROMPT = """You are the Memory Recovery Agent for Esona, a mental wellness companion.
Your task is to analyze the user's past chat history with Buddy and reconstruct their lost memories.
Extract meaningful insights about the user's:
1. Personality traits, hobbies, communication style, or preferences (e.g., likes supportive validation, studies computer science).
2. Emotional baseline, patterns, triggers, or stressors (e.g., gets anxious about exams, feels lonely on weekends, recently went through a breakup).
3. Significant life events (e.g., breakup, career change, exam).

Avoid generic small talk. Only extract distinct, factual, and significant memories.

For each memory, extract:
- memory_summary: A concise, direct summary (e.g., "Went through a breakup recently and feels sad").
- memory_type: Must be one of: "personality", "emotion", "event".
- importance_score: A float between 1.0 (low) and 10.0 (high/critical).
- behavior_patterns: A JSON object with fields:
  - trigger: Description of trigger or stressor (or null)
  - stress_level: 1-10 (or null)
  - dominant_emotion: One of: Sadness, Anger, Fear, Anxiety, Happiness, Excitement, Frustration, Loneliness, Neutral (or null)

Format the output strictly as a JSON object containing a list of memories:
{
  "memories": [
    {
      "memory_summary": "...",
      "memory_type": "...",
      "importance_score": 7.5,
      "behavior_patterns": {
        "trigger": "...",
        "stress_level": 5,
        "dominant_emotion": "..."
      }
    }
  ]
}"""

        try:
            from app.models.conversation import Message
            # 1. Fetch all messages for the user
            stmt = select(Message).where(Message.user_id == user_uuid).order_by(Message.created_at.asc())
            res = await db.execute(stmt)
            messages = res.scalars().all()
            
            if not messages:
                logger.info(f"No chat history found for user {user_id} to rebuild memories.")
                return []
                
            # Format history (take at most last 100 messages)
            recent_messages = messages[-100:]
            history_lines = []
            for m in recent_messages:
                role_name = "User" if m.role == "user" or m.role.value == "user" else "Buddy"
                history_lines.append(f"{role_name}: {m.content}")
            history_text = "\n".join(history_lines)
            
            # 2. Call LLM to extract memories in bulk
            client = get_chat_client()
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": REBUILD_MEMORIES_PROMPT},
                    {"role": "user", "content": f"User's past chat history:\n{history_text}"}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
            extracted_memories = data.get("memories", [])
            
            saved_memories = []
            for mem_data in extracted_memories:
                summary = mem_data.get("memory_summary")
                if not summary:
                    continue
                patterns = mem_data.get("behavior_patterns", {}) or {}
                m_type = mem_data.get("memory_type", "emotion")
                imp = mem_data.get("importance_score", 5.0)
                
                saved = await self.save_memory(
                    db=db,
                    user_id=str(user_uuid),
                    memory_summary=summary,
                    behavior_patterns=patterns,
                    memory_type=m_type,
                    importance_score=float(imp)
                )
                if saved:
                    saved_memories.append(saved)
            
            if saved_memories:
                await db.flush()
                logger.info(f"Rebuilt and saved {len(saved_memories)} memories from chat history for user {user_id}")
            return saved_memories
        except Exception as e:
            logger.error(f"Failed to rebuild memories from chat history: {e}", exc_info=True)
            return []

    async def rebuildMemoriesFromHistory(self, db: AsyncSession, user_id: Any) -> List[Memory]:
        return await self.rebuild_memories_from_history(db, user_id)

    # --- Reusable aliases matching camelCase requirements ---
    async def analyzeMemoryImportance(
        self, user_message: str, history_context: str = ""
    ) -> Dict[str, Any]:
        return await self.analyze_memory_importance(user_message, history_context)

    async def saveMemory(
        self,
        db: AsyncSession,
        user_id: str,
        memory_summary: str,
        behavior_patterns: Dict[str, Any],
        memory_type: Optional[str] = None,
        importance_score: Optional[float] = None,
    ) -> Optional[Memory]:
        return await self.save_memory(
            db, user_id, memory_summary, behavior_patterns, memory_type, importance_score
        )

    async def retrieveRelevantMemories(
        self, db: AsyncSession, user_id: str, query: str, limit: int = 5
    ) -> List[Memory]:
        return await self.retrieve_relevant_memories(db, user_id, query, limit)


# Export standard singleton instance
memory_service = MemoryService()
