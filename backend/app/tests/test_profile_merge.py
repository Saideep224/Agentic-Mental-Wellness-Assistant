"""
Esona V2 - Unit Tests for profile merge and duplicate email conflict resolution.
"""

import os
import uuid
import unittest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from sqlalchemy.pool import NullPool

from app.database import Base
from app.models import User, Conversation, Message, UserProfile, UserPersonalProfile
from app.routes.auth import get_current_user


class ProfileMergeTestCase(unittest.IsolatedAsyncioTestCase):
    """Test suite for verifying profile merging and user_id translation on email conflicts."""

    async def asyncSetUp(self):
        # Setup clean test SQLite file
        self.db_filename = f"./test_merge_{uuid.uuid4().hex}.db"
        self.test_db_url = f"sqlite+aiosqlite:///{self.db_filename}"
        self.engine = create_async_engine(self.test_db_url, echo=False, poolclass=NullPool)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.db = self.session_maker()

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()
        if os.path.exists(self.db_filename):
            try:
                os.remove(self.db_filename)
            except Exception:
                pass

    async def test_duplicate_email_conflict_merge(self):
        """Verify that when a new session with an existing email but different user_id is synced:
        1. Old profile is deleted/renamed.
        2. New profile is created.
        3. All child records (conversations, messages, etc.) are successfully reassigned to new user_id.
        """
        # 1. Create old user and profile
        old_user_id = uuid.uuid4()
        email = "duplicate@esona.com"
        
        old_user = User(
            id=old_user_id,
            user_id=old_user_id,
            email=email,
            name="Alice (Old Session)",
            onboarding_completed=True
        )
        self.db.add(old_user)
        
        # Add child records
        conv_id = uuid.uuid4()
        conv = Conversation(
            id=conv_id,
            user_id=old_user_id,
            title="Alice's Conversation"
        )
        self.db.add(conv)
        
        msg_id = uuid.uuid4()
        msg = Message(
            id=msg_id,
            conversation_id=conv_id,
            user_id=old_user_id,
            role="user",
            content="Hello world"
        )
        self.db.add(msg)
        
        # One-to-one child tables
        old_personality = UserProfile(
            user_id=old_user_id,
            onboarding_completed=True,
            personality_profile={"theme": "calm"}
        )
        self.db.add(old_personality)
        
        old_personal = UserPersonalProfile(
            user_id=old_user_id,
            name="Alice",
            profession="Designer"
        )
        self.db.add(old_personal)
        
        await self.db.commit()

        # 2. Simulate new session auth with same email but new user_id
        new_user_id = uuid.uuid4()
        mock_payload = {
            "sub": str(new_user_id),
            "email": email,
            "user_metadata": {
                "full_name": "Alice (New Session)",
                "onboarding_completed": True
            },
            "app_metadata": {
                "provider": "google"
            }
        }
        
        # We call the dependency helper logic directly to trigger the merge
        # Mocking the request parameter
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer some-token"}
        
        # Mock decode_and_verify_token inside auth.py
        with unittest.mock.patch("app.routes.auth.decode_and_verify_token", return_value=mock_payload):
            mock_credentials = MagicMock()
            mock_credentials.credentials = "some-token"
            
            # Execute dependency check-in
            synced_user = await get_current_user(mock_request, mock_credentials, self.db)
            
            # Assertions on return
            self.assertEqual(synced_user.id, new_user_id)
            self.assertEqual(synced_user.email, email)
            self.assertEqual(synced_user.name, "Alice (New Session)")

        # Clear SQLAlchemy session cache to force fresh DB fetch of child rows
        self.db.expire_all()

        # 3. Assert old user is deleted from profiles
        res_old = await self.db.execute(select(User).where(User.id == old_user_id))
        self.assertIsNone(res_old.scalar_one_or_none())

        # 4. Assert new user exists in profiles
        res_new = await self.db.execute(select(User).where(User.id == new_user_id))
        self.assertIsNotNone(res_new.scalar_one_or_none())

        # 5. Assert child records are successfully reassigned to new_user_id (NO CASCADE DELETION occurred)
        res_conv = await self.db.execute(select(Conversation).where(Conversation.id == conv_id))
        conv_retrieved = res_conv.scalar_one()
        self.assertEqual(conv_retrieved.user_id, new_user_id)

        res_msg = await self.db.execute(select(Message).where(Message.id == msg_id))
        msg_retrieved = res_msg.scalar_one()
        self.assertEqual(msg_retrieved.user_id, new_user_id)

        res_personality = await self.db.execute(select(UserProfile).where(UserProfile.user_id == new_user_id))
        pers_retrieved = res_personality.scalar_one()
        self.assertEqual(pers_retrieved.personality_profile, {"theme": "calm"})

        res_personal = await self.db.execute(select(UserPersonalProfile).where(UserPersonalProfile.user_id == new_user_id))
        personal_retrieved = res_personal.scalar_one()
        self.assertEqual(personal_retrieved.profession, "Designer")
