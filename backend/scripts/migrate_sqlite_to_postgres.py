import asyncio
import argparse
import logging
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Add the parent directory to sys.path so we can import from app
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
# Import all models to ensure they are registered with Base
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

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def migrate(sqlite_url: str, pg_url: str, dry_run: bool):
    logger.info(f"Starting migration.")
    logger.info(f"Source (SQLite): {sqlite_url}")
    logger.info(f"Target (Postgres): {pg_url}")
    logger.info(f"Dry Run Mode: {'ENABLED' if dry_run else 'DISABLED'}")

    # Create engines
    sqlite_engine = create_async_engine(sqlite_url, echo=False)
    
    # Postgres engine needs to support the Supabase pooler
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    pg_engine = create_async_engine(
        pg_url,
        connect_args={
            "prepared_statement_cache_size": 0,
            "ssl": ctx
        },
        pool_pre_ping=True,
        echo=False
    )

    try:
        # We need to create tables in Postgres if they don't exist
        if not dry_run:
            logger.info("Ensuring all tables exist in target PostgreSQL database...")
            async with pg_engine.begin() as pg_conn:
                await pg_conn.run_sync(Base.metadata.create_all)
            logger.info("Target tables ready.")

        # Tables are automatically sorted in dependency order by SQLAlchemy
        # meaning parent tables (like users) come before child tables (like conversations)
        tables = Base.metadata.sorted_tables
        
        async with sqlite_engine.connect() as sqlite_conn:
            async with pg_engine.begin() as pg_conn: # Use a transaction for Postgres
                for table in tables:
                    logger.info(f"--- Migrating table: {table.name} ---")
                    
                    # Fetch all rows from SQLite
                    result = await sqlite_conn.execute(table.select())
                    rows = result.mappings().all()
                    
                    if not rows:
                        logger.info(f"0 rows found in SQLite for {table.name}. Skipping.")
                        continue
                        
                    logger.info(f"Found {len(rows)} rows to migrate.")
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would insert {len(rows)} rows into {table.name}.")
                        continue
                    
                    # Convert mappings to dicts
                    insert_data = [dict(row) for row in rows]
                    
                    # Insert into Postgres using ON CONFLICT DO NOTHING
                    # We need the primary key columns to define the conflict target
                    primary_keys = [key.name for key in table.primary_key]
                    
                    if not primary_keys:
                        logger.warning(f"Table {table.name} has no primary key! Falling back to standard insert (may cause duplicates if re-run).")
                        stmt = table.insert().values(insert_data)
                    else:
                        stmt = pg_insert(table).values(insert_data)
                        stmt = stmt.on_conflict_do_nothing(index_elements=primary_keys)
                    
                    # Execute the insert
                    res = await pg_conn.execute(stmt)
                    logger.info(f"Successfully migrated data for {table.name}. Rows affected: {res.rowcount}")

        if dry_run:
            logger.info("Dry run completed. No data was written to PostgreSQL.")
        else:
            logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        await sqlite_engine.dispose()
        await pg_engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate data from SQLite to PostgreSQL")
    parser.add_argument("--sqlite-url", type=str, default="sqlite+aiosqlite:///./esona.db",
                        help="SQLite database URL (default: sqlite+aiosqlite:///./esona.db)")
    parser.add_argument("--pg-url", type=str, required=True,
                        help="PostgreSQL database URL (e.g., postgresql+asyncpg://...)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Perform a dry run without actually inserting data")
    
    args = parser.parse_args()
    
    asyncio.run(migrate(args.sqlite_url, args.pg_url, args.dry_run))
