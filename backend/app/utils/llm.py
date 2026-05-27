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


async def generate_chat_completion_with_fallback(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 800,
    response_format: dict | None = None,
) -> str:
    """
    Generate a chat completion using the primary provider,
    falling back to other configured API clients if the primary fails.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Build order of providers based on settings
    providers = []
    
    # 1. Primary provider based on settings config
    if settings.USE_OPENROUTER and settings.OPENROUTER_API_KEY:
        providers.append(("OpenRouter", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL))
    elif settings.USE_UNCLOSEAI:
        providers.append(("UncloseAI", settings.UNCLOSEAI_API_BASE, settings.OPENAI_API_KEY or "free", settings.UNCLOSEAI_MODEL))
    elif settings.GEMINI_API_KEY:
        providers.append(("Gemini", settings.GEMINI_API_BASE, settings.GEMINI_API_KEY, settings.GEMINI_MODEL))
    elif settings.OPENAI_API_KEY:
        providers.append(("OpenAI", None, settings.OPENAI_API_KEY, settings.OPENAI_MODEL))

    # 2. Backups (if not already tried)
    if settings.OPENROUTER_API_KEY and not any(p[0] == "OpenRouter" for p in providers):
        providers.append(("OpenRouter", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL))
    if settings.GEMINI_API_KEY and not any(p[0] == "Gemini" for p in providers):
        providers.append(("Gemini", settings.GEMINI_API_BASE, settings.GEMINI_API_KEY, settings.GEMINI_MODEL))
    if settings.OPENAI_API_KEY and not any(p[0] == "OpenAI" for p in providers):
        providers.append(("OpenAI", None, settings.OPENAI_API_KEY, settings.OPENAI_MODEL))
    if settings.USE_UNCLOSEAI and not any(p[0] == "UncloseAI" for p in providers):
        providers.append(("UncloseAI", settings.UNCLOSEAI_API_BASE, settings.OPENAI_API_KEY or "free", settings.UNCLOSEAI_MODEL))

    # If list is empty, default to settings variables
    if not providers:
        providers.append(("ConfigDefault", settings.llm_base_url, settings.llm_api_key, settings.llm_model))

    last_error = None
    for name, base_url, api_key, model in providers:
        try:
            logger.info(f"Attempting chat completion with provider {name} using model {model}...")
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format
                
            response = await client.chat.completions.create(**kwargs)
            logger.info(f"Success with provider {name}!")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"LLM Provider {name} failed: {e}")
            last_error = e
            continue

    if last_error:
        raise last_error
    raise Exception("All configured LLM providers failed to execute.")

