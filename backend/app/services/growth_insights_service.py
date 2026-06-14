"""
Growth Insights Service – derives observable personal growth patterns from existing data.

Analyses MoodLog, Memory, and KnowledgeGraphRelation tables to generate
human-readable insight strings that Esona can surface in the Dashboard and
occasionally reference in chat conversations.

No new LLM calls or external services required; all analytics are pure SQL
aggregation and keyword extraction over data already collected.
"""

import logging
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.models.mood_log import MoodLog
from app.models.knowledge_graph import KnowledgeGraphRelation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword taxonomy for topic detection inside memory content
# ---------------------------------------------------------------------------

TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "exam stress": [
        "exam", "exams", "test", "tests", "finals", "midterms", "quiz",
        "assessment", "semester", "study", "studying", "cram", "revision",
    ],
    "internship / placement": [
        "internship", "placement", "interview", "offer", "campus", "recruit",
        "job", "hr", "resume", "cv", "shortlist", "oa", "online assessment",
    ],
    "AI / coding": [
        "ai", "ml", "machine learning", "deep learning", "coding", "code",
        "programming", "python", "project", "llm", "model", "research",
        "algorithm", "github", "hackathon",
    ],
    "sleep / fatigue": [
        "sleep", "tired", "exhausted", "fatigue", "insomnia", "rest",
        "burnout", "energy", "nap", "sleepy", "awake all night",
    ],
    "social / relationships": [
        "friend", "friends", "family", "relationship", "lonely", "alone",
        "girlfriend", "boyfriend", "crush", "roommate", "people", "social",
    ],
    "self-doubt / confidence": [
        "doubt", "confident", "confidence", "imposter", "worth", "failure",
        "failed", "loser", "not good enough", "stupid", "useless",
    ],
    "motivation / productivity": [
        "motivat", "productive", "productivity", "procrastinat", "focus",
        "distract", "goal", "habit", "routine", "disciplin",
    ],
}

# Emotions that count as "positive" for the positive-correlation analysis
POSITIVE_EMOTION_LABELS = {"happy", "calm", "motivated", "confident", "excited", "hopeful"}


# ---------------------------------------------------------------------------
# Result schemas (dataclasses for internal use — Pydantic models in schemas.py)
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field


@dataclass
class GrowthInsightItem:
    icon: str
    category: str
    observation: str
    timeframe: str
    count: Optional[int] = None
    trend: str = "stable"  # "rising" | "falling" | "stable"


@dataclass
class GrowthInsightsResult:
    insights: List[GrowthInsightItem] = field(default_factory=list)
    generated_at: str = ""
    total_logs: int = 0
    total_memories: int = 0


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------


