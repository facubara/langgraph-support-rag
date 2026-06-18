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


settings = Settings()
