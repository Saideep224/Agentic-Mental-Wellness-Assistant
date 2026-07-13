"""Application services — business logic layers.

Keep this package initializer lightweight. Importing one service must not eagerly import
all other services during FastAPI startup; that previously turned an unrelated stale
export into a full Render boot failure.
"""

__all__ = [
    "analyze_onboarding",
    "MoodTracker",
    "memory_service",
    "profile_service",
    "knowledge_graph_service",
    "recommendation_service",
    "mentalbert_service",
]


def __getattr__(name):
    """Lazily resolve legacy package-level service exports."""
    if name == "analyze_onboarding":
        from app.services.onboarding_analyzer import analyze_onboarding
        return analyze_onboarding
    if name == "MoodTracker":
        from app.services.mood_tracker import MoodTracker
        return MoodTracker
    if name == "memory_service":
        from app.services.memory_service import memory_service
        return memory_service
    if name == "profile_service":
        from app.services.profile_service import profile_service
        return profile_service
    if name == "knowledge_graph_service":
        from app.services.knowledge_graph_service import knowledge_graph_service
        return knowledge_graph_service
    if name == "recommendation_service":
        from app.services.recommendation_service import recommendation_service
        return recommendation_service
    if name == "mentalbert_service":
        from app.services.mentalbert_service import mentalbert_service
        return mentalbert_service
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
