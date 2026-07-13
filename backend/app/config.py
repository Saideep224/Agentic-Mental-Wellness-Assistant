"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and .env file support.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Esona application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    # For local dev: sqlite+aiosqlite:///./esona.db
    # For Supabase: postgresql+asyncpg://postgres.[REF]:[PASS]@aws-0-[REGION].pooler.supabase.com:6543/postgres
    DATABASE_URL: str = "sqlite+aiosqlite:///./esona.db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    # ── Supabase (optional, for direct client access if needed) ─
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # Required for Admin API (account deletion)

    # ── OpenAI ────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"  # Cheaper than gpt-4o, excellent for conversational chat

    # ── Gemini ────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-2"
    GEMINI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # ── OpenRouter ────────────────────────────────────────────
    USE_OPENROUTER: bool = False  # Provider routing handled by PRIMARY_PROVIDER in llm.py
    OPENROUTER_API_KEY: str = ""
    # Free-tier waterfall: all models are zero-cost. Tries each in order on rate-limit/errors.
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it:free,meta-llama/llama-3.3-70b-instruct:free,qwen/qwen3-next-80b-a3b-instruct:free,google/gemma-4-26b-a4b-it:free,nousresearch/hermes-3-llama-3.1-405b:free"
    OPENROUTER_API_BASE: str = "https://openrouter.ai/api/v1"

    PRIMARY_PROVIDER: str = "openrouter"  # Use openrouter with free models by default

    # ── Ollama ────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = ""  # Leave empty if Ollama is not running locally
    OLLAMA_MODEL: str = "llama3"

    # ── DeepSeek ──────────────────────────────────────────────
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"

    # ── UncloseAI ─────────────────────────────────────────────
    USE_UNCLOSEAI: bool = False
    UNCLOSEAI_API_BASE: str = "https://hermes.ai.unturf.com/v1"
    UNCLOSEAI_MODEL: str = "adamo1139/Hermes-3-Llama-3.1-8B-FP8-Dynamic"

    @property
    def llm_api_key(self) -> str:
        if self.USE_OPENROUTER:
            return self.OPENROUTER_API_KEY or self.OPENAI_API_KEY
        if self.USE_UNCLOSEAI:
            return self.OPENAI_API_KEY or "free"
        return self.GEMINI_API_KEY or self.OPENAI_API_KEY

    @property
    def llm_base_url(self) -> str | None:
        if self.USE_OPENROUTER:
            return self.OPENROUTER_API_BASE
        if self.USE_UNCLOSEAI:
            return self.UNCLOSEAI_API_BASE
        if self.GEMINI_API_KEY:
            return self.GEMINI_API_BASE
        return None

    @property
    def llm_model(self) -> str:
        if self.USE_OPENROUTER:
            return self.OPENROUTER_MODEL
        if self.USE_UNCLOSEAI:
            return self.UNCLOSEAI_MODEL
        if self.GEMINI_API_KEY:
            return self.GEMINI_MODEL
        return self.OPENAI_MODEL

    @property
    def embedding_model(self) -> str:
        if self.USE_OPENROUTER:
            return "text-embedding-3-small"
        if self.USE_UNCLOSEAI:
            return "text-embedding-3-small"
        if self.GEMINI_API_KEY:
            return self.GEMINI_EMBEDDING_MODEL
        return "text-embedding-3-small"

    @property
    def is_postgres(self) -> bool:
        """Check if the database is PostgreSQL (Supabase)."""
        return self.DATABASE_URL.startswith("postgresql")

    # ── ChromaDB ──────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # ── Frontend ──────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Local Emotion Model (MentalBERT / general) ────────────
    USE_LOCAL_EMOTION_MODEL: bool = False
    EMOTION_MODEL_NAME: str = "bhadresh-savani/bert-base-uncased-emotion"


settings = Settings()
