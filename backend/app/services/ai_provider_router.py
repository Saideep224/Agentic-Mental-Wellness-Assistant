"""
ESONA Provider Manager V2 - Centralized AI Provider Router with per-request
health monitoring, failover, circuit breakers, strict timeouts, and background checks.
"""

import os
import time
import logging
import asyncio
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional
from openai import AsyncOpenAI, RateLimitError, AuthenticationError, APIStatusError, InternalServerError, APIConnectionError
from app.config import settings

logger = logging.getLogger(__name__)

# Configured first-token (TTFB) and full completion timeouts per provider
PROVIDER_TIMEOUTS_FIRST_TOKEN = {
    "openrouter": 4.0,
    "groq": 3.0,
    "gemini": 4.0,
    "openai": 4.0,
}

PROVIDER_TIMEOUTS_FULL = {
    "openrouter": 12.0,
    "groq": 10.0,
    "gemini": 12.0,
    "openai": 12.0,
}

# Default search priorities (Gemini preferred first if configured for rock-solid stability)
PROVIDER_PRIORITY = (
    "gemini",
    "openrouter",
    "groq",
    "openai",
)

class TokenChunk:
    def __init__(self, text: str, finished: bool):
        self.text = text
        self.finished = finished


class ProviderStats:
    """Tracks latency, switch rates, and failures for a provider."""
    def __init__(self, provider: str):
        self.provider = provider
        self.latency_sum = 0.0
        self.latency_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_failure_time = None
        self.last_success_time = None

    def record_success(self, latency_ms: float):
        self.latency_sum += latency_ms
        self.latency_count += 1
        self.success_count += 1
        self.last_success_time = time.time()

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

    @property
    def average_latency(self) -> float:
        return self.latency_sum / self.latency_count if self.latency_count > 0 else 0.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 1.0


class ProviderHealth:
    def __init__(self, provider: str):
        self.provider = provider
        self.consecutive_failures = 0
        self.circuit_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.disabled_until = None
        self.last_error_type = None

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
        return True

    def record_success(self):
        if self.circuit_state != "CLOSED":
            logger.info(f"[AI_PROVIDER] provider={self.provider} stage=RECOVERED_CLOSED")
        self.consecutive_failures = 0
        self.circuit_state = "CLOSED"
        self.disabled_until = None
        self.last_error_type = None

    def record_failure(self, error_type: str):
        # 404 Model Not Found is a specific model slug error, not an infrastructure outage
        if error_type == "NOT_FOUND":
            return

        self.consecutive_failures += 1
        self.last_error_type = error_type
        
        cooldown = 0.0
        # Rule 7: Cooldown on 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.circuit_state = "OPEN"
            cooldown = 300.0  # 5 minutes
        elif error_type == "RATE_LIMIT":
            self.circuit_state = "OPEN"
            cooldown = 60.0
        elif error_type == "AUTH_ERROR":
            self.circuit_state = "OPEN"
            cooldown = 600.0

        if self.circuit_state == "OPEN":
            self.disabled_until = time.time() + cooldown
            logger.warning(
                f"[AI_PROVIDER] provider={self.provider} stage=CIRCUIT_OPEN "
                f"reason={error_type} cooldown_seconds={int(cooldown)}"
            )


