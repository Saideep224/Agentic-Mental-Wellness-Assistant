"""
Unit Tests for Esona Profile Redesign and Start Fresh Reset.
"""

import os
import uuid
import unittest
import asyncio
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.pool import NullPool

from app.database import Base
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
    UserRelationship
)
from app.services.profile_service import profile_service

TEST_RESET_DB_URL = "sqlite+aiosqlite:///./test_reset.db"


class ProfileResetTestCase(unittest.IsolatedAsyncioTestCase):
    """Test suite for start fresh profile resets and dynamic About You/Traits generation."""

    async def asyncSetUp(self):
        # Initialize test engine and tables
        self.engine = create_async_engine(TEST_RESET_DB_URL, echo=False, poolclass=NullPool)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        self.db = self.session_maker()

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()
        # Clean up database file
        if os.path.exists("./test_reset.db"):
            try:
                os.remove("./test_reset.db")
            except Exception:
                pass

    async def test_dynamic_summary_generation_empty(self):
        """Verify summary generation fallback when profile is empty."""
        summary = profile_service.generate_about_you_summary(None)
        traits = profile_service.select_profile_traits(None)
        self.assertIn("Esona is still getting to know you", summary)
        self.assertEqual(traits, ["Getting started"])

    async def test_dynamic_summary_generation_filled(self):
        """Verify summary and traits generated deterministically from UserPersonalProfile."""
        personal_profile = UserPersonalProfile(
            user_id=uuid.uuid4(),
            profession="student",
            field_of_work="Computer Science",
            current_challenge="finding focus",
            advice_preference="listen before advising",
            communication_style="brief and concise",
            primary_support_need="validation",
            sleep_habits="poor"
        )
        summary = profile_service.generate_about_you_summary(personal_profile)
        traits = profile_service.select_profile_traits(personal_profile)

        # Check summary keywords
        self.assertIn("student", summary)
        self.assertIn("Computer Science", summary)
        self.assertIn("prefer brief, straight-to-the-point", summary)
        self.assertIn("prefer being heard and validated", summary)
        self.assertIn("finding quiet pockets of rest", summary)

        # Check trait chips matches
        self.assertIn("Listen before advising", traits)
        self.assertIn("Likes shorter replies", traits)
        self.assertIn("Emotional validation first", traits)

    async def test_start_fresh_operation(self):
        """Verify Start Fresh resets only targeted user tables and keeps credentials."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="reset_test@esona.com",
            name="Alice",
            onboarding_completed=True,
            onboarding_step=5,
            personality_profile={"stage": "complete"}
        )
        self.db.add(user)
        
        # Populate all user-related tables
        ans = UserAnswer(user_id=user_id, question_id=1, category="background", question_text="Q1", selected_answers=["A"])
        conv = Conversation(user_id=user_id, title="Test Chat")
        self.db.add(ans)
        self.db.add(conv)
        await self.db.flush()

        msg = Message(conversation_id=conv.id, user_id=user_id, role="user", message="Hello Esona")
        mem = Memory(user_id=user_id, memory_content="Test memory")
        mood = MoodLog(user_id=user_id, mood_score=4.0, mood_label="positive", detected_emotion="happy")
        emotion = EmotionLog(user_id=user_id, message="Hello", detected_emotion="happy", confidence_score=0.9)
        kg = KnowledgeGraphRelation(user_id=user_id, subject="Alice", predicate="chats_with", object="Esona")
        entity = UserEntity(user_id=user_id, entity="Alice", type="person")
        rel = UserRelationship(user_id=user_id, source="Alice", relationship_name="self", target="Alice")
        personal = UserPersonalProfile(user_id=user_id, profession="developer")
        profile = UserProfile(user_id=user_id, onboarding_completed=True)

        self.db.add_all([msg, mem, mood, emotion, kg, entity, rel, personal, profile])
        await self.db.commit()

        # Execute Start Fresh
        from app.routes.dashboard import start_fresh
        
        # Simulate route dependencies
        current_user = {"id": str(user_id), "email": "reset_test@esona.com"}
        res = await start_fresh(current_user=current_user, db=self.db)
        self.assertTrue(res["success"])
        self.assertTrue(res["requires_onboarding"])

        # Fetch fresh database state
        await self.db.close()
        self.db = self.session_maker()

        # Verify User row exists but is reset
        db_user = await self.db.get(User, user_id)
        self.assertIsNotNone(db_user)
        self.assertFalse(db_user.onboarding_completed)
        self.assertEqual(db_user.onboarding_step, 1)
        self.assertEqual(db_user.personality_profile, {})

        # Verify other tables are empty for this user
        self.assertEqual(len((await self.db.execute(select(UserAnswer).where(UserAnswer.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(Conversation).where(Conversation.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(Message).where(Message.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(Memory).where(Memory.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(MoodLog).where(MoodLog.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(EmotionLog).where(EmotionLog.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(KnowledgeGraphRelation).where(KnowledgeGraphRelation.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(UserEntity).where(UserEntity.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(UserRelationship).where(UserRelationship.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(UserPersonalProfile).where(UserPersonalProfile.user_id == user_id))).scalars().all()), 0)
        self.assertEqual(len((await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalars().all()), 0)

    async def test_start_fresh_transaction_rollback(self):
        """Verify transaction rollbacks completely on deletion errors."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="rollback_test@esona.com",
            name="Bob",
            onboarding_completed=True,
            onboarding_step=5
        )
        self.db.add(user)
        ans = UserAnswer(user_id=user_id, question_id=1, category="background", question_text="Q1", selected_answers=["A"])
        self.db.add(ans)
        await self.db.commit()

        # Mock db.execute to raise Exception on second call (deleting conversations)
        original_execute = self.db.execute
        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Simulated DB Deletion Error")
            return await original_execute(*args, **kwargs)

        self.db.execute = mock_execute

        from app.routes.dashboard import start_fresh
        current_user = {"id": str(user_id), "email": "rollback_test@esona.com"}
        
        with self.assertRaises(Exception):
            await start_fresh(current_user=current_user, db=self.db)

        # Re-fetch state using a fresh session to confirm rollback
        await self.db.close()
        self.db = self.session_maker()

        db_user = await self.db.get(User, user_id)
        self.assertTrue(db_user.onboarding_completed)  # User properties not reset

        db_answers = (await self.db.execute(select(UserAnswer).where(UserAnswer.user_id == user_id))).scalars().all()
        self.assertEqual(len(db_answers), 1)  # Onboarding answers preserved

    async def test_start_fresh_user_isolation(self):
        """Verify resetting User A does not modify or delete User B's records."""
        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()

        user_a = User(id=user_a_id, email="a@esona.com", name="User A", onboarding_completed=True, onboarding_step=5)
        user_b = User(id=user_b_id, email="b@esona.com", name="User B", onboarding_completed=True, onboarding_step=5)
        self.db.add_all([user_a, user_b])

        ans_a = UserAnswer(user_id=user_a_id, question_id=1, category="background", question_text="Q1", selected_answers=["A"])
        ans_b = UserAnswer(user_id=user_b_id, question_id=1, category="background", question_text="Q1", selected_answers=["B"])
        self.db.add_all([ans_a, ans_b])
        await self.db.commit()

        # Run start fresh for User A
        from app.routes.dashboard import start_fresh
        current_user = {"id": str(user_a_id), "email": "a@esona.com"}
        await start_fresh(current_user=current_user, db=self.db)

        # Verify User A is reset and has no answers
        db_user_a = await self.db.get(User, user_a_id)
        self.assertFalse(db_user_a.onboarding_completed)
        self.assertEqual(len((await self.db.execute(select(UserAnswer).where(UserAnswer.user_id == user_a_id))).scalars().all()), 0)

        # Verify User B is completely untouched
        db_user_b = await self.db.get(User, user_b_id)
        self.assertTrue(db_user_b.onboarding_completed)
        self.assertEqual(db_user_b.onboarding_step, 5)
        
        answers_b = (await self.db.execute(select(UserAnswer).where(UserAnswer.user_id == user_b_id))).scalars().all()
        self.assertEqual(len(answers_b), 1)
        self.assertEqual(answers_b[0].selected_answers, ["B"])
