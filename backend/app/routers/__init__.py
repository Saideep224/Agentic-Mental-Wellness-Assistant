"""
API routers.
"""

from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.onboarding import router as onboarding_router
from app.routers.dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "chat_router",
    "onboarding_router",
    "dashboard_router",
]
