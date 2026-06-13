"""
Unit and Integration Tests for Knowledge Graph System.
"""

import os
import uuid
import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.database import Base
from app.models import User
from app.models.knowledge_graph import KnowledgeGraphRelation
from app.services.knowledge_graph_service import knowledge_graph_service
from app.orchestrator.response_orchestrator import response_orchestrator

TEST_DB_URL = "sqlite+aiosqlite:///./test_knowledge_graph.db"


class KnowledgeGraphTestCase(unittest.IsolatedAsyncioTestCase):
    """Test suite for the Knowledge Graph extraction, persistence, and injection."""

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
            email="kg_test@esona.com",
            name="Alice",
            onboarding_completed=True
        )
        self.db.add(self.user)
        await self.db.commit()
        await self.db.refresh(self.user)

    async def asyncTearDown(self):
        await self.db.close()
        await self.engine.dispose()
        # Clean up database file
        if os.path.exists("./test_knowledge_graph.db"):
            try:
                os.remove("./test_knowledge_graph.db")
            except Exception:
                pass

    async def test_relationship_persistence(self):
        """Verify graph relationships can be stored and retrieved directly."""
        rel = KnowledgeGraphRelation(
            user_id=self.user_id,
            subject="User",
            predicate="Likes",
            object="Anime",
            confidence=0.95
        )
        self.db.add(rel)
        await self.db.commit()

        # Query back
        res = await self.db.execute(select(KnowledgeGraphRelation))
        fetched = res.scalars().all()
        self.assertEqual(len(fetched), 1)
        self.assertEqual(fetched[0].predicate, "Likes")
        self.assertEqual(fetched[0].object, "Anime")
        self.assertEqual(fetched[0].confidence, 0.95)

    async def test_service_store_and_retrieve(self):
        """Verify service store_relationships handles insert, update, and retrieve correctly."""
        relations = [
            {"subject": "User", "predicate": "Likes", "object": "Anime", "confidence": 0.90},
            {"subject": "User", "predicate": "Hobby", "object": "Editing", "confidence": 0.85}
        ]
        
        # 1. Store
        await knowledge_graph_service.store_relationships(self.db, self.user_id, relations)
        
        # 2. Retrieve
        fetched = await knowledge_graph_service.retrieve_relationships(self.db, self.user_id)
        self.assertEqual(len(fetched), 2)
        
        # Assert specific triple values
        triples = {(f.subject, f.predicate, f.object) for f in fetched}
        self.assertIn(("User", "Likes", "Anime"), triples)
        self.assertIn(("User", "Hobby", "Editing"), triples)

        # 3. Update existing triple confidence
        update_relations = [
            {"subject": "User", "predicate": "Likes", "object": "Anime", "confidence": 0.98}
        ]
        await knowledge_graph_service.store_relationships(self.db, self.user_id, update_relations)
        
        # Verify no duplicate was created, but confidence updated
        fetched_after = await knowledge_graph_service.retrieve_relationships(self.db, self.user_id)
        self.assertEqual(len(fetched_after), 2)
        
        likes_relation = next(f for f in fetched_after if f.predicate == "Likes")
        self.assertEqual(likes_relation.confidence, 0.98)

    async def test_service_retrieve_relevant(self):
        """Verify retrieve_relevant_relationships returns direct matches or falls back."""
        relations = [
            {"subject": "User", "predicate": "Likes", "object": "Anime", "confidence": 0.90},
            {"subject": "User", "predicate": "Hobby", "object": "Editing", "confidence": 0.85},
            {"subject": "User", "predicate": "Goal", "object": "Internship", "confidence": 0.95}
        ]
        await knowledge_graph_service.store_relationships(self.db, self.user_id, relations)

        # 1. Direct text match
        relevant = await knowledge_graph_service.retrieve_relevant_relationships(
            self.db, self.user_id, "I love anime"
        )
        self.assertEqual(len(relevant), 1)
        self.assertEqual(relevant[0].object, "Anime")

        # 2. Fallback to all (limit 5) when no direct keyword matches
        fallback = await knowledge_graph_service.retrieve_relevant_relationships(
            self.db, self.user_id, "Some random text about nothing"
        )
        self.assertEqual(len(fallback), 3)

    @patch("app.services.knowledge_graph_service.get_chat_client")
    async def test_relationship_extraction(self, mock_get_client):
        """Verify extract_relationships calls LLM and parses JSON output correctly."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"relations": [{"subject": "User", "predicate": "Likes", "object": "Anime", "confidence": 0.95}]}'))
        ]
        mock_get_client.return_value.chat.completions.create = AsyncMock(return_value=mock_response)

        extracted = await knowledge_graph_service.extract_relationships("I love anime.")
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["object"], "Anime")
        self.assertEqual(extracted[0]["predicate"], "Likes")

    def test_prompt_injection(self):
        """Verify response orchestrator injects knowledge graph relationships into system prompt."""
        graph_rels = [
            "- User -> Likes -> Anime",
            "- User -> Hobby -> Editing"
        ]
        prompt = response_orchestrator.build_final_prompt(
            user_name="Alice",
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
            graph_relationships=graph_rels
        )

        self.assertIn("KNOWLEDGE GRAPH RELATIONSHIPS:", prompt)
        self.assertIn("- User -> Likes -> Anime", prompt)
        self.assertIn("- User -> Hobby -> Editing", prompt)
