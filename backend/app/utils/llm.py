"""Shared low-latency LLM client and provider fallback with circuit breakers."""
import json
import logging
import re
import time
import os
from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

_chat_client = None
_embedding_client = None
_provider_clients: dict[tuple, AsyncOpenAI] = {}

# Monotonic timing logger for performance audits
perf_logger = logging.getLogger("ESONA_CHAT_PERF")

# Centralized Model Registry & Config
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_API_BASE = "https://api.groq.com/openai/v1"
GROQ_MODELS = ["llama-3.3-70b-specdec", "llama3-70b-8192", "gemma2-9b-it"]

# Centralized Route Priorities
ROUTE_PROVIDER_PRIORITY = {
    "FAST_SOCIAL": ["Groq", "OpenRouter", "Gemini", "OpenAI", "DeepSeek", "Ollama"],
    "NORMAL_CHAT": ["Groq", "OpenRouter", "Gemini", "OpenAI", "DeepSeek", "Ollama"],
    "EMOTIONAL_SUPPORT": ["OpenRouter", "Groq", "Gemini", "OpenAI", "DeepSeek", "Ollama"],
    "DEEP_PERSONAL": ["OpenRouter", "Gemini", "Groq", "OpenAI", "DeepSeek", "Ollama"],
    "SNAPSHOT_GENERATION": ["Gemini", "OpenRouter", "Groq", "OpenAI", "DeepSeek", "Ollama"],
}


class CircuitBreaker:
    def __init__(self, model_name: str, threshold: int = 3, cooldown: float = 60.0):
        self.model_name = model_name
        self.threshold = threshold
        self.cooldown = cooldown
        self.consecutive_failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.opened_at = 0.0

    def record_success(self):
        if self.state != "CLOSED":
            logger.info("[CIRCUIT CLOSED] Model %s returned to CLOSED state after success", self.model_name)
        self.consecutive_failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.threshold:
            self.state = "OPEN"
            self.opened_at = time.time()
            logger.warning("[CIRCUIT OPEN] Model %s opened due to %d consecutive failures", self.model_name, self.consecutive_failures)

    def is_available(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.opened_at > self.cooldown:
                self.state = "HALF_OPEN"
                logger.info("[CIRCUIT HALF-OPEN] Probing model %s after cooldown", self.model_name)
                return True
            return False
        if self.state == "HALF_OPEN":
            # Allow a probe request
            return True
        return True


_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(model_name: str) -> CircuitBreaker:
    if model_name not in _circuit_breakers:
        _circuit_breakers[model_name] = CircuitBreaker(model_name)
    return _circuit_breakers[model_name]


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


def is_transient_error(exc: Exception) -> bool:
    """Classify if the error is a transient API failure that justifies a fallback."""
    from openai import APIStatusError, BadRequestError, AuthenticationError
    if isinstance(exc, (BadRequestError, AuthenticationError)):
        return False
    if isinstance(exc, APIStatusError):
        # Transient status codes: 408 (timeout), 429 (rate limit), 5xx (server errors)
        return exc.status_code in (408, 429, 500, 502, 503, 504)
    # Connection issues or timeouts are transient
    err_str = str(exc).lower()
    if any(x in err_str for x in ["timeout", "timed out", "connection error", "connection refused", "rate limit", "quota", "overloaded", "429"]):
        return True
    return True  # Default to True for unknown exceptions to enable fallbacks


def _local_cognitive_analysis(messages: list) -> str | None:
    """Replace the old extra analyzer LLM round-trip with deterministic local routing."""
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


def _providers(route_category: str = "NORMAL_CHAT", preferred_model: str | None = None):
    """Gathers and sorts eligible providers based on the route category priority."""
    providers_pool = []

    # 1. Groq
    if GROQ_API_KEY:
        for model in GROQ_MODELS:
            providers_pool.append(("Groq", GROQ_API_BASE, GROQ_API_KEY, model))

    # 2. OpenRouter
    if settings.OPENROUTER_API_KEY:
        for model in [m.strip() for m in settings.OPENROUTER_MODEL.split(",") if m.strip()]:
            providers_pool.append(("OpenRouter", settings.OPENROUTER_API_BASE, settings.OPENROUTER_API_KEY, model))

    # 3. Gemini (OpenAI Compatibility Endpoint)
    if settings.GEMINI_API_KEY:
        model = settings.GEMINI_MODEL
        if model and not model.startswith("models/"):
            model = f"models/{model}"
        providers_pool.append(("Gemini", settings.GEMINI_API_BASE, settings.GEMINI_API_KEY, model))

    # 4. OpenAI
    if settings.OPENAI_API_KEY:
        providers_pool.append(("OpenAI", None, settings.OPENAI_API_KEY, settings.OPENAI_MODEL))

    # 5. DeepSeek
    if settings.DEEPSEEK_API_KEY:
        providers_pool.append(("DeepSeek", settings.DEEPSEEK_API_BASE, settings.DEEPSEEK_API_KEY, "deepseek-chat"))

    # 6. Ollama
    if settings.OLLAMA_BASE_URL:
        providers_pool.append(("Ollama", get_ollama_base(settings.OLLAMA_BASE_URL), "ollama", settings.OLLAMA_MODEL))

    # Sort based on Route Priority
    priority = ROUTE_PROVIDER_PRIORITY.get(route_category, ROUTE_PROVIDER_PRIORITY["NORMAL_CHAT"])
    
    def sort_key(p):
        provider_name = p[0]
        # Match preferred model first
        if preferred_model:
            if preferred_model.lower() in str(p[3]).lower() or preferred_model.lower() == provider_name.lower():
                return -100
        try:
            return priority.index(provider_name)
        except ValueError:
            return len(priority)

    providers_pool.sort(key=sort_key)
    
    if not providers_pool:
        # Fallback default if nothing is set
        providers_pool.append(("ConfigDefault", settings.llm_base_url, settings.llm_api_key, settings.llm_model))

    return providers_pool


async def generate_chat_completion_with_fallback(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 800,
    response_format: dict | None = None,
    preferred_model: str | None = None,
    route_category: str = "NORMAL_CHAT"
) -> str:
    local = _local_cognitive_analysis(messages)
    if local is not None:
        logger.info("[FAST PATH] Cognitive analyzer resolved locally; skipping one LLM round-trip")
        return local

    last_error = None
    for name, base_url, api_key, model in _providers(route_category, preferred_model):
        cb = get_circuit_breaker(model)
        if not cb.is_available():
            logger.info("[CIRCUIT ACTIVE] Skipping model %s because circuit is OPEN", model)
            continue
            
        try:
            key = (str(base_url), str(api_key))
            client = _provider_clients.get(key)
            if client is None:
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                _provider_clients[key] = client
                
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": min(max_tokens, 500)
            }
            if response_format and ":free" not in str(model):
                kwargs["response_format"] = response_format
                
            started = time.perf_counter()
            response = await client.chat.completions.create(**kwargs, timeout=12.0)
            content = response.choices[0].message.content
            if not content:
                raise ValueError(f"{name} returned empty content")
                
            cb.record_success()
            logger.info("[LLM] %s/%s completed in %.2fs", name, model, time.perf_counter() - started)
            return content.strip()
            
        except Exception as exc:
            cb.record_failure()
            last_error = exc
            if not is_transient_error(exc):
                # Critical bug or bad config — raise immediately without looping on fallbacks
                logger.error("[LLM CRITICAL ERROR] Non-transient failure %s/%s: %s", name, model, exc)
                raise exc
                
            logger.warning("[LLM] %s/%s failed once; fallback triggered: %s", name, model, exc)
            continue
            
    if last_error:
        raise last_error
    raise RuntimeError("No configured LLM provider is available")


