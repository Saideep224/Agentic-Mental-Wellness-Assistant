"""
Knowledge Graph Service – extracts, stores, and retrieves semantic relationship triples for users.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.knowledge_graph import KnowledgeGraphRelation
from app.utils.llm import get_chat_client

logger = logging.getLogger(__name__)

KNOWLEDGE_GRAPH_EXTRACTION_PROMPT = """You are a Knowledge Graph Relationship Extractor.
Extract semantic triples representing facts about the user from the user's message.

Instructions:
1. Identify facts about the user's current situation, thoughts, emotions, and life details.
2. Format them as (subject, predicate, object) triples.
3. The subject MUST be "{user_name}".
4. The predicate should be a singular term representing the relationship type. You MUST use one of these exact predicates:
   - Emotion (the user's current or stated emotional state, e.g. Anger, Sadness, Joy)
   - Person (any person mentioned in the user's life, e.g. Girlfriend, Father, Boss, Friend)
   - Relationship (the type of relationship, e.g. Toxic, Married, Distant, Boyfriend)
   - Goal (aspirations, targets, focus areas, e.g. Find Job, Pass Exam, Stay Calm)
   - Problem (issues, struggles, stressors, e.g. Financial Distress, Sleep Issues, Toxic Girlfriend)
   - LifeEvent (significant life events, e.g. Breakup, Graduation, Job Loss, New Job)
   - Health (physical or mental health states/symptoms, e.g. Chronic Pain, Anxiety, ADHD)
   - Finance (financial status, issues, or goals, e.g. Debt, Broke, Save Money)
   - Education (educational details, e.g. CS Student, College, University, Exams)
5. The object should be a short, clean, capitalized entity or phrase (e.g. "Toxic Girlfriend", "Anxiety", "CS Student", "Breakup").
6. Provide a confidence score between 0.0 and 1.0 for each relationship.

Output ONLY a valid JSON object matching this schema:
{{
  "relations": [
    {{"subject": "{user_name}", "predicate": "Problem", "object": "Toxic Girlfriend", "confidence": 0.95}},
    {{"subject": "{user_name}", "predicate": "Finance", "object": "Lost All Money", "confidence": 0.90}},
    {{"subject": "{user_name}", "predicate": "Emotion", "object": "Anger", "confidence": 0.85}}
  ]
}}
"""


class KnowledgeGraphService:
    """Manages extraction, persistence, and querying of user graph relationships."""

    async def extract_relationships(self, message: str, user_name: str = "User") -> List[Dict[str, Any]]:
        """Call LLM client to extract subject-predicate-object triples from user's message."""
        if not message or len(message.strip()) < 2:
            return []

        try:
            client = get_chat_client()
            prompt = KNOWLEDGE_GRAPH_EXTRACTION_PROMPT.format(user_name=user_name)
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"User message: {message}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            return parsed.get("relations", [])
        except Exception as e:
            logger.error(f"Failed to extract relationships from message: {e}", exc_info=True)
            return []

    async def store_relationships(self, db: AsyncSession, user_id: uuid.UUID, relations: List[Dict[str, Any]]) -> None:
        """Store semantic relationships in the database, avoiding duplicate triples."""
        for rel in relations:
            subject = rel.get("subject", "User").strip()
            predicate = rel.get("predicate", "").strip()
            obj = rel.get("object", "").strip()
            confidence = float(rel.get("confidence", 1.0))

            if not predicate or not obj:
                continue

            try:
                # Check if this exact triple already exists for the user
                result = await db.execute(
                    select(KnowledgeGraphRelation).where(
                        KnowledgeGraphRelation.user_id == user_id,
                        KnowledgeGraphRelation.subject == subject,
                        KnowledgeGraphRelation.predicate == predicate,
                        KnowledgeGraphRelation.object == obj
                    )
                )
                existing = result.scalars().first()
                if existing:
                    existing.confidence = confidence
                    existing.updated_at = datetime.now(timezone.utc)
                    db.add(existing)
                else:
                    new_rel = KnowledgeGraphRelation(
                        user_id=user_id,
                        subject=subject,
                        predicate=predicate,
                        object=obj,
                        confidence=confidence
                    )
                    db.add(new_rel)
                await db.flush()
            except Exception as e:
                logger.error(f"Failed to store relationship {rel} for user {user_id}: {e}", exc_info=True)

    async def retrieve_relationships(self, db: AsyncSession, user_id: uuid.UUID) -> List[KnowledgeGraphRelation]:
        """Fetch all stored graph relationships for a user."""
        try:
            result = await db.execute(
                select(KnowledgeGraphRelation)
                .where(KnowledgeGraphRelation.user_id == user_id)
                .order_by(KnowledgeGraphRelation.updated_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to retrieve relationships for user {user_id}: {e}", exc_info=True)
            return []

    async def retrieve_relevant_relationships(
        self, db: AsyncSession, user_id: uuid.UUID, message: str
    ) -> List[KnowledgeGraphRelation]:
        """Query relevant relationships based on matching message keywords, falling back to top 40 recent."""
        all_rels = await self.retrieve_relationships(db, user_id)
        if not all_rels:
            return []

        message_lower = message.lower()
        relevant = []
        for rel in all_rels:
            # Check if predicate or object is mentioned in the message
            if rel.predicate.lower() in message_lower or rel.object.lower() in message_lower:
                relevant.append(rel)

        # Fallback to top 40 recent if no direct text matches are found
        if not relevant:
            relevant = all_rels[:40]

        return relevant


# Export standard singleton
knowledge_graph_service = KnowledgeGraphService()
