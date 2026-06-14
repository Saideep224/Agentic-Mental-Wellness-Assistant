"""
Unit tests for the Interest-Based Recommendation Service.
Tests: comfort kit assembly, prompt formatting, emotion gating, and empty kit handling.
"""

import os
import uuid
import unittest

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.database import Base

TEST_DB_URL = "sqlite+aiosqlite:///./test_recommendation.db"


class RecommendationServiceTestCase(unittest.IsolatedAsyncioTestCase):
    """Tests for RecommendationService — comfort kit building and formatting."""

    async def asyncSetUp(self):
        from app.services.recommendation_service import recommendation_service, ComfortKit
        self.svc = recommendation_service
        self.ComfortKit = ComfortKit

        self.engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
        self.session_maker = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        self.db = self.session_maker()
        self.user_id = uuid.uuid4()

        # Create a user + personal profile with interests
        from app.models.user import User
        from app.models.user_personal_profile import UserPersonalProfile

        self.user = User(
            id=self.user_id,
            email="rec_test@esona.com",
            name="Tester",
            onboarding_completed=True,
        )
        self.db.add(self.user)

        self.personal_profile = UserPersonalProfile(
            user_id=self.user_id,
            name="Tester",
            profession="College Student",
            interests=["Anime", "Music"],
            hobbies=["Editing", "Gaming"],
            coping_mechanisms=["Listening to music", "Walking"],
        )
        self.db.add(self.personal_profile)
        await self.db.commit()

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()
        if os.path.exists("./test_recommendation.db"):
            try:
                os.remove("./test_recommendation.db")
            except Exception:
                pass

    # ── Test 1: Stress emotion produces a non-empty comfort kit ───────────
    async def test_stress_produces_comfort_kit(self):
        """Stress emotion should build a non-empty comfort kit from profile data."""
        kit = await self.svc.build_comfort_kit(
            db=self.db,
            user_id=self.user_id,
            detected_emotion="Stress",
        )
        self.assertFalse(kit.is_empty, "Kit should not be empty for Stress emotion")
        self.assertIn("Anime", kit.interests)
        self.assertIn("Music", kit.interests)
        self.assertIn("Editing", kit.hobbies)
        self.assertGreater(len(kit.activity_suggestions), 0)

    # ── Test 2: Neutral emotion returns an empty kit ───────────────────────
    async def test_neutral_emotion_returns_empty_kit(self):
        """Neutral or Happy emotion should return an empty kit — no suggestions."""
        for emotion in ("Neutral", "Happy"):
            kit = await self.svc.build_comfort_kit(
                db=self.db,
                user_id=self.user_id,
                detected_emotion=emotion,
            )
            self.assertTrue(kit.is_empty, f"Kit should be empty for {emotion} emotion")
            self.assertEqual(kit.activity_suggestions, [])

    # ── Test 3: Anxiety and Sadness also trigger kit ───────────────────────
    async def test_anxiety_and_sadness_trigger_kit(self):
        """Anxiety and Sadness should also produce a non-empty kit."""
        for emotion in ("Anxiety", "Sadness", "Frustration", "Loneliness"):
            kit = await self.svc.build_comfort_kit(
                db=self.db,
                user_id=self.user_id,
                detected_emotion=emotion,
            )
            self.assertFalse(kit.is_empty, f"Kit should NOT be empty for {emotion}")

    # ── Test 4: Knowledge graph triples enrich the kit ────────────────────
    async def test_graph_relationships_enrich_kit(self):
        """Knowledge graph Likes/Hobby triples should add new interests to the kit."""
        graph_rels = [
            "- User -> Likes -> Drawing",
            "- User -> Hobby -> Cooking",
        ]
        kit = await self.svc.build_comfort_kit(
            db=self.db,
            user_id=self.user_id,
            detected_emotion="Stress",
            graph_relationships=graph_rels,
        )
        self.assertIn("Drawing", kit.interests)
        self.assertIn("Cooking", kit.hobbies)

    # ── Test 5: format_kit_for_prompt produces correct output ─────────────
    def test_format_kit_for_prompt_contains_suggestions(self):
        """format_kit_for_prompt should return a non-empty block with suggestions."""
        kit = self.ComfortKit(
            emotional_trigger="Stress",
            interests=["Music", "Anime"],
            hobbies=["Editing"],
            coping_activities=["put on music"],
            activity_suggestions=[
                "put on a lo-fi / study playlist",
                "rewatch a comfort anime episode",
            ],
            is_empty=False,
        )
        result = self.svc.format_kit_for_prompt(kit)
        self.assertIn("PERSONAL COMFORT KIT", result)
        self.assertIn("lo-fi", result)
        self.assertIn("anime", result.lower())
        self.assertIn("COMFORT KIT USAGE RULES:", result)

    # ── Test 6: Empty kit produces empty prompt block ─────────────────────
    def test_format_empty_kit_returns_empty_string(self):
        """format_kit_for_prompt should return '' for an empty kit."""
        kit = self.ComfortKit(is_empty=True)
        result = self.svc.format_kit_for_prompt(kit)
        self.assertEqual(result, "")

    # ── Test 7: Suggestions capped at 3 ──────────────────────────────────
    async def test_suggestions_capped_at_three(self):
        """Activity suggestions should never exceed 3 items."""
        # Give the user many interests to ensure cap is enforced
        from app.services.profile_service import profile_service
        await profile_service.update_profile(self.db, self.user_id, {
            "interests": ["Music", "Anime", "Reading", "Gaming", "Drawing"],
            "hobbies": ["Editing", "Cooking", "Writing"],
        })
        await self.db.commit()

        kit = await self.svc.build_comfort_kit(
            db=self.db,
            user_id=self.user_id,
            detected_emotion="Anxiety",
        )
        self.assertLessEqual(len(kit.activity_suggestions), 3,
                             "Suggestions must be capped at 3")

    # ── Test 8: Coping mechanisms appear in kit ───────────────────────────
    async def test_coping_mechanisms_included(self):
        """Stored coping mechanisms should be included in the kit."""
        kit = await self.svc.build_comfort_kit(
            db=self.db,
            user_id=self.user_id,
            detected_emotion="Sadness",
        )
        self.assertTrue(
            len(kit.coping_activities) > 0,
            "Coping activities should be extracted from profile"
        )


if __name__ == "__main__":
    unittest.main()
