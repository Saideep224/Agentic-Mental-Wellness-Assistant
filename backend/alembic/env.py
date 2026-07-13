"""
Alembic async environment configuration.

Uses the application's single authoritative async engine so migrations and the
FastAPI runtime share the exact same Supabase/PgBouncer compatibility settings.
"""

import asyncio
from logging.config import fileConfig

from alembic import context

from app.config import settings
from app.database import Base, engine

# Import all models so metadata is populated.
from app.models import user, conversation, user_profile, onboarding  # noqa: F401

# ── Alembic Config object ────────────────────────────────────────────────────
config = context.config

# Keep the configured URL available for offline SQL generation. Online
# migrations intentionally reuse app.database.engine instead of constructing a
# second engine that can silently omit PgBouncer/asyncpg connection arguments.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode without opening a database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Configure Alembic and execute migrations on an existing connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run online migrations through the application's configured async engine."""
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)

    # Alembic is a short-lived process on Render. Dispose the NullPool-backed
    # engine explicitly so the asyncpg connection is closed before Uvicorn
    # starts its own process and imports the application.
    await engine.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Alembic normally runs synchronously, but tests may invoke this module
        # while an event loop is active.
        import threading

        error: list[BaseException] = []

        def run_in_thread() -> None:
            try:
                asyncio.run(run_async_migrations())
            except BaseException as exc:  # propagate migration failures
                error.append(exc)

        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()
        if error:
            raise error[0]
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
