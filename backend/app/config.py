"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider
    llm_provider: str = "mock"          # mock | gemini
    llm_model: str = "gemini-2.0-flash"
    google_api_key: str = ""

    # Resilience
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2
    llm_fallback_model: str = ""

    # Streaming / conversations
    mock_stream_delay: float = 0.0       # seconds between mock tokens; >0 makes the demo visibly stream
    conversation_history_turns: int = 6  # prior turns fed back into the response prompt

    # Prompts
    prompt_version: str = "v2"

    # Retrieval
    rag_top_k: int = 5
    rag_min_score: float = 0.10

    # Storage
    sqlite_path: str = "data/runtime/app.sqlite"
    vector_db: str = "chroma"
    chroma_path: str = ".chroma"

    # App
    api_port: int = 8000
    dashboard_port: int = 8501

    # CORS — the Next.js frontend (Vercel + local dev) calls this API.
    # Comma-separated; kept a str (not list) to avoid pydantic-settings JSON-list env parsing.
    cors_allow_origins: str = "http://localhost:3000"
    cors_allow_origin_regex: str = ""        # e.g. https://.*-myproject\.vercel\.app for preview URLs

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


settings = Settings()
