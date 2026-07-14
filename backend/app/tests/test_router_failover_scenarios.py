"""Unit tests for the new AIProviderRouter failover logic, circuit breakers, timeouts, and fallbacks."""
import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from openai import RateLimitError, AuthenticationError, InternalServerError, APIConnectionError
from app.services.ai_provider_router import AIProviderRouter, ProviderHealth

class RouterFailoverScenariosTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Create a fresh router instance for each test
        self.router = AIProviderRouter()
        # Reset health state for testing predictability
        for p in self.router.health_states.values():
            p.consecutive_failures = 0
            self.router.health_states[p.provider].circuit_state = "CLOSED"
            self.router.health_states[p.provider].disabled_until = None

    def test_provider_health_transitions(self):
        """Verify ProviderHealth transitions and cooldowns according to rules."""
        health = ProviderHealth("test-provider")
        self.assertTrue(health.is_available())

        # 1. Auth error (401/403) -> Immediate OPEN for 10 mins (600s)
        import time
        health.record_failure("AUTH_ERROR")
        self.assertEqual(health.circuit_state, "OPEN")
        self.assertAlmostEqual(health.disabled_until - time.time(), 600.0, delta=10.0)

        # Reset
        health.record_success()
        self.assertEqual(health.circuit_state, "CLOSED")

        # 2. Rate limit (429) -> Immediate OPEN for 60s
        health.record_failure("RATE_LIMIT")
        self.assertEqual(health.circuit_state, "OPEN")
        self.assertAlmostEqual(health.disabled_until - time.time(), 60.0, delta=10.0)

        # Reset
        health.record_success()

        # 3. Timeout -> OPEN for 30s only after 2 consecutive failures
        health.record_failure("TIMEOUT")
        self.assertEqual(health.circuit_state, "CLOSED")  # Should still be closed on 1st fail
        health.record_failure("TIMEOUT")
        self.assertEqual(health.circuit_state, "OPEN")    # OPEN on 2nd consecutive fail
        self.assertAlmostEqual(health.disabled_until - time.time(), 30.0, delta=5.0)

    @patch("app.services.ai_provider_router.os.environ.get")
    @patch("app.services.ai_provider_router.settings")
    async def test_router_groq_success(self, mock_settings, mock_env):
        """Verify that when Groq is healthy and succeeds, we return the result immediately without failovers."""
        mock_env.return_value = "groq-api-key"
        mock_settings.OPENROUTER_API_KEY = ""
        mock_settings.GEMINI_API_KEY = ""
        mock_settings.OPENAI_API_KEY = ""

        # Mock the client creation
        mock_client = AsyncMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Hello from Groq!"
        mock_client.chat.completions.create.return_value = mock_completion
        
        with patch.object(self.router, "_get_client", return_value=mock_client):
            res = await self.router.generate([{"role": "user", "content": "hi"}])
            self.assertEqual(res, "Hello from Groq!")
            self.assertEqual(self.router.health_states["groq"].consecutive_failures, 0)
            self.assertEqual(self.router.health_states["groq"].circuit_state, "CLOSED")

    @patch("app.services.ai_provider_router.os.environ.get")
    @patch("app.services.ai_provider_router.settings")
    async def test_router_groq_429_failover_to_openrouter(self, mock_settings, mock_env):
        """Verify that if Groq returns 429, we immediately mark it open and fail over to OpenRouter."""
        mock_env.return_value = "groq-api-key"
        mock_settings.OPENROUTER_API_KEY = "or-key"
        mock_settings.OPENROUTER_MODEL = "google/gemma-4-31b-it:free"
        mock_settings.GEMINI_API_KEY = ""
        mock_settings.OPENAI_API_KEY = ""

        # We will mock _get_client to return a client that fails on Groq and succeeds on OpenRouter
        groq_client = AsyncMock()
        # Raise RateLimitError
        groq_client.chat.completions.create.side_effect = RateLimitError("Rate limit", response=MagicMock(status_code=429), body=None)

        or_client = AsyncMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Hello from OpenRouter!"
        or_client.chat.completions.create.return_value = mock_completion

        def mock_get_client(provider, *args, **kwargs):
            if provider == "groq":
                return groq_client
            return or_client

        with patch.object(self.router, "_get_client", side_effect=mock_get_client):
            res = await self.router.generate([{"role": "user", "content": "hi"}])
            self.assertEqual(res, "Hello from OpenRouter!")
            self.assertEqual(self.router.health_states["groq"].circuit_state, "OPEN")
            self.assertEqual(self.router.health_states["openrouter"].circuit_state, "CLOSED")

    @patch("app.services.ai_provider_router.os.environ.get")
    @patch("app.services.ai_provider_router.settings")
    async def test_router_gemini_429_circuit_opening(self, mock_settings, mock_env):
        """Verify that a Gemini 429 immediately opens its circuit for 60 seconds."""
        mock_env.return_value = ""  # Disable Groq/OpenRouter
        mock_settings.OPENROUTER_API_KEY = ""
        mock_settings.GEMINI_API_KEY = "gemini-key"
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
        mock_settings.OPENAI_API_KEY = "openai-key"

        gemini_client = AsyncMock()
        gemini_client.chat.completions.create.side_effect = RateLimitError("Too Many Requests", response=MagicMock(status_code=429), body=None)

        openai_client = AsyncMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "Hello from OpenAI!"
        openai_client.chat.completions.create.return_value = mock_completion

        def mock_get_client(provider, *args, **kwargs):
            if provider == "gemini":
                return gemini_client
            return openai_client

        with patch.object(self.router, "_get_client", side_effect=mock_get_client):
            res = await self.router.generate([{"role": "user", "content": "hi"}])
            self.assertEqual(res, "Hello from OpenAI!")
            self.assertEqual(self.router.health_states["gemini"].circuit_state, "OPEN")
            self.assertEqual(self.router.health_states["openai"].circuit_state, "CLOSED")

    @patch("app.services.ai_provider_router.os.environ.get")
    @patch("app.services.ai_provider_router.settings")
    async def test_all_providers_fail_returns_local_fallback(self, mock_settings, mock_env):
        """Verify that when all providers fail, a safe local fallback string is returned."""
        mock_env.return_value = "groq-key"
        mock_settings.OPENROUTER_API_KEY = "or-key"
        mock_settings.OPENROUTER_MODEL = "google/gemma-4-31b-it:free"
        mock_settings.GEMINI_API_KEY = "gemini-key"
        mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
        mock_settings.OPENAI_API_KEY = "openai-key"

        failing_client = AsyncMock()
        failing_client.chat.completions.create.side_effect = InternalServerError("500 error", response=MagicMock(status_code=500), body=None)

        with patch.object(self.router, "_get_client", return_value=failing_client):
            res = await self.router.generate([{"role": "user", "content": "feeling so stressed out"}])
            # Should fall back to the Stress fallback message
            self.assertIn("slow down with me", res.lower())

if __name__ == "__main__":
    unittest.main()
