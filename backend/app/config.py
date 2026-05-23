"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and .env file support.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Esona application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/esona"

    # ── OpenAI ────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # ── Gemini ────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    @property
    def llm_api_key(self) -> str:
        return self.GEMINI_API_KEY or self.OPENAI_API_KEY

    @property
    def llm_base_url(self) -> str | None:
        if self.GEMINI_API_KEY:
            return self.GEMINI_API_BASE
        return None

    @property
    def llm_model(self) -> str:
        if self.GEMINI_API_KEY:
            return self.GEMINI_MODEL
        return self.OPENAI_MODEL

    @property
    def embedding_model(self) -> str:
        if self.GEMINI_API_KEY:
            return self.GEMINI_EMBEDDING_MODEL
        return "text-embedding-3-small"

    # ── ChromaDB ──────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # ── Frontend ──────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"


settings = Settings()
