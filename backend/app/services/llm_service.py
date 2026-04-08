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
            }
            if use_cuda:
                pipeline_kwargs["device_map"] = "auto"
                pipeline_kwargs["torch_dtype"] = torch.float16

            LLMService._generator = pipeline(**pipeline_kwargs)
        return LLMService._generator

    def _generate_once(self, prompt: str, max_new_tokens: int) -> str:
        generator = self._get_generator()
        output = generator(
            prompt,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            return_full_text=False,
        )[0]["generated_text"]
        return output.strip()

    def generate(
        self,
        prompt: str,
        timeout_seconds: int | None = None,
        max_new_tokens: int = 380,
    ) -> str:
        timeout = timeout_seconds or settings.CHAT_GENERATION_TIMEOUT_SECONDS

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._generate_once, prompt, max_new_tokens)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as exc:
            raise TimeoutError(f"LLM generation timed out after {timeout} seconds") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
