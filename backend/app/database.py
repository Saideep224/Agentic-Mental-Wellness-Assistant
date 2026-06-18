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
else:
    # SQLite parameters for concurrent write resiliency
    connect_args["timeout"] = 30

# ── Engine ────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

# ── SQLite WAL Mode & Synchronous Normal setup ────────────────
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if not settings.is_postgres:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
        except Exception as e:
            logger.warning(f"Failed to set SQLite PRAGMA journal_mode/synchronous: {e}")
        finally:
            cursor.close()

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
    """Create all tables (used during app startup / dev) and run migrations.
    
    IMPORTANT: create_all uses checkfirst=True semantics — it NEVER drops existing tables.
    Only new tables and columns are added. Existing data is always preserved.
    """
    # Import all models to ensure they are registered with Base before running create_all
    from app.models import (
        User,
        Conversation,
        Message,
        UserProfile,
        UserPersonalProfile,
        UserAnswer,
        Memory,
        MoodLog,
        EmotionLog,
        KnowledgeGraphRelation,
        UserEntity,
        UserRelationship,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            if settings.is_postgres:
                # ── V1 columns ──────────────────────────────────────────────
                await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS emotion_score double precision;"))
                await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS stress_score double precision;"))
                await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS anxiety_score double precision;"))
                await conn.execute(text("ALTER TABLE user_profile ADD COLUMN IF NOT EXISTS university text;"))
                # ── V2 columns ──────────────────────────────────────────────
                await conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS agent_id text DEFAULT 'buddy';"))
                await conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS active_specialists jsonb DEFAULT '[]';"))
                await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS sender_type text DEFAULT 'user';"))
                # ── V2.1 mood / emotion columns ─────────────────────────────
                await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS mood_score double precision;"))
                await conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS detected_emotion text;"))
                # ── emotion_logs table columns ─────────────────────────────
                await conn.execute(text("ALTER TABLE emotion_logs ADD COLUMN IF NOT EXISTS confidence_score double precision;"))
                await conn.execute(text("ALTER TABLE emotion_logs ADD COLUMN IF NOT EXISTS secondary_emotion text;"))
                # ── memories table columns ─────────────────────────────────
                await conn.execute(text("ALTER TABLE memories ADD COLUMN IF NOT EXISTS metadata_json jsonb DEFAULT '{}';"))
                await conn.execute(text("ALTER TABLE memories ADD COLUMN IF NOT EXISTS importance_score double precision DEFAULT 0.5;"))
                await conn.execute(text("ALTER TABLE memories ADD COLUMN IF NOT EXISTS expires_at timestamp with time zone;"))
                # ── knowledge_graph_relations columns ─────────────────────
                await conn.execute(text("ALTER TABLE knowledge_graph_relations ADD COLUMN IF NOT EXISTS confidence double precision DEFAULT 1.0;"))
                # ── user_personal_profiles columns ────────────────────────
                await conn.execute(text("ALTER TABLE user_personal_profiles ADD COLUMN IF NOT EXISTS personality_json jsonb DEFAULT '{}';"))
                await conn.execute(text("ALTER TABLE user_personal_profiles ADD COLUMN IF NOT EXISTS last_analyzed_at timestamp with time zone;"))
            else:
                # SQLite: try/except each individually since SQLite doesn't support IF NOT EXISTS for columns
                _sqlite_add_cols = [
                    ("chat_messages", "emotion_score", "FLOAT"),
                    ("chat_messages", "stress_score", "FLOAT"),
                    ("chat_messages", "anxiety_score", "FLOAT"),
                    ("chat_messages", "mood_score", "FLOAT"),
                    ("chat_messages", "detected_emotion", "VARCHAR(100)"),
                    ("chat_messages", "sender_type", "VARCHAR(50) DEFAULT 'user'"),
                    ("user_profile", "university", "VARCHAR(255)"),
                    ("conversations", "agent_id", "VARCHAR(50) DEFAULT 'buddy'"),
                    ("conversations", "active_specialists", "JSON DEFAULT '[]'"),
                    ("emotion_logs", "confidence_score", "FLOAT"),
                    ("emotion_logs", "secondary_emotion", "VARCHAR(100)"),
                    ("memories", "metadata_json", "JSON DEFAULT '{}'"),
                    ("memories", "importance_score", "FLOAT DEFAULT 0.5"),
                    ("memories", "expires_at", "DATETIME"),
                    ("knowledge_graph_relations", "confidence", "FLOAT DEFAULT 1.0"),
                    ("user_personal_profiles", "personality_json", "JSON DEFAULT '{}'"),
                    ("user_personal_profiles", "last_analyzed_at", "DATETIME"),
                ]
                for table, col, col_type in _sqlite_add_cols:
                    try:
                        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"))
                    except Exception:
                        pass  # Column already exists — safe to ignore
        logger.info("[Migration] Database columns checked/added successfully. All user data preserved.")
    except Exception as migration_err:
        logger.error(f"[Migration Warning] Failed to run database alter migrations: {migration_err}")


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

