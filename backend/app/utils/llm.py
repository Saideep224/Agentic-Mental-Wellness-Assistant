"""
Shared LLM client — singleton AsyncOpenAI instances for chat and embeddings.

Centralizes LLM client creation to avoid duplicate module-level instances
across graph.py, memory_service.py, etc.
"""

from openai import AsyncOpenAI
from app.config import settings

# Singleton clients — reused across the application
_chat_client: AsyncOpenAI | None = None
_embedding_client: AsyncOpenAI | None = None


def get_chat_client() -> AsyncOpenAI:
    """Get the shared async LLM client for chat completions."""
    global _chat_client
    if _chat_client is None:
        _chat_client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
    return _chat_client


def get_embedding_client() -> AsyncOpenAI:
    """Get the shared async LLM client for embeddings."""
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
    return _embedding_client
