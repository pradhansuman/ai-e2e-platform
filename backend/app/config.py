"""Application configuration loaded from environment variables / .env.

All secrets live here and are read via pydantic-settings. Never hard-code
credentials anywhere else in the codebase.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root (ai-e2e-platform/), so .env is found regardless of the CWD the
# server is launched from (repo root, backend/, or Docker env vars).
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ai-e2e-platform"
    environment: Literal["dev", "test", "staging", "prod"] = "dev"
    api_prefix: str = "/api/v1"

    # ------------------------------------------------------------------ LLM
    # auto: prefer OpenRouter if a key is set, then Anthropic, then OpenAI.
    llm_provider: Literal[
        "auto", "openai", "openrouter", "anthropic", "google", "groq", "cerebras", "mistral"
    ] = "auto"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.0
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # OpenRouter (OpenAI-compatible; free-tier models available).
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemma-4-26b-a4b-it:free"
    # Comma-separated extra free models to fail over to (in preference order)
    # when the primary model is rate-limited / unavailable.
    openrouter_fallback_models: str = ""

    # Google Gemini (via the OpenAI-compatible endpoint, so we reuse ChatOpenAI
    # and get native function-calling / structured output).
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    # Groq (OpenAI-compatible; free tier with fast llama models).
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Cerebras (OpenAI-compatible; free tier ~1M tokens/day, fast inference).
    cerebras_api_key: str | None = None
    cerebras_model: str = "llama-3.3-70b"
    cerebras_base_url: str = "https://api.cerebras.ai/v1"

    # Mistral (OpenAI-compatible; free tier with rate limits).
    mistral_api_key: str | None = None
    mistral_model: str = "mistral-small-latest"
    mistral_base_url: str = "https://api.mistral.ai/v1"

    # --- LLM resilience (free-tier models are often rate-limited) ---
    llm_max_retries: int = 4
    llm_timeout: int = 180

    # ------------------------------------------------------------ LangSmith
    langsmith_api_key: str | None = None
    langsmith_project: str = "ai-e2e-platform"
    langsmith_tracing: bool = True

    # ------------------------------------------------------------ Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_e2e"
    )

    # --------------------------------------------------------- Vector store
    vector_store_url: str = "http://localhost:6333"  # Qdrant REST endpoint
    vector_store_collection: str = "test_knowledge"
    embedding_model: str = "text-embedding-3-small"

    # ----------------------------------------------------------- Playwright
    browser_headless: bool = True
    browser_timeout_ms: int = 30_000
    browser_slow_mo: int = 0  # ms delay between actions (watchable headed runs)
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    screenshot_dir: str = ".artifacts/screenshots"
    trace_dir: str = ".artifacts/traces"
    video_dir: str = ".artifacts/videos"

    # ------------------------------------------------------ Workflow limits
    max_retries: int = 3
    max_heal_retries: int = 2
    # When True, self-healing changes are blocked pending human approval.
    human_approval_required: bool = True
    # Background workers draining the run queue (serial by default to avoid
    # overloading the browser + free-tier LLM).
    worker_concurrency: int = 1

    # ------------------------------------------------------------ Security
    secret_key: str = Field(default="dev-only-insecure-secret-0000000000000000", repr=False)
    admin_api_token: str | None = None
    allow_unauthenticated: bool = True
    # Regex/field allow-list used by the data-masking layer.
    pii_fields: tuple[str, ...] = (
        "password",
        "token",
        "secret",
        "api_key",
        "authorization",
        "credit_card",
        "ssn",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
