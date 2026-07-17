"""
Database sessions, Declarative Base, and Background Recovery Cache.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.database.engine import engine

logger = logging.getLogger(__name__)

# ── Declarative base ─────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass

# ── Session factory ───────────────────────────────────────────
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Dependency ────────────────────────────────────────────────
async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency that yields an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# ── In-Memory Session Caches for Fallback Resilience ─────────
_history_cache: dict[tuple[str, str], list[dict]] = {}  # key: (user_id, conversation_id)
_profile_cache: dict[str, DeclarativeBase] = {}            # key: user_id (ORM models)
_emotional_profile_cache: dict[str, dict] = {}         # key: user_id (profile dicts)
_memory_cache: dict[str, list] = {}                     # key: user_id

# ── Background Task Writing Queue for Async Recovery ────────
class BackgroundWriteQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self._worker_task = None

    def start_worker(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

    async def add_task(self, func, *args, **kwargs):
        await self.queue.put((func, args, kwargs))
        self.start_worker()

    async def _worker(self):
        logger.info("[BackgroundWriteQueue] Worker started.")
        while True:
            func, args, kwargs = await self.queue.get()
            retries = 3
            success = False
            for attempt in range(retries):
                try:
                    await func(*args, **kwargs)
                    success = True
                    break
                except Exception as e:
                    delay = 2 ** attempt
                    logger.warning(f"[BackgroundWriteQueue] Write task failed (attempt {attempt+1}/{retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
            
            if not success:
                logger.error(f"[BackgroundWriteQueue] Write task failed permanently after {retries} retries.")
            self.queue.task_done()

write_queue = BackgroundWriteQueue()
