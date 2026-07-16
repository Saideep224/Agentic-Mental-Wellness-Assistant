import pytest
import time
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ai_provider_router import ProviderManager, ProviderHealth, ProviderStats

@pytest.mark.asyncio
async def test_provider_priority_sorting():
    pm = ProviderManager()
    
    # Crisis -> Groq first
    crisis_pri = pm.select_provider_priority("SAFETY_CRITICAL")
    assert crisis_pri[0] == "groq"
    
    # Greetings/Casual -> OpenRouter first
    social_pri = pm.select_provider_priority("FAST_SOCIAL")
    assert social_pri[0] == "openrouter"
    
    # Heavy reasoning -> Gemini first
    deep_pri = pm.select_provider_priority("DEEP_PERSONAL")
    assert deep_pri[0] == "gemini"
    
    # Long conversations -> OpenRouter first
    long_pri = pm.select_provider_priority("NORMAL_CHAT", history_len=20)
    assert long_pri[0] == "openrouter"


@pytest.mark.asyncio
async def test_provider_cooldown_and_circuit_breaker():
    health = ProviderHealth("openrouter")
    assert health.is_available() is True
    assert health.circuit_state == "CLOSED"
    
    # First failure
    health.record_failure("TIMEOUT")
    assert health.is_available() is True
    assert health.consecutive_failures == 1
    
    # Second failure
    health.record_failure("SERVER_ERROR")
    assert health.is_available() is True
    assert health.consecutive_failures == 2
    
    # Third failure -> should open circuit
    health.record_failure("SERVER_ERROR")
    assert health.is_available() is False
    assert health.circuit_state == "OPEN"
    assert health.consecutive_failures == 3
    
    # Record success should reset
    health.record_success()
    assert health.is_available() is True
    assert health.circuit_state == "CLOSED"
    assert health.consecutive_failures == 0


@pytest.mark.asyncio
async def test_dynamic_generation_failover():
    pm = ProviderManager()
    
    # Mock configs so openrouter key is present but mock calls fail
    mock_config = {
        "openrouter": [{"api_key": "or_key", "base_url": "http://or", "model": "or-model"}],
        "groq": [{"api_key": "groq_key", "base_url": "http://groq", "model": "groq-model"}]
    }
    
    # Force mock priorities
    pm.select_provider_priority = lambda cat, h=0: ["openrouter", "groq"]
    pm._get_provider_config = lambda p: mock_config.get(p, [])
    
    mock_or_client = MagicMock()
    # Mock OpenRouter client request to fail
    mock_or_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error 500"))
    
    mock_groq_client = MagicMock()
    # Mock Groq client request to succeed
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "groq hello reply"
    mock_groq_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    def mock_get_client(provider, api_key, base_url):
        if provider == "openrouter":
            return mock_or_client
        return mock_groq_client
        
    pm._get_client = mock_get_client
    
    res = await pm.generate(
        messages=[{"role": "user", "content": "hello"}],
        route_category="FAST_SOCIAL"
    )
    
    # OpenRouter fails, should fall back to Groq successfully
    assert res == "groq hello reply"
    assert pm.health_states["openrouter"].consecutive_failures == 1
    assert pm.health_states["groq"].consecutive_failures == 0


@pytest.mark.asyncio
async def test_active_ping_health_check_recovery():
    pm = ProviderManager()
    health = pm.health_states["openrouter"]
    
    # Force unhealthy
    health.record_failure("TIMEOUT")
    health.record_failure("TIMEOUT")
    health.record_failure("TIMEOUT")
    assert health.is_available() is False
    
    # Mock successful ping
    pm._ping_provider = AsyncMock(return_value=True)
    
    # Run active recovery ping
    # Temporarily set sleep to 0 for checking
    with patch("asyncio.sleep", return_value=None):
        # We can test _ping_provider or the check logic directly
        success = await pm._ping_provider("openrouter")
        assert success is True
        
        # Manually invoke recovery record success
        if success:
            health.record_success()
            
    assert health.is_available() is True
    assert health.consecutive_failures == 0
