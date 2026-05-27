"""
Memory Manager – implements vector storage and semantic search using
SQLAlchemy (PostgreSQL/SQLite) and OpenAI embeddings.
Uses async sessions so it works with both local SQLite and Supabase PostgreSQL.
"""

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from collections import Counter

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.memory import Memory
from app.utils.llm import get_embedding_client

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages user emotional memories. Stores texts and metadata, and performs
    semantic vector search using OpenAI embeddings and SQLAlchemy.
    """

    def __init__(self) -> None:
        pass

    async def _get_embedding(self, text: str) -> list[float] | None:
        """Fetch OpenAI vector embedding for text asynchronously."""
        if settings.USE_UNCLOSEAI:
            return None
        try:
            client = get_embedding_client()
            response = await client.embeddings.create(
                input=[text],
                model=settings.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return None

    async def store_memory(
        self,
        db: AsyncSession,
        user_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> str:
        """Store a new emotional memory with optional vector embedding."""
        meta = {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }

        # Clean metadata values
        sanitized_meta = {}
        for k, v in meta.items():
            if isinstance(v, (str, int, float, bool)):
                sanitized_meta[k] = v
            else:
                sanitized_meta[k] = str(v)

        # Generate embedding
        embedding_list = await self._get_embedding(content)
        embedding_data = embedding_list if embedding_list else None

        memory = Memory(
            user_id=user_id,
            content=content,
            metadata_json=sanitized_meta,
            embedding_json=embedding_data,
        )
        db.add(memory)
        await db.flush()

        logger.debug("Stored memory %s for user %s", memory.id, user_id)
        return str(memory.id)

    async def retrieve_memories(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        n_results: int = 5,
    ) -> list[dict]:
        """Retrieve most semantically similar memories using cosine similarity."""
        result = await db.execute(
            select(Memory).where(Memory.user_id == user_id)
        )
        rows = result.scalars().all()

        if not rows:
            return []

        # If we have an OpenAI client, try vector similarity
        query_vector = await self._get_embedding(query)

        memories = []
        for mem in rows:
            meta = mem.metadata_json or {}

            similarity = 0.0
            if query_vector and mem.embedding_json:
                try:
                    db_vector = mem.embedding_json
                    if isinstance(db_vector, list) and len(db_vector) == len(query_vector):
                        # Cosine similarity (dot product for normalized embeddings)
                        similarity = sum(q * d for q, d in zip(query_vector, db_vector))
                except Exception as e:
                    logger.warning(f"Error calculating similarity: {e}")
            else:
                # Fallback lexical overlap if no embedding
                query_words = set(query.lower().split())
                content_words = set(mem.content.lower().split())
                overlap = len(query_words.intersection(content_words))
                similarity = overlap / max(len(query_words), 1)

            memories.append({
                "content": mem.content,
                "metadata": meta,
                "distance": float(round(1.0 - similarity, 4))
            })

        # Sort by distance (smaller = more similar)
        memories.sort(key=lambda x: x["distance"])
        return memories[:n_results]

    async def get_emotional_patterns(self, db: AsyncSession, user_id: str) -> dict:
        """Aggregate all stored memories to extract recurring emotional patterns."""
        result = await db.execute(
            select(Memory).where(Memory.user_id == user_id)
        )
        memories = result.scalars().all()

        if not memories:
            return {
                "emotion_counts": {},
                "dominant_emotion": "neutral",
                "common_triggers": [],
                "average_stress": 0.3,
            }

        emotions = []
        stress_levels = []
        triggers = []

        for mem in memories:
            meta = mem.metadata_json
            if not meta:
                continue
            try:
                if meta.get("emotion"):
                    emotions.append(str(meta["emotion"]))
                if meta.get("stress_level"):
                    try:
                        stress_levels.append(float(meta["stress_level"]))
                    except (ValueError, TypeError):
                        pass
                if meta.get("message_type") == "emotional" or meta.get("source") == "conversation":
                    triggers.append(str(meta.get("emotion", "unknown")))
            except Exception:
                pass

        emotion_counter = Counter(emotions)
        dominant = emotion_counter.most_common(1)[0][0] if emotion_counter else "neutral"
        avg_stress = sum(stress_levels) / len(stress_levels) if stress_levels else 0.3

        trigger_counter = Counter(triggers)
        common_triggers = [t for t, _ in trigger_counter.most_common(5)]

        return {
            "emotion_counts": dict(emotion_counter),
            "dominant_emotion": dominant,
            "common_triggers": common_triggers if common_triggers else ["work", "sleep", "relationships"],
            "average_stress": round(avg_stress, 2),
        }

    async def get_mood_history(self, db: AsyncSession, user_id: str, days: int = 30) -> list[dict]:
        """Return chronological daily mood scores from memories."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await db.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.created_at >= cutoff)
            .order_by(Memory.created_at.asc())
        )
        rows = result.scalars().all()

        history = []
        for mem in rows:
            try:
                meta = mem.metadata_json or {}
                try:
                    mood = float(meta.get("mood_score", 0.5))
                except (ValueError, TypeError):
                    mood = 0.5
                history.append({
                    "date": mem.created_at.strftime("%Y-%m-%d") if mem.created_at else "",
                    "mood_score": mood,
                    "emotion": meta.get("emotion", "neutral"),
                })
            except Exception:
                pass

        return history
