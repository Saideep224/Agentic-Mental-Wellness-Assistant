"""
API routes package — all FastAPI routers for the Esona backend.
"""

from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.conversations import router as conversations_router
from app.routes.onboarding import router as onboarding_router
from app.routes.dashboard import router as dashboard_router, mood_router
from app.routes.insights import router as insights_router

__all__ = [
    "auth_router",
    "chat_router",
    "conversations_router",
    "onboarding_router",
    "dashboard_router",
    "insights_router",
    "mood_router",
]
