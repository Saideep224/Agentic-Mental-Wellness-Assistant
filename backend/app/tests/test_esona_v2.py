"""
Esona V2 - Unit and Integration Tests for Memory, Onboarding, and Emotion Systems.
"""

import os
import uuid
import unittest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, func

from app.database import Base, SafeUUID
from app.models import User, Conversation, Message, UserProfile, Memory, EmotionLog, MoodLog
from app.services.emotion_service import emotion_service
from app.services.onboarding_service import onboarding_service
from app.services.memory_service import memory_service
from app.orchestrator.response_orchestrator import response_orchestrator

TEST_DB_URL = "sqlite+aiosqlite:///./test_esona.db"


class EsonaV2TestCase(unittest.IsolatedAsyncioTestCase):
    """Test suite for Esona V2 features: database, memory, emotion, and onboarding."""

    async def asyncSetUp(self):
        # Initialize test engine and tables
        self.engine = create_async_engine(TEST_DB_URL, echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        self.db = self.session_maker()

        # Create a test user
        self.user_id = uuid.uuid4()
        self.user = User(
            id=self.user_id,
            email="test_user@esona.com",
            name="Alice",
            onboarding_completed=False,
            personality_profile={"onboarding_stage": 1}
        )
        self.db.add(self.user)
        
        # Create a test conversation
        self.conv_id = uuid.uuid4()
        self.conv = Conversation(
            id=self.conv_id,
            user_id=self.user_id,
            title="Test Conversation"
        )
        self.db.add(self.conv)
        await self.db.commit()
        await self.db.refresh(self.user)
        await self.db.refresh(self.conv)

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()
        # Clean up database file
        if os.path.exists("./test_esona.db"):
            try:
                os.remove("./test_esona.db")
            except Exception:
                pass

    async def test_message_persistence(self):
        """Phase 1: Verify user and assistant messages can be successfully persisted."""
        # 1. Create User message
        user_msg = Message(
            conversation_id=self.conv_id,
            user_id=self.user_id,
            role="user",
            content="I have an exam next Friday."
        )
        self.db.add(user_msg)
        await self.db.commit()

        # 2. Query back and assert
        res = await self.db.execute(select(Message).where(Message.role == "user"))
        msg = res.scalar_one()
        self.assertEqual(msg.content, "I have an exam next Friday.")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.conversation_id, self.conv_id)

        # 3. Create Assistant message
        asst_msg = Message(
            conversation_id=self.conv_id,
            user_id=self.user_id,
            role="assistant",
            content="That sounds stressful. Exams can be tough.",
            emotion="Stress"
        )
        self.db.add(asst_msg)
        await self.db.commit()

        # 4. Query back and verify emotion column
        res_asst = await self.db.execute(select(Message).where(Message.role == "assistant"))
        asst_msg_db = res_asst.scalar_one()
        self.assertEqual(asst_msg_db.emotion, "Stress")
        self.assertEqual(asst_msg_db.emotion_detected, "Stress") # property alias

    @patch("app.services.emotion_service.get_chat_client")
    async def test_emotion_classification_mentalbert(self, mock_get_client):
        """Phase 5: Verify simulated MentalBERT classifies messages and stores them in emotion_logs."""
        # Setup mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"detected_emotion": "Stress", "confidence_score": 0.95}'))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

        # Classify
        res = await emotion_service.classify_emotion_mentalbert(
            self.db, str(self.user_id), "I am so overwhelmed with all my coursework."
        )

        self.assertEqual(res["detected_emotion"], "Stress")
        self.assertEqual(res["confidence_score"], 0.95)

        # Check DB log persistence
        await self.db.commit() # commit transaction
        log_res = await self.db.execute(select(EmotionLog))
        log = log_res.scalar_one()
        self.assertEqual(log.user_id, self.user_id)
        self.assertEqual(log.detected_emotion, "Stress")
        self.assertEqual(log.confidence_score, 0.95)
        self.assertEqual(log.message, "I am so overwhelmed with all my coursework.")

    @patch("app.services.onboarding_service.get_chat_client")
    async def test_conversational_onboarding_flow(self, mock_get_client):
        """Phase 3: Verify user onboarding answers are parsed, stages increment, and profiles compiled."""
        # Create user profile record
        profile = UserProfile(
            user_id=self.user_id,
            onboarding_completed=False,
            personality_profile={"onboarding_stage": 1}
        )
        self.db.add(profile)
        await self.db.commit()

        # Mock Stage 1 Parser (Identity)
        mock_response_1 = MagicMock()
        mock_response_1.choices = [
            MagicMock(message=MagicMock(content='{"name": "Saideep"}'))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response_1)

        # Parse & save identity (Stage 1)
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, profile, 1, "Call me Saideep"
        )
        self.assertTrue(success)
        self.assertEqual(self.user.name, "Saideep")
        self.assertEqual(profile.personality_profile["onboarding_stage"], 2)

        # Mock Stage 4 Parser (Communication Style)
        mock_response_4 = MagicMock()
        mock_response_4.choices = [
            MagicMock(message=MagicMock(content='{"communication_style": "Friendly Friend"}'))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response_4)

        # Parse & save communication style (Stage 4)
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, profile, 4, "Friendly Friend please"
        )
        self.assertTrue(success)
        self.assertEqual(self.user.communication_style, "Friendly Friend")

        # Mock Stage 8 finalize compilation
        mock_response_8 = MagicMock()
        mock_response_8.choices = [
            MagicMock(message=MagicMock(content='{"important_info": "I study best at night"}'))
        ]
        mock_finalize_response = MagicMock()
        mock_finalize_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=(
                        '{"personality_type": {"type": "Night Owl", "strengths": ["creative"], "growth_areas": ["sleep"]}, '
                        '"emotional_baseline": {"dominant_emotion": "neutral", "stress_level": 3.0}, '
                        '"comfort_preferences": {"escape_mechanisms": ["coding"]}, '
                        '"reply_style": {"reply_style": "casual", "communication_style": "Friendly Friend"}}'
                    )
                )
            )
        ]
        
        # We'll use side_effect to return mock_response_8, then mock_finalize_response
        mock_get_client.return_value.chat.completions.create = AsyncMock(side_effect=[mock_response_8, mock_finalize_response])

        # Complete final stage
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, profile, 8, "Remember I study best at night."
        )
        self.assertTrue(success)
        self.assertTrue(self.user.onboarding_completed)
        self.assertTrue(profile.onboarding_completed)
        self.assertEqual(self.user.personality_type, "Night Owl")

    @patch("app.memory.memory_manager.MemoryManager._get_embedding")
    async def test_long_term_memory_storage_and_retrieval(self, mock_embedding):
        """Phase 4 & Phase 6: Verify memory persistence with memory_type & importance_score."""
        mock_embedding.return_value = [0.1, 0.2, 0.3]

        # 1. Save event memory (e.g. interview)
        await memory_service.saveMemory(
            db=self.db,
            user_id=str(self.user_id),
            memory_summary="User has an interview next Friday",
            behavior_patterns={"decay_priority": 5},
            memory_type="event",
            importance_score=9.0
        )
        await self.db.commit()

        # 2. Save emotion memory
        await memory_service.saveMemory(
            db=self.db,
            user_id=str(self.user_id),
            memory_summary="User gets anxious about public speaking",
            behavior_patterns={"decay_priority": 4},
            memory_type="emotion",
            importance_score=8.0
        )
        await self.db.commit()

        # 3. Retrieve relevant memories
        mems = await memory_service.retrieveRelevantMemories(
            db=self.db,
            user_id=str(self.user_id),
            query="interview preparation"
        )
        self.assertTrue(len(mems) > 0)
        
        # The interview event memory should be returned and have correct columns
        first_mem = mems[0]
        self.assertEqual(first_mem.memory_type, "event")
        self.assertEqual(first_mem.importance_score, 9.0)
        self.assertEqual(first_mem.memory_content, "User has an interview next Friday")

    def test_response_personalization_and_events(self):
        """Phase 7: Verify ResponseOrchestrator tailors system prompt to profile and event memories."""
        personality_profile = {
            "age": "21",
            "profession": "College Student",
            "interests": {"hobbies": ["Anime", "Gaming"]},
            "goals": ["Get an internship", "Complete semester exams"],
            "stress_triggers": {"triggers": ["Exams", "Deadlines"]},
            "communication_style": "Supportive Listener"
        }

        # Mock event memory
        memories = [
            {
                "content": "User has an exam next Friday",
                "memory_type": "event",
                "importance_score": 9.0,
                "metadata": {}
            }
        ]

        # Generate system prompt
        sys_prompt = response_orchestrator.build_final_prompt(
            user_name="Alice",
            personality_profile=personality_profile,
            personality={"confidence_level": "moderate"},
            emotion={"stress": 0.5},
            behavior={"productivity_patterns": "good"},
            growth={"motivation": "high"},
            memories=memories,
            tone="supportive",
            strategy="Keep check-in natural and warm",
            current_time_str="Monday, June 08, 2026 10:00 AM (IST)"
        )

        # Assert personalization inclusions
        self.assertIn("Alice", sys_prompt)
        self.assertIn("College Student", sys_prompt)
        self.assertIn("Supportive Listener", sys_prompt)
        self.assertIn("User has an exam next Friday", sys_prompt)
        self.assertIn("CRITICAL FRIEND RECALL CHECK-IN RULE", sys_prompt)
        self.assertIn("How's the exam preparation going", sys_prompt)


if __name__ == "__main__":
    unittest.main()
