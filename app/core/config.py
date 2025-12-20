from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


# Load .env early for local development
load_dotenv()


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    # Security
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "dev-secret-change-me")
    access_token_exp_minutes: int = int(os.getenv("ACCESS_TOKEN_EXP_MINUTES", str(60 * 24)))

    # Local LLM (Hugging Face)
    llm_provider: str = os.getenv("LLM_PROVIDER", "hf_local")  # hf_local | disabled
    hf_model_id: str = os.getenv("HF_MODEL_ID", "Qwen/Qwen2.5-14B-Instruct")
    hf_device: str = os.getenv("HF_DEVICE", "auto")  # auto | cpu | cuda

    # Quantization (bitsandbytes)
    hf_load_in_4bit: bool = os.getenv("HF_LOAD_IN_4BIT", "1").strip() not in {"0", "false", "False"}
    hf_4bit_quant_type: str = os.getenv("HF_4BIT_QUANT_TYPE", "nf4")  # nf4 | fp4
    hf_4bit_double_quant: bool = os.getenv("HF_4BIT_DOUBLE_QUANT", "1").strip() not in {"0", "false", "False"}
    hf_4bit_compute_dtype: str = os.getenv("HF_4BIT_COMPUTE_DTYPE", "float16")  # float16 | bfloat16

    # Generation params
    hf_max_new_tokens: int = int(os.getenv("HF_MAX_NEW_TOKENS", "256"))
    hf_temperature: float = float(os.getenv("HF_TEMPERATURE", "0.7"))
    hf_top_p: float = float(os.getenv("HF_TOP_P", "0.9"))

    # Caching
    llm_cache_ttl_seconds: int = int(os.getenv("LLM_CACHE_TTL_SECONDS", str(60 * 10)))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_dir: str = os.getenv("LOG_DIR", "./logs")

    # Places parser
    geoapify_url: str = os.getenv("GEOAPIFY_URL", "https://api.geoapify.com/v2/places")
    geoapify_key: str = os.getenv("GEOAPIFY_KEY", "")


settings = Settings()
