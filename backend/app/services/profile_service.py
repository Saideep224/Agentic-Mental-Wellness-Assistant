"""
Profile Service – manages the personalized UserPersonalProfile CRUD and context generation.
"""

import logging
import uuid
from typing import Dict, Any, Optional, Union, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_personal_profile import UserPersonalProfile

logger = logging.getLogger(__name__)


class ProfileService:
    """Manages the creation, retrieval, and updating of personalization profiles."""

    async def get_profile(self, db: AsyncSession, user_id: Union[uuid.UUID, str]) -> Optional[UserPersonalProfile]:
        """Fetch the personal profile for a user."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        try:
            result = await db.execute(
                select(UserPersonalProfile).where(UserPersonalProfile.user_id == user_id)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching UserPersonalProfile for {user_id}: {e}", exc_info=True)
            return None

    async def create_profile(
        self, db: AsyncSession, user_id: Union[uuid.UUID, str], profile_data: Dict[str, Any]
    ) -> UserPersonalProfile:
        """Create a new personal profile for a user."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        profile = UserPersonalProfile(
            user_id=user_id,
            name=profile_data.get("name"),
            age=str(profile_data.get("age")) if profile_data.get("age") is not None else None,
            profession=profile_data.get("profession"),
            student_year=profile_data.get("student_year"),
            communication_style=profile_data.get("communication_style"),
            interests=profile_data.get("interests") or [],
            hobbies=profile_data.get("hobbies") or [],
            goals=profile_data.get("goals") or [],
            stress_triggers=profile_data.get("stress_triggers") or [],
            coping_mechanisms=profile_data.get("coping_mechanisms") or [],
            support_system=profile_data.get("support_system"),
            sleep_habits=profile_data.get("sleep_habits"),
        )
        db.add(profile)
        await db.flush()
        return profile

    async def update_profile(
        self, db: AsyncSession, user_id: Union[uuid.UUID, str], profile_data: Dict[str, Any]
    ) -> UserPersonalProfile:
        """Update (or create if missing) a user's personal profile."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        profile = await self.get_profile(db, user_id)
        if not profile:
            return await self.create_profile(db, user_id, profile_data)

        # Standard field mapping
        string_fields = ["name", "age", "profession", "student_year", "communication_style", "support_system", "sleep_habits"]
        list_fields = ["interests", "hobbies", "goals", "stress_triggers", "coping_mechanisms"]

        for field in string_fields:
            if field in profile_data:
                val = profile_data[field]
                setattr(profile, field, str(val) if val is not None else None)

        for field in list_fields:
            if field in profile_data:
                val = profile_data[field]
                if isinstance(val, str):
                    # Fallback in case list is passed as a raw string
                    setattr(profile, field, [val] if val else [])
                elif isinstance(val, list):
                    setattr(profile, field, val)
                else:
                    setattr(profile, field, [])

        db.add(profile)
        await db.flush()
        return profile

    async def build_profile_context(self, db: AsyncSession, user_id: Union[uuid.UUID, str]) -> str:
        """Build the formatted profile context block to inject into the system prompt."""
        profile = await self.get_profile(db, user_id)
        if not profile:
            return ""

        lines = ["User Profile:"]
        if profile.name:
            lines.append(f"Name: {profile.name}")
        if profile.age:
            lines.append(f"Age: {profile.age}")
        if profile.profession:
            lines.append(f"Profession: {profile.profession}")
        if profile.student_year and profile.student_year.lower() != "n/a":
            lines.append(f"Student Year: {profile.student_year}")
        if profile.communication_style:
            lines.append(f"Communication Style: {profile.communication_style}")
        if profile.goals:
            lines.append(f"Goals: {', '.join(profile.goals)}")
        if profile.stress_triggers:
            lines.append(f"Stress Triggers: {', '.join(profile.stress_triggers)}")
        if profile.interests:
            lines.append(f"Interests: {', '.join(profile.interests)}")
        if profile.hobbies:
            lines.append(f"Hobbies: {', '.join(profile.hobbies)}")
        if profile.coping_mechanisms:
            lines.append(f"Coping Mechanisms: {', '.join(profile.coping_mechanisms)}")
        if profile.support_system:
            lines.append(f"Support System: {profile.support_system}")
        if profile.sleep_habits:
            lines.append(f"Sleep Habits: {profile.sleep_habits}")

        return "\n".join(lines)


# Export standard singleton
profile_service = ProfileService()
