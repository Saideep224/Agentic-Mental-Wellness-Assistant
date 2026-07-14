"""Centralized AI Provider Router with per-request health-based failover, circuit breakers, and telemetry."""
import os
import time
import logging
import asyncio
import uuid
from typing import AsyncGenerator, Dict, Any, List
from openai import AsyncOpenAI, RateLimitError, AuthenticationError, APIStatusError, InternalServerError, APIConnectionError
from app.config import settings

logger = logging.getLogger(__name__)

# Configured timeouts per provider (first-token/connect timeout)
PROVIDER_TIMEOUTS = {
    "groq": 5.0,
    "openrouter": 7.0,
    "gemini": 6.0,
    "openai": 7.0,
}

# Source of truth for provider priority
PROVIDER_PRIORITY = (
    "groq",
    "openrouter",
    "gemini",
    "openai",
)

# Cooldowns and configuration thresholds
COOLDOWN_RATE_LIMIT = 60.0
COOLDOWN_AUTH_ERROR = 600.0
COOLDOWN_CONSECUTIVE_FAILURES = 30.0

class ProviderHealth:
    def __init__(self, provider: str):
        self.provider = provider
        self.consecutive_failures = 0
        self.circuit_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.disabled_until = None
        self.last_error_type = None
        self.last_success_at = None

    def is_available(self) -> bool:
        now = time.time()
        if self.circuit_state == "CLOSED":
            return True
        if self.circuit_state == "OPEN":
            if self.disabled_until and now > self.disabled_until:
                self.circuit_state = "HALF_OPEN"
                logger.info(f"[AI_PROVIDER] provider={self.provider} stage=HALF_OPEN_PROBE")
                return True
            return False
        # HALF_OPEN allows a single probe request
        return True

    def record_success(self):
        if self.circuit_state != "CLOSED":
            logger.info(f"[AI_PROVIDER] provider={self.provider} stage=RECOVERED_CLOSED")
        self.consecutive_failures = 0
        self.circuit_state = "CLOSED"
        self.disabled_until = None
        self.last_error_type = None
        self.last_success_at = time.time()

    def record_failure(self, error_type: str):
        self.consecutive_failures += 1
        self.last_error_type = error_type
        
        cooldown = 0.0
        if error_type == "RATE_LIMIT":
            self.circuit_state = "OPEN"
            cooldown = COOLDOWN_RATE_LIMIT
        elif error_type == "AUTH_ERROR":
            self.circuit_state = "OPEN"
            cooldown = COOLDOWN_AUTH_ERROR
        else:
            # TIMEOUT, SERVER_ERROR, NETWORK_ERROR, INVALID_RESPONSE, UNKNOWN_ERROR
            if self.consecutive_failures >= 2:
                self.circuit_state = "OPEN"
                cooldown = COOLDOWN_CONSECUTIVE_FAILURES

        if self.circuit_state == "OPEN":
            self.disabled_until = time.time() + cooldown
            logger.warning(
                f"[AI_PROVIDER] provider={self.provider} stage=CIRCUIT_OPEN "
                f"reason={error_type} cooldown_seconds={int(cooldown)}"
            )

