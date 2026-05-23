"""
Memory Manager – implements vector storage and semantic search using
SQLite and OpenAI embeddings, replacing ChromaDB to avoid MSVC compiler dependency.
"""

import json
import os
import sqlite3
import uuid
import logging
from datetime import datetime, timezone, timedelta
from collections import Counter
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Path to the SQLite memory database
DB_PATH = os.path.join(settings.CHROMA_PERSIST_DIR, "memories.db")


def init_db():
    """Ensure the memories directory and SQLite table exist."""
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT NOT NULL,
            embedding TEXT,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


class MemoryManager:
    """
    Manages user emotional memories. Stores texts and metadata, and performs
    semantic vector search using OpenAI embeddings and SQLite.
    """

    def __init__(self) -> None:
        init_db()
        self.openai_client = None
        if settings.llm_api_key:
            try:
                self.openai_client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client for MemoryManager: {e}")

    def _get_embedding(self, text: str) -> list[float] | None:
        """Fetch OpenAI vector embedding for text."""
        if not self.openai_client:
            return None
        try:
            response = self.openai_client.embeddings.create(
                input=[text],
                model=settings.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return None

    def store_memory(
        self,
        user_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> str:
        """Store a new emotional memory with vector embedding."""
        doc_id = str(uuid.uuid4())
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
        embedding_list = self._get_embedding(content)
        embedding_str = json.dumps(embedding_list) if embedding_list else None

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memories (id, user_id, content, metadata, embedding, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                doc_id,
                user_id,
                content,
                json.dumps(sanitized_meta),
                embedding_str,
                sanitized_meta["timestamp"]
            )
        )
        conn.commit()
        conn.close()
        logger.debug("Stored memory %s for user %s", doc_id, user_id)
        return doc_id

    def retrieve_memories(
        self,
        user_id: str,
        query: str,
        n_results: int = 5,
    ) -> list[dict]:
        """Retrieve most semantically similar memories using cosine similarity."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content, metadata, embedding, timestamp FROM memories WHERE user_id = ?",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return []

        # If we have an OpenAI client, try vector similarity
        query_vector = self._get_embedding(query)
        
        memories = []
        for r_id, content, metadata_str, embedding_str, timestamp in rows:
            meta = json.loads(metadata_str)
            
            similarity = 0.0
            if query_vector and embedding_str:
                try:
                    db_vector = json.loads(embedding_str)
                    if db_vector and len(db_vector) == len(query_vector):
                        # Cosine similarity (since OpenAI embeddings are normalized to length 1, dot product is cosine similarity)
                        similarity = sum(q * d for q, d in zip(query_vector, db_vector))
                except Exception as e:
                    logger.warning(f"Error calculating similarity: {e}")
            else:
                # Fallback lexical overlap if no embedding
                query_words = set(query.lower().split())
                content_words = set(content.lower().split())
                overlap = len(query_words.intersection(content_words))
                similarity = overlap / max(len(query_words), 1)

            memories.append({
                "content": content,
                "metadata": meta,
                "distance": float(round(1.0 - similarity, 4))  # Convert similarity to distance
            })

        # Sort by distance (smaller distance = higher similarity)
        memories.sort(key=lambda x: x["distance"])
        return memories[:n_results]

    def get_emotional_patterns(self, user_id: str) -> dict:
        """Aggregate all stored memories to extract recurring emotional patterns."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM memories WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "emotion_counts": {},
                "dominant_emotion": "neutral",
                "common_triggers": [],
                "average_stress": 0.3,
            }

        emotions = []
        stress_levels = []
        triggers = []

        for (metadata_str,) in rows:
            try:
                meta = json.loads(metadata_str)
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

    def get_mood_history(self, user_id: str, days: int = 30) -> list[dict]:
        """Return chronological daily mood scores from memories."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT metadata, timestamp FROM memories WHERE user_id = ? AND timestamp >= ? ORDER BY timestamp ASC",
            (user_id, cutoff)
        )
        rows = cursor.fetchall()
        conn.close()

        history = []
        for metadata_str, timestamp in rows:
            try:
                meta = json.loads(metadata_str)
                try:
                    mood = float(meta.get("mood_score", 0.5))
                except (ValueError, TypeError):
                    mood = 0.5
                history.append({
                    "date": timestamp[:10],
                    "mood_score": mood,
                    "emotion": meta.get("emotion", "neutral"),
                })
            except Exception:
                pass

        return history
