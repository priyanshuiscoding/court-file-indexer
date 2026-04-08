from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import torch
from transformers import pipeline

from app.core.config import get_settings

settings = get_settings()


class LLMService:
    _generator = None

    def _get_generator(self):
        if LLMService._generator is None:
            use_cuda = torch.cuda.is_available()
            pipeline_kwargs = {
                "task": "text-generation",
                "model": settings.LOCAL_CHAT_MODEL,
                "max_new_tokens": 300,
            }
            if use_cuda:
                pipeline_kwargs["device_map"] = "auto"
                pipeline_kwargs["torch_dtype"] = torch.float16

            LLMService._generator = pipeline(**pipeline_kwargs)
        return LLMService._generator

    def _generate_once(self, prompt: str) -> str:
        generator = self._get_generator()
        output = generator(prompt)[0]["generated_text"]
        if output.startswith(prompt):
            return output[len(prompt) :].strip()
        return output.strip()

    def generate(self, prompt: str, timeout_seconds: int | None = None) -> str:
        timeout = timeout_seconds or settings.CHAT_GENERATION_TIMEOUT_SECONDS

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._generate_once, prompt)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as exc:
            raise TimeoutError(f"LLM generation timed out after {timeout} seconds") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