class ProviderManager:
    """Manages AI providers failovers, circuit states, and response streams."""

    def __init__(self):
        self.health_states: Dict[str, ProviderHealth] = {
            p: ProviderHealth(p) for p in PROVIDER_PRIORITY
        }
        self.stats: Dict[str, ProviderStats] = {
            p: ProviderStats(p) for p in PROVIDER_PRIORITY
        }
        self.clients: Dict[str, AsyncOpenAI] = {}
        self._log_startup_config()
        
        # Start background health task
        if not self._is_mocked_env():
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.start_background_health_loop())
            except RuntimeError:
                logger.info("[AI_PROVIDER] No running event loop detected during initialization. Deferring background health loop.")

    def _is_mocked_env(self) -> bool:
        import sys
        if "pytest" in sys.modules:
            return True
        return False

    def _log_startup_config(self):
        logger.info(f"[AI_CONFIG] provider=groq configured={bool(os.environ.get('GROQ_API_KEY'))}")
        logger.info(f"[AI_CONFIG] provider=openrouter configured={bool(settings.OPENROUTER_API_KEY)}")
        logger.info(f"[AI_CONFIG] provider=gemini configured={bool(settings.GEMINI_API_KEY)}")
        logger.info(f"[AI_CONFIG] provider=openai configured={bool(settings.OPENAI_API_KEY)}")

    def _get_client(self, provider: str, api_key: str, base_url: str | None) -> AsyncOpenAI:
        client_key = f"{provider}:{base_url}"
        if client_key not in self.clients:
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

    def select_provider_priority(self, route_category: str, history_len: int = 0) -> List[str]:
        """Dynamically order providers based on input details/rules."""
        # 1. Crisis -> Groq (fastest healthy provider)
        if route_category == "SAFETY_CRITICAL":
            return ["groq", "gemini", "openai", "openrouter"]
            
        # 2. Greetings/Casual -> Gemini / OpenRouter
        if route_category == "FAST_SOCIAL":
            return ["gemini", "openrouter", "groq", "openai"]
            
        # 3. Heavy reasoning -> Gemini or OpenAI
        if route_category == "DEEP_PERSONAL":
            return ["gemini", "openai", "groq", "openrouter"]
            
        # 4. Very long conversations -> Gemini / OpenRouter
        if history_len > 15:
            return ["gemini", "openrouter", "openai", "groq"]
            
        # Default: Gemini -> OpenRouter -> Groq -> OpenAI
        return ["gemini", "openrouter", "groq", "openai"]

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
            if status == 404:
                return "NOT_FOUND"
            if status in (401, 403):
                return "AUTH_ERROR"
            if status == 429:
                return "RATE_LIMIT"
            if status in (408, 504):
                return "TIMEOUT"
            if status in (500, 502, 503):
                return "SERVER_ERROR"

        if "404" in err_str or "not found" in err_str or "unavailable for free" in err_str or "no endpoints found" in err_str:
            return "NOT_FOUND"
        if "429" in err_str or "rate limit" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
            return "RATE_LIMIT"
        if "401" in err_str or "403" in err_str or "unauthorized" in err_str or "invalid api key" in err_str:
            return "AUTH_ERROR"
        if "timeout" in err_str or "timed out" in err_str:
            return "TIMEOUT"
        if "500" in err_str or "502" in err_str or "503" in err_str or "504" in err_str:
            return "SERVER_ERROR"
            
        return "UNKNOWN_ERROR"

    def is_valid_ai_response(self, content: str | None) -> bool:
        if not content:
            return False
        c_stripped = content.strip()
        if not c_stripped:
            return False
        lower_content = c_stripped.lower()
        if "my brain lagged for a moment" in lower_content:
            return False
        if "sorry my bad" in lower_content:
            return False
        if "internal server error" in lower_content:
            return False
        return True

    def get_safe_local_fallback(self, messages: list) -> str:
        return "hey — my brain lagged for a second 😭 say that again?"

    async def _ping_provider(self, provider: str) -> bool:
        """Background health check: ping a provider with a sufficient token budget."""
        configs = self._get_provider_config(provider)
        if not configs:
            return False
        config = configs[0]
        client = self._get_client(provider, config["api_key"], config["base_url"])
        try:
            async with asyncio.timeout(6.0):
                response = await client.chat.completions.create(
                    model=config["model"],
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=50,
                    temperature=0.1
                )
                content = response.choices[0].message.content
                return bool(content and len(content.strip()) > 0)
        except Exception:
            return False

    async def start_background_health_loop(self):
        """Rule 8: Background health checks every 5 minutes."""
        while True:
            await asyncio.sleep(300.0)
            logger.info("[BackgroundHealthCheck] Running scheduled checks...")
            for provider in PROVIDER_PRIORITY:
                health = self.health_states[provider]
                if health.circuit_state == "OPEN" or health.consecutive_failures > 0:
                    success = await self._ping_provider(provider)
                    if success:
                        logger.info(f"[BackgroundHealthCheck] Provider {provider} recovered.")
                        health.record_success()
                    else:
                        logger.warning(f"[BackgroundHealthCheck] Provider {provider} is still unhealthy.")

    async def generate(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 800,
        response_format: dict | None = None,
        route_category: str = "NORMAL_CHAT"
    ) -> str:
        request_id = uuid.uuid4().hex[:8]
        logger.info(f"[ProviderManager] request_id={request_id} stage=GENERATION_STARTED")
        
        last_error = None
        providers = self.select_provider_priority(route_category)
        
        for provider in providers:
            health = self.health_states[provider]
            if not health.is_available():
                continue
                
            configs = self._get_provider_config(provider)
            if not configs:
                continue
                
            for config in configs:
                api_key = config["api_key"]
                base_url = config["base_url"]
                model = config["model"]
                
                client = self._get_client(provider, api_key, base_url)
                timeout_val = PROVIDER_TIMEOUTS_FULL.get(provider, 6.0)
                
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
                    self.stats[provider].record_success(latency)
                    
                    # Rule 15: Log Telemetry
                    logger.info(
                        f"[ProviderManager Telemetry] request_id={request_id} provider={provider} "
                        f"latency_ms={latency} status=SUCCESS"
                    )
                    return content.strip()
                    
                except Exception as exc:
                    error_type = self.classify_error(exc)
                    health.record_failure(error_type)
                    self.stats[provider].record_failure()
                    last_error = exc
                    
                    logger.warning(
                        f"[ProviderManager Fallback] request_id={request_id} failed_provider={provider} "
                        f"reason={error_type} error={str(exc)}"
                    )
        
        # Rule 16: Return safe fallback if all providers fail
        return self.get_safe_local_fallback(messages)

    async def stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 800,
        route_category: str = "NORMAL_CHAT"
    ) -> AsyncGenerator[TokenChunk, None]:
        request_id = uuid.uuid4().hex[:8]
        logger.info(f"[ProviderManager] request_id={request_id} stage=STREAM_STARTED")
        
        providers = self.select_provider_priority(route_category)
        partial_content = ""
        
        for provider in providers:
            health = self.health_states[provider]
            if not health.is_available():
                continue
                
            configs = self._get_provider_config(provider)
            if not configs:
                continue
                
            for config in configs:
                api_key = config["api_key"]
                base_url = config["base_url"]
                model = config["model"]
                
                client = self._get_client(provider, api_key, base_url)
                first_token_timeout = PROVIDER_TIMEOUTS_FIRST_TOKEN.get(provider, 2.0)
                full_timeout = PROVIDER_TIMEOUTS_FULL.get(provider, 6.0)
                
                start_time = time.perf_counter()
                yielded_anything = False
                
                # Guide fallback provider with partial generation context (Step 5)
                active_messages = list(messages)
                if partial_content:
                    active_messages.append({"role": "assistant", "content": partial_content})
                    active_messages.append({
                        "role": "system",
                        "content": f"Your previous generation was cut off. You generated: \"{partial_content}\". Please continue exactly from where it left off. Do not repeat what you already said."
                    })
                
                try:
                    kwargs = {
                        "model": model,
                        "messages": active_messages,
                        "temperature": temperature,
                        "max_tokens": min(max_tokens, 500),
                        "stream": True
                    }
                    
                    # Rule 10: Stream first token timeout check
                    async with asyncio.timeout(first_token_timeout):
                        response = await client.chat.completions.create(**kwargs)
                        iterator = response.__aiter__()
                        first_chunk = await iterator.__anext__()
                        
                    ttfb = int((time.perf_counter() - start_time) * 1000)
                    logger.info(f"[ProviderManager] request_id={request_id} provider={provider} stage=FIRST_TOKEN ttfb_ms={ttfb}")
                    
                    yielded_anything = True
                    if first_chunk.choices and first_chunk.choices[0].delta and first_chunk.choices[0].delta.content:
                        token = first_chunk.choices[0].delta.content
                        yield TokenChunk(text=token, finished=False)
                        partial_content += token
                        
                    # Stream the rest under full timeout limits
                    remaining_timeout = max(0.1, full_timeout - (time.perf_counter() - start_time))
                    async with asyncio.timeout(remaining_timeout):
                        while True:
                            try:
                                async with asyncio.timeout(5.0):
                                    chunk = await iterator.__anext__()
                                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                    token = chunk.choices[0].delta.content
                                    yield TokenChunk(text=token, finished=False)
                                    partial_content += token
                            except StopAsyncIteration:
                                break
                                
                    health.record_success()
                    latency = int((time.perf_counter() - start_time) * 1000)
                    self.stats[provider].record_success(latency)
                    
                    logger.info(
                        f"[ProviderManager Telemetry] request_id={request_id} provider={provider} "
                        f"ttfb_ms={ttfb} total_ms={latency} status=SUCCESS"
                    )
                    yield TokenChunk(text="", finished=True)
                    return
                except Exception as exc:
                    error_type = self.classify_error(exc)
                    health.record_failure(error_type)
                    self.stats[provider].record_failure()
                    
                    logger.warning(
                        f"[ProviderManager Fallback] request_id={request_id} failed_provider={provider} "
                        f"reason={error_type} error={str(exc)} mid_stream={yielded_anything}"
                    )
                    
        # Rule 16: Return safe fallback if all providers fail
        if not partial_content:
            logger.warning(f"[ProviderManager] request_id={request_id} stage=ALL_PROVIDERS_FAILED. Yielding fallback stream.")
            fallback_text = self.get_safe_local_fallback(messages)
            chunk_size = 4
            for i in range(0, len(fallback_text), chunk_size):
                yield TokenChunk(text=fallback_text[i:i+chunk_size], finished=False)
                await asyncio.sleep(0.01)
            yield TokenChunk(text="", finished=True)


# Singleton instances
provider_manager = ProviderManager()
ai_provider_router = provider_manager
