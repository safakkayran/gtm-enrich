"""LLM wrapper with caching, retry, and JSON validation."""

from __future__ import annotations

import hashlib
import json
import os
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from gtm_enrich.config import settings

T = TypeVar("T", bound=BaseModel)


class CachedLLMClient:
    """OpenAI-compatible client with disk cache, retry, and JSON validation."""

    def __init__(self) -> None:
        self.cache_dir = settings.CACHE_DIR / "llm_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.client = OpenAI(
            base_url=settings.LITELLM_BASE_URL,
            api_key=settings.LITELLM_API_KEY or os.getenv("LITELLM_API_KEY", "dummy"),
        )

    def _cache_key(self, model: str, messages: list[dict]) -> str:
        content = json.dumps([model, messages], sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _get_cached(self, key: str) -> str | None:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            return path.read_text()
        return None

    def _save_cache(self, key: str, response: str) -> None:
        path = self.cache_dir / f"{key}.json"
        path.write_text(response)

    def complete_json(
        self,
        system: str,
        user: str,
        schema: type[T],
        model: str | None = None,
        temperature: float = 0.0,
    ) -> T:
        """Call LLM and return validated JSON. Retries once on validation error."""
        model = model or settings.LLM_MODEL
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        key = self._cache_key(model, messages)
        cached = self._get_cached(key)
        if cached:
            data = json.loads(cached)
            return schema.model_validate(data)

        for attempt in range(2):  # try twice: once fresh, once with error feedback
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
                timeout=60.0,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")

            try:
                data = json.loads(content)
                validated = schema.model_validate(data)
                self._save_cache(key, content)
                return validated
            except Exception as e:
                if attempt == 0:
                    # Retry with validation error
                    msg = f"Invalid JSON: {e}. Fix and return valid JSON only."
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": msg})
                    continue
                raise

        raise RuntimeError("Failed to get valid JSON after retries")


_client: CachedLLMClient | None = None


def get_llm_client() -> CachedLLMClient:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = CachedLLMClient()
    return _client


def complete_json(
    system: str,
    user: str,
    schema: type[T],
    model: str | None = None,
) -> T:
    """Convenience function for one-shot JSON completion."""
    return get_llm_client().complete_json(system, user, schema, model)