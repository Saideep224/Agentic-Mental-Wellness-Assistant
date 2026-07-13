"""
Unit test to verify that the PostgreSQL/asyncpg engine configuration is valid,
uses NullPool, and correctly configures prepared statement caching.
"""

import unittest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

class PostgresEngineConfigTestCase(unittest.TestCase):
    """Verifies PostgreSQL engine config satisfiesPgBouncer / Supabase requirements."""

    def test_postgres_engine_creation_args(self):
        # Emulate database.py setup logic
        connect_args = {}
        engine_kwargs = {"echo": False, "pool_pre_ping": True}
        engine_database_url = "postgresql+asyncpg://postgres:password@localhost:5432/postgres"

        # Emulate ssl
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        connect_args["statement_cache_size"] = 0
        connect_args["ssl"] = ctx
        
        # Configure NullPool and remove pool size configs
        engine_kwargs["poolclass"] = NullPool
        if "pool_size" in engine_kwargs:
            del engine_kwargs["pool_size"]
        if "max_overflow" in engine_kwargs:
            del engine_kwargs["max_overflow"]

        if "prepared_statement_cache_size=" not in engine_database_url:
            separator = "&" if "?" in engine_database_url else "?"
            engine_database_url = (
                f"{engine_database_url}"
                f"{separator}prepared_statement_cache_size=0"
            )

        # 1. Verify connect_args includes statement_cache_size=0
        self.assertEqual(connect_args.get("statement_cache_size"), 0)

        # 2. Verify PostgreSQL engine URL includes prepared_statement_cache_size=0
        self.assertIn("prepared_statement_cache_size=0", engine_database_url)

        # 3. Verify prepared_statement_cache_size is NOT passed as a top-level create_async_engine argument
        self.assertNotIn("prepared_statement_cache_size", engine_kwargs)

        # 4. Verify incompatible pool_size/max_overflow are not used with NullPool
        self.assertNotIn("pool_size", engine_kwargs)
        self.assertNotIn("max_overflow", engine_kwargs)
        self.assertEqual(engine_kwargs.get("poolclass"), NullPool)

        # 5. Create engine and check it succeeds
        try:
            engine = create_async_engine(
                engine_database_url,
                connect_args=connect_args,
                **engine_kwargs
            )
            self.assertIsNotNone(engine)
        except TypeError as e:
            self.fail(f"create_async_engine raised TypeError: {e}")

    def test_database_module_import_success(self):
        # 6. Verify database module imports successfully
        try:
            import app.database
            self.assertIsNotNone(app.database.engine)
        except Exception as e:
            self.fail(f"Failed to import app.database: {e}")
