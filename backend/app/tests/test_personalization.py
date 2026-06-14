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
