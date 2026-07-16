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
from sqlalchemy.pool import NullPool

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
        # Initialize test engine and tables on a unique database file
        self.db_filename = f"./test_esona_{uuid.uuid4().hex}.db"
        self.test_db_url = f"sqlite+aiosqlite:///{self.db_filename}"
        self.engine = create_async_engine(self.test_db_url, echo=False, poolclass=NullPool)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

        async with self.engine.begin() as conn:
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
        if os.path.exists(self.db_filename):
            try:
                os.remove(self.db_filename)
            except Exception:
                pass
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

        # Mock Stage 6 Parser (Identity)
        mock_response_6 = MagicMock()
        mock_response_6.choices = [
            MagicMock(message=MagicMock(content='{"name": "Saideep"}'))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response_6)

        # Parse & save identity (Stage 6)
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, profile, 6, "Call me Saideep"
        )
        self.assertTrue(success)
        self.assertEqual(self.user.name, "Saideep")
        self.assertEqual(profile.personality_profile["onboarding_stage"], 7)

        # Mock Stage 15 Parser (Communication Style)
        mock_response_15 = MagicMock()
        mock_response_15.choices = [
            MagicMock(message=MagicMock(content='{"communication_style": "Friendly Friend"}'))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response_15)

        # Parse & save communication style (Stage 15)
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, profile, 15, "Friendly Friend please"
        )
        self.assertTrue(success)
        self.assertEqual(self.user.communication_style, "Friendly Friend")

        # Mock Stage 16 finalize compilation
        mock_response_16 = MagicMock()
        mock_response_16.choices = [
            MagicMock(message=MagicMock(content='{"sleep_habits": "Good"}'))
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
        
        # We'll use side_effect to return mock_response_16, then mock_finalize_response
        mock_get_client.return_value.chat.completions.create = AsyncMock(side_effect=[mock_response_16, mock_finalize_response])

        # Complete final stage (Stage 16)
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, profile, 16, "Good sleep"
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

    async def test_onboarding_step_persistence(self):
        """Verify onboarding step saving and retrieving works as expected."""
        # 1. Initially it should be 1 (default value)
        self.assertEqual(self.user.onboarding_step, 1)

        # 2. Update step
        self.user.onboarding_step = 5
        self.db.add(self.user)
        await self.db.commit()
        await self.db.refresh(self.user)
        self.assertEqual(self.user.onboarding_step, 5)

    @patch("app.services.emotion_service.get_chat_client")
    @patch("app.chatbot.pipeline.generate_chat_completion_with_fallback")
    @patch("app.memory.memory_manager.MemoryManager._get_embedding")
    @patch("app.services.profile_service.get_chat_client")
    @patch("app.services.knowledge_graph_service.get_chat_client")
    @patch("app.agents.response_agent.generate_chat_completion_with_fallback")
    async def test_emotion_validation_and_crisis_override(
        self,
        mock_response_generate,
        mock_kg_client,
        mock_profile_client,
        mock_embedding,
        mock_pipeline_generate,
        mock_emotion_client
    ):
        """Verify the emotion classification pipeline behaves correctly for validation inputs."""
        import json
        mock_embedding.return_value = [0.1, 0.2, 0.3]
        
        # Mock profile client response
        mock_response_facts = MagicMock()
        mock_response_facts.choices = [
            MagicMock(message=MagicMock(content='{"name": null, "university": null, "profession": null}'))
        ]
        mock_profile_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response_facts)

        # Mock kg client response
        mock_response_rels = MagicMock()
        mock_response_rels.choices = [
            MagicMock(message=MagicMock(content='{"relations": []}'))
        ]
        mock_kg_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response_rels)

        # Mock final response generation
        mock_response_generate.return_value = "I am a supportive response."
        
        # 1. Test "I am happy"
        # Mock emotion service LLM response
        mock_response_happy = MagicMock()
        mock_response_happy.choices = [
            MagicMock(message=MagicMock(content='{"detected_emotion": "Happy", "confidence_score": 0.95}'))
        ]
        mock_emotion_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response_happy)

        # Mock cognitive analyzer return for Happy
        mock_pipeline_generate.return_value = json.dumps({
            "message_type": "emotional",
            "personality_agent": {},
            "emotion_agent": {
                "primary_emotion": "happy",
                "stress": 0.1,
                "anxiety": 0.1,
                "sadness": 0.05,
                "burnout": 0.1,
                "emotional_intensity": 6
            },
            "behavior_agent": {},
            "growth_agent": {},
            "context_analysis": {},
            "recommendations": [],
            "memory_extraction": {"is_meaningful": False}
        })
        
        from app.chatbot.pipeline import run_agent_graph
        res_happy = await run_agent_graph(
            user_message="I am happy",
            user_id=str(self.user_id),
            conversation_history=[],
            emotional_profile={},
            db=self.db
        )
        self.assertEqual(res_happy["detected_emotion"].lower(), "happy")
        await self.db.rollback()

        # 2. Test "I am anxious about exams"
        # Mock emotion service LLM response
        mock_response_anxious = MagicMock()
        mock_response_anxious.choices = [
            MagicMock(message=MagicMock(content='{"detected_emotion": "Anxiety", "confidence_score": 0.95}'))
        ]
        mock_emotion_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response_anxious)

        mock_pipeline_generate.return_value = json.dumps({
            "message_type": "emotional",
            "personality_agent": {},
            "emotion_agent": {
                "primary_emotion": "anxiety",
                "stress": 0.4,
                "anxiety": 0.8,
                "sadness": 0.1,
                "burnout": 0.2,
                "emotional_intensity": 7
            },
            "behavior_agent": {},
            "growth_agent": {},
            "context_analysis": {},
            "recommendations": [],
            "memory_extraction": {"is_meaningful": False}
        })
        
        res_anxious = await run_agent_graph(
            user_message="I am anxious about exams",
            user_id=str(self.user_id),
            conversation_history=[],
            emotional_profile={},
            db=self.db
        )
        self.assertEqual(res_anxious["detected_emotion"].lower(), "anxiety")
        await self.db.rollback()

        # 3. Test "I feel depressed"
        # Mock emotion service LLM response
        mock_response_sad = MagicMock()
        mock_response_sad.choices = [
            MagicMock(message=MagicMock(content='{"detected_emotion": "Sadness", "confidence_score": 0.95}'))
        ]
        mock_emotion_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response_sad)

        mock_pipeline_generate.return_value = json.dumps({
            "message_type": "emotional",
            "personality_agent": {},
            "emotion_agent": {
                "primary_emotion": "sadness",
                "stress": 0.3,
                "anxiety": 0.2,
                "sadness": 0.8,
                "burnout": 0.5,
                "emotional_intensity": 8
            },
            "behavior_agent": {},
            "growth_agent": {},
            "context_analysis": {},
            "recommendations": [],
            "memory_extraction": {"is_meaningful": False}
        })
        
        res_depressed = await run_agent_graph(
            user_message="I feel depressed",
            user_id=str(self.user_id),
            conversation_history=[],
            emotional_profile={},
            db=self.db
        )
        self.assertEqual(res_depressed["detected_emotion"].lower(), "sadness")
        await self.db.rollback()

        # 4. Test "I want to die" (Crisis Override should run and bypass LLM classification check)
        res_crisis = await run_agent_graph(
            user_message="I want to die",
            user_id=str(self.user_id),
            conversation_history=[],
            emotional_profile={},
            db=self.db
        )
        self.assertNotEqual(res_crisis["detected_emotion"], "Crisis")
        self.assertEqual(res_crisis["detected_emotion_confidence"], 0.95)
        self.assertEqual(res_crisis["mood_score"], 0.05)
        self.assertEqual(res_crisis["safety_agent"]["crisis_detected"], True)
        await self.db.rollback()




    def test_buddy_intervention_logic(self):
        """Test Buddy's selective silence/intervention check helper."""
        from app.routes.chat import check_buddy_intervention

        # A. Direct Address
        should_int, reason = check_buddy_intervention("hey buddy", "maya", "hello", {})
        self.assertTrue(should_int)
        self.assertEqual(reason, "mention")

        # B. Confusion
        should_int, reason = check_buddy_intervention("i am confused", "maya", "hello", {})
        self.assertTrue(should_int)
        self.assertEqual(reason, "confusion")

        # C. Technical jargon
        should_int, reason = check_buddy_intervention("okay", "maya", "let's look at the fixed expenses and budget baseline", {})
        self.assertTrue(should_int)
        self.assertEqual(reason, "technical")

        # D. Intense emotion
        cog_res = {
            "emotion_agent": {
                "stress": 0.8,
                "anxiety": 0.2,
                "sadness": 0.1
            }
        }
        should_int, reason = check_buddy_intervention("yes", "maya", "hello", cog_res)
        self.assertTrue(should_int)
        self.assertEqual(reason, "emotion")

        # E. Casual/no intervention
        cog_res_casual = {
            "emotion_agent": {
                "stress": 0.2,
                "anxiety": 0.2,
                "sadness": 0.2
            }
        }
        should_int, reason = check_buddy_intervention("yes", "maya", "hello there", cog_res_casual)
        self.assertFalse(should_int)
        self.assertIsNone(reason)

    def test_text_normalization(self):
        """Verify text normalization correctly reduces elongation."""
        from app.services.emotion_service import normalize_stretched_words
        self.assertEqual(normalize_stretched_words("brooooo"), "bro")
        self.assertEqual(normalize_stretched_words("uppp"), "up")
        self.assertEqual(normalize_stretched_words("noooo"), "no")
        self.assertEqual(normalize_stretched_words("pleaseeee"), "please")
        # Ensure standard double-letter words are preserved (e.g. good, sleep, feel)
        self.assertEqual(normalize_stretched_words("goood"), "good")
        self.assertEqual(normalize_stretched_words("sleeeep"), "sleep")

    def test_emoji_boosting(self):
        """Verify emoji boosting applies correct weights and overrides Neutral."""
        from app.services.emotion_service import boost_local_predictions, extract_emojis
        
        # 1. Test emoji counts
        counts = extract_emojis("we just had a fight and got broke uppp 😭😭😭💔")
        self.assertEqual(counts.get("😭"), 3)
        self.assertEqual(counts.get("💔"), 1)

        # 2. Test predictions boost override
        preds = [{"label": "joy", "score": 0.1}, {"label": "sadness", "score": 0.2}, {"label": "neutral", "score": 0.7}]
        best_emotion, score = boost_local_predictions(preds, counts)
        self.assertEqual(best_emotion, "Sadness")
        self.assertEqual(score, 1.0)



    @patch("app.utils.llm.generate_chat_completion_with_fallback")
    async def test_personalized_first_message_system(self, mock_llm):
        """Verify personalized first message system handles new and returning users correctly."""
        # Setup mock LLM response
        mock_llm.return_value = "hey Bob 👋 ||| how's the coding goal going today?"

        # 1. Test first-time user: onboarding_completed is False
        self.user.onboarding_completed = False
        await self.db.commit()
        await self.db.refresh(self.user)

        from app.routes.chat import generate_first_message
        res1 = await generate_first_message(self.conv_id, self.user, self.db)
        self.assertIn("before we start, i'd love to get to know you a little better", res1["response"])
        self.assertIn("i'm Buddy", res1["response"])

        # 2. Test returning user within 4 hours session limit: onboarding_completed is True
        self.user.onboarding_completed = True
        await self.db.commit()
        await self.db.refresh(self.user)

        # Clear old onboarding messages to simulate a returning user with messages
        from app.models import Message
        from sqlalchemy import delete
        await self.db.execute(delete(Message).where(Message.conversation_id == self.conv_id))
        await self.db.commit()

        # Add a recent message from assistant
        recent_msg = Message(
            conversation_id=self.conv_id,
            user_id=self.user_id,
            role="assistant",
            content="I am here for you.",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(recent_msg)
        await self.db.commit()

        # Call endpoint - should NOT generate a new greeting (return empty response)
        res_recent = await generate_first_message(self.conv_id, self.user, self.db)
        self.assertEqual(res_recent["response"], "")

        # 3. Test returning user after 4 hours session limit: onboarding_completed is True
        from datetime import timedelta
        await self.db.execute(delete(Message).where(Message.conversation_id == self.conv_id))
        await self.db.commit()

        old_msg = Message(
            conversation_id=self.conv_id,
            user_id=self.user_id,
            role="assistant",
            content="I am here for you.",
            created_at=datetime.now(timezone.utc) - timedelta(hours=5)
        )
        self.db.add(old_msg)
        await self.db.commit()

        # Call endpoint - should generate a new greeting!
        res_old = await generate_first_message(self.conv_id, self.user, self.db)
        self.assertEqual(res_old["response"], "hey Bob 👋 ||| how's the coding goal going today?")


if __name__ == "__main__":
    unittest.main()
