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
from app.utils.llm import generate_chat_completion_with_fallback, get_chat_client

logger = logging.getLogger(__name__)

KNOWLEDGE_GRAPH_EXTRACTION_PROMPT = """You are a Knowledge Graph Relationship Extractor.
Analyze the user's message and extract:
1. Entities: Any key actors, objects, or concepts in the user's life (e.g. "girlfriend", "exams", "boss"). Format as {"entity": "entity_name", "type": "relationship" | "stressor" | "event" | "finance" | "education" | "person" | "other"}.
2. Relationships: The semantic connections between the user and entities (e.g. source="user", relationship="has_relationship", target="girlfriend"). Format as {"source": "source_entity", "relationship": "relationship_type", "target": "target_entity"}.
3. Emotional Events: Any life event described with an associated emotion (e.g. event="breakup", emotion="sadness"). Format as {"event": "event_name", "emotion": "emotion_name"}.

Input:
- User Message: "{message}"

Output ONLY a valid JSON matching this schema:
{{
  "entities": [
    {{"entity": "girlfriend", "type": "relationship"}}
  ],
  "relationships": [
    {{"source": "user", "relationship": "has_relationship", "target": "girlfriend"}}
  ],
  "events": [
    {{"event": "breakup", "emotion": "sadness"}}
  ]
}}
"""

from app.models.user_graph import UserEntity, UserRelationship