async def generate_chat_completion_stream_with_fallback(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 800,
    preferred_model: str | None = None,
    route_category: str = "NORMAL_CHAT"
) -> AsyncGenerator[str, None]:
    last_error = None
    for name, base_url, api_key, model in _providers(route_category, preferred_model):
        cb = get_circuit_breaker(model)
        if not cb.is_available():
            logger.info("[CIRCUIT ACTIVE] Skipping stream model %s because circuit is OPEN", model)
            continue
            
        yielded_anything = False
        try:
            key = (str(base_url), str(api_key))
            client = _provider_clients.get(key)
            if client is None:
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                _provider_clients[key] = client
                
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": min(max_tokens, 500),
                "stream": True,
            }
            response = await client.chat.completions.create(**kwargs, timeout=15.0)
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yielded_anything = True
                    yield chunk.choices[0].delta.content
                    
            if yielded_anything:
                cb.record_success()
                return
                
        except Exception as exc:
            if yielded_anything:
                logger.error("[LLM STREAM] Stream interrupted after yielding some tokens: %s", exc)
                return
                
            cb.record_failure()
            last_error = exc
            if not is_transient_error(exc):
                # Critical bug or bad config — raise immediately without looping on fallbacks
                logger.error("[LLM STREAM CRITICAL ERROR] Non-transient failure %s/%s: %s", name, model, exc)
                raise exc
                
            logger.warning("[LLM STREAM] %s/%s failed to start stream; fallback triggered: %s", name, model, exc)
            continue
            
    if last_error:
        raise last_error
    raise RuntimeError("No configured LLM provider is available for streaming")
