import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.specialist_registry import SPECIALIST_REGISTRY
from app.utils.llm import generate_chat_completion_with_fallback

logger = logging.getLogger(__name__)

class SpecialistService:
    """Service to handle specialist agent execution with relevant context sharing."""

    async def generate_specialist_response(
        self,
        db: AsyncSession,
        user_id: str,
        specialist_id: str,
        user_message: str,
        conversation_history: list[dict],
        cog_res: dict,
    ) -> dict:
        """
        Executes a specialist agent using shared context.
        Only exposes relevant context (summaries, memories, graph nodes) rather than full history.
        """
        spec_info = SPECIALIST_REGISTRY.get(specialist_id)
        if not spec_info:
            raise ValueError(f"Specialist '{specialist_id}' not found in registry.")

        # 1. Extract context elements from cognitive analysis
        emotion = cog_res.get("detected_emotion", "Neutral")
        
        # Determine topic/causes
        context_analysis = cog_res.get("context_analysis", {}) or {}
        inferred_causes = context_analysis.get("inferred_causes", [])
        topic = ", ".join(inferred_causes) if inferred_causes else "General inquiry / situational stress"

        # Build personalization/profile prompt block
        profile_context = ""
        try:
            from app.services.profile_service import profile_service
            legacy_context = await profile_service.build_profile_context(db, user_id)
            personalization_block = await profile_service.build_personalization_prompt_block(db, user_id)
            profile_context = f"{legacy_context}\n{personalization_block}"
        except Exception as p_err:
            logger.warning(f"Failed to build profile context for specialist '{specialist_id}': {p_err}")

        # Relevant memories
        memories = cog_res.get("memories", [])
        memories_str = "\n".join([f"- {m.get('memory_summary') if isinstance(m, dict) else str(m)}" for m in memories]) if memories else "No relevant past memories."

        # Fetch all relationships from the Knowledge Graph to ensure it is fully shared
        graph_relationships = []
        try:
            from app.services.knowledge_graph_service import knowledge_graph_service
            import uuid
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            rels = await knowledge_graph_service.retrieve_relationships(db, user_uuid)
            graph_relationships = [f"- {r.subject} -> {r.predicate} -> {r.object}" for r in rels]
        except Exception as kg_err:
            logger.warning(f"Failed to fetch relationships for specialist '{specialist_id}': {kg_err}")
            # Fallback to whatever was in cog_res
            graph_relationships = cog_res.get("graph_relationships", [])

        graph_str = "\n".join(graph_relationships) if graph_relationships else "No relevant knowledge graph nodes."

        context_block = (
            f"\n\n=== SHARED CONTEXT FROM BUDDY ===\n"
            f"Current User Emotion: {emotion}\n"
            f"Current Topic/Issue: {topic}\n"
            f"\n{profile_context}\n"
            f"Relevant User Context / Memories:\n{memories_str}\n"
            f"Shared Knowledge Graph Nodes:\n{graph_str}\n"
            f"=================================\n\n"
            f"Remember, Buddy is also in the conversation. Focus on your specialist area ({spec_info['role']}) and practical problem-solving. Let Buddy address the primary emotional needs."
        )

        # 2. Build system message
        system_content = spec_info["system_prompt"] + context_block
        messages = [{"role": "system", "content": system_content}]

        # 3. Add recent conversation history (limit to last 4 to avoid leaking too much old history)
        # We only pass assistant responses that match this specialist or buddy, and the user's messages
        recent_history = conversation_history[-4:] if conversation_history else []
        for msg in recent_history:
            role = msg.get("role")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": msg["content"]})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        logger.info(f"Generating specialist response for '{specialist_id}' using model '{spec_info['preferred_model']}'")

        try:
            response_text = await generate_chat_completion_with_fallback(
                messages=messages,
                temperature=0.7,
                max_tokens=600,
                preferred_model=spec_info["preferred_model"],
            )
        except Exception as e:
            logger.error(f"Failed to generate specialist response for '{specialist_id}': {e}", exc_info=True)
            response_text = f"I apologize, I'm having trouble connecting to my knowledge base right now to help with this {spec_info['role']} issue. Let me try again in a moment."

        return {
            "specialist_id": specialist_id,
            "sender_type": specialist_id,
            "response": response_text,
            "role": "assistant"
        }

specialist_service = SpecialistService()
