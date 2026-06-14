"""
Unit and Integration Tests for User Profile Personalization System.
"""

import os
import uuid
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.database import Base
from app.models import User, UserProfile
from app.models.user_personal_profile import UserPersonalProfile
from app.services.profile_service import profile_service
from app.services.onboarding_service import onboarding_service
from app.orchestrator.response_orchestrator import response_orchestrator

TEST_DB_URL = "sqlite+aiosqlite:///./test_personalization.db"


class PersonalizationTestCase(unittest.IsolatedAsyncioTestCase):
    """Test suite for personalization, UserPersonalProfile and onboarding changes."""

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
            email="personalization_test@esona.com",
            name="Bob",
            onboarding_completed=False,
            personality_profile={"onboarding_stage": 1}
        )
        self.db.add(self.user)

        # Create a test UserProfile (legacy user_personality)
        self.profile = UserProfile(
            user_id=self.user_id,
            onboarding_completed=False,
            personality_profile={"onboarding_stage": 1}
        )
        self.db.add(self.profile)
        await self.db.commit()
        await self.db.refresh(self.user)
        await self.db.refresh(self.profile)

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()
        # Clean up database file
        if os.path.exists("./test_personalization.db"):
            try:
                os.remove("./test_personalization.db")
            except Exception:
                pass

    async def test_profile_service_crud(self):
        """Verify ProfileService can create, get, update, and build context."""
        # 1. Create profile
        profile_data = {
            "name": "Saideep",
            "age": "20",
            "profession": "College Student",
            "student_year": "2nd year",
            "communication_style": "Friendly Friend",
            "interests": ["Anime", "Coding"],
            "goals": ["Get an internship"],
            "stress_triggers": ["Exams"],
            "coping_mechanisms": ["Listening to music"],
            "support_system": "Parents",
            "sleep_habits": "Average"
        }
        
        profile = await profile_service.create_profile(self.db, self.user_id, profile_data)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "Saideep")
        self.assertEqual(profile.age, "20")
        self.assertEqual(profile.interests, ["Anime", "Coding"])

        # 2. Get profile
        fetched = await profile_service.get_profile(self.db, self.user_id)
        self.assertEqual(fetched.id, profile.id)
        self.assertEqual(fetched.profession, "College Student")

        # 3. Update profile
        updated_data = {
            "age": "21",
            "goals": ["Get a job", "Fitness"],
            "sleep_habits": "Good"
        }
        updated = await profile_service.update_profile(self.db, self.user_id, updated_data)
        self.assertEqual(updated.age, "21")
        self.assertEqual(updated.goals, ["Get a job", "Fitness"])
        self.assertEqual(updated.sleep_habits, "Good")
        # Ensure name is untouched
        self.assertEqual(updated.name, "Saideep")

        # 4. Build context
        context = await profile_service.build_profile_context(self.db, self.user_id)
        self.assertIn("Name: Saideep", context)
        self.assertIn("Age: 21", context)
        self.assertIn("Profession: College Student", context)
        self.assertIn("Student Year: 2nd year", context)
        self.assertIn("Communication Style: Friendly Friend", context)
        self.assertIn("Goals: Get a job, Fitness", context)
        self.assertIn("Sleep Habits: Good", context)

    @patch("app.services.onboarding_service.get_chat_client")
    async def test_onboarding_student_flow(self, mock_get_client):
        """Verify student onboarding proceeds step by step through all stages."""
        # Setup mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"profession": "College Student"}'))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

        # Answer stage 1 (Profession) as College Student
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, self.profile, 1, "I am a college student"
        )
        self.assertTrue(success)
        
        # Verify onboarding stage is advanced to 2
        await self.db.refresh(self.profile)
        self.assertEqual(self.profile.personality_profile["onboarding_stage"], 2)

        # Verify UserPersonalProfile was updated with profession
        personal_profile = await profile_service.get_profile(self.db, self.user_id)
        self.assertEqual(personal_profile.profession, "College Student")

        # Answer stage 7 (Age)
        mock_response.choices = [MagicMock(message=MagicMock(content='{"age": "20"}'))]
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, self.profile, 7, "I am 20 years old"
        )
        self.assertTrue(success)
        
        # Verify stage 7 (Age) redirects to 9 (Student Year) for students, skipping 8
        await self.db.refresh(self.profile)
        self.assertEqual(self.profile.personality_profile["onboarding_stage"], 9)

    @patch("app.services.onboarding_service.get_chat_client")
    async def test_onboarding_non_student_skip_flow(self, mock_get_client):
        """Verify non-student onboarding skips stage 8 and student_year (stage 9) and advances to stage 10."""
        # Setup mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"profession": "Working Professional"}'))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

        # Answer stage 1 (Profession) as Working Professional
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, self.profile, 1, "I am a software engineer"
        )
        self.assertTrue(success)
        
        # Verify onboarding stage is advanced to 2
        await self.db.refresh(self.profile)
        self.assertEqual(self.profile.personality_profile["onboarding_stage"], 2)

        # Answer stage 7 (Age)
        mock_response.choices = [MagicMock(message=MagicMock(content='{"age": "28"}'))]
        success = await onboarding_service.parse_and_save_answer(
            self.db, self.user, self.profile, 7, "I am 28"
        )
        self.assertTrue(success)
        
        # Verify stage 7 (Age) redirects directly to 10 (Interests) for non-students, skipping 8 and 9
        await self.db.refresh(self.profile)
        self.assertEqual(self.profile.personality_profile["onboarding_stage"], 10)

    def test_response_orchestrator_personalization_rules(self):
        """Verify build_final_prompt correctly formats the prompt and includes personalization rules."""
        profile_context = (
            "User Profile:\n"
            "Name: Sdr\n"
            "Age: 19\n"
            "Profession: College Student\n"
            "Communication Style: Friendly Friend\n"
            "Goals: Internship"
        )
        
        prompt = response_orchestrator.build_final_prompt(
            user_name="Sdr",
            personality_profile={"communication_style": "Friendly Friend"},
            personality={},
            emotion={},
            behavior={},
            growth={},
            memories=[],
            tone="reflective",
            strategy="Ask questions",
            current_time_str="Monday, June 15, 2026 10:00 AM",
            profile_context=profile_context
        )

        self.assertIn("User Profile:", prompt)
        self.assertIn("Name: Sdr", prompt)
        self.assertIn("Profession: College Student", prompt)
        self.assertIn("PERSONALIZATION RULES:", prompt)
        self.assertIn("If 'Friendly and Casual': keep it warm, relaxed, and talk like a close friend", prompt)

    def test_emotion_context_injection(self):
        """Verify build_final_prompt correctly formats and injects emotion context."""
        prompt = response_orchestrator.build_final_prompt(
            user_name="Bob",
            personality_profile={},
            personality={},
            emotion={},
            behavior={},
            growth={},
            memories=[],
            tone="reflective",
            strategy="Ask open questions",
            current_time_str="Monday, June 15, 2026 10:00 AM",
            profile_context="",
            detected_emotion="Anxiety",
            detected_emotion_confidence=0.91
        )
        self.assertIn("EMOTION CONTEXT:", prompt)
        self.assertIn('"emotion": "anxiety"', prompt)
        self.assertIn('"confidence": 0.91', prompt)

    async def test_missing_field_detection(self):
        """Verify get_personalization_data consolidates information from all sources and identifies missing fields."""
        # 1. Setup mock data: UserPersonalProfile has profession and student_year
        profile_data = {
            "name": "Sai",
            "profession": "College Student",
            "student_year": "2nd year",
        }
        await profile_service.create_profile(self.db, self.user_id, profile_data)
        
        # 2. Add some raw onboarding answers
        from app.models.onboarding import UserAnswer
        ans1 = UserAnswer(
            user_id=self.user_id,
            question_id=2,
            question_text="What field are you studying?",
            category="field_of_work",
            selected_answers=[],
            custom_answer="Computer Science"
        )
        self.db.add(ans1)
        await self.db.commit()

        # 3. Retrieve personalization data
        p_data = await profile_service.get_personalization_data(self.db, self.user_id)
        existing = p_data["existing"]
        missing = p_data["missing"]

        # Validate that populated values are correctly consolidated
        self.assertEqual(existing.get("name"), "Sai")
        self.assertEqual(existing.get("profession"), "College Student")
        self.assertEqual(existing.get("student_year"), "2nd year")
        self.assertEqual(existing.get("field_of_work"), "Computer Science")

        # Validate that empty/missing fields are detected
        self.assertIn("goals", missing)
        self.assertIn("sleep_habits", missing)
        self.assertNotIn("profession", missing)
        self.assertNotIn("field_of_work", missing)

        # 4. Validate personalization prompt block generation
        block = await profile_service.build_personalization_prompt_block(self.db, self.user_id)
        self.assertIn("Name: Sai", block)
        self.assertIn("Profession: College Student", block)
        self.assertIn("Field Of Work: Computer Science", block)
        self.assertIn("goals (current goals)", block)
        self.assertIn("CRITICAL PERSONALIZATION QUESTIONS RULES:", block)

    @patch("app.services.profile_service.get_chat_client")
    async def test_extract_and_update_profile_facts(self, mock_get_client):
        """Verify extract_and_update_profile_facts parses statements and updates database profile and merges list fields."""
        # 1. Mock the LLM client response for fact extraction
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="""{
                "name": "Sai",
                "university": "SRM AP",
                "profession": "Student",
                "field_of_work": "AI",
                "interests": ["Coding"],
                "goals": ["pass the midterm exam"],
                "stress_triggers": ["Exams"],
                "coping_mechanisms": ["lo-fi music"],
                "sleep_habits": "poor"
            }"""))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

        # 2. Extract and update
        profile = await profile_service.extract_and_update_profile_facts(self.db, self.user_id, "Hi I am Sai studying AI at SRM AP")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "Sai")
        self.assertEqual(profile.university, "SRM AP")
        self.assertEqual(profile.field_of_work, "AI")
        self.assertEqual(profile.interests, ["Coding"])
        self.assertEqual(profile.stress_triggers, ["Exams"])

        # 3. Call again with new mock data to verify merging of list fields and overwriting single fields
        mock_response2 = MagicMock()
        mock_response2.choices = [
            MagicMock(message=MagicMock(content="""{
                "name": null,
                "university": null,
                "profession": "Graduate",
                "field_of_work": null,
                "interests": ["Gaming"],
                "goals": ["find a job"],
                "stress_triggers": ["Interviews"],
                "coping_mechanisms": null,
                "sleep_habits": "good"
            }"""))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response2)

        profile2 = await profile_service.extract_and_update_profile_facts(self.db, self.user_id, "I graduated and like gaming now")
        self.assertIsNotNone(profile2)
        # Check single values (overwritten or preserved)
        self.assertEqual(profile2.name, "Sai")  # Preserved since new mock returned null
        self.assertEqual(profile2.profession, "Graduate")  # Overwritten with new value
        self.assertEqual(profile2.sleep_habits, "good")  # Overwritten with new value
        # Check list values (merged and deduplicated)
        self.assertIn("Coding", profile2.interests)
        self.assertIn("Gaming", profile2.interests)
        self.assertIn("pass the midterm exam", profile2.goals)
        self.assertIn("find a job", profile2.goals)
        self.assertIn("Exams", profile2.stress_triggers)
        self.assertIn("Interviews", profile2.stress_triggers)

    async def test_prune_expired_memories(self):
        """Verify memory_service.prune_expired_memories prunes memories based on importance and age."""
        from app.models.memory import Memory
        from app.services.memory_service import memory_service
        from datetime import datetime, timezone, timedelta

        # Create low-importance memory older than 3 days
        m1 = Memory(
            user_id=self.user_id,
            memory_summary="I like cheese",
            memory_type="opinion",
            importance_score=2.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=4)
        )
        # Create medium-importance memory older than 14 days
        m2 = Memory(
            user_id=self.user_id,
            memory_summary="Preparing for placement",
            memory_type="event",
            importance_score=5.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=15)
        )
        # Create high-importance memory (permanent)
        m3 = Memory(
            user_id=self.user_id,
            memory_summary="Studies CS at SRM AP",
            memory_type="profile",
            importance_score=9.0,
            created_at=datetime.now(timezone.utc) - timedelta(days=40)
        )

        self.db.add_all([m1, m2, m3])
        await self.db.commit()

        # Run pruning
        deleted = await memory_service.prune_expired_memories(self.db, self.user_id)
        self.assertEqual(deleted, 2)

        # Check remaining
        result = await self.db.execute(select(Memory).where(Memory.user_id == self.user_id))
        remaining = result.scalars().all()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].memory_summary, "Studies CS at SRM AP")

    @patch("app.services.memory_service.get_chat_client")
    async def test_reflect_and_consolidate_memories(self, mock_get_client):
        """Verify memory_service.reflect_and_consolidate_memories consolidates memories and wipes old reflections."""
        from app.models.memory import Memory
        from app.services.memory_service import memory_service

        # Create 5 memories (minimum requirement)
        m_list = [
            Memory(user_id=self.user_id, memory_summary=f"Memory {i}", memory_type="detail", importance_score=5.0)
            for i in range(5)
        ]
        # Create an existing reflection memory
        old_ref = Memory(
            user_id=self.user_id,
            memory_summary="User is interested in nothing",
            memory_type="reflection",
            importance_score=9.0
        )

        self.db.add_all(m_list + [old_ref])
        await self.db.commit()

        # Mock LLM client response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="User is:\n- Interested in AI"))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

        # Run reflection
        new_ref = await memory_service.reflect_and_consolidate_memories(self.db, self.user_id)
        self.assertIsNotNone(new_ref)
        self.assertEqual(new_ref.memory_type, "reflection")
        self.assertIn("Interested in AI", new_ref.memory_summary)

        # Verify old reflection is deleted
        result = await self.db.execute(
            select(Memory).where(
                Memory.user_id == self.user_id,
                Memory.memory_type == "reflection"
            )
        )
        reflections = result.scalars().all()
        self.assertEqual(len(reflections), 1)
        self.assertEqual(reflections[0].id, new_ref.id)

    async def test_retrieve_emotion_timeline(self):
        """Verify MoodTracker.retrieve_emotion_timeline returns chronological primary emotions."""
        from app.models.mood_log import MoodLog
        from app.services.mood_tracker import MoodTracker
        from datetime import datetime, timezone, timedelta

        # Create logs
        log1 = MoodLog(user_id=self.user_id, mood_score=0.2, mood_label="anxiety", detected_emotion="anxiety", created_at=datetime.now(timezone.utc) - timedelta(days=5))
        log2 = MoodLog(user_id=self.user_id, mood_score=0.4, mood_label="stress", detected_emotion="stress", created_at=datetime.now(timezone.utc) - timedelta(days=3))
        log3 = MoodLog(user_id=self.user_id, mood_score=0.1, mood_label="anxiety", detected_emotion="anxiety", created_at=datetime.now(timezone.utc) - timedelta(days=1))

        self.db.add_all([log1, log2, log3])
        await self.db.commit()

        mt = MoodTracker(self.db)
        timeline = await mt.retrieve_emotion_timeline(self.user_id, days=7)
        self.assertEqual(timeline, ["anxiety", "stress", "anxiety"])

    def test_timeline_prompt_injection(self):
        """Verify build_final_prompt correctly formats and injects emotion timeline."""
        timeline = ["anxiety", "anxiety", "stress", "stress", "anxiety"]
        prompt = response_orchestrator.build_final_prompt(
            user_name="Bob",
            personality_profile={},
            personality={},
            emotion={},
            behavior={},
            growth={},
            memories=[],
            tone="reflective",
            strategy="Ask questions",
            current_time_str="Monday, June 15, 2026 10:00 AM",
            profile_context="",
            emotion_timeline=timeline
        )
        self.assertIn("RECENT EMOTION TIMELINE (LAST 7 DAYS):", prompt)
        self.assertIn("Anxiety -> Anxiety -> Stress -> Stress -> Anxiety", prompt)
        self.assertIn("Emotion Timeline Trend Checking:", prompt)


