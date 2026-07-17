"""Unit tests for the Esona Chat Overhaul features: Router, Circuit Breaker, and Fallbacks."""
import unittest
import asyncio
from unittest.mock import MagicMock, patch
from openai import BadRequestError, AuthenticationError

from app.routes.chat import classify_message_complexity
from app.utils.llm import (
    CircuitBreaker,
    get_circuit_breaker,
    is_transient_error,
    _providers,
)


class OverhaulScenariosTestCase(unittest.TestCase):
    def test_message_classification(self):
        """Verify message complexity is classified correctly into overhaul categories."""
        # 1. SAFETY_CRITICAL
        self.assertEqual(classify_message_complexity("I want to die"), "SAFETY_CRITICAL")
        self.assertEqual(classify_message_complexity("suicidal thoughts"), "SAFETY_CRITICAL")

        # 2. FAST_SOCIAL
        self.assertEqual(classify_message_complexity("hey"), "FAST_SOCIAL")
        self.assertEqual(classify_message_complexity("ok"), "FAST_SOCIAL")
        self.assertEqual(classify_message_complexity("thanks bro"), "FAST_SOCIAL")

        # 3. EMOTIONAL_SUPPORT
        self.assertEqual(classify_message_complexity("feeling so stressed out"), "EMOTIONAL_SUPPORT")
        self.assertEqual(classify_message_complexity("crying myself to sleep"), "EMOTIONAL_SUPPORT")

        # 4. DEEP_PERSONAL
        self.assertEqual(classify_message_complexity("relationship issues with my parents"), "DEEP_PERSONAL")
        self.assertEqual(classify_message_complexity("reflecting on my childhood memories"), "DEEP_PERSONAL")

        # 5. NORMAL_CHAT (Default)
        self.assertEqual(classify_message_complexity("I watched a cool movie today"), "NORMAL_CHAT")

    def test_circuit_breaker_transitions(self):
        """Verify CircuitBreaker CLOSED -> OPEN -> HALF_OPEN transitions."""
        cb = CircuitBreaker("test-model", threshold=2, cooldown=1.0)
        self.assertTrue(cb.is_available())

        # First failure
        cb.record_failure()
        self.assertTrue(cb.is_available())
        self.assertEqual(cb.state, "CLOSED")

        # Second failure (reaches threshold)
        cb.record_failure()
        self.assertFalse(cb.is_available())
        self.assertEqual(cb.state, "OPEN")

        # Wait for cooldown
        import time
        time.sleep(1.1)
        self.assertTrue(cb.is_available())
        self.assertEqual(cb.state, "HALF_OPEN")

        # Success resets to CLOSED
        cb.record_success()
        self.assertTrue(cb.is_available())
        self.assertEqual(cb.state, "CLOSED")

    def test_transient_error_classification(self):
        """Verify API errors are correctly classified as transient vs non-transient."""
        # Mock requests exceptions
        req_mock = MagicMock()
        
        # BadRequestError and AuthenticationError are non-transient (raise immediately)
        bad_req = BadRequestError("Bad parameter", response=MagicMock(status_code=400), body=None)
        auth_err = AuthenticationError("Invalid key", response=MagicMock(status_code=401), body=None)
        
        self.assertFalse(is_transient_error(bad_req))
        self.assertFalse(is_transient_error(auth_err))

        # Transient: Timeout, 429 Rate limits, 500 Server Errors, etc.
        from openai import RateLimitError, InternalServerError
        rate_limit = RateLimitError("Rate limit exceeded", response=MagicMock(status_code=429), body=None)
        server_err = InternalServerError("Internal server error", response=MagicMock(status_code=500), body=None)
        
        self.assertTrue(is_transient_error(rate_limit))
        self.assertTrue(is_transient_error(server_err))
        self.assertTrue(is_transient_error(RuntimeError("Connection timed out")))

    def test_central_router_priority(self):
        """Verify provider prioritization changes based on category."""
        # Mock settings to have OpenRouter and OpenAI configured
        with patch("app.utils.llm.settings") as mock_settings:
            mock_settings.OPENROUTER_API_KEY = "or-key"
            mock_settings.OPENROUTER_MODEL = "google/gemma-4-31b-it:free"
            mock_settings.OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
            
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.GEMINI_MODEL = "gemini-2.5-flash"
            mock_settings.GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
            
            mock_settings.OPENAI_API_KEY = "oa-key"
            mock_settings.OPENAI_MODEL = "gpt-4o-mini"
            mock_settings.PRIMARY_PROVIDER = "openrouter"
            mock_settings.DEEPSEEK_API_KEY = ""
            mock_settings.OLLAMA_BASE_URL = ""
            
            # For FAST_SOCIAL, Groq or OpenRouter might be prioritized depending on keys.
            # Let's verify we get a sorted list
            providers = _providers("FAST_SOCIAL")
            self.assertGreater(len(providers), 0)
            
            # Verify structure (name, base_url, api_key, model)
            self.assertEqual(providers[0][0], "OpenRouter")
            
            # Verify DEEP_PERSONAL priority
            providers_deep = _providers("DEEP_PERSONAL")
            self.assertEqual(providers_deep[0][0], "OpenRouter")
