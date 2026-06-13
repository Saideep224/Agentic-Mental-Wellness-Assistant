"""
Recommendation Service – builds a Personal Comfort Kit from stored user interests,
hobbies, coping mechanisms, and knowledge graph relationships.

The kit is assembled when a negative emotion is detected (Stress, Anxiety, Sadness,
Frustration, Loneliness) and injected into the LLM system prompt so Esona can weave
contextual, interest-aware suggestions into its response naturally.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.profile_service import profile_service

logger = logging.getLogger(__name__)

# Emotions that trigger comfort kit assembly
NEGATIVE_EMOTIONS = {"stress", "anxiety", "sadness", "frustration", "loneliness"}

# Interest-to-activity mapping for contextual suggestions
INTEREST_ACTIVITY_MAP = {
    # Music
    "music": [
        "put on a lo-fi / study playlist",
        "listen to something calming or whatever matches your mood right now",
        "throw on some music and just zone out for a bit",
    ],
    "singing": [
        "hum or sing something — even quietly to yourself",
        "blast a song that matches exactly how you feel right now",
    ],
    # Anime / Shows
    "anime": [
        "rewatch a comfort anime episode",
        "start something light and feel-good on Crunchyroll",
        "pick an anime that you associate with feeling cozy",
    ],
    "movies": [
        "put on a comfort movie you've seen a hundred times",
        "find something lowkey on Netflix and just decompress",
    ],
    "series": [
        "binge an episode or two of something you've been meaning to watch",
        "revisit a series that always makes you feel better",
    ],
    "shows": [
        "find something easy to watch and just chill",
    ],
    # Creative
    "editing": [
        "do a short creative editing session — channel the energy into something",
        "open your editing project and just tinker for 15 mins",
    ],
    "drawing": [
        "sketch something — even random doodles help",
        "do a quick drawing, doesn't have to be anything serious",
    ],
    "writing": [
        "write it out — even just journaling privately can help",
        "open a doc and brain-dump everything without judgment",
    ],
    "photography": [
        "go take a few photos of anything around you",
        "look through your camera roll — nostalgia can actually help",
    ],
    "art": [
        "do something creative, even just doodle",
        "channel it into something artistic",
    ],
    # Gaming
    "gaming": [
        "play something casual or mindless for a bit",
        "hop on a game that doesn't require intense focus",
        "if gaming is your stress outlet, use it — a little break won't hurt",
    ],
    "games": [
        "play something low-stakes for a while",
    ],
    # Reading
    "reading": [
        "pick up a book you've been meaning to read",
        "even a few pages of something good can shift your headspace",
    ],
    "books": [
        "read something light — fiction especially can be a good escape",
    ],
    # Physical
    "walking": [
        "go for a short walk, even just around the block",
        "step outside for 10 minutes — fresh air genuinely helps",
    ],
    "running": [
        "a short run or jog can burn through the tension",
    ],
    "gym": [
        "hit a quick workout — physical movement can shift your state fast",
    ],
    "exercise": [
        "even 10 minutes of movement helps — stretch, walk, anything",
    ],
    "yoga": [
        "do a short yoga or stretching session",
        "5 minutes of stretching + breathing can reset you",
    ],
    "sports": [
        "play something physical to burn through the stress",
    ],
    # Social
    "cooking": [
        "cook or make something — it can be meditative",
        "make your comfort food",
    ],
    "baking": [
        "bake something — the process is genuinely calming",
    ],
    # Tech / Coding
    "coding": [
        "work on a side project you actually enjoy — not the stressful one",
        "explore a fun coding problem or tutorial for a bit",
    ],
    "programming": [
        "build something small just for fun — no pressure",
    ],
}

# Coping mechanism → natural phrasing
COPING_PHRASE_MAP = {
    "listening to music": "put on music",
    "music": "put on some music",
    "walks": "go for a walk",
    "walking": "take a short walk",
    "meditation": "try a few minutes of quiet breathing or meditation",
    "breathing exercises": "do a slow breathing exercise",
    "journaling": "write it down in a journal",
    "talking to someone": "reach out to someone you trust",
    "gaming": "play something to decompress",
    "sleeping": "take a short rest if you can",
    "watching shows": "watch something easy",
    "exercise": "get some movement in",
    "drawing": "doodle or draw something",
    "cooking": "make something in the kitchen",
}


@dataclass
class ComfortKit:
    """Assembled personal comfort kit for a user at a given emotional state."""
    emotional_trigger: str = ""
    interests: List[str] = field(default_factory=list)
    hobbies: List[str] = field(default_factory=list)
    coping_activities: List[str] = field(default_factory=list)
    comfort_environment: str = ""
    activity_suggestions: List[str] = field(default_factory=list)
    is_empty: bool = True


class RecommendationService:
    """
    Builds a Personal Comfort Kit from stored profile data and knowledge graph
    relationships, then formats it for injection into the LLM system prompt.
    """

    NEGATIVE_EMOTIONS = NEGATIVE_EMOTIONS

    async def build_comfort_kit(
        self,
        db: AsyncSession,
        user_id: Union[uuid.UUID, str],
        detected_emotion: str,
        graph_relationships: Optional[List[str]] = None,
        personality_profile: Optional[dict] = None,
    ) -> ComfortKit:
        """
        Assemble a comfort kit for the user based on their stored profile and
        knowledge graph. Returns an empty kit for neutral/positive emotions.
        """
        emotion_lower = detected_emotion.lower()
        if emotion_lower not in NEGATIVE_EMOTIONS:
            return ComfortKit(is_empty=True)

        kit = ComfortKit(emotional_trigger=detected_emotion)

        # ── 1. Retrieve UserPersonalProfile ───────────────────────
        try:
            profile = await profile_service.get_profile(db, user_id)
        except Exception as e:
            logger.warning(f"[RecommendationService] Could not fetch profile: {e}")
            profile = None

        # ── 2. Extract interests & hobbies from profile ───────────
        if profile:
            raw_interests = profile.interests or []
            raw_hobbies = profile.hobbies or []
            kit.interests = [i.strip() for i in raw_interests if i and i.strip()]
            kit.hobbies = [h.strip() for h in raw_hobbies if h and h.strip()]

            # Coping mechanisms → natural phrases
            raw_coping = profile.coping_mechanisms or []
            for item in raw_coping:
                item_lower = item.lower().strip()
                phrase = COPING_PHRASE_MAP.get(item_lower, item.strip())
                if phrase:
                    kit.coping_activities.append(phrase)

        # ── 3. Pull extra interests from knowledge graph triples ──
        if graph_relationships:
            for rel_str in graph_relationships:
                # Format: "- User -> Likes -> Anime"
                parts = [p.strip() for p in rel_str.strip("- ").split("->")]
                if len(parts) == 3:
                    predicate = parts[1].strip()
                    obj = parts[2].strip()
                    if predicate in ("Likes", "Hobby", "CopingMechanism"):
                        target_list = kit.interests if predicate == "Likes" else kit.hobbies
                        if obj not in target_list:
                            target_list.append(obj)

        # ── 4. Pull comfort environment from personality_profile ──
        if personality_profile:
            comfort_prefs = personality_profile.get("comfort_preferences", {})
            if isinstance(comfort_prefs, dict):
                safe_env = comfort_prefs.get("safest_environment", "")
                if safe_env:
                    kit.comfort_environment = safe_env

        # ── 5. Build contextual activity suggestions ───────────────
        all_interests = list(dict.fromkeys(
            [i.lower() for i in kit.interests + kit.hobbies]
        ))

        suggestions = []
        for interest in all_interests:
            matches = INTEREST_ACTIVITY_MAP.get(interest, [])
            if matches and len(suggestions) < 3:
                # Pick only the first suggestion per interest to avoid overwhelm
                suggestions.append(matches[0])

        # Add one coping activity if room remains
        if kit.coping_activities and len(suggestions) < 3:
            first_coping = kit.coping_activities[0]
            if first_coping not in suggestions:
                suggestions.append(first_coping)

        kit.activity_suggestions = suggestions[:3]  # Hard cap at 3
        kit.is_empty = not bool(suggestions or kit.interests or kit.hobbies)

        logger.info(
            f"[RecommendationService] Built comfort kit for user {user_id} | "
            f"emotion={detected_emotion} | suggestions={kit.activity_suggestions}"
        )
        return kit

    def format_kit_for_prompt(self, kit: ComfortKit) -> str:
        """
        Format the comfort kit as a structured string block for the system prompt.
        Returns an empty string if the kit is empty or emotion is not negative.
        """
        if kit.is_empty or not kit.activity_suggestions:
            return ""

        lines = [
            "=================================================",
            f"PERSONAL COMFORT KIT (detected emotion: {kit.emotional_trigger}):",
        ]

        if kit.interests:
            lines.append(f"User's Interests: {', '.join(kit.interests)}")
        if kit.hobbies:
            lines.append(f"User's Hobbies: {', '.join(kit.hobbies)}")
        if kit.coping_activities:
            lines.append(f"Coping Activities They Use: {', '.join(kit.coping_activities)}")
        if kit.comfort_environment:
            lines.append(f"Comfort Environment: {kit.comfort_environment}")

        lines.append("")
        lines.append("Contextual Activity Suggestions (pick 1–2 at most, use naturally):")
        for suggestion in kit.activity_suggestions:
            lines.append(f"  - {suggestion}")

        lines.append("")
        lines.append("COMFORT KIT USAGE RULES:")
        lines.append("- Do NOT list suggestions as a therapy bullet-point prescription.")
        lines.append("- Weave 1–2 suggestions in casually, like a friend texting: "
                     "\"have you tried putting on some lo-fi?\" or "
                     "\"honestly watch an ep of something comfort-y ngl\"")
        lines.append("- Only suggest if it feels natural. If the user is clearly just "
                     "venting and not asking for suggestions, skip them entirely.")
        lines.append("- Never say 'based on your interests' or any robotic phrasing.")
        lines.append("=================================================")

        return "\n".join(lines)


# Export standard singleton
recommendation_service = RecommendationService()
