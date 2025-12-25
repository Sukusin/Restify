from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from functools import partial

import anyio

from app.core.config import settings
from app.services.cache import TTLCache

logger = logging.getLogger(__name__)

_cache = TTLCache(ttl_seconds=settings.llm_cache_ttl_seconds, max_items=512)


def _cache_key(prefix: str, payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(raw).hexdigest()}"


class LLMError(Exception):
    pass


@dataclass
class _HFState:
    tokenizer: object
    model: object
    device: str


class LocalLLM:

    def __init__(self) -> None:
        self.provider = (settings.llm_provider or "").lower().strip()
        self._state: _HFState | None = None
        self._load_lock = anyio.Lock()

    async def _ensure_loaded(self) -> _HFState:
        if self._state is not None:
            return self._state

        async with self._load_lock:
            if self._state is not None:
                return self._state

            if self.provider == "disabled":
                raise LLMError("LLM is disabled")

            if self.provider not in {"hf_local", "hf"}:
                raise LLMError(f"Unknown LLM provider: {self.provider}")

            logger.info(
                "Loading HF model: %s (device=%s)", settings.hf_model_id, settings.hf_device
            )
            state = await anyio.to_thread.run_sync(self._load_sync)
            self._state = state
            logger.info("HF model ready: %s (%s)", settings.hf_model_id, state.device)
            return state

    @staticmethod
    def _pick_device() -> str:
        wanted = (settings.hf_device or "auto").lower().strip()
        if wanted in {"cpu", "cuda"}:
            return wanted
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    @classmethod
    def _load_sync(cls) -> _HFState:
        # Heavy imports inside so app starts fast when LLM is disabled
        from transformers import AutoModelForCausalLM, AutoTokenizer

        import torch

        device = cls._pick_device()

        # Dtype: fp16 on CUDA; fp32 on CPU
        dtype = torch.float16 if device == "cuda" else torch.float32

        tokenizer = AutoTokenizer.from_pretrained(settings.hf_model_id, use_fast=True)
        model = AutoModelForCausalLM.from_pretrained(
            settings.hf_model_id,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
            cache_dir="weights"
        )
        model.eval()
        model.to(device)
        return _HFState(tokenizer=tokenizer, model=model, device=device)

    @staticmethod
    def _build_prompt(tokenizer: object, messages: list[dict]) -> str:
        apply = getattr(tokenizer, "apply_chat_template", None)
        if callable(apply):
            return apply(messages, tokenize=False, add_generation_prompt=True)

        parts: list[str] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"[SYSTEM]\n{content}\n")
            elif role == "assistant":
                parts.append(f"[ASSISTANT]\n{content}\n")
            else:
                parts.append(f"[USER]\n{content}\n")
        parts.append("[ASSISTANT]\n")
        return "\n".join(parts)

    @classmethod
    def _generate_sync(
        cls,
        state: _HFState,
        messages: list[dict],
        *,
        max_new_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        import torch

        tokenizer = state.tokenizer
        model = state.model

        prompt = cls._build_prompt(tokenizer, messages)
        inputs = tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(state.device) for k, v in inputs.items()}
        input_len = inputs["input_ids"].shape[-1]

        do_sample = temperature > 0
        gen_kwargs = {
            "max_new_tokens": int(max_new_tokens),
            "do_sample": bool(do_sample),
        }
        if do_sample:
            gen_kwargs.update(
                {
                    "temperature": float(temperature),
                    "top_p": float(top_p),
                }
            )

        with torch.inference_mode():
            out = model.generate(**inputs, **gen_kwargs)

        new_tokens = out[0][input_len:]
        text = tokenizer.decode(new_tokens, skip_special_tokens=True)
        return (text or "").strip()

    async def chat(self, *, system: str, user_message: str, context: list[dict] | None = None) -> str:
        if self.provider == "disabled":
            return (
                "(LLM отключена) Я могу подобрать места по фильтрам. "
                "Откройте /recommendations или /places?category=..."
            )

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        if context:
            messages.extend(context)
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": settings.hf_model_id,
            "messages": messages,
            "max_new_tokens": settings.hf_max_new_tokens,
            "temperature": settings.hf_temperature,
            "top_p": settings.hf_top_p,
        }
        key = _cache_key("chat", payload)
        cached = _cache.get(key)
        if cached is not None:
            return cached

        try:
            state = await self._ensure_loaded()
            fn = partial(
                self._generate_sync,
                state,
                messages,
                max_new_tokens=settings.hf_max_new_tokens,
                temperature=settings.hf_temperature,
                top_p=settings.hf_top_p,
            )
            text = await anyio.to_thread.run_sync(fn)
        except Exception as e:
            logger.exception("HF LLM chat failed")
            raise LLMError(str(e)) from e

        text = text.strip() or "(пустой ответ модели)"
        _cache.set(key, text)
        return text

    async def summarize_reviews(self, *, place_name: str, reviews: list[str]) -> str:
        if self.provider == "disabled":
            return "(LLM отключена)"

        joined = "\n".join(f"- {r}" for r in reviews)
        system = "Ты помощник, который кратко суммаризирует отзывы." \
            " Пиши по-русски, без воды."
        user_message = (
            f"Суммаризируй отзывы о месте '{place_name}'.\n"
            "Сделай: 5–8 буллетов (плюсы/минусы) и общий вывод в 1 предложение.\n\n"
            f"Отзывы:\n{joined}"
        )

        payload = {
            "model": settings.hf_model_id,
            "place": place_name,
            "reviews_hash": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
            "max_new_tokens": min(256, settings.hf_max_new_tokens),
            "temperature": 0.2,
            "top_p": 0.9,
        }
        key = _cache_key("summary", payload)
        cached = _cache.get(key)
        if cached is not None:
            return cached

        try:
            state = await self._ensure_loaded()
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ]
            fn = partial(
                self._generate_sync,
                state,
                messages,
                max_new_tokens=min(256, settings.hf_max_new_tokens),
                temperature=0.2,
                top_p=0.9,
            )
            text = await anyio.to_thread.run_sync(fn)
        except Exception as e:
            logger.exception("HF LLM summary failed")
            raise LLMError(str(e)) from e

        text = text.strip() or "(пустой ответ модели)"
        _cache.set(key, text)
        return text


llm = LocalLLM()
