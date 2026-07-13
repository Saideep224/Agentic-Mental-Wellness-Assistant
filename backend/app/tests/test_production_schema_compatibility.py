"""
Integration test for legacy Supabase PostgreSQL/SQLite schema compatibility.
Simulates a database with a legacy `chat_messages` table (containing `detected_emotion` but not `emotion`).
Runs the migration/startup routine and verifies that it is safely upgraded without data loss.
"""

import os
import uuid
import unittest
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from sqlalchemy.pool import NullPool

# Mock settings database URL before importing app modules
import app.config
# Force SQLite URL for testing
test_db_filename = f"./test_compat_{uuid.uuid4().hex}.db"
app.config.settings.DATABASE_URL = f"sqlite+aiosqlite:///{test_db_filename}"

from app.database import Base
from app.models import User, Conversation, Message

class ProductionSchemaCompatibilityTestCase(unittest.IsolatedAsyncioTestCase):
    """Verifies that the Esona database upgrade migrates legacy schemas and preserves data."""

    async def asyncSetUp(self):
        self.db_filename = test_db_filename
        self.test_db_url = f"sqlite+aiosqlite:///{self.db_filename}"
        
        # 1. Create engine and manually build legacy table structure (without 'emotion')
        self.engine = create_async_engine(self.test_db_url, echo=False, poolclass=NullPool)
        
        # Patch the global engine in app.database
        import app.database
        self._orig_engine = app.database.engine
        app.database.engine = self.engine
        
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        async with self.engine.begin() as conn:
            # Create user profiles table
            await conn.execute(text("""
                CREATE TABLE profiles (
                    user_id CHAR(36) PRIMARY KEY,
                    id CHAR(36) UNIQUE,
                    email VARCHAR(320) UNIQUE,
                    full_name VARCHAR(255) NOT NULL,
                    avatar_url VARCHAR(1024),
                    provider VARCHAR(50) NOT NULL,
                    github_username VARCHAR(255),
                    onboarding_completed BOOLEAN NOT NULL,
                    onboarding_step INTEGER,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    last_login TIMESTAMP
                );
            """))
            # Create conversations table
            await conn.execute(text("""
                CREATE TABLE conversations (
                    id CHAR(36) PRIMARY KEY,
                    user_id CHAR(36) NOT NULL,
                    title VARCHAR(512),
                    agent_id VARCHAR(50) NOT NULL,
                    active_specialists TEXT,
                    emotional_tag VARCHAR(255),
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES profiles(user_id) ON DELETE CASCADE
                );
            """))
            # Create legacy chat_messages containing detected_emotion but NOT emotion
            await conn.execute(text("""
                CREATE TABLE chat_messages (
                    id CHAR(36) PRIMARY KEY,
                    conversation_id CHAR(36) NOT NULL,
                    user_id CHAR(36) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    message TEXT NOT NULL,
                    detected_emotion VARCHAR(100),
                    mood_score FLOAT,
                    created_at TIMESTAMP,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    FOREIGN KEY(user_id) REFERENCES profiles(user_id) ON DELETE CASCADE
                );
            """))

        self.db = self.session_maker()

        # 2. Insert mock legacy data
        self.user_id = uuid.uuid4()
        self.conv_id = uuid.uuid4()
        self.msg_id1 = uuid.uuid4()
        self.msg_id2 = uuid.uuid4()

        # Insert User Profile
        await self.db.execute(text("""
            INSERT INTO profiles (user_id, id, email, full_name, provider, onboarding_completed)
            VALUES (:user_id, :profile_id, 'alice@esona.com', 'Alice', 'credentials', 1);
        """), {
            "user_id": str(self.user_id),
            "profile_id": str(self.user_id),
        })

        # Insert Conversation
        await self.db.execute(text("""
            INSERT INTO conversations (id, user_id, title, agent_id)
            VALUES (:conv_id, :user_id, 'Legacy Chat', 'buddy');
        """), {
            "conv_id": str(self.conv_id),
            "user_id": str(self.user_id),
        })

        # Insert Legacy chat messages (using detected_emotion column)
        await self.db.execute(text("""
            INSERT INTO chat_messages (id, conversation_id, user_id, role, message, detected_emotion, mood_score)
            VALUES (:msg_id, :conv_id, :user_id, 'assistant', 'I am here for you.', 'Sadness', 0.2);
        """), {
            "msg_id": str(self.msg_id1),
            "conv_id": str(self.conv_id),
            "user_id": str(self.user_id),
        })
        
        await self.db.execute(text("""
            INSERT INTO chat_messages (id, conversation_id, user_id, role, message, detected_emotion, mood_score)
            VALUES (:msg_id, :conv_id, :user_id, 'assistant', 'How has your day been?', 'Neutral', 0.5);
        """), {
            "msg_id": str(self.msg_id2),
            "conv_id": str(self.conv_id),
            "user_id": str(self.user_id),
        })

        await self.db.commit()

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()
        
        # Restore the original global engine
        import app.database
        app.database.engine = self._orig_engine
        
        # Clean up database file
        if os.path.exists(self.db_filename):
            try:
                os.remove(self.db_filename)
            except Exception:
                pass

    async def test_migration_upgrades_legacy_schema_and_backfills(self):
        """Verify that the upgrade migration adds the 'emotion' column and backfills historical data."""
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")

        # 2. Verify column existence in SQLite table info
        async with self.engine.connect() as conn:
            res = await conn.execute(text("PRAGMA table_info(chat_messages);"))
            columns = [row[1] for row in res.fetchall()]
            self.assertIn("emotion", columns)
            self.assertIn("detected_emotion", columns)

        # 3. Verify backfill of historical values
        # Open fresh session and query via Message ORM model
        async with self.session_maker() as session:
            result = await session.execute(
                select(Message).order_by(Message.created_at.asc())
            )
            messages = result.scalars().all()
            
            self.assertEqual(len(messages), 2)
            # The values from 'detected_emotion' must now be present in 'emotion'
            self.assertEqual(messages[0].emotion, "Sadness")
            self.assertEqual(messages[0].emotion_detected, "Sadness")  # via property getter
            
            self.assertEqual(messages[1].emotion, "Neutral")
            self.assertEqual(messages[1].emotion_detected, "Neutral")

            # 4. Verify that we can write new messages using the upgraded ORM model
            new_msg = Message(
                conversation_id=self.conv_id,
                user_id=self.user_id,
                role="user",
                content="I feel a bit better today.",
                emotion="Happy"
            )
            session.add(new_msg)
            await session.commit()
            await session.refresh(new_msg)

            # Query back new message
            fresh_result = await session.execute(
                select(Message).where(Message.id == new_msg.id)
            )
            saved_msg = fresh_result.scalar_one()
            self.assertEqual(saved_msg.emotion, "Happy")
            self.assertEqual(saved_msg.emotion_detected, "Happy")
