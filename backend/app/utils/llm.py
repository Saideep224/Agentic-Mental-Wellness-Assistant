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
    providers = []

    # Helper to clean model names for specific providers
    def get_ollama_base(url):
        if url and not url.endswith('/v1') and not url.endswith('/v1/'):
            return url.rstrip('/') + '/v1'
        return url

    # If preferred_model is specified, try to resolve it first
    if preferred_model:
        pref = preferred_model.lower()
        if "llama" in pref or "ollama" in pref:
            if settings.OLLAMA_BASE_URL:
                providers.append(("Ollama-Preferred", get_ollama_base(settings.OLLAMA_BASE_URL), "ollama", settings.OLLAMA_MODEL))
        elif "deepseek" in pref:
            if settings.DEEPSEEK_API_KEY:
                providers.append(("DeepSeek-Preferred", settings.DEEPSEEK_API_BASE, settings.DEEPSEEK_API_KEY, "deepseek-chat"))
            elif settings.OPENROUTER_API_KEY:
                providers.append(("OpenRouter-DeepSeek", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, "deepseek/deepseek-chat"))
        elif "gemini" in pref:
            if settings.GEMINI_API_KEY:
                providers.append(("Gemini-Preferred", settings.GEMINI_API_BASE, settings.GEMINI_API_KEY, preferred_model))
            elif settings.OPENROUTER_API_KEY:
                providers.append(("OpenRouter-Gemini", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, "google/gemini-2.5-flash"))
        elif "gpt" in pref:
            if settings.OPENAI_API_KEY:
                providers.append(("OpenAI-Preferred", None, settings.OPENAI_API_KEY, preferred_model))
            elif settings.OPENROUTER_API_KEY:
                providers.append(("OpenRouter-OpenAI", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, f"openai/{preferred_model}"))

    # Add other providers based on configurations (fallbacks)

    # 1. Ollama
    if settings.OLLAMA_BASE_URL and not any(p[0].startswith("Ollama") for p in providers):
        providers.append(("Ollama", get_ollama_base(settings.OLLAMA_BASE_URL), "ollama", settings.OLLAMA_MODEL))

    # 2. Gemini
    if settings.GEMINI_API_KEY and not any(p[0].startswith("Gemini") for p in providers):
        providers.append(("Gemini", settings.GEMINI_API_BASE, settings.GEMINI_API_KEY, settings.GEMINI_MODEL))

    # 3. OpenAI
    if settings.OPENAI_API_KEY and not any(p[0].startswith("OpenAI") for p in providers):
        providers.append(("OpenAI", None, settings.OPENAI_API_KEY, settings.OPENAI_MODEL))

    # 4. DeepSeek
    if settings.DEEPSEEK_API_KEY and not any(p[0].startswith("DeepSeek") for p in providers):
        providers.append(("DeepSeek", settings.DEEPSEEK_API_BASE, settings.DEEPSEEK_API_KEY, "deepseek-chat"))

    # 5. OpenRouter
    if settings.OPENROUTER_API_KEY and not any(p[0].startswith("OpenRouter") for p in providers):
        providers.append(("OpenRouter", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL))

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
