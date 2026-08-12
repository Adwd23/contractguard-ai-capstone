"""Optional Groq model adapter. The project remains fully executable offline."""
from __future__ import annotations

import json
from typing import Any

import httpx

from .config import Settings
from .observability import Observability


class GroqReasoner:
    ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, settings: Settings, observability: Observability):
        self.settings = settings
        self.observability = observability

    @property
    def enabled(self) -> bool:
        return self.settings.llm_provider == "groq" and bool(self.settings.groq_api_key)

    def generate(self, *, system: str, user: str, temperature: float = 0.0) -> str | None:
        if not self.enabled:
            return None
        payload: dict[str, Any] = {
            "model": self.settings.groq_model,
            "temperature": temperature,
            "max_completion_tokens": 900,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(self.ENDPOINT, headers=headers, json=payload, timeout=45.0)
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            self.observability.record_llm_usage(
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
                estimated_cost_usd=0.0,
            )
            return str(data["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.observability.log(
                "llm_fallback",
                level="warning",
                provider="groq",
                model=self.settings.groq_model,
                error=str(exc),
            )
            return None
