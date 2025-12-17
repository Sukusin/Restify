from __future__ import annotations

import hashlib
import json
import logging

import httpx

from app.core.config import settings
from app.services.cache import TTLCache

logger = logging.getLogger(__name__)

_cache = TTLCache(ttl_seconds=settings.llm_cache_ttl_seconds, max_items=512)


def _cache_key(prefix: str, payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(raw).hexdigest()}"


class LLMError(Exception):
    pass


class LocalLLM:
    """Minimal LLM facade (chat + summarization).

    Default provider: Ollama (local REST API on localhost:11434).
    """

    def __init__(self):
        self.provider = settings.llm_provider.lower().strip()

    async def chat(self, *, system: str, user_message: str, context: list[dict] | None = None) -> str:
        if self.provider == "disabled":
            return (
                "(LLM отключена) Я могу подобрать места по фильтрам. "
                "Откройте /recommendations или /places?category=..."
            )

        if self.provider != "ollama":
            raise LLMError(f"Unknown LLM provider: {self.provider}")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "stream": False,
        }
        key = _cache_key("chat", payload)
        cached = _cache.get(key)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=60) as client:
                resp = await client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = (data.get("message") or {}).get("content") or ""
        except Exception as e:
            logger.exception("Ollama chat failed")
            raise LLMError(str(e)) from e

        text = text.strip() or "(пустой ответ модели)"
        _cache.set(key, text)
        return text

    async def summarize_reviews(self, *, place_name: str, reviews: list[str]) -> str:
        if self.provider == "disabled":
            return "(LLM отключена)"

        joined = "\n\n".join(f"- {r}" for r in reviews)
        prompt = (
            f"Суммаризируй отзывы о месте '{place_name}'.\n"
            "Сделай кратко: 5–8 буллетов (плюсы/минусы) и общий вывод в 1 предложение.\n\n"
            f"Отзывы:\n{joined}"
        )

        payload = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        key = _cache_key("summary", payload)
        cached = _cache.get(key)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=60) as client:
                resp = await client.post("/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response") or ""
        except Exception as e:
            logger.exception("Ollama summary failed")
            raise LLMError(str(e)) from e

        text = text.strip() or "(пустой ответ модели)"
        _cache.set(key, text)
        return text


llm = LocalLLM()