# ---------------------------------------------------------------------------
# Growth Insights Service Tests
# ---------------------------------------------------------------------------

class GrowthInsightsServiceTestCase(unittest.IsolatedAsyncioTestCase):
    """Unit tests for GrowthInsightsService analytics logic."""

    async def asyncSetUp(self):
        from app.services.growth_insights_service import GrowthInsightsService
        from app.models.mood_log import MoodLog
        from app.models.memory import Memory
        from app.models.knowledge_graph import KnowledgeGraphRelation

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.service = GrowthInsightsService()

        # Create all tables (including new ones)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create a test user and profile (needed for FK constraints)
        self.user_id = uuid.uuid4()
        async with self.session_maker() as session:
            user = User(id=self.user_id, email=f"growthtest_{self.user_id}@test.com", name="GrowthTest")
            session.add(user)
            from app.models.user_profile import UserProfile
            profile = UserProfile(user_id=self.user_id)
            session.add(profile)
            await session.commit()

    async def asyncTearDown(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    async def test_empty_state_returns_empty_insights(self):
        """generate_insights returns an empty list when no MoodLogs or Memories exist."""
        async with self.session_maker() as session:
            result = await self.service.generate_insights(session, self.user_id)
        self.assertIsNotNone(result)
        self.assertEqual(result.insights, [])
        self.assertEqual(result.total_logs, 0)
        self.assertEqual(result.total_memories, 0)

    async def test_emotion_frequency_insight_generated(self):
        """Inserts MoodLogs and verifies emotion frequency insights are produced."""
        from app.models.mood_log import MoodLog
        from datetime import datetime, timezone

        async with self.session_maker() as session:
            for _ in range(5):
                log = MoodLog(
                    user_id=self.user_id,
                    detected_emotion="anxiety",
                    mood_score=0.3,
                    mood_label="anxious",
                    stress=0.7,
                    happiness=0.2,
                    sadness=0.3,
                    anxiety=0.7,
                    motivation=0.2,
                    confidence=0.3,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(log)
            await session.commit()

        async with self.session_maker() as session:
            result = await self.service.generate_insights(session, self.user_id)

        self.assertGreater(len(result.insights), 0)
        categories = [i.category for i in result.insights]
        self.assertTrue(any("anxiety" in cat.lower() or "Anxiety" in cat for cat in categories))

    async def test_topic_frequency_insight_from_memory(self):
        """Inserts Memories with exam keywords and verifies topic insights are created."""
        from app.models.memory import Memory
        from datetime import datetime, timezone

        async with self.session_maker() as session:
            for i in range(3):
                mem = Memory(
                    user_id=self.user_id,
                    memory_content=f"User is stressed about upcoming exam and finals season #{i}",
                    memory_type="emotion",
                    importance_score=6.0,
                    behavior_patterns={},
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(mem)
            await session.commit()

        async with self.session_maker() as session:
            result = await self.service.generate_insights(session, self.user_id)

        observations = [i.observation for i in result.insights]
        self.assertTrue(any("exam" in obs.lower() for obs in observations))

    async def test_overall_trend_returns_none_with_insufficient_data(self):
        """_overall_trend_insight returns None when only one half has data."""
        async with self.session_maker() as session:
            trend = await self.service._overall_trend_insight(session, self.user_id, 30)
        # With no data in either half, should return None
        self.assertIsNone(trend)

    async def test_growth_insight_injected_in_orchestrator_prompt(self):
        """build_final_prompt includes the growth insight block when growth_insight is provided."""
        insight_text = "You've mentioned exam stress 5 times this month."
        prompt = response_orchestrator.build_final_prompt(
            user_name="TestUser",
            personality_profile={},
            personality={},
            emotion={},
            behavior={},
            growth={},
            memories=[],
            tone="reflective",
            strategy="Support",
            current_time_str="Monday, June 15, 2026 10:00 AM",
            profile_context="",
            emotion_timeline=[],
            growth_insight=insight_text,
        )
        self.assertIn("PERSONAL GROWTH OBSERVATION:", prompt)
        self.assertIn(insight_text, prompt)

    async def test_no_growth_insight_block_when_none(self):
        """build_final_prompt does NOT include growth block when growth_insight is None."""
        prompt = response_orchestrator.build_final_prompt(
            user_name="TestUser",
            personality_profile={},
            personality={},
            emotion={},
            behavior={},
            growth={},
            memories=[],
            tone="reflective",
            strategy="Support",
            current_time_str="Monday, June 15, 2026 10:00 AM",
            profile_context="",
            emotion_timeline=[],
            growth_insight=None,
        )
        self.assertNotIn("PERSONAL GROWTH OBSERVATION:", prompt)

    async def test_get_top_insight_for_chat_returns_none_when_empty(self):
        """get_top_insight_for_chat returns None when there are no insights."""
        async with self.session_maker() as session:
            result = await self.service.get_top_insight_for_chat(session, self.user_id)
        self.assertIsNone(result)
