import asyncio
import logging
import uuid
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class SafeUUID(TypeDecorator):
    """
    A platform-independent UUID type.
    Uses PostgreSQL's UUID type when on PostgreSQL,
    otherwise uses CHAR(36) for SQLite.
    
    Accepts string UUIDs or uuid.UUID objects transparently.
    Always returns uuid.UUID objects to the application for consistency.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        
        # Normalize to uuid.UUID object if postgresql, or string if SQLite
        if dialect.name == 'postgresql':
            if isinstance(value, uuid.UUID):
                return value
            try:
                return uuid.UUID(str(value))
            except ValueError:
                return None
        else:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except ValueError:
            return value


# ── Build connect_args based on database type ────────────────
connect_args: dict = {}
engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}

if settings.is_postgres:
    # Supabase PostgreSQL via transaction pooler (port 6543)
    # prepared_statement_cache_size=0 is REQUIRED for Supabase pooler
    # ssl=True is REQUIRED for Supabase cloud connections
    connect_args["prepared_statement_cache_size"] = 0
    connect_args["ssl"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

# ── Engine ────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

# ── Session factory ───────────────────────────────────────────
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative base ─────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


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


async def create_tables() -> None:
    """Create all tables (used during app startup / dev)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── In-Memory Session Caches for Fallback Resilience ─────────
_history_cache: dict[tuple[str, str], list[dict]] = {}  # key: (user_id, conversation_id)
_profile_cache: dict[str, dict] = {}                   # key: user_id
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

