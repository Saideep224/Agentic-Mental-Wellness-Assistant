"""
Backward-compatibility shim — redirects to the new chatbot.pipeline module.

All actual logic has been moved to app.chatbot.pipeline.
This file is kept only so existing imports like `from app.agents.graph import run_agent_graph`
continue to work during the transition period.

NOTE: Uses lazy imports to avoid circular dependency with chatbot.pipeline.
"""


def __getattr__(name):
    """Lazy import to avoid circular dependency."""
    if name == "run_agent_graph":
        from app.chatbot.pipeline import run_agent_graph
        return run_agent_graph
    elif name == "AgentState":
        from app.chatbot.state import AgentState
        return AgentState
    elif name == "client":
        from app.utils.llm import get_chat_client
        return get_chat_client()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
