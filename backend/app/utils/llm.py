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


def get_ollama_base(url: str | None) -> str | None:
    """Helper to clean model names for specific providers."""
    if url and not url.endswith('/v1') and not url.endswith('/v1/'):
        return url.rstrip('/') + '/v1'
    return url


async def generate_chat_completion_with_fallback(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 800,
    response_format: dict | None = None,
    preferred_model: str | None = None,
) -> str:
    """
    Generate a chat completion using the primary provider,
    falling back to other configured API clients if the primary fails.
    Supports routing specific agents to their preferred models.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Build order of providers based on settings and preferred_model
    all_possible_providers = {}

    # 1. Ollama
    if settings.OLLAMA_BASE_URL:
        all_possible_providers["ollama"] = ("Ollama", get_ollama_base(settings.OLLAMA_BASE_URL), "ollama", settings.OLLAMA_MODEL)

    # 2. Gemini
    if settings.GEMINI_API_KEY:
        all_possible_providers["gemini"] = ("Gemini", settings.GEMINI_API_BASE, settings.GEMINI_API_KEY, settings.GEMINI_MODEL)

    # 3. OpenAI
    if settings.OPENAI_API_KEY:
        all_possible_providers["openai"] = ("OpenAI", None, settings.OPENAI_API_KEY, settings.OPENAI_MODEL)

    # 4. DeepSeek
    if settings.DEEPSEEK_API_KEY:
        all_possible_providers["deepseek"] = ("DeepSeek", settings.DEEPSEEK_API_BASE, settings.DEEPSEEK_API_KEY, "deepseek-chat")

    # 5. OpenRouter
    if settings.OPENROUTER_API_KEY:
        all_possible_providers["openrouter"] = ("OpenRouter", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL)

    providers = []
    first_provider_key = None

    # If preferred_model is specified, try to resolve it first
    if preferred_model:
        pref = preferred_model.lower()
        if "llama" in pref or "ollama" in pref:
            first_provider_key = "ollama"
        elif "deepseek" in pref:
            first_provider_key = "deepseek"
        elif "gemini" in pref:
            first_provider_key = "gemini"
        elif "gpt" in pref:
            first_provider_key = "openai"

    primary_provider = (settings.PRIMARY_PROVIDER or "gemini").lower()
    if not first_provider_key or first_provider_key not in all_possible_providers:
        first_provider_key = primary_provider if primary_provider in all_possible_providers else None

    # Add the selected first provider
    if first_provider_key and first_provider_key in all_possible_providers:
        p_info = all_possible_providers[first_provider_key]
        p_model = preferred_model if preferred_model and first_provider_key in preferred_model.lower() else p_info[3]
        providers.append((p_info[0], p_info[1], p_info[2], p_model))

    # Add other providers as fallbacks
    for key, p_info in all_possible_providers.items():
        if key != first_provider_key:
            providers.append(p_info)

    # Fallback to ConfigDefault if nothing is added
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
