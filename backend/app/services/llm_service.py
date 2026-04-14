from __future__ import annotations

import json
from urllib import error, request

from app.core.config import get_settings

settings = get_settings()


class LLMService:
    def _ollama_generate(self, prompt: str, timeout_seconds: int, max_new_tokens: int) -> str:
        payload = {
            "model": settings.OLLAMA_CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": max_new_tokens,
            },
        }

        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=timeout_seconds) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore") if exc.fp else str(exc)
            raise RuntimeError(f"Ollama HTTP error: {detail}") from exc
        except Exception as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid Ollama JSON response: {raw[:500]}") from exc

        text = (data.get("response") or "").strip()
        return text

    def generate(
        self,
        prompt: str,
        timeout_seconds: int | None = None,
        max_new_tokens: int = 380,
    ) -> str:
        timeout = timeout_seconds or settings.CHAT_GENERATION_TIMEOUT_SECONDS
        return self._ollama_generate(
            prompt=prompt,
            timeout_seconds=timeout,
            max_new_tokens=max_new_tokens,
        )
