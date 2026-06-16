"""Utility modules — shared helpers, LLM clients."""
from .llm import get_chat_client, get_embedding_client, generate_chat_completion_with_fallback
from .helpers import safe_json_parse, get_ist_time, normalize_uuid, get_random_human_fallback, get_speculative_transition, detect_specialist_action

