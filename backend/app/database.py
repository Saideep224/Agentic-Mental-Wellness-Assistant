"""
Async SQLAlchemy engine and session factory.
Supports both SQLite (local dev) and PostgreSQL (Supabase production).
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

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
