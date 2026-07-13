"""Shared low-latency LLM client and provider fallback."""
import json
import logging
import re
import time
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)
_chat_client = None
_embedding_client = None
_provider_clients: dict[tuple, AsyncOpenAI] = {}
_unhealthy_models: dict[str, float] = {}
_MODEL_COOLDOWN_SECONDS = 60.0


def get_chat_client() -> AsyncOpenAI:
    global _chat_client
    if _chat_client is None:
        _chat_client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    return _chat_client


def get_embedding_client() -> AsyncOpenAI:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    return _embedding_client


def get_ollama_base(url: str | None) -> str | None:
    if url and not url.endswith('/v1') and not url.endswith('/v1/'):
        return url.rstrip('/') + '/v1'
    return url


def _local_cognitive_analysis(messages: list) -> str | None:
    """Replace the old extra analyzer LLM round-trip with deterministic local routing.
    MentalBERT emotion classification already runs before this call in the pipeline.
    """
    system = str((messages[0] if messages else {}).get("content", ""))
    if "personality_agent" not in system or "emotion_agent" not in system or "memory_extraction" not in system:
        return None
    user_content = str((messages[-1] if messages else {}).get("content", ""))
    msg_match = re.search(r"Current message to analyze:\s*(.*)$", user_content, re.S)
    message = (msg_match.group(1).strip() if msg_match else user_content).lower()
    emo_match = re.search(r"Classifier result for current message:\s*([^\n(]+)", user_content, re.I)
    emotion = (emo_match.group(1).strip().lower() if emo_match else "neutral")
    casual = len(message.split()) <= 8 and any(x in message for x in ["hi", "hey", "hello", "yo", "sup", "good morning", "good night", "what's up", "whats up"])
    informational = any(message.startswith(x) for x in ["what is", "how do", "how can", "explain", "tell me about"])
    message_type = "casual" if casual else ("informational" if informational else "emotional")
    intensity = 2 if emotion == "neutral" else 6
    analysis = {
        "message_type": message_type,
        "personality_agent": {"confidence_level": "moderate", "communication_style": "use stored profile", "emotional_openness": "use stored profile", "introvert_extrovert_tendencies": "use stored profile"},
        "emotion_agent": {"primary_emotion": emotion, "stress": 0.3, "anxiety": 0.3, "sadness": 0.3, "burnout": 0.2, "emotional_intensity": intensity},
        "behavior_agent": {"productivity_patterns": "use known context", "sleep_issues": "use known context", "procrastination": "unknown", "routine_consistency": "unknown"},
        "growth_agent": {"emotional_improvement": "observe history", "motivation": "moderate", "self_awareness": "moderate", "mental_growth": "observe history"},
        "context_analysis": {"emotional_triggers": [], "inferred_causes": [], "underlying_need": "respond to the actual message", "what_user_needs": "profile-adapted response"},
        "recommendations": [],
        "memory_extraction": {"is_meaningful": False, "importance_level": 1, "memory_summary": None, "behavior_patterns": None},
    }
    return json.dumps(analysis)


def _providers(preferred_model: str | None = None):
    providers = []
    if settings.OPENROUTER_API_KEY:
        for model in [m.strip() for m in settings.OPENROUTER_MODEL.split(",") if m.strip()]:
            providers.append(("OpenRouter", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, model))
    if settings.GEMINI_API_KEY:
        model = settings.GEMINI_MODEL
        if model and not model.startswith("models/"): model = f"models/{model}"
        providers.append(("Gemini", settings.GEMINI_API_BASE, settings.GEMINI_API_KEY, model))
    if settings.OPENAI_API_KEY:
        providers.append(("OpenAI", None, settings.OPENAI_API_KEY, settings.OPENAI_MODEL))
    if settings.DEEPSEEK_API_KEY:
        providers.append(("DeepSeek", settings.DEEPSEEK_API_BASE, settings.DEEPSEEK_API_KEY, "deepseek-chat"))
    if settings.OLLAMA_BASE_URL:
        providers.append(("Ollama", get_ollama_base(settings.OLLAMA_BASE_URL), "ollama", settings.OLLAMA_MODEL))
    primary = (settings.PRIMARY_PROVIDER or "openrouter").lower()
    providers.sort(key=lambda p: 0 if p[0].lower() == primary else 1)
    if preferred_model:
        providers.sort(key=lambda p: 0 if preferred_model.lower() in str(p[3]).lower() or preferred_model.lower() == p[0].lower() else 1)
    if not providers:
        providers.append(("ConfigDefault", settings.llm_base_url, settings.llm_api_key, settings.llm_model))
    return providers


async def generate_chat_completion_with_fallback(messages: list, temperature: float = 0.7, max_tokens: int = 800,
                                                 response_format: dict | None = None, preferred_model: str | None = None) -> str:
    local = _local_cognitive_analysis(messages)
    if local is not None:
        logger.info("[FAST PATH] Cognitive analyzer resolved locally; skipping one LLM round-trip")
        return local

    last_error = None
    now = time.time()
    for name, base_url, api_key, model in _providers(preferred_model):
        if now < _unhealthy_models.get(str(model), 0):
            continue
        try:
            key = (str(base_url), str(api_key))
            client = _provider_clients.get(key)
            if client is None:
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                _provider_clients[key] = client
            kwargs = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": min(max_tokens, 500)}
            if response_format and ":free" not in str(model):
                kwargs["response_format"] = response_format
            started = time.perf_counter()
            response = await client.chat.completions.create(**kwargs, timeout=10.0)
            content = response.choices[0].message.content
            if not content:
                raise ValueError(f"{name} returned empty content")
            logger.info("[LLM] %s/%s completed in %.2fs", name, model, time.perf_counter() - started)
            return content.strip()
        except Exception as exc:
            last_error = exc
            error = str(exc).lower()
            if any(x in error for x in ["429", "rate limit", "quota", "timeout", "unavailable", "credit"]):
                _unhealthy_models[str(model)] = time.time() + _MODEL_COOLDOWN_SECONDS
            logger.warning("[LLM] %s/%s failed once; moving immediately to fallback: %s", name, model, exc)
            continue
    if last_error:
        raise last_error
    raise RuntimeError("No configured LLM provider is available")