class GrowthInsightsService:
    """
    Derives observable growth patterns from existing database data.

    All methods accept an open `AsyncSession` and a `user_id` (str or UUID).
    They are designed to be non-blocking and resilient — any exception is logged
    and an empty result is returned instead of propagating the error.
    """

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def generate_insights(
        self,
        db: AsyncSession,
        user_id: Any,
        days: int = 30,
    ) -> GrowthInsightsResult:
        """
        Orchestrates all analytics and returns a consolidated GrowthInsightsResult.
        At most ~10 insights are returned, ordered by significance.
        """
        try:
            user_uuid = _to_uuid(user_id)
            insights: List[GrowthInsightItem] = []

            # 1. Emotion frequency patterns from MoodLog
            emotion_insights = await self._emotion_frequency_insights(db, user_uuid, days)
            insights.extend(emotion_insights)

            # 2. Topic frequency patterns from Memory content
            topic_insights = await self._topic_frequency_insights(db, user_uuid, days)
            insights.extend(topic_insights)

            # 3. Positive mood correlations
            positive_insights = await self._positive_correlation_insights(db, user_uuid, days)
            insights.extend(positive_insights)

            # 4. Knowledge graph–based character insights
            graph_insights = await self._graph_character_insights(db, user_uuid)
            insights.extend(graph_insights)

            # 5. Mood trend insight (improving / declining / stable)
            trend_insight = await self._overall_trend_insight(db, user_uuid, days)
            if trend_insight:
                insights.append(trend_insight)

            # Count totals for metadata
            total_logs = await self._count_logs(db, user_uuid)
            total_memories = await self._count_memories(db, user_uuid)

            # Sort: put higher-count insights first, then stable ones
            insights.sort(key=lambda x: (x.count or 0), reverse=True)

            return GrowthInsightsResult(
                insights=insights[:10],
                generated_at=datetime.now(timezone.utc).isoformat(),
                total_logs=total_logs,
                total_memories=total_memories,
            )

        except Exception as exc:
            logger.error(f"GrowthInsightsService.generate_insights failed: {exc}", exc_info=True)
            return GrowthInsightsResult(generated_at=datetime.now(timezone.utc).isoformat())

    # ------------------------------------------------------------------ #
    # Single top insight (for chat injection)
    # ------------------------------------------------------------------ #

    async def get_top_insight_for_chat(
        self,
        db: AsyncSession,
        user_id: Any,
        days: int = 30,
    ) -> Optional[str]:
        """
        Returns a single human-readable insight sentence for Esona to
        optionally reference in a chat system prompt.
        Returns None if no meaningful insight is available.
        """
        try:
            result = await self.generate_insights(db, user_id, days)
            if result.insights:
                return result.insights[0].observation
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------ #
    # 1. Emotion frequency insights
    # ------------------------------------------------------------------ #

    async def _emotion_frequency_insights(
        self,
        db: AsyncSession,
        user_uuid: uuid.UUID,
        days: int,
    ) -> List[GrowthInsightItem]:
        """Count emotion label occurrences in MoodLog for the given window."""
        try:
            since = _since(days)
            result = await db.execute(
                select(
                    MoodLog.detected_emotion,
                    func.count(MoodLog.id).label("cnt"),
                )
                .where(
                    MoodLog.user_id == user_uuid,
                    MoodLog.detected_emotion.isnot(None),
                    MoodLog.created_at >= since,
                )
                .group_by(MoodLog.detected_emotion)
                .order_by(func.count(MoodLog.id).desc())
            )
            rows = result.all()
            if not rows:
                return []

            insights: List[GrowthInsightItem] = []
            total = sum(r.cnt for r in rows)

            for row in rows[:3]:  # Top 3 emotions only
                emotion = (row.detected_emotion or "neutral").lower()
                cnt = row.cnt
                pct = round(cnt / total * 100) if total > 0 else 0

                # Skip neutral if it dominates trivially
                if emotion == "neutral" and pct > 60:
                    continue

                icon, category = _emotion_meta(emotion)
                observation = _emotion_observation(emotion, cnt, days)

                insights.append(GrowthInsightItem(
                    icon=icon,
                    category=category,
                    observation=observation,
                    timeframe=f"Last {days} days",
                    count=cnt,
                    trend=_emotion_trend(emotion),
                ))

            return insights

        except Exception as exc:
            logger.warning(f"_emotion_frequency_insights failed: {exc}")
            return []

    # ------------------------------------------------------------------ #
    # 2. Topic frequency insights from Memory content
    # ------------------------------------------------------------------ #

    async def _topic_frequency_insights(
        self,
        db: AsyncSession,
        user_uuid: uuid.UUID,
        days: int,
    ) -> List[GrowthInsightItem]:
        """Scan Memory.memory_content for topic keyword frequency."""
        try:
            since = _since(days)
            result = await db.execute(
                select(Memory.memory_content)
                .where(
                    Memory.user_id == user_uuid,
                    Memory.created_at >= since,
                )
            )
            texts: List[str] = [r for r in result.scalars().all() if r]
            if not texts:
                return []

            combined = " ".join(texts).lower()
            topic_counts: Dict[str, int] = {}

            for topic, keywords in TOPIC_KEYWORDS.items():
                count = 0
                for kw in keywords:
                    count += len(re.findall(r'\b' + re.escape(kw) + r'\b', combined))
                if count >= 2:  # Only report topics with at least 2 occurrences
                    topic_counts[topic] = count

            if not topic_counts:
                return []

            # Return top 2 topics
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            insights: List[GrowthInsightItem] = []

            for topic, count in sorted_topics[:2]:
                icon, category, observation = _topic_meta(topic, count, days)
                insights.append(GrowthInsightItem(
                    icon=icon,
                    category=category,
                    observation=observation,
                    timeframe=f"Last {days} days",
                    count=count,
                    trend="rising" if count >= 5 else "stable",
                ))

            return insights

        except Exception as exc:
            logger.warning(f"_topic_frequency_insights failed: {exc}")
            return []

    # ------------------------------------------------------------------ #
    # 3. Positive mood correlation insights
    # ------------------------------------------------------------------ #

    async def _positive_correlation_insights(
        self,
        db: AsyncSession,
        user_uuid: uuid.UUID,
        days: int,
    ) -> List[GrowthInsightItem]:
        """
        Identifies the topic most frequently co-occurring with positive mood logs.
        Positive = happiness > 0.6 OR motivation > 0.6.
        """
        try:
            since = _since(days)

            # Fetch memories created within 1 hour of a positive mood log
            positive_logs = await db.execute(
                select(MoodLog.created_at)
                .where(
                    MoodLog.user_id == user_uuid,
                    MoodLog.created_at >= since,
                    (MoodLog.happiness > 0.6) | (MoodLog.motivation > 0.6),
                )
            )
            positive_timestamps = list(positive_logs.scalars().all())

            if not positive_timestamps:
                return []

            # Fetch all memories in the window
            mem_result = await db.execute(
                select(Memory.memory_content, Memory.created_at)
                .where(
                    Memory.user_id == user_uuid,
                    Memory.created_at >= since,
                )
            )
            memories: List[Tuple[str, datetime]] = [
                (r[0], r[1]) for r in mem_result.all() if r[0]
            ]

            if not memories:
                return []

            # Find memories within ±1 hour of a positive log
            positive_texts: List[str] = []
            for mem_text, mem_time in memories:
                mem_dt = mem_time if mem_time.tzinfo else mem_time.replace(tzinfo=timezone.utc)
                for pos_ts in positive_timestamps:
                    pos_dt = pos_ts if pos_ts.tzinfo else pos_ts.replace(tzinfo=timezone.utc)
                    if abs((mem_dt - pos_dt).total_seconds()) < 3600:
                        positive_texts.append(mem_text.lower())
                        break

            if not positive_texts:
                return []

            combined = " ".join(positive_texts)
            topic_counts: Dict[str, int] = {}
            for topic, keywords in TOPIC_KEYWORDS.items():
                count = sum(
                    len(re.findall(r'\b' + re.escape(kw) + r'\b', combined))
                    for kw in keywords
                )
                if count >= 2:
                    topic_counts[topic] = count

            if not topic_counts:
                return []

            best_topic = max(topic_counts, key=lambda t: topic_counts[t])
            best_count = topic_counts[best_topic]

            return [GrowthInsightItem(
                icon="✨",
                category="Positive Trigger",
                observation=(
                    f"Most of your positive conversations are connected to "
                    f"{best_topic} — that seems to genuinely energize you."
                ),
                timeframe=f"Last {days} days",
                count=best_count,
                trend="stable",
            )]

        except Exception as exc:
            logger.warning(f"_positive_correlation_insights failed: {exc}")
            return []

    # ------------------------------------------------------------------ #
    # 4. Knowledge graph character insights
    # ------------------------------------------------------------------ #

    async def _graph_character_insights(
        self,
        db: AsyncSession,
        user_uuid: uuid.UUID,
    ) -> List[GrowthInsightItem]:
        """
        Pull the most recent KG triples for the user and derive a character
        insight, e.g. "You're working on an AI research project."
        """
        try:
            result = await db.execute(
                select(
                    KnowledgeGraphRelation.predicate,
                    KnowledgeGraphRelation.object,
                )
                .where(KnowledgeGraphRelation.user_id == user_uuid)
                .order_by(KnowledgeGraphRelation.updated_at.desc())
                .limit(20)
            )
            triples = result.all()
            if not triples:
                return []

            # Aggregate predicates → objects
            predicate_map: Dict[str, Counter] = {}
            for predicate, obj in triples:
                predicate_map.setdefault(predicate, Counter())[obj] += 1

            insights: List[GrowthInsightItem] = []
            seen_predicates = set()

            for predicate, obj_counter in predicate_map.items():
                if predicate.lower() in seen_predicates:
                    continue
                top_obj = obj_counter.most_common(1)[0][0]
                observation = _graph_observation(predicate, top_obj)
                if observation:
                    insights.append(GrowthInsightItem(
                        icon="🧩",
                        category="About You",
                        observation=observation,
                        timeframe="All time",
                        trend="stable",
                    ))
                    seen_predicates.add(predicate.lower())

                if len(insights) >= 2:
                    break

            return insights

        except Exception as exc:
            logger.warning(f"_graph_character_insights failed: {exc}")
            return []

    # ------------------------------------------------------------------ #
    # 5. Overall mood trend insight
    # ------------------------------------------------------------------ #

    async def _overall_trend_insight(
        self,
        db: AsyncSession,
        user_uuid: uuid.UUID,
        days: int,
    ) -> Optional[GrowthInsightItem]:
        """
        Compares the average mood score in the first half vs. the second half
        of the time window and returns a trend insight.
        """
        try:
            since = _since(days)
            midpoint = _since(days // 2)

            early_res = await db.execute(
                select(func.avg(MoodLog.mood_score))
                .where(
                    MoodLog.user_id == user_uuid,
                    MoodLog.created_at >= since,
                    MoodLog.created_at < midpoint,
                    MoodLog.mood_score.isnot(None),
                )
            )
            early_avg = early_res.scalar()

            late_res = await db.execute(
                select(func.avg(MoodLog.mood_score))
                .where(
                    MoodLog.user_id == user_uuid,
                    MoodLog.created_at >= midpoint,
                    MoodLog.mood_score.isnot(None),
                )
            )
            late_avg = late_res.scalar()

            if early_avg is None or late_avg is None:
                return None

            early_val = float(early_avg) * 10  # Scale to 1-10
            late_val = float(late_avg) * 10
            delta = late_val - early_val

            if abs(delta) < 0.5:
                trend = "stable"
                observation = (
                    f"Your overall mood has been pretty steady over the last {days} days. "
                    "Consistency is a strength 💪"
                )
            elif delta > 0:
                trend = "rising"
                observation = (
                    f"Your mood has been trending upward over the last {days} days — "
                    f"up {delta:.1f} points on average. Something good is happening ✨"
                )
            else:
                trend = "falling"
                observation = (
                    f"Your mood has dipped a bit over the last {days} days "
                    f"(about {abs(delta):.1f} points). It might be worth checking in on yourself 🌿"
                )

            icon = "📈" if trend == "rising" else ("📉" if trend == "falling" else "➡️")

            return GrowthInsightItem(
                icon=icon,
                category="Mood Trend",
                observation=observation,
                timeframe=f"Last {days} days",
                trend=trend,
            )

        except Exception as exc:
            logger.warning(f"_overall_trend_insight failed: {exc}")
            return None

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    async def _count_logs(self, db: AsyncSession, user_uuid: uuid.UUID) -> int:
        try:
            res = await db.execute(
                select(func.count(MoodLog.id)).where(MoodLog.user_id == user_uuid)
            )
            return res.scalar() or 0
        except Exception:
            return 0

    async def _count_memories(self, db: AsyncSession, user_uuid: uuid.UUID) -> int:
        try:
            res = await db.execute(
                select(func.count(Memory.id)).where(Memory.user_id == user_uuid)
            )
            return res.scalar() or 0
        except Exception:
            return 0


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _to_uuid(user_id: Any) -> uuid.UUID:
    if isinstance(user_id, uuid.UUID):
        return user_id
    return uuid.UUID(str(user_id))


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _emotion_meta(emotion: str) -> Tuple[str, str]:
    mapping = {
        "anxiety": ("😰", "Anxiety Pattern"),
        "anxious": ("😰", "Anxiety Pattern"),
        "stress": ("😓", "Stress Pattern"),
        "stressed": ("😓", "Stress Pattern"),
        "sad": ("💙", "Sadness Pattern"),
        "sadness": ("💙", "Sadness Pattern"),
        "happy": ("😊", "Happiness Trend"),
        "happiness": ("😊", "Happiness Trend"),
        "calm": ("🌿", "Calm State"),
        "motivated": ("🔥", "Motivation Trend"),
        "confident": ("💪", "Confidence Trend"),
        "burnout": ("🪫", "Burnout Pattern"),
        "lonely": ("🌙", "Loneliness Pattern"),
    }
    return mapping.get(emotion, ("💭", "Emotional Pattern"))


def _emotion_observation(emotion: str, count: int, days: int) -> str:
    label = emotion.capitalize()
    templates = {
        "anxiety": f"You've experienced anxiety {count} times in the last {days} days — that's a pattern worth noticing.",
        "anxious": f"Anxiety has shown up {count} times this month. You're carrying a lot.",
        "stress": f"Stress has come up {count} times over the last {days} days.",
        "stressed": f"You've been stressed {count} times recently. Might be time for a proper rest.",
        "sad": f"Sadness has surfaced {count} times this month. Be gentle with yourself.",
        "sadness": f"You've felt sad {count} times recently. That's worth paying attention to.",
        "happy": f"You've logged happiness {count} times in the last {days} days — that's something to celebrate! 🌟",
        "calm": f"You've been calm {count} times this month. Your self-regulation is strong.",
        "motivated": f"Motivation has shown up {count} times recently — keep that momentum going 🔥",
        "burnout": f"Burnout signals have appeared {count} times in the last {days} days. Rest is not optional.",
    }
    return templates.get(emotion, f"{label} has been your most common emotional state lately ({count} times this month).")


def _emotion_trend(emotion: str) -> str:
    """Negative emotions that are increasing are 'rising' (in a concerning sense)."""
    negative = {"anxiety", "anxious", "stress", "stressed", "sad", "sadness", "burnout", "lonely"}
    positive = {"happy", "happiness", "calm", "motivated", "confident"}
    if emotion in negative:
        return "rising"
    if emotion in positive:
        return "rising"  # Rising is good here too — context explained by observation
    return "stable"


def _topic_meta(topic: str, count: int, days: int) -> Tuple[str, str, str]:
    icons = {
        "exam stress": ("📚", "Academic Stress"),
        "internship / placement": ("💼", "Career Focus"),
        "ai / coding": ("🤖", "Tech Interest"),
        "sleep / fatigue": ("😴", "Fatigue Pattern"),
        "social / relationships": ("🫂", "Social Life"),
        "self-doubt / confidence": ("🌱", "Self-Growth"),
        "motivation / productivity": ("⚡", "Productivity"),
    }
    icon, category = icons.get(topic, ("💬", "Recurring Theme"))
    observation = (
        f"You've brought up {topic} {count} times over the last {days} days — "
        "it's clearly on your mind."
    )
    return icon, category, observation


def _graph_observation(predicate: str, obj: str) -> Optional[str]:
    """Convert a KG triple into a human-readable observation."""
    p = predicate.lower().strip()
    o = obj.strip()

    templates = {
        "studies_at": f"You're studying at {o}.",
        "interested_in": f"You have a strong interest in {o}.",
        "working_on": f"You're currently working on {o}.",
        "worried_about": f"You've been worried about {o} lately.",
        "enjoys": f"One thing that brings you joy is {o}.",
        "struggles_with": f"You've mentioned struggling with {o}.",
        "aspires_to": f"You aspire to {o} — that's a meaningful goal.",
        "values": f"You value {o} deeply.",
    }
    return templates.get(p)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

growth_insights_service = GrowthInsightsService()
