"""
API routes package init.
"""

from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.onboarding import router as onboarding_router
from app.routes.dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "chat_router",
    "onboarding_router",
    "dashboard_router",
]