class KnowledgeGraphService:
    """Manages extraction, persistence, and querying of user graph relationships."""

    async def extract_relationships(self, message: str, user_name: str = "User") -> Any:
        """Call LLM client to extract subject-predicate-object triples from user's message."""
        if not message or len(message.strip()) < 2:
            return {"entities": [], "relationships": [], "events": []}

        try:
            # Use replace instead of format to avoid KeyErrors on template braces
            prompt = KNOWLEDGE_GRAPH_EXTRACTION_PROMPT.replace("{message}", message)
            raw = await generate_chat_completion_with_fallback(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"User message: {message}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            parsed = json.loads(raw)
            
            # --- USER DIAGNOSTIC LOGS ---
            log_entities = []
            for ent in parsed.get("entities", []):
                log_entities.append({
                    "name": ent.get("entity") or ent.get("name") or "",
                    "type": ent.get("type") or ""
                })
            log_relations = parsed.get("relationships", []) or parsed.get("relations", [])
            print("MESSAGE:", message)
            print("EXTRACTED ENTITIES:", log_entities)
            print("EXTRACTED RELATIONS:", log_relations)
            # -----------------------------
            
            if "relations" in parsed:
                return parsed["relations"]
            return {
                "entities": parsed.get("entities", []),
                "relationships": parsed.get("relationships", []),
                "events": parsed.get("events", [])
            }
        except Exception as e:
            print("MESSAGE:", message)
            print("EXTRACTED ENTITIES:", [])
            print("EXTRACTED RELATIONS:", [])
            logger.error(f"Failed to extract relationships from message: {e}", exc_info=True)
            return {"entities": [], "relationships": [], "events": []}

    async def store_graph_data(self, db: AsyncSession, user_id: uuid.UUID, graph_data: Dict[str, Any]) -> None:
        """Store semantic entities, relationships, and emotional events in the database, avoiding duplicates."""
        # Support legacy relations list inside graph_data dict (backward compatibility with mocks)
        if isinstance(graph_data, list):
            await self.store_relationships(db, user_id, graph_data)
            return
        if isinstance(graph_data, dict) and "relations" in graph_data:
            await self.store_relationships(db, user_id, graph_data["relations"])

        # 1. Store entities
        for ent in graph_data.get("entities", []):
            entity_val = ent.get("entity", "").strip().lower()
            type_val = ent.get("type", "").strip().lower()
            if not entity_val or not type_val:
                continue
            stmt = select(UserEntity).where(
                UserEntity.user_id == user_id,
                UserEntity.entity == entity_val,
                UserEntity.type == type_val
            )
            res = await db.execute(stmt)
            if not res.scalars().first():
                db.add(UserEntity(user_id=user_id, entity=entity_val, type=type_val))

        # 2. Store relationships
        for rel in graph_data.get("relationships", []):
            source = rel.get("source", "").strip().lower()
            rel_name = rel.get("relationship", "").strip().lower()
            target = rel.get("target", "").strip().lower()
            if not source or not rel_name or not target:
                continue
            stmt = select(UserRelationship).where(
                UserRelationship.user_id == user_id,
                UserRelationship.source == source,
                UserRelationship.relationship_name == rel_name,
                UserRelationship.target == target
            )
            res = await db.execute(stmt)
            if not res.scalars().first():
                db.add(UserRelationship(user_id=user_id, source=source, relationship_name=rel_name, target=target))

        # 3. Store events inside knowledge_graph
        for evt in graph_data.get("events", []):
            event_val = evt.get("event", "").strip().lower()
            emotion_val = evt.get("emotion", "").strip().lower()
            if not event_val or not emotion_val:
                continue
            
            # Triple 1: User -> event -> event_val
            stmt1 = select(KnowledgeGraphRelation).where(
                KnowledgeGraphRelation.user_id == user_id,
                KnowledgeGraphRelation.subject == "User",
                KnowledgeGraphRelation.predicate == "event",
                KnowledgeGraphRelation.object == event_val
            )
            res1 = await db.execute(stmt1)
            if not res1.scalars().first():
                db.add(KnowledgeGraphRelation(user_id=user_id, subject="User", predicate="event", object=event_val))
                
            # Triple 2: event_val -> emotion -> emotion_val
            stmt2 = select(KnowledgeGraphRelation).where(
                KnowledgeGraphRelation.user_id == user_id,
                KnowledgeGraphRelation.subject == event_val,
                KnowledgeGraphRelation.predicate == "emotion",
                KnowledgeGraphRelation.object == emotion_val
            )
            res2 = await db.execute(stmt2)
            if not res2.scalars().first():
                db.add(KnowledgeGraphRelation(user_id=user_id, subject=event_val, predicate="emotion", object=emotion_val))
                
        print("Saving to knowledge_graph...")
        try:
            await db.commit()
            
            stmt = select(KnowledgeGraphRelation).where(KnowledgeGraphRelation.user_id == user_id)
            res = await db.execute(stmt)
            inserted = res.scalars().all()
            data_list = []
            for r in inserted:
                data_list.append({
                    "id": str(r.id),
                    "user_id": str(r.user_id),
                    "subject": r.subject,
                    "predicate": r.predicate,
                    "object": r.object,
                    "confidence": r.confidence,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                })
            print("DATA:", data_list)
            print("ERROR: null")
        except Exception as e:
            print("DATA: null")
            print("ERROR:", str(e))
            raise e

    async def retrieve_full_graph_context(self, db: AsyncSession, user_id: uuid.UUID) -> str:
        """Fetch all stored graph relationships, entities, and events for a user and format as text."""
        try:
            # Fetch entities
            ent_stmt = select(UserEntity).where(UserEntity.user_id == user_id)
            ent_res = await db.execute(ent_stmt)
            entities = ent_res.scalars().all()
            
            # Fetch relationships
            rel_stmt = select(UserRelationship).where(UserRelationship.user_id == user_id)
            rel_res = await db.execute(rel_stmt)
            relationships = rel_res.scalars().all()
            
            # Fetch knowledge graph triples
            kg_stmt = select(KnowledgeGraphRelation).where(KnowledgeGraphRelation.user_id == user_id)
            kg_res = await db.execute(kg_stmt)
            kg_triples = kg_res.scalars().all()
            
            lines = []
            if entities:
                lines.append("User Entities:")
                for e in entities:
                    lines.append(f"  - {e.entity} ({e.type})")
            if relationships:
                lines.append("User Relationships:")
                for r in relationships:
                    lines.append(f"  - {r.source} -> {r.relationship_name} -> {r.target}")
            if kg_triples:
                lines.append("Events & Emotional Connections:")
                for k in kg_triples:
                    lines.append(f"  - {k.subject} -> {k.predicate} -> {k.object}")
                    
            return "\n".join(lines) if lines else "None"
        except Exception as e:
            logger.error(f"Failed to retrieve full graph context: {e}")
            return "None"

    # Maintain backward-compatible methods for old calls
    async def store_relationships(self, db: AsyncSession, user_id: uuid.UUID, relations: List[Dict[str, Any]]) -> None:
        """Store semantic triples directly in the knowledge_graph table (compatibility method for unit tests)."""
        for rel in relations:
            sub = rel.get("subject", "User")
            pred = rel.get("predicate", "")
            obj = rel.get("object", "")
            conf = rel.get("confidence", 1.0)
            if not pred or not obj:
                continue
            
            # Check if exists
            stmt = select(KnowledgeGraphRelation).where(
                KnowledgeGraphRelation.user_id == user_id,
                KnowledgeGraphRelation.subject == sub,
                KnowledgeGraphRelation.predicate == pred,
                KnowledgeGraphRelation.object == obj
            )
            res = await db.execute(stmt)
            existing = res.scalars().first()
            if existing:
                existing.confidence = conf
            else:
                db.add(KnowledgeGraphRelation(
                    user_id=user_id,
                    subject=sub,
                    predicate=pred,
                    object=obj,
                    confidence=conf
                ))
        print("Saving to knowledge_graph...")
        try:
            await db.commit()
            
            stmt = select(KnowledgeGraphRelation).where(KnowledgeGraphRelation.user_id == user_id)
            res = await db.execute(stmt)
            inserted = res.scalars().all()
            data_list = []
            for r in inserted:
                data_list.append({
                    "id": str(r.id),
                    "user_id": str(r.user_id),
                    "subject": r.subject,
                    "predicate": r.predicate,
                    "object": r.object,
                    "confidence": r.confidence,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                })
            print("DATA:", data_list)
            print("ERROR: null")
        except Exception as e:
            print("DATA: null")
            print("ERROR:", str(e))
            raise e

    async def retrieve_relationships(self, db: AsyncSession, user_id: uuid.UUID) -> List[KnowledgeGraphRelation]:
        try:
            result = await db.execute(
                select(KnowledgeGraphRelation)
                .where(KnowledgeGraphRelation.user_id == user_id)
                .order_by(KnowledgeGraphRelation.updated_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to retrieve relationships: {e}")
            return []

    async def retrieve_relevant_relationships(
        self, db: AsyncSession, user_id: uuid.UUID, message: str
    ) -> List[KnowledgeGraphRelation]:
        all_rels = await self.retrieve_relationships(db, user_id)
        if not message or not all_rels:
            return all_rels[:5]
        
        # Simple case-insensitive word overlap matching
        words = set(message.lower().split())
        matched = []
        for rel in all_rels:
            # Check subject, predicate, and object
            rel_words = (
                (rel.subject or "").lower().split() +
                (rel.predicate or "").lower().split() +
                (rel.object or "").lower().split()
            )
            if any(w in words for w in rel_words):
                matched.append(rel)
                
        if matched:
            return matched[:5]
        return all_rels[:5]


# Export standard singleton
knowledge_graph_service = KnowledgeGraphService()
