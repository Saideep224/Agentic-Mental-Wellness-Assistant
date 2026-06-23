"""
Agent Insights Route – compiles high-level insights for the user profile.
"""

import logging
import uuid
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.emotion_log import EmotionLog
from app.models.user_graph import UserEntity, UserRelationship
from app.models.knowledge_graph import KnowledgeGraphRelation
from app.routes.auth import get_current_user
from app.utils.llm import get_chat_client
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Insights"])


@router.get("/agent-insights")
async def get_agent_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve aggregated agent insights for the authenticated user:
    - Current Mood (most recent detected emotion)
    - Emotion Trend (analysis over recent logs)
    - Important Topics (derived from user entities)
    - Recent Stressors (derived from knowledge graph events & stressors)
    """
    try:
        user_uuid = current_user.id

        # 1. Retrieve Current Mood (last emotion log)
        stmt_last_emotion = (
            select(EmotionLog)
            .where(EmotionLog.user_id == user_uuid)
            .order_by(EmotionLog.timestamp.desc())
            .limit(1)
        )
        res_last_emotion = await db.execute(stmt_last_emotion)
        last_log = res_last_emotion.scalar_one_or_none()
        current_mood = last_log.detected_emotion.capitalize() if last_log else "Neutral"

        # 2. Retrieve last 10 logs for Emotion Trend
        stmt_recent_emotions = (
            select(EmotionLog)
            .where(EmotionLog.user_id == user_uuid)
            .order_by(EmotionLog.timestamp.desc())
            .limit(10)
        )
        res_recent_emotions = await db.execute(stmt_recent_emotions)
        recent_logs = res_recent_emotions.scalars().all()

        emotion_trend = "Stable"
        if len(recent_logs) >= 2:
            try:
                # Use Gemini to generate a premium descriptive trend (e.g. "Improving", "Fluctuating", "Gradual Recovery")
                emotions_list = [log.detected_emotion for log in recent_logs]
                # Reverse to make it chronological (oldest to newest)
                emotions_list.reverse()
                emotions_str = ", ".join(emotions_list)

                client = get_chat_client()
                trend_prompt = (
                    f"Analyze this chronological list of recent user emotions: [{emotions_str}].\n"
                    "Determine the emotional trend of the user.\n"
                    "Provide a concise, 1-3 word description (e.g., 'Improving', 'Stable', 'Fluctuating', 'Anxious', 'Gradual Recovery').\n"
                    "Output ONLY the description, no explanation, no period."
                )
                response = await client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": "You are a trend analysis tool. Respond only with the trend description."},
                        {"role": "user", "content": trend_prompt}
                    ],
                    temperature=0.1,
                )
                emotion_trend = response.choices[0].message.content.strip()
            except Exception as trend_err:
                logger.warning(f"Failed to generate dynamic trend with LLM: {trend_err}")
                # Fallback to simple rule-based trend
                emotions_set = set(log.detected_emotion.lower() for log in recent_logs[:3])
                if "happiness" in emotions_set or "excitement" in emotions_set:
                    emotion_trend = "Improving"
                elif "sadness" in emotions_set or "loneliness" in emotions_set or "anxiety" in emotions_set:
                    emotion_trend = "Stressed"
                else:
                    emotion_trend = "Stable"
        elif len(recent_logs) == 1:
            emotion_trend = "Establishing Baseline"

        # 3. Retrieve Important Topics (from UserEntity)
        stmt_entities = select(UserEntity).where(UserEntity.user_id == user_uuid)
        res_entities = await db.execute(stmt_entities)
        entities = res_entities.scalars().all()

        # Map entity types to nice topics or extract unique entities
        topic_mapping = {
            "relationship": "Relationships",
            "stressor": "Recent Stressors",
            "event": "Life Events",
            "finance": "Career & Finance",
            "education": "Studies & Academics",
            "person": "Social Life",
        }
        
        topics_set = set()
        specific_topics = []
        for ent in entities:
            # Add type category mapping
            mapped_cat = topic_mapping.get(ent.type.lower())
            if mapped_cat:
                topics_set.add(mapped_cat)
            
            # Add specific important entity names (excluding common words)
            name = ent.entity.capitalize()
            if name not in ["User", "Buddy", "I", "Me"] and len(name) > 2:
                specific_topics.append(name)
        
        # Merge topics
        important_topics = list(topics_set)
        # If we have specific entities, add the top ones
        for t in specific_topics[:3]:
            if t not in important_topics:
                important_topics.append(t)

        # Fallback topics if none extracted yet
        if not important_topics:
            important_topics = ["General Wellbeing", "Self Reflection"]

        # 4. Retrieve Recent Stressors (from entities of type 'stressor' and negative events in KG)
        stmt_kg = select(KnowledgeGraphRelation).where(
            KnowledgeGraphRelation.user_id == user_uuid,
            KnowledgeGraphRelation.predicate == "event"
        )
        res_kg = await db.execute(stmt_kg)
        kg_relations = res_kg.scalars().all()

        stressors_set = set()
        # Add entities marked as stressors
        for ent in entities:
            if ent.type.lower() == "stressor":
                stressors_set.add(ent.entity.capitalize())

        # For events, let's verify if they are associated with negative emotions
        negative_emotions = ["sadness", "anger", "fear", "anxiety", "frustration", "loneliness"]
        for rel in kg_relations:
            # Find if there is an emotion associated with this event
            event_name = rel.object
            stmt_evt_emo = select(KnowledgeGraphRelation).where(
                KnowledgeGraphRelation.user_id == user_uuid,
                KnowledgeGraphRelation.subject == event_name,
                KnowledgeGraphRelation.predicate == "emotion"
            )
            res_evt_emo = await db.execute(stmt_evt_emo)
            emotions_associated = res_evt_emo.scalars().all()
            
            is_stressful = False
            for emo_rel in emotions_associated:
                if emo_rel.object.lower() in negative_emotions:
                    is_stressful = True
                    break
            
            # If the event itself is inherently stressful (e.g. breakup, exam, conflict, loss) or mapped to negative emotion
            stress_keywords = ["breakup", "exam", "failed", "fired", "scared", "fight", "conflict", "lonely", "stress"]
            if is_stressful or any(kw in event_name.lower() for kw in stress_keywords):
                stressors_set.add(event_name.capitalize())

        recent_stressors = list(stressors_set)
        if not recent_stressors:
            recent_stressors = ["None Identified Yet"]

        return {
            "current_mood": current_mood,
            "emotion_trend": emotion_trend,
            "important_topics": important_topics[:5],
            "recent_stressors": recent_stressors[:5]
        }

    except Exception as e:
        logger.error(f"Error compiling agent insights: {e}", exc_info=True)
        return {
            "current_mood": "Neutral",
            "emotion_trend": "Stable",
            "important_topics": ["General Wellbeing"],
            "recent_stressors": ["None Identified Yet"]
        }
