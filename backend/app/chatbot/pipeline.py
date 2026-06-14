"""
LangGraph chatbot pipeline — orchestrates the multi-agent workflow.

Workflow:
User Input
↓
Emotion Agent + Intent Agent + Safety Agent (via Cognitive Analyzer LLM call)
↓
Memory Agent (retrieves memories & patterns, reads conversation summaries)
↓
Response Agent (orchestrates tone/strategy, checks quality, runs LLM with fallback)
↓
Final Response
"""

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from langgraph.graph import StateGraph, END
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_maker, _memory_cache
from app.utils.llm import generate_chat_completion_with_fallback
from app.chatbot.state import AgentState
from app.chatbot.prompts import MULTI_AGENT_ANALYZER_SYSTEM_PROMPT

# Import logical agents and orchestrator
from app.agents import (
    personality_agent,
    emotion_agent,
    behavior_agent,
    growth_agent,
    intent_agent,
    safety_agent,
    memory_agent,
    response_agent,
)
from app.orchestrator.response_orchestrator import response_orchestrator

logger = logging.getLogger(__name__)


# ── Helper: Retrieve Conversation Summary ─────────────────────
async def _get_conversation_summary(db: AsyncSession, user_id: str, conversation_id: str) -> str | None:
    """Query the memories table for a conversation summary memory with a 600ms timeout."""
    try:
        from app.models.memory import Memory
        
        async def _query():
            result = await db.execute(
                select(Memory).where(Memory.user_id == user_id)
            )
            memories = result.scalars().all()
            for m in memories:
                meta = m.metadata_json or {}
                if meta.get("source") == "conversation_summary" and meta.get("conversation_id") == str(conversation_id):
                    return m.memory_summary
            return None

        return await asyncio.wait_for(_query(), timeout=0.6)
    except Exception as e:
        logger.warning(f"Failed to fetch conversation summary (timeout or error): {e}")
    return None


