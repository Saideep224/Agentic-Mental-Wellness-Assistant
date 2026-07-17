import pytest
import time
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ai_provider_router import ProviderManager, TokenChunk

@pytest.mark.asyncio
async def test_token_chunk_normalization():
    pm = ProviderManager()
    
    mock_config = {
        "openrouter": [{"api_key": "or_key", "base_url": "http://or", "model": "or-model"}]
    }
    pm._get_provider_config = lambda p: mock_config.get(p, [])
    
    mock_client = MagicMock()
    # Mock OpenRouter chat completions generator
    async def mock_async_generator():
        class MockChoiceDelta:
            def __init__(self, content):
                self.content = content
        class MockChoice:
            def __init__(self, content):
                self.delta = MockChoiceDelta(content)
        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(content)]
        yield MockChunk("hello ")
        yield MockChunk("buddy")
        
    mock_client.chat.completions.create = AsyncMock(return_value=mock_async_generator())
    pm._get_client = lambda p, k, b: mock_client
    
    chunks = []
    async for chunk in pm.stream(
        messages=[{"role": "user", "content": "hi"}],
        route_category="FAST_SOCIAL"
    ):
        chunks.append(chunk)
        
    assert len(chunks) == 3
    assert all(isinstance(c, TokenChunk) for c in chunks)
    assert chunks[0].text == "hello "
    assert chunks[0].finished is False
    assert chunks[1].text == "buddy"
    assert chunks[1].finished is False
    assert chunks[2].text == ""
    assert chunks[2].finished is True


@pytest.mark.asyncio
async def test_mid_stream_failover_and_recovery():
    pm = ProviderManager()
    
    mock_config = {
        "openrouter": [{"api_key": "or_key", "base_url": "http://or", "model": "or-model"}],
        "groq": [{"api_key": "groq_key", "base_url": "http://groq", "model": "groq-model"}]
    }
    pm._get_provider_config = lambda p: mock_config.get(p, [])
    pm.select_provider_priority = lambda cat, h=0: ["openrouter", "groq"]
    
    mock_or_client = MagicMock()
    # Mock OpenRouter generator that yields one token and then throws connection error
    async def mock_or_generator():
        class MockChoiceDelta:
            def __init__(self, content):
                self.content = content
        class MockChoice:
            def __init__(self, content):
                self.delta = MockChoiceDelta(content)
        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(content)]
        yield MockChunk("part 1 ")
        raise ConnectionError("Simulated network dropout mid-stream")
        
    mock_or_client.chat.completions.create = AsyncMock(return_value=mock_or_generator())
    
    mock_groq_client = MagicMock()
    # Mock Groq generator that succeeds
    async def mock_groq_generator():
        class MockChoiceDelta:
            def __init__(self, content):
                self.content = content
        class MockChoice:
            def __init__(self, content):
                self.delta = MockChoiceDelta(content)
        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(content)]
        yield MockChunk("part 2 finished")
        
    mock_groq_client.chat.completions.create = AsyncMock(return_value=mock_groq_generator())
    
    def mock_get_client(provider, api_key, base_url):
        if provider == "openrouter":
            return mock_or_client
        return mock_groq_client
        
    pm._get_client = mock_get_client
    
    chunks = []
    async for chunk in pm.stream(
        messages=[{"role": "user", "content": "hi"}],
        route_category="FAST_SOCIAL"
    ):
        chunks.append(chunk)
        
    # Check that we received chunks from both providers merged seamlessly
    assert len(chunks) == 3
    assert chunks[0].text == "part 1 "
    assert chunks[0].finished is False
    # Groq finishes it
    assert chunks[1].text == "part 2 finished"
    assert chunks[1].finished is False
    assert chunks[2].text == ""
    assert chunks[2].finished is True
