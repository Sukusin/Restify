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

    # Local LLM (Hugging Face)
    # Minimal local inference via Transformers.
    # `hf_local`  - use a local Hugging Face model (downloaded on first run)
    # `disabled`  - turn off LLM features
    llm_provider: str = "hf_local"  # hf_local | disabled

    # Default: small free model
    hf_model_id: str = "Qwen/Qwen3-8B"
    # auto | cpu | cuda
    hf_device: str = "auto"

    # Generation params
    hf_max_new_tokens: int = 256
    hf_temperature: float = 0.7
    hf_top_p: float = 0.9

    # Caching
    llm_cache_ttl_seconds: int = 60 * 10

    # Logging
    log_level: str = "INFO"
    log_dir: str = "./logs"


settings = Settings()
