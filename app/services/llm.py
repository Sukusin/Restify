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
        # auto
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    @classmethod
    def _load_sync(cls) -> _HFState:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        import torch

        device = cls._pick_device()

        tokenizer = AutoTokenizer.from_pretrained(
            settings.hf_model_id,
            use_fast=True,
            trust_remote_code=True,
        )
        if getattr(tokenizer, "pad_token_id", None) is None:
            tokenizer.pad_token = tokenizer.eos_token

        use_4bit = bool(device == "cuda" and settings.hf_load_in_4bit)
        if use_4bit:
            from transformers import BitsAndBytesConfig

            compute_dtype = (
                torch.bfloat16
                if (settings.hf_4bit_compute_dtype or "").lower() == "bfloat16"
                else torch.float16
            )
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type=settings.hf_4bit_quant_type,
                bnb_4bit_use_double_quant=settings.hf_4bit_double_quant,
                bnb_4bit_compute_dtype=compute_dtype,
            )

            model = AutoModelForCausalLM.from_pretrained(
                settings.hf_model_id,
                quantization_config=bnb_config,
                device_map="auto",
                low_cpu_mem_usage=True,
                trust_remote_code=True,
                dtype="auto",
            )
        else:
            # Dtype: fp16 on CUDA; fp32 on CPU.
            dtype = torch.float16 if device == "cuda" else torch.float32

            model = AutoModelForCausalLM.from_pretrained(
                settings.hf_model_id,
                dtype=dtype,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
            model.to(device)

        model.eval()

        model_device = device
        try:
            first_param = next(model.parameters())
            model_device = str(first_param.device)
        except Exception:
            model_device = "cuda:0" if device == "cuda" else "cpu"

        try:
            if getattr(model, "generation_config", None) is not None:
                if getattr(model.generation_config, "pad_token_id", None) is None:
                    model.generation_config.pad_token_id = tokenizer.pad_token_id
        except Exception:
            pass

        return _HFState(tokenizer=tokenizer, model=model, device=model_device)

    @staticmethod
    def _build_prompt(tokenizer: object, messages: list[dict]) -> str:
        apply = getattr(tokenizer, "apply_chat_template", None)
        if callable(apply):
            return apply(messages, tokenize=False, add_generation_prompt=True)

        # Fallback: very simple chat formatting.
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
