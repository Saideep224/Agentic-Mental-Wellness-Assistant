"""
Database engine creation and connection pooling configuration.
Disables caching and sets NullPool for PgBouncer / Supabase transaction pooling.
"""

import logging
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import event

from app.config import settings

logger = logging.getLogger(__name__)

# ── Build connect_args and database URL based on database type ────────────────
connect_args: dict = {}
engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
engine_database_url = settings.DATABASE_URL

if settings.is_postgres:
    # Supabase PostgreSQL via transaction pooler (port 6543)
    # ssl context that disables verification (to allow self-signed certificates and dev connections)
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # 1. Disable driver-level prepared statement caching in asyncpg
    connect_args["statement_cache_size"] = 0
    connect_args["ssl"] = ctx
    
    # 2. Use globally unique names for prepared statements to prevent PgBouncer conflicts
    connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid.uuid4()}__"
    
    # 3. Use NullPool to completely disable local pooling, delegating connection management to PgBouncer
    engine_kwargs["poolclass"] = NullPool
    
    # 4. Disable SQLAlchemy asyncpg dialect caching by appending query param to the URL
    if "prepared_statement_cache_size=" not in engine_database_url:
        separator = "&" if "?" in engine_database_url else "?"
        engine_database_url = (
            f"{engine_database_url}"
            f"{separator}prepared_statement_cache_size=0"
        )
    logger.info("[DB] PostgreSQL asyncpg prepared statement cache disabled via query params")
    logger.info("[DB] PostgreSQL prepared_statement_name_func enabled (UUID naming)")
    logger.info("[DB] asyncpg statement cache disabled")
    logger.info("[DB] Supabase transaction pooler compatibility enabled (NullPool)")
else:
    # SQLite parameters for concurrent write resiliency
    connect_args["timeout"] = 30

# ── Create the Engine ────────────────────────────────────────────────────
engine = create_async_engine(
    engine_database_url,
    connect_args=connect_args,
    **engine_kwargs,
)

# ── SQLite WAL Mode & Synchronous Normal setup ────────────────
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
