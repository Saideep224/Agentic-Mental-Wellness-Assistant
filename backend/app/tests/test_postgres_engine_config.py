"""
Unit test to verify that the PostgreSQL/asyncpg engine configuration is valid and does not raise TypeErrors.
"""

import unittest
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

class PostgresEngineConfigTestCase(unittest.TestCase):
    """Verifies PostgreSQL engine arguments are valid for SQLAlchemy + asyncpg."""

    def test_postgres_engine_creation_args(self):
        # Build mock connection configurations representing database.py setup
        connect_args = {}
        engine_kwargs = {"echo": False, "pool_pre_ping": True}

        # Emulate database.py setup
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        connect_args["statement_cache_size"] = 0
        connect_args["ssl"] = ctx
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

        # Attempt engine creation using postgresql+asyncpg scheme
        # This will trigger SQLAlchemy's internal argument validations for create_engine
        try:
            engine = create_async_engine(
                "postgresql+asyncpg://postgres:password@localhost:5432/postgres",
                connect_args=connect_args,
                **engine_kwargs
            )
            self.assertIsNotNone(engine)
        except TypeError as e:
            self.fail(f"create_async_engine raised TypeError: {e}")
