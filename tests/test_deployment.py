"""Day 7 — deployment slice.

Two things must hold for `docker compose up` to be trustworthy:
1. provider/config is genuinely env-driven (the image ships sane defaults but env overrides win), and
2. the committed deploy files stay coherent with how the app actually runs (module path, port, healthcheck).
These tests are static/in-process, so they need neither Docker nor a network.
"""

from __future__ import annotations

from pathlib import Path

from app.config import Settings

ROOT = Path(__file__).resolve().parent.parent


def test_provider_config_is_env_driven(monkeypatch):
    # Defaults: no key needed, mock provider runs the whole pipeline.
    assert Settings(_env_file=None).llm_provider == "mock"

    # Env overrides win — this is what docker-compose injects for a real provider.
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("API_PORT", "9001")
    s = Settings(_env_file=None)
    assert s.llm_provider == "gemini"
    assert s.google_api_key == "test-key"
    assert s.api_port == 9001


def test_env_example_keys_all_map_to_settings():
    """Every key documented in .env.example must be a real setting, or the example lies."""
    fields = set(Settings.model_fields)
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip().lower()
        assert key in fields, f".env.example documents unknown setting: {key}"


def test_dockerfile_runs_the_app_on_the_expected_port():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "app.main:app" in dockerfile          # serves the real ASGI app
    assert "--port" in dockerfile and "8000" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "/health" in dockerfile               # healthcheck hits a route that exists
    assert "USER appuser" in dockerfile          # not running as root


def test_compose_is_coherent_with_the_image():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "build: ." in compose
    assert ":8000" in compose                    # maps the container port the app listens on
    assert "/app/data/runtime" in compose        # persists the sqlite run/trace store
