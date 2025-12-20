from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env for local development (if file exists).
load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    # Database
    database_url: str = "sqlite:///./app.db"

    # Security
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "dev-secret-change-me")
    access_token_exp_minutes: int = 60 * 24

    # Local LLM (Hugging Face)
    # hf_local | disabled
    llm_provider: str = os.getenv("LLM_PROVIDER", "hf_local")
    hf_model_id: str = os.getenv("HF_MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")
    # auto | cpu | cuda
    hf_device: str = os.getenv("HF_DEVICE", "auto")

    # Generation params
    hf_max_new_tokens: int = 256
    hf_temperature: float = 0.7
    hf_top_p: float = 0.9

    # Caching
    llm_cache_ttl_seconds: int = 60 * 10

    # Logging
    log_level: str = "INFO"
    log_dir: str = "./logs"

    # Places parser
    geoapify_url: str = "https://api.geoapify.com/v2/places"
    geoapify_key: str = os.getenv("GEOAPIFY_KEY", "")


settings = Settings()
