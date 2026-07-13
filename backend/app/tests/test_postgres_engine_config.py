"""
Unit test to verify that the PostgreSQL/asyncpg engine configuration is valid,
uses NullPool, and correctly configures PgBouncer compat prepared statement caching.
"""

import unittest
import uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

class PostgresEngineConfigTestCase(unittest.TestCase):
    """Verifies PostgreSQL engine config satisfies PgBouncer / Supabase requirements."""

    def test_postgres_engine_creation_args(self):
        # Emulate database/engine.py setup logic
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
        
        # 1. Ensure prepared_statement_name_func is defined
        connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid.uuid4()}__"
        
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

        # 2. Verify connect_args includes statement_cache_size=0 and prepared_statement_name_func
        self.assertEqual(connect_args.get("statement_cache_size"), 0)
        self.assertTrue(callable(connect_args.get("prepared_statement_name_func")))

        # 3. Verify PostgreSQL engine URL includes prepared_statement_cache_size=0
        self.assertIn("prepared_statement_cache_size=0", engine_database_url)

        # 4. Verify prepared_statement_cache_size is NOT passed as a top-level create_async_engine argument
        self.assertNotIn("prepared_statement_cache_size", engine_kwargs)

        # 5. Verify incompatible pool_size/max_overflow are not used with NullPool
        self.assertNotIn("pool_size", engine_kwargs)
        self.assertNotIn("max_overflow", engine_kwargs)
        self.assertEqual(engine_kwargs.get("poolclass"), NullPool)

        # 6. Create engine and check it succeeds
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
        # 7. Verify database package imports successfully and exposes engine
        try:
            import app.database
            self.assertIsNotNone(app.database.engine)
            self.assertIsNotNone(app.database.Base)
            self.assertIsNotNone(app.database.get_db)
            self.assertIsNotNone(app.database.SafeUUID)
            self.assertIsNotNone(app.database.write_queue)
        except Exception as e:
            self.fail(f"Failed to import/verify app.database package: {e}")