# ── 1. Cognitive Analyzer Agent (Coordinating Node) ───────────
async def cognitive_analyzer_agent(state: AgentState) -> dict:
    """Run structured analyzer Gemini call and parse with logical agents."""
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])
    profile = state.get("emotional_profile", {})
    db = state.get("db")
    user_id = state.get("user_id", "")

    # 1. Run MentalBERT Emotion Classification and save to db (happens inside the service)
    detected_emotion = "Neutral"
    confidence_score = 1.0
    if user_id:
        try:
            from app.services.emotion_service import emotion_service
            from app.database import async_session_maker
            close_temp_db = False
            temp_db = db
            if temp_db is None:
                temp_db = async_session_maker()
                close_temp_db = True
            
            emotion_res = await emotion_service.classify_emotion_mentalbert(temp_db, user_id, user_message)
            detected_emotion = emotion_res.get("detected_emotion", "Neutral")
            confidence_score = emotion_res.get("confidence_score", 1.0)
            
            # Run Profile Fact Extraction and update db
            try:
                from app.services.profile_service import profile_service
                await profile_service.extract_and_update_profile_facts(temp_db, user_id, user_message)
            except Exception as fact_err:
                logger.error(f"Failed to extract and update profile facts: {fact_err}", exc_info=True)
            
            # Run Knowledge Graph Extraction
            try:
                from app.services.knowledge_graph_service import knowledge_graph_service
                import uuid
                user_name = profile.get("user_name", "User") or "User"
                extracted_rels = await knowledge_graph_service.extract_relationships(user_message, user_name=user_name)
                if extracted_rels:
                    user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
                    await knowledge_graph_service.store_relationships(temp_db, user_uuid, extracted_rels)
            except Exception as kg_err:
                logger.error(f"Failed to extract/store knowledge graph relations: {kg_err}", exc_info=True)

            if close_temp_db:
                await temp_db.commit()
                await temp_db.close()
        except Exception as emo_err:
            logger.error(f"Failed to run MentalBERT classification in pipeline: {emo_err}", exc_info=True)

    recent_context = ""
    if history:
        last_messages = history[-6:]
        recent_context = "\n".join(
            f"{m['role']}: {m['content'][:300]}" for m in last_messages
        )

    profile_snippet = ""
    if profile:
        profile_snippet = f"\nUser Profile:\n{json.dumps(profile, indent=2)}"

    try:
        user_content = (
            f"User Profile details:\n{profile_snippet}\n\n"
            f"Recent conversation history:\n{recent_context}\n\n"
            f"MentalBERT Sequence Classifier result for current message: {detected_emotion} (confidence: {confidence_score})\n\n"
            f"Current message to analyze: {user_message}"
        )
        raw = await generate_chat_completion_with_fallback(
            messages=[
                {"role": "system", "content": MULTI_AGENT_ANALYZER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        from app.utils.helpers import safe_json_parse
        analysis = safe_json_parse(raw)
        if not analysis:
            raise ValueError("Parsed JSON is empty or invalid")
    except Exception as e:
        logger.warning(f"Multi-agent cognitive analyzer failed, using fallback: {e}. Raw was: {repr(raw) if 'raw' in locals() else 'None'}", exc_info=True)
        analysis = {
            "message_type": "emotional",
            "personality_agent": {
                "confidence_level": "moderate",
                "communication_style": "casual",
                "emotional_openness": "neutral",
                "introvert_extrovert_tendencies": "ambivert"
            },
            "emotion_agent": {
                "primary_emotion": detected_emotion.lower(),
                "stress": 0.3,
                "anxiety": 0.3,
                "sadness": 0.3,
                "burnout": 0.3,
                "emotional_intensity": 5
            },
            "behavior_agent": {
                "productivity_patterns": "none detected",
                "sleep_issues": "none detected",
                "procrastination": "low",
                "routine_consistency": "stable"
            },
            "growth_agent": {
                "emotional_improvement": "stable",
                "motivation": "moderate",
                "self_awareness": "moderate",
                "mental_growth": "none detected"
            },
            "context_analysis": {
                "emotional_triggers": [],
                "inferred_causes": ["exhaustion"],
                "underlying_need": "to be heard and acknowledged",
                "what_user_needs": "listening"
            },
            "recommendations": [],
            "memory_extraction": {
                "is_meaningful": False,
                "importance_level": 1,
                "memory_summary": None,
                "behavior_patterns": None
            }
        }

    # Execute logical agents to format their states
    p_data = personality_agent.analyze(analysis)
    from app.services.mentalbert_service import mentalbert_service
    emotion_scores = mentalbert_service.predict(user_message)
    e_data = emotion_agent.analyze(emotion_scores)
    b_data = behavior_agent.analyze(analysis)
    g_data = growth_agent.analyze(analysis)
    
    # Sync detected_emotion and confidence_score with direct MentalBERT outputs
    detected_emotion = e_data.get("primary_emotion", "Neutral").capitalize()
    probs_list = []
    try:
        import torch
        if torch.is_tensor(emotion_scores):
            probs_list = emotion_scores.tolist()[0]
    except Exception:
        pass
    if not probs_list and isinstance(emotion_scores, list):
        probs_list = emotion_scores
    confidence_score = max(probs_list) if probs_list else 1.0

    # Run new Intent and Safety Agents
    i_data = intent_agent.analyze(analysis)
    s_data = safety_agent.check_safety(analysis, user_message)

    # Calculate mood score (0.0 to 1.0)
    stress_val = e_data.get("stress", 0.3)
    anxiety_val = e_data.get("anxiety", 0.3)
    sadness_val = e_data.get("sadness", 0.3)
    burnout_val = e_data.get("burnout", 0.3)
    mood_score = round(1.0 - (stress_val * 0.2 + anxiety_val * 0.3 + sadness_val * 0.3 + burnout_val * 0.2), 2)
    mood_score = max(0.05, min(0.95, mood_score))

    # Populate backward-compatible keys
    emotion_dimensions = {
        "stress": stress_val,
        "anxiety": anxiety_val,
        "sadness": sadness_val,
        "burnout": burnout_val,
        "happiness": round(max(0.0, 1.0 - (sadness_val + stress_val) / 2.0), 2),
        "motivation": 0.8 if "high" in str(g_data.get("motivation")).lower() else (0.2 if "low" in str(g_data.get("motivation")).lower() else 0.5),
        "confidence": 0.8 if "high" in str(p_data.get("confidence_level")).lower() else (0.2 if "low" in str(p_data.get("confidence_level")).lower() else 0.5)
    }

    personality_analysis = {
        "overthinking_detected": "overthink" in str(p_data.get("communication_style")).lower() or stress_val > 0.7,
        "communication_pattern": p_data.get("communication_style", "casual"),
        "social_energy": b_data.get("routine_consistency", "stable"),
        "personality_traits": [p_data.get("introvert_extrovert_tendencies", "ambivert")],
        "emotional_needs": [p_data.get("emotional_openness", "neutral")]
    }

    logger.info(f"[ANALYSIS] Coordinated agents analysis: message_type={i_data.get('message_type')}, primary_emotion={detected_emotion}, mood={mood_score}, is_safe={s_data.get('is_safe')}")

    return {
        "router_decision": {"message_type": analysis.get("message_type", "emotional")},
        "personality_agent": p_data,
        "emotion_agent": e_data,
        "behavior_agent": b_data,
        "growth_agent": g_data,
        "intent_agent": i_data,
        "safety_agent": s_data,
        "memory_extraction": analysis.get("memory_extraction", {}),
        "emotion_analysis": e_data,
        "emotion_dimensions": emotion_dimensions,
        "personality_analysis": personality_analysis,
        "context_analysis": analysis.get("context_analysis", {}),
        "recommendations": analysis.get("recommendations", []),
        "detected_emotion": detected_emotion,
        "detected_emotion_confidence": confidence_score,
        "mood_score": mood_score,
    }


# ── 2. Memory Agent ───────────────────────────────────────────
async def memory_agent_node(state: AgentState) -> dict:
    """Use Memory Agent to recall context and emotional patterns from DB with an 800ms timeout."""
    user_message = state.get("user_message", "")
    user_id = state.get("user_id", "")

    db = state.get("db")
    close_db = False
    if db is None:
        db = async_session_maker()
        close_db = True

    try:
        # Retrieve memories and patterns using the memory agent (limit top 5 to optimize tokens) with an 800ms timeout
        result = await asyncio.wait_for(
            memory_agent.retrieve_context(db, user_id, user_message, limit=5),
            timeout=0.8
        )
        retrieved_memories = result.get("memories", [])
        patterns = result.get("emotional_patterns", {})
        
        # Prune expired memories
        try:
            from app.services.memory_service import memory_service
            await memory_service.prune_expired_memories(db, user_id)
        except Exception as prune_err:
            logger.warning(f"[MEMORY] Memory pruning failed: {prune_err}")

        # Populate in-memory cache
        _memory_cache[str(user_id)] = (retrieved_memories, patterns)
    except Exception as e:
        logger.warning(f"[MEMORY] Memory agent node error or timeout: {e}. Using cached memories if available.")
        # Try to retrieve from cache
        cached = _memory_cache.get(str(user_id))
        if cached:
            retrieved_memories, patterns = cached
        else:
            retrieved_memories, patterns = [], {}
            
    # Retrieve relevant Knowledge Graph relationships
    graph_relationships = []
    try:
        from app.services.knowledge_graph_service import knowledge_graph_service
        import uuid
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        rels = await knowledge_graph_service.retrieve_relevant_relationships(db, user_uuid, user_message)
        graph_relationships = [f"- {r.subject} -> {r.predicate} -> {r.object}" for r in rels]
    except Exception as kg_retrieve_err:
        logger.error(f"Failed to retrieve knowledge graph relations: {kg_retrieve_err}", exc_info=True)

    # Build Personal Comfort Kit when a negative emotion is detected
    comfort_kit_dict = {}
    detected_emotion = state.get("detected_emotion", "Neutral")
    try:
        from app.services.recommendation_service import recommendation_service
        if detected_emotion.lower() in recommendation_service.NEGATIVE_EMOTIONS:
            personality_profile = state.get("emotional_profile", {}).get("personality_profile", {})
            kit = await recommendation_service.build_comfort_kit(
                db=db,
                user_id=user_id,
                detected_emotion=detected_emotion,
                graph_relationships=graph_relationships,
                personality_profile=personality_profile,
            )
            comfort_kit_dict = {
                "emotional_trigger": kit.emotional_trigger,
                "interests": kit.interests,
                "hobbies": kit.hobbies,
                "coping_activities": kit.coping_activities,
                "comfort_environment": kit.comfort_environment,
                "activity_suggestions": kit.activity_suggestions,
                "is_empty": kit.is_empty,
            }
    except Exception as rec_err:
        logger.warning(f"[RecommendationService] Failed to build comfort kit: {rec_err}")

    finally:
        if close_db:
            await db.close()

    return {
        "memories": retrieved_memories,
        "graph_relationships": graph_relationships,
        "emotional_patterns": patterns,
        "comfort_kit": comfort_kit_dict,
    }


# ── 3. Response Agent ─────────────────────────────────────────
async def response_agent_node(state: AgentState) -> dict:
    """Call Response Agent to compile system prompt and generate final output."""
    user_message = state.get("user_message", "")
    history = state.get("conversation_history", [])
    profile = state.get("emotional_profile", {})
    memories = state.get("memories", [])
    conversation_id = state.get("conversation_id", "")
    user_id = state.get("user_id", "")

    personality_profile = profile.get("personality_profile", {})
    user_name = profile.get("user_name", "friend")

    db = state.get("db")
    profile_context = ""
    if db and user_id:
        from app.services.profile_service import profile_service
        legacy_context = await profile_service.build_profile_context(db, user_id)
        personalization_block = await profile_service.build_personalization_prompt_block(db, user_id)
        profile_context = f"{legacy_context}\n{personalization_block}"

    # If crisis is detected by the Safety Agent, override response strategy
    safety_data = state.get("safety_agent", {})
    if safety_data.get("crisis_detected"):
        tone = "calming"
        strategy = "Activate Esona Crisis Support Protocol. Focus on validating pain, sharing safety hotlines (e.g. Vandrevala Foundation or AASRA), staying grounded, and being direct. Strictly no humor."
    else:
        # Call Orchestrator to decide Tone and Strategy
        orchestrated = response_orchestrator.determine_tone_and_strategy(
            personality=state.get("personality_agent", {}),
            emotion=state.get("emotion_agent", {}),
            behavior=state.get("behavior_agent", {}),
            growth=state.get("growth_agent", {})
        )
        tone = orchestrated["tone"]
        strategy = orchestrated["strategy"]

    # Format Current Time
    ist_tz = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(ist_tz)
    current_time_str = current_time_ist.strftime('%A, %B %d, %Y %I:%M %p (IST)')

    # Fetch emotion timeline for the last 7 days
    emotion_timeline = []
    if db and user_id:
        try:
            from app.services.mood_tracker import MoodTracker
            import uuid
            user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
            mt = MoodTracker(db)
            emotion_timeline = await mt.retrieve_emotion_timeline(user_uuid, days=7)
        except Exception as timeline_err:
            logger.warning(f"Failed to retrieve emotion timeline: {timeline_err}")

    # Fetch a single growth insight every 15 user messages for natural chat injection
    growth_insight: str | None = None
    try:
        total_msgs = len([m for m in history if m.get("role") == "user"])
        if db and user_id and total_msgs > 0 and total_msgs % 15 == 0:
            from app.services.growth_insights_service import growth_insights_service
            growth_insight = await growth_insights_service.get_top_insight_for_chat(db, user_id)
            if growth_insight:
                logger.info(f"[GrowthInsights] Injecting insight at message {total_msgs}: {growth_insight[:60]}...")
    except Exception as gi_err:
        logger.warning(f"Failed to fetch growth insight for chat injection: {gi_err}")

    # Compile Final Orchestrated System Prompt
    system_prompt = response_orchestrator.build_final_prompt(
        user_name=user_name,
        personality_profile=personality_profile,
        personality=state.get("personality_agent", {}),
        emotion=state.get("emotion_agent", {}),
        behavior=state.get("behavior_agent", {}),
        growth=state.get("growth_agent", {}),
        memories=memories,
        tone=tone,
        strategy=strategy,
        current_time_str=current_time_str,
        profile_context=profile_context,
        detected_emotion=state.get("detected_emotion", "Neutral"),
        detected_emotion_confidence=state.get("detected_emotion_confidence", 1.0),
        graph_relationships=state.get("graph_relationships", []),
        comfort_kit=state.get("comfort_kit", {}),
        emotion_timeline=emotion_timeline,
        growth_insight=growth_insight,
    )

    # Prompt Summary for Live Debug Panel
    prompt_summary = f"[Tone: {tone.upper()} | Strategy: {strategy}]\nSystem prompt length: {len(system_prompt)} chars."

    messages = [{"role": "system", "content": system_prompt}]
    
    # Fetch and prepend conversation summaries if they exist to keep context window optimized
    db = state.get("db")
    if db and conversation_id and user_id:
        summary = await _get_conversation_summary(db, user_id, conversation_id)
        if summary:
            messages.append({
                "role": "system",
                "content": f"System Note: Here is a summary of the earlier part of this conversation:\n\"{summary}\"\nUse it for context, but do not repeat it verbatim."
            })

    # Limit history to the last 8 messages to optimize token usage
    if history:
        for msg in history[-8:]:
            role = msg.get("role", "user")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    # Call Response Agent to generate response with quality checks
    try:
        gen_res = await response_agent.generate(messages=messages, temperature=0.7, max_tokens=800)
        text = gen_res.get("text", "")
        reasoning = gen_res.get("reasoning", "")
    except Exception as e:
        logger.error(f"Response agent generation failed: {e}", exc_info=True)
        text = "I'm here for you. ||| Things sound a bit heavy right now... ||| What's on your mind?"
        reasoning = "Response generation failed, fallback triggered."

    # Assemble structured developer debug payload
    agent_analysis = {
        "personality_agent": state.get("personality_agent", {}),
        "emotion_agent": state.get("emotion_agent", {}),
        "behavior_agent": state.get("behavior_agent", {}),
        "growth_agent": state.get("growth_agent", {}),
        "intent_agent": state.get("intent_agent", {}),
        "safety_agent": state.get("safety_agent", {}),
        "retrieved_memories": memories,
        "response_strategy": {
            "tone": tone,
            "strategy": strategy
        },
        "orchestrated_prompt_summary": prompt_summary,
        "hidden_reasoning": reasoning,
        # Keep backward compatible fields in agent_analysis
        "emotion_analysis": state.get("emotion_analysis", {}),
        "personality_analysis": state.get("personality_analysis", {}),
        "context_analysis": state.get("context_analysis", {}),
        "recommendations": state.get("recommendations", [])
    }

    return {
        "response": text,
        "agent_analysis": agent_analysis,
        "response_strategy": {
            "tone": tone,
            "strategy": strategy
        }
    }


# ── Build the compiled graph ──────────────────────────────────
async def preprocessing_node(state: AgentState) -> dict:
    """Run cognitive analysis and memory retrieval concurrently to optimize speed."""
    cog_task = asyncio.create_task(cognitive_analyzer_agent(state))
    mem_task = asyncio.create_task(memory_agent_node(state))
    cog_res, mem_res = await asyncio.gather(cog_task, mem_task)
    return {**cog_res, **mem_res}

def build_graph() -> StateGraph:
    """Construct the LangGraph StateGraph with concurrent preprocessing."""
    graph = StateGraph(AgentState)

    # Add optimized nodes
    graph.add_node("preprocessing_node", preprocessing_node)
    graph.add_node("response_agent", response_agent_node)

    # Entry point
    graph.set_entry_point("preprocessing_node")

    # Workflow chain
    graph.add_edge("preprocessing_node", "response_agent")
    graph.add_edge("response_agent", END)

    return graph


# Compile module-level compiled graph
_compiled_graph = build_graph().compile()


async def run_agent_graph(
    user_message: str,
    user_id: str,
    conversation_history: list[dict],
    emotional_profile: dict,
    conversation_id: str | None = None,
    db: AsyncSession | None = None,
) -> dict:
    """Execute the full agent pipeline and return the final state."""
    initial_state: AgentState = {
        "user_message": user_message,
        "user_id": user_id,
        "conversation_id": str(conversation_id) if conversation_id else "",
        "conversation_history": conversation_history,
        "emotional_profile": emotional_profile,
        "db": db,
        "router_decision": {},
        "emotion_analysis": {},
        "personality_analysis": {},
        "context_analysis": {},
        "memories": [],
        "recommendations": [],
        "comfort_kit": {},
        "response": "",
        "mood_score": 0.5,
        "detected_emotion": "neutral",
        "personality_agent": {},
        "emotion_agent": {},
        "behavior_agent": {},
        "growth_agent": {},
        "intent_agent": {},
        "safety_agent": {},
        "memory_extraction": {},
        "response_strategy": {},
        "orchestrated_prompt_summary": "",
        "agent_analysis": {},
    }

    try:
        result = await _compiled_graph.ainvoke(initial_state)
        return result
    except Exception as e:
        logger.error(f"Agent graph execution failed: {e}", exc_info=True)
        return {
            **initial_state,
            "response": (
                "Hey, I hit a bump trying to think that through. "
                "Can you say that again? I want to give you a proper response."
            ),
        }
