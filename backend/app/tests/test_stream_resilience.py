"""
Unit and Integration Tests for Esona Chat Stream Resilience, Fallback, and Deduplication.
"""

import os
import uuid
import unittest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from sqlalchemy.pool import NullPool

from app.database import Base
from app.models import User, Conversation, Message, UserProfile
from app.models.conversation import MessageRole
from app.utils.llm import generate_chat_completion_stream_with_fallback

TEST_RESILIENCE_DB_URL = "sqlite+aiosqlite:///./test_resilience.db"


class ChatStreamResilienceTestCase(unittest.IsolatedAsyncioTestCase):
    """Test suite for SSE chat stream resilience, fallbacks, and message deduplication."""

    async def asyncSetUp(self):
        # Initialize test engine and tables
        self.engine = create_async_engine(TEST_RESILIENCE_DB_URL, echo=False, poolclass=NullPool)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        self.db = self.session_maker()

        # Seed mock user
        self.user_id = uuid.uuid4()
        self.user = User(
            id=self.user_id,
            email="resilience@esona.com",
            name="Resilience Test User",
            onboarding_completed=True,
            onboarding_step=5
        )
        self.db.add(self.user)
        
        # Seed mock user profile
        self.profile = UserProfile(
            user_id=self.user_id,
            onboarding_completed=True
        )
        self.db.add(self.profile)

        # Seed mock conversation
        self.conversation_id = uuid.uuid4()
        self.conversation = Conversation(
            id=self.conversation_id,
            user_id=self.user_id,
            title="Resilience Conversation"
        )
        self.db.add(self.conversation)
        await self.db.commit()

    async def asyncTearDown(self):
        await self.db.close()
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()
        if os.path.exists("./test_resilience.db"):
            try:
                os.remove("./test_resilience.db")
            except Exception:
                pass

    @patch("app.utils.llm._providers")
    @patch("app.utils.llm.AsyncOpenAI")
    async def test_llm_stream_fallback_on_rate_limit(self, mock_openai_cls, mock_providers):
        """Verify that generate_chat_completion_stream_with_fallback successfully falls back when a model is rate-limited (HTTP 429)."""
        # Mock providers list: Provider A (fails), Provider B (succeeds)
        mock_providers.return_value = [
            ("ProviderA", "http://provider-a.com", "key-a", "model-a"),
            ("ProviderB", "http://provider-b.com", "key-b", "model-b"),
        ]

        # Mock Clients
        mock_client_a = MagicMock()
        mock_client_b = MagicMock()

        # Mock exception for Provider A
        from openai import RateLimitError
        # OpenAI exceptions require a response object
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        rate_limit_err = RateLimitError("Rate limited", response=mock_response, body=None)
        
        # Set up side effects for completions.create
        mock_client_a.chat.completions.create = AsyncMock(side_effect=rate_limit_err)

        # Mock successful stream for Provider B
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta = MagicMock()
        mock_chunk.choices[0].delta.content = "hello from provider b"

        class AsyncIterator:
            def __init__(self, items):
                self.items = items
            def __aiter__(self):
                return self
            async def __anext__(self):
                if not self.items:
                    raise StopAsyncIteration
                return self.items.pop(0)

        mock_client_b.chat.completions.create = AsyncMock(return_value=AsyncIterator([mock_chunk]))

        # Mapping for AsyncOpenAI instantiations
        def client_side_effect(api_key, base_url):
            if api_key == "key-a":
                return mock_client_a
            return mock_client_b

        mock_openai_cls.side_effect = client_side_effect

        # Call the fallback function
        yielded_content = []
        async for chunk in generate_chat_completion_stream_with_fallback(
            messages=[{"role": "user", "content": "hi"}],
            preferred_model=None
        ):
            yielded_content.append(chunk)

        # Assertions
        self.assertEqual(len(yielded_content), 1)
        self.assertEqual(yielded_content[0], "hello from provider b")
        mock_client_a.chat.completions.create.assert_called_once()
        mock_client_b.chat.completions.create.assert_called_once()

    async def test_client_message_id_deduplication(self):
        """Verify that the deduplication logic in stream_message_sse correctly identifies duplicates by client_message_id."""
        client_msg_id = "test-client-msg-123"
        message_content = "Deduplication Test Message"

        # Create first message with client_message_id stored in emotional_context
        msg1 = Message(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            role=MessageRole.user,
            message=message_content,
            emotional_context={"client_message_id": client_msg_id}
        )
        self.db.add(msg1)
        await self.db.commit()

        # Simulate the query logic inside chat.py stream_message_sse
        from sqlalchemy import and_
        dedup_result = await self.db.execute(
            select(Message).where(
                and_(
                    Message.conversation_id == self.conversation_id,
                    Message.role == MessageRole.user,
                    Message.message == message_content,
                )
            ).order_by(Message.created_at.desc()).limit(1)
        )
        candidate = dedup_result.scalar_one_or_none()
        
        # Verify deduplication match
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.content, message_content)
        self.assertIsNotNone(candidate.emotional_context)
        self.assertEqual(candidate.emotional_context.get("client_message_id"), client_msg_id)