class AIProviderRouter:
    def __init__(self):
        self.health_states: Dict[str, ProviderHealth] = {
            p: ProviderHealth(p) for p in PROVIDER_PRIORITY
        }
        self.clients: Dict[str, AsyncOpenAI] = {}
        self._log_startup_config()

    def _log_startup_config(self):
        # Startup telemetry logs (do not expose keys)
        logger.info(f"[AI_CONFIG] provider=groq configured={bool(os.environ.get('GROQ_API_KEY'))}")
        logger.info(f"[AI_CONFIG] provider=openrouter configured={bool(settings.OPENROUTER_API_KEY)}")
        logger.info(f"[AI_CONFIG] provider=gemini configured={bool(settings.GEMINI_API_KEY)}")
        logger.info(f"[AI_CONFIG] provider=openai configured={bool(settings.OPENAI_API_KEY)}")

    def _get_client(self, provider: str, api_key: str, base_url: str | None) -> AsyncOpenAI:
        client_key = f"{provider}:{base_url}"
        if client_key not in self.clients:
            # Disable automatic retries inside OpenAI SDK (interactive speed is critical)
            self.clients[client_key] = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                max_retries=0
            )
        return self.clients[client_key]

    def _get_provider_config(self, provider: str) -> List[Dict[str, Any]]:
        configs = []
        if provider == "groq":
            groq_key = os.environ.get("GROQ_API_KEY")
            if groq_key:
                # Fallback list of models on Groq
                groq_models = ["llama-3.3-70b-specdec", "llama3-70b-8192", "gemma2-9b-it"]
                for m in groq_models:
                    configs.append({
                        "api_key": groq_key,
                        "base_url": "https://api.groq.com/openai/v1",
                        "model": m
                    })
        elif provider == "openrouter":
            or_key = settings.OPENROUTER_API_KEY
            if or_key:
                models = [m.strip() for m in settings.OPENROUTER_MODEL.split(",") if m.strip()]
                for m in models:
                    configs.append({
                        "api_key": or_key,
                        "base_url": settings.OPENROUTER_API_BASE,
                        "model": m
                    })
        elif provider == "gemini":
            gemini_key = settings.GEMINI_API_KEY
            if gemini_key:
                model = settings.GEMINI_MODEL
                if model and not model.startswith("models/"):
                    model = f"models/{model}"
                configs.append({
                    "api_key": gemini_key,
                    "base_url": settings.GEMINI_API_BASE,
                    "model": model
                })
        elif provider == "openai":
            openai_key = settings.OPENAI_API_KEY
            if openai_key:
                configs.append({
                    "api_key": openai_key,
                    "base_url": None,
                    "model": settings.OPENAI_MODEL
                })
        return configs

    def classify_error(self, exc: Exception) -> str:
        err_str = str(exc).lower()
        if isinstance(exc, RateLimitError):
            return "RATE_LIMIT"
        if isinstance(exc, AuthenticationError):
            return "AUTH_ERROR"
        if isinstance(exc, InternalServerError):
            return "SERVER_ERROR"
        if isinstance(exc, APIConnectionError):
            return "NETWORK_ERROR"
        if isinstance(exc, asyncio.TimeoutError):
            return "TIMEOUT"
            
        if isinstance(exc, APIStatusError):
            status = exc.status_code
            if status in (401, 403):
                return "AUTH_ERROR"
            if status == 429:
                return "RATE_LIMIT"
            if status in (408, 504):
                return "TIMEOUT"
            if status in (500, 502, 503):
                return "SERVER_ERROR"

        # Safe fallback regex string matching
        if "429" in err_str or "rate limit" in err_str or "quota" in err_str or "resource_exhausted" in err_str or "too many requests" in err_str:
            return "RATE_LIMIT"
        if "401" in err_str or "403" in err_str or "unauthorized" in err_str or "forbidden" in err_str or "invalid api key" in err_str or "invalid_api_key" in err_str:
            return "AUTH_ERROR"
        if "timeout" in err_str or "timed out" in err_str:
            return "TIMEOUT"
        if "500" in err_str or "502" in err_str or "503" in err_str or "504" in err_str or "server error" in err_str:
            return "SERVER_ERROR"
        if "connection" in err_str or "network" in err_str or "dns" in err_str or "transport" in err_str or "reset" in err_str or "refused" in err_str:
            return "NETWORK_ERROR"
            
        return "UNKNOWN_ERROR"

    def is_valid_ai_response(self, content: str | None) -> bool:
        if not content:
            return False
        c_stripped = content.strip()
        if not c_stripped:
            return False
        # Remove masking fallback phrases from success logic
        lower_content = c_stripped.lower()
        if "my brain lagged for a moment" in lower_content:
            return False
        if "sorry my bad, something went off on my end" in lower_content:
            return False
        if "internal server error" in lower_content:
            return False
        if "exception:" in lower_content or "traceback (most recent call" in lower_content:
            return False
        return True

    def get_safe_local_fallback(self, messages: list) -> str:
        """Predefined category/emotion aware lightweight local fallback."""
        user_message = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_message = m.get("content", "").lower()
                break
                
        # Simple local keyword categorization
        if any(w in user_message for w in ["hi", "hey", "hello", "sup"]):
            return "hey :) I'm here. what's up?"
        if any(w in user_message for w in ["sad", "cry", "depress", "hurt", "pain"]):
            return "I'm here. you don't have to explain everything at once."
        if any(w in user_message for w in ["stress", "anxious", "worry", "panic", "overwhelm"]):
            return "okay, slow down with me for a sec. one thing at a time."
        if any(w in user_message for w in ["angry", "mad", "hate", "annoy", "frustrate"]):
            return "yeah, I can tell this really got to you. take your time."
        return "gotcha. wanna just hang here for a bit?"

    async def generate(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 800,
        response_format: dict | None = None,
        route_category: str = "NORMAL_CHAT"
    ) -> str:
        request_id = uuid.uuid4().hex[:8]
        logger.info(f"[CHAT_TRACE] request_id={request_id} stage=GENERATION_STARTED")
        
        last_error = None
        current_provider_idx = 0
        
        while current_provider_idx < len(PROVIDER_PRIORITY):
            provider = PROVIDER_PRIORITY[current_provider_idx]
            health = self.health_states[provider]
            
            if not health.is_available():
                logger.info(f"[AI_PROVIDER] request_id={request_id} provider={provider} stage=SKIPPED reason=CIRCUIT_OPEN")
                current_provider_idx += 1
                continue
                
            configs = self._get_provider_config(provider)
            if not configs:
                current_provider_idx += 1
                continue
                
            success = False
            for config in configs:
                api_key = config["api_key"]
                base_url = config["base_url"]
                model = config["model"]
                
                logger.info(f"[AI_PROVIDER] request_id={request_id} provider={provider} stage=ATTEMPT_STARTED model={model}")
                client = self._get_client(provider, api_key, base_url)
                timeout_val = PROVIDER_TIMEOUTS.get(provider, 7.0)
                
                start_time = time.perf_counter()
                try:
                    kwargs = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": min(max_tokens, 500)
                    }
                    if response_format and ":free" not in str(model) and provider != "groq":
                        kwargs["response_format"] = response_format
                        
                    async with asyncio.timeout(timeout_val):
                        response = await client.chat.completions.create(**kwargs)
                        
                    content = response.choices[0].message.content
                    if not self.is_valid_ai_response(content):
                        raise ValueError("Invalid/empty response text returned")
                        
                    health.record_success()
                    latency = int((time.perf_counter() - start_time) * 1000)
                    logger.info(f"[AI_PROVIDER] request_id={request_id} provider={provider} stage=SUCCESS latency_ms={latency}")
                    logger.info(f"[CHAT_TRACE] request_id={request_id} stage=RESPONSE_COMPLETE total_latency_ms={latency} provider={provider}")
                    return content.strip()
                    
                except Exception as exc:
                    error_type = self.classify_error(exc)
                    health.record_failure(error_type)
                    last_error = exc
                    
                    next_provider = PROVIDER_PRIORITY[current_provider_idx + 1] if current_provider_idx + 1 < len(PROVIDER_PRIORITY) else "Fallback"
                    logger.warning(
                        f"[AI_PROVIDER] request_id={request_id} from_provider={provider} "
                        f"to_provider={next_provider} stage=FAILOVER reason={error_type} error={str(exc)}"
                    )
            
            current_provider_idx += 1

        # All providers failed, trigger safe local fallback
        logger.warning(f"[CHAT_TRACE] request_id={request_id} stage=ALL_PROVIDERS_FAILED. Triggering safe fallback.")
        return self.get_safe_local_fallback(messages)

    async def stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 800,
        route_category: str = "NORMAL_CHAT"
    ) -> AsyncGenerator[str, None]:
        request_id = uuid.uuid4().hex[:8]
        logger.info(f"[CHAT_TRACE] request_id={request_id} stage=STREAM_STARTED")
        
        last_error = None
        current_provider_idx = 0
        
        while current_provider_idx < len(PROVIDER_PRIORITY):
            provider = PROVIDER_PRIORITY[current_provider_idx]
            health = self.health_states[provider]
            
            if not health.is_available():
                logger.info(f"[AI_PROVIDER] request_id={request_id} provider={provider} stage=SKIPPED reason=CIRCUIT_OPEN")
                current_provider_idx += 1
                continue
                
            configs = self._get_provider_config(provider)
            if not configs:
                current_provider_idx += 1
                continue
                
            success = False
            for config in configs:
                api_key = config["api_key"]
                base_url = config["base_url"]
                model = config["model"]
                
                logger.info(f"[AI_PROVIDER] request_id={request_id} provider={provider} stage=ATTEMPT_STARTED model={model}")
                client = self._get_client(provider, api_key, base_url)
                timeout_val = PROVIDER_TIMEOUTS.get(provider, 7.0)
                
                start_time = time.perf_counter()
                yielded_anything = False
                try:
                    kwargs = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": min(max_tokens, 500),
                        "stream": True
                    }
                    
                    # Connect phase timeout
                    async with asyncio.timeout(timeout_val):
                        response = await client.chat.completions.create(**kwargs)
                        
                    # Stream iterate phase with rolling idle timeout
                    iterator = response.__aiter__()
                    while True:
                        try:
                            # 5.0s idle timeout between chunks to catch hung streams without stopping slow complete replies
                            async with asyncio.timeout(5.0):
                                chunk = await iterator.__anext__()
                        except StopAsyncIteration:
                            break
                            
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            yielded_anything = True
                            yield content
                            
                    if yielded_anything:
                        health.record_success()
                        latency = int((time.perf_counter() - start_time) * 1000)
                        logger.info(f"[AI_PROVIDER] request_id={request_id} provider={provider} stage=SUCCESS latency_ms={latency}")
                        logger.info(f"[CHAT_TRACE] request_id={request_id} stage=RESPONSE_COMPLETE total_latency_ms={latency} provider={provider}")
                        return
                    else:
                        raise ValueError("Stream yielded empty tokens")
                        
                except Exception as exc:
                    if yielded_anything:
                        # If we already sent chunks, we cannot roll back the SSE connection.
                        # We just log the interruption and stop.
                        logger.error(f"[AI_PROVIDER] request_id={request_id} provider={provider} stage=STREAM_INTERRUPTED error={str(exc)}")
                        return
                        
                    error_type = self.classify_error(exc)
                    health.record_failure(error_type)
                    last_error = exc
                    
                    next_provider = PROVIDER_PRIORITY[current_provider_idx + 1] if current_provider_idx + 1 < len(PROVIDER_PRIORITY) else "Fallback"
                    logger.warning(
                        f"[AI_PROVIDER] request_id={request_id} from_provider={provider} "
                        f"to_provider={next_provider} stage=FAILOVER reason={error_type} error={str(exc)}"
                    )
                    
            current_provider_idx += 1

        # All providers failed, output safe local fallback
        logger.warning(f"[CHAT_TRACE] request_id={request_id} stage=ALL_PROVIDERS_FAILED. Triggering safe fallback stream.")
        fallback_text = self.get_safe_local_fallback(messages)
        # Yield character-by-character or chunk-by-chunk to simulate streaming
        chunk_size = 4
        for i in range(0, len(fallback_text), chunk_size):
            yield fallback_text[i:i+chunk_size]
            await asyncio.sleep(0.01)

# Central router instance singleton
ai_provider_router = AIProviderRouter()
