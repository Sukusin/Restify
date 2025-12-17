from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    # Database
    database_url: str = "sqlite:///./app.db"

    # Security
    app_secret_key: str = "dev-secret-change-me"
    access_token_exp_minutes: int = 60 * 24

    # Local LLM
    llm_provider: str = "ollama"  # ollama | disabled
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"

    # Caching
    llm_cache_ttl_seconds: int = 60 * 10

    # Logging
    log_level: str = "INFO"
    log_dir: str = "./logs"


settings = Settings()
