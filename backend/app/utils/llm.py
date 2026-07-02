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

    def _safe_print(*args, **kwargs):
        """Print that handles UnicodeEncodeError on Windows console."""
        try:
            print(*args, **kwargs)
        except UnicodeEncodeError:
            text = " ".join(str(a) for a in args)
            print(text.encode('ascii', errors='replace').decode('ascii'), **kwargs)

    # Check which API keys are loaded
    gemini_loaded = bool(settings.GEMINI_API_KEY)
    openrouter_loaded = bool(settings.OPENROUTER_API_KEY)
    logger.info(f"[API KEY LOADED] Gemini: {gemini_loaded}, OpenRouter: {openrouter_loaded}")
    _safe_print(f"[API KEY LOADED] Gemini: {gemini_loaded}, OpenRouter: {openrouter_loaded}")

    # Build order of providers based on settings and preferred_model
    all_possible_providers = {}

    # 1. Ollama
    if settings.OLLAMA_BASE_URL:
        all_possible_providers["ollama"] = ("Ollama", get_ollama_base(settings.OLLAMA_BASE_URL), "ollama", settings.OLLAMA_MODEL)

    # 2. Gemini
    if settings.GEMINI_API_KEY:
        gemini_model = settings.GEMINI_MODEL
        if gemini_model and not gemini_model.startswith("models/"):
            gemini_model = f"models/{gemini_model}"
        all_possible_providers["gemini"] = ("Gemini", settings.GEMINI_API_BASE, settings.GEMINI_API_KEY, gemini_model)

    # 3. OpenAI
    if settings.OPENAI_API_KEY:
        all_possible_providers["openai"] = ("OpenAI", None, settings.OPENAI_API_KEY, settings.OPENAI_MODEL)

    # 4. DeepSeek
    if settings.DEEPSEEK_API_KEY:
        all_possible_providers["deepseek"] = ("DeepSeek", settings.DEEPSEEK_API_BASE, settings.DEEPSEEK_API_KEY, "deepseek-chat")

    # 5. OpenRouter — supports comma-separated model list for multi-model waterfall
    # e.g. OPENROUTER_MODEL=google/gemma-4-31b-it:free,meta-llama/llama-3.3-70b-instruct:free
    if settings.OPENROUTER_API_KEY:
        or_models = [m.strip() for m in settings.OPENROUTER_MODEL.split(",") if m.strip()]
        for idx, or_model in enumerate(or_models):
            provider_key = f"openrouter" if idx == 0 else f"openrouter_{idx}"
            all_possible_providers[provider_key] = ("OpenRouter", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, or_model)


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
        if preferred_model and preferred_model.lower() in ["gemini", "openai", "deepseek", "openrouter", "ollama"]:
            p_model = p_info[3]
        else:
            p_model = preferred_model if preferred_model and first_provider_key in preferred_model.lower() else p_info[3]
        if first_provider_key == "gemini" and p_model and not p_model.startswith("models/"):
            p_model = f"models/{p_model}"
        providers.append((p_info[0], p_info[1], p_info[2], p_model))

    # Add other providers as fallbacks
    for key, p_info in all_possible_providers.items():
        if key != first_provider_key:
            p_model = p_info[3]
            if key == "gemini" and p_model and not p_model.startswith("models/"):
                p_model = f"models/{p_model}"
            providers.append((p_info[0], p_info[1], p_info[2], p_model))

    # Fallback to ConfigDefault if nothing is added
    if not providers:
        default_model = settings.llm_model
        if (not settings.USE_OPENROUTER) and settings.GEMINI_API_KEY and default_model and not default_model.startswith("models/"):
            default_model = f"models/{default_model}"
        providers.append(("ConfigDefault", settings.llm_base_url, settings.llm_api_key, default_model))

    import json
    import asyncio

    last_error = None
    for name, base_url, api_key, model in providers:
        # Retry up to 3 attempts per provider
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempting chat completion with provider {name} using model {model} (Attempt {attempt+1}/{max_attempts})...")
                logger.info(
                    f"\n--- LLM REQUEST ({name}) ---\n"
                    f"Model: {model}\n"
                    f"Messages: {json.dumps(messages, indent=2)}\n"
                    f"Temperature: {temperature}\n"
                    f"Max Tokens: {max_tokens}\n"
                    f"----------------------------\n"
                )
                
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                # Free models (e.g. :free suffix) don't support response_format JSON mode
                # Drop it silently — the system prompt instructs JSON output which is sufficient
                is_free_model = ":free" in str(model)
                if response_format and not is_free_model:
                    kwargs["response_format"] = response_format
                elif response_format and is_free_model:
                    logger.debug(f"[{name}] Dropping response_format for free model '{model}' (not supported)")
                    
                # Model request logging
                logger.info(f"[MODEL REQUEST] Provider: {name}, Model: {model}")
                _safe_print(f"[MODEL REQUEST] Provider: {name}, Model: {model}")
                print("MODEL USED:", model)
                
                response = await client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                content = choice.message.content
                print("LLM RESPONSE RECEIVED")
                
                # Explicitly ignore reasoning tokens from OpenRouter thinking models
                # Some models return reasoning in separate fields (e.g., reasoning_content, thinking)
                # We only want the final assistant message content
                msg_dict = choice.message.model_extra or {}
                if msg_dict.get("reasoning_content") or msg_dict.get("reasoning"):
                    logger.info(f"[{name}] Discarding separate reasoning tokens from model response (defense-in-depth)")
                
                # Model response logging
                logger.info(f"[MODEL RESPONSE] Provider: {name}, Content: {content}")
                _safe_print(f"[MODEL RESPONSE] Provider: {name}, Content: {content}")
                
                if content is None:
                    raise ValueError(f"Provider {name} returned response with choice content as None. Finish reason: {choice.finish_reason}")
                
                logger.info(
                    f"\n--- LLM RESPONSE ({name}) ---\n"
                    f"Content: {content}\n"
                    f"-----------------------------\n"
                )
                
                logger.info(f"Success with provider {name}!")
                
                # Final response logging
                logger.info(f"[FINAL RESPONSE] Text: {content.strip()}")
                _safe_print(f"[FINAL RESPONSE] Text: {content.strip()}")
                
                return content.strip()
            except Exception as e:
                # Model error logging
                error_msg = f"[MODEL ERROR]\nException Type: {type(e).__name__}\nException Message: {str(e)}"
                logger.error(error_msg)
                _safe_print(error_msg)
                
                logger.warning(f"LLM Provider {name} failed on attempt {attempt+1}: {e}")
                last_error = e
                
                import openai
                # 401 = wrong API key / user not found — no point retrying, move to next provider immediately
                if isinstance(e, openai.AuthenticationError):
                    logger.warning(f"[{name}] 401 AuthenticationError — skipping to next provider immediately.")
                    break
                
                # Check for OpenRouter token limit restriction (402)
                import re
                match_tokens = re.search(r"can only afford (\d+)", str(e))
                if match_tokens:
                    affordable = int(match_tokens.group(1))
                    if affordable < 20:
                        # Not worth retrying, move on to next provider
                        logger.warning(f"[{name}] Can only afford {affordable} tokens — skipping to next provider.")
                        break
                    max_tokens = affordable
                    logger.info(f"Adjusting max_tokens to affordable limit {max_tokens} for next retry.")
                    _safe_print(f"Adjusting max_tokens to affordable limit {max_tokens} for next retry.")
                
                if attempt < max_attempts - 1:
                    if isinstance(e, openai.RateLimitError):
                        error_str = str(e)
                        # Check for retry_after_seconds_raw in OpenRouter metadata
                        match_retry = re.search(r"retry_after_seconds_raw\":(\d+\.?\d*)", error_str)
                        match_secs = re.search(r"Please retry in (\d+\.?\d*)s", error_str)
                        
                        # Free-model rate limit: skip to next model immediately instead of sleeping
                        if "is_byok\":false" in error_str or ":free" in str(model):
                            logger.info(f"[{name}] Free model rate-limited — skipping to next provider immediately.")
                            break
                        elif match_retry:
                            sleep_time = float(match_retry.group(1)) + 1.0
                            logger.info(f"Rate limit hit. Sleeping for {sleep_time:.2f}s (from retry_after_seconds_raw)...")
                            await asyncio.sleep(sleep_time)
                        elif match_secs:
                            sleep_time = float(match_secs.group(1)) + 1.5
                            logger.info(f"Rate limit hit. Sleeping for {sleep_time:.2f}s...")
                            await asyncio.sleep(sleep_time)
                        else:
                            sleep_time = 5.0 * (attempt + 1)
                            logger.info(f"Rate limit hit. Sleeping for {sleep_time:.2f}s...")
                            await asyncio.sleep(sleep_time)
                    else:
                        await asyncio.sleep(2 ** attempt)
                continue

    if last_error:
        raise last_error
    raise Exception("All configured LLM providers failed to execute.")
