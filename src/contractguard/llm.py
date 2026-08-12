"""Provider-neutral LLM reasoning and JSON-schema function-calling support.

The capstone remains reproducible without a secret: ``offline`` mode uses a deterministic
schema-aware router and still executes the same MCP-style tool registry. When a Groq,
OpenRouter, or Gemini key is configured, the same interface performs a real model-native
function call and records provider/model/token/latency telemetry.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
from typing import Any

import httpx

from .config import Settings
from .observability import Observability


@dataclass(slots=True)
class ToolSelection:
    """A validated tool decision produced by the live model or offline schema router."""

    tool_name: str
    arguments: dict[str, Any]
    rationale: str
    source: str
    provider: str
    model: str
    used_live_llm: bool


class AgentReasoner:
    """Generate summaries and select function tools without provider-specific SDKs."""

    OPENAI_COMPATIBLE_ENDPOINTS = {
        "groq": "https://api.groq.com/openai/v1/chat/completions",
        "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    }

    def __init__(self, settings: Settings, observability: Observability):
        self.settings = settings
        self.observability = observability

    @property
    def provider(self) -> str:
        return self.settings.llm_provider.lower().strip()

    @property
    def model(self) -> str:
        if self.provider == "groq":
            return self.settings.groq_model
        if self.provider == "openrouter":
            return self.settings.openrouter_model
        if self.provider == "gemini":
            return self.settings.gemini_model
        return "deterministic-schema-router-v1"

    @property
    def enabled(self) -> bool:
        return bool(self._api_key()) and self.provider in {"groq", "openrouter", "gemini"}

    def select_tool(
        self,
        *,
        agent_name: str,
        task: str,
        context: dict[str, Any],
        tools: list[dict[str, Any]],
        candidate_arguments: dict[str, dict[str, Any]],
        locked_arguments: dict[str, set[str]] | None = None,
    ) -> ToolSelection:
        """Select one allowed function and return schema-shaped arguments.

        ``candidate_arguments`` provides safe application-owned defaults. A live model may
        refine non-locked fields, while path, approval, simulation, and persistence values
        remain controlled by application code.
        """
        if not tools:
            raise ValueError(f"No tools were exposed to {agent_name}")
        allowed_names = {str(item["name"]) for item in tools}
        if allowed_names != set(candidate_arguments):
            missing = allowed_names.symmetric_difference(candidate_arguments)
            raise ValueError(f"Tool schemas and candidate arguments differ: {sorted(missing)}")

        selection: ToolSelection | None = None
        if self.enabled:
            try:
                if self.provider in self.OPENAI_COMPATIBLE_ENDPOINTS:
                    selection = self._select_openai_compatible(
                        agent_name=agent_name,
                        task=task,
                        context=context,
                        tools=tools,
                    )
                else:
                    selection = self._select_gemini(
                        agent_name=agent_name,
                        task=task,
                        context=context,
                        tools=tools,
                    )
            except Exception as exc:
                self.observability.log(
                    "llm_tool_call_fallback",
                    level="warning",
                    provider=self.provider,
                    model=self.model,
                    agent=agent_name,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        if selection is None or selection.tool_name not in allowed_names:
            selection = self._select_offline(task=task, tools=tools, candidate_arguments=candidate_arguments)

        base_arguments = dict(candidate_arguments[selection.tool_name])
        locked = (locked_arguments or {}).get(selection.tool_name, set())
        for key, value in selection.arguments.items():
            if key not in locked:
                base_arguments[key] = value
        selection.arguments = base_arguments
        return selection

    def generate(self, *, system: str, user: str, temperature: float = 0.0) -> str | None:
        """Generate text with the configured live provider; return ``None`` offline/failure."""
        if not self.enabled:
            return None
        try:
            if self.provider in self.OPENAI_COMPATIBLE_ENDPOINTS:
                return self._generate_openai_compatible(system=system, user=user, temperature=temperature)
            return self._generate_gemini(system=system, user=user, temperature=temperature)
        except Exception as exc:
            self.observability.log(
                "llm_generation_fallback",
                level="warning",
                provider=self.provider,
                model=self.model,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return None

    def _select_offline(
        self,
        *,
        task: str,
        tools: list[dict[str, Any]],
        candidate_arguments: dict[str, dict[str, Any]],
    ) -> ToolSelection:
        task_tokens = self._tokens(task)
        ranked: list[tuple[float, str]] = []
        for tool in tools:
            name = str(tool["name"])
            searchable = f"{name.replace('_', ' ')} {tool.get('description', '')}"
            tool_tokens = self._tokens(searchable)
            overlap = len(task_tokens & tool_tokens)
            phrase_bonus = sum(2.0 for token in name.split("_") if token in task_tokens)
            ranked.append((overlap + phrase_bonus, name))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = ranked[0][1]
        return ToolSelection(
            tool_name=selected,
            arguments=dict(candidate_arguments[selected]),
            rationale=(
                f"Offline schema router matched the task to '{selected}' using the exposed "
                "function name, description, and JSON schema."
            ),
            source="offline_schema_router",
            provider="offline",
            model="deterministic-schema-router-v1",
            used_live_llm=False,
        )

    def _select_openai_compatible(
        self,
        *,
        agent_name: str,
        task: str,
        context: dict[str, Any],
        tools: list[dict[str, Any]],
    ) -> ToolSelection:
        endpoint = self.OPENAI_COMPATIBLE_ENDPOINTS[self.provider]
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are {agent_name}. Select exactly one provided function that best "
                        "advances the task. Return a function call only. Never invent a tool name."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"task": task, "context": context}, ensure_ascii=False, default=str),
                },
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": item["name"],
                        "description": item["description"],
                        "parameters": item["input_schema"],
                    },
                }
                for item in tools
            ],
            "tool_choice": "required",
        }
        headers = self._headers()
        started = time.perf_counter()
        try:
            response = httpx.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            message = data["choices"][0]["message"]
            calls = message.get("tool_calls") or []
            if not calls:
                raise ValueError("Provider returned no function call")
            function = calls[0]["function"]
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments or "{}")
            usage = data.get("usage", {})
            self._record_live_call(
                operation="tool_selection",
                status="success",
                started=started,
                input_tokens=int(usage.get("prompt_tokens", 0) or 0),
                output_tokens=int(usage.get("completion_tokens", 0) or 0),
            )
            return ToolSelection(
                tool_name=str(function["name"]),
                arguments=dict(arguments or {}),
                rationale=f"{self.provider} returned a model-native JSON function call.",
                source="llm_function_call",
                provider=self.provider,
                model=self.model,
                used_live_llm=True,
            )
        except Exception:
            self._record_live_call(operation="tool_selection", status="error", started=started)
            raise

    def _select_gemini(
        self,
        *,
        agent_name: str,
        task: str,
        context: dict[str, Any],
        tools: list[dict[str, Any]],
    ) -> ToolSelection:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.settings.gemini_api_key}"
        )
        declarations = [
            {
                "name": item["name"],
                "description": item["description"],
                "parameters": self._clean_schema(item["input_schema"]),
            }
            for item in tools
        ]
        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": (
                            f"You are {agent_name}. Choose exactly one allowed function. "
                            "Do not answer in prose and do not invent tools."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": json.dumps({"task": task, "context": context}, ensure_ascii=False, default=str)}
                    ],
                }
            ],
            "tools": [{"functionDeclarations": declarations}],
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "ANY",
                    "allowedFunctionNames": [item["name"] for item in tools],
                }
            },
            "generationConfig": {"temperature": 0},
        }
        started = time.perf_counter()
        try:
            response = httpx.post(endpoint, json=payload, timeout=self.settings.llm_timeout_seconds)
            response.raise_for_status()
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            function_call = next(part["functionCall"] for part in parts if "functionCall" in part)
            usage = data.get("usageMetadata", {})
            self._record_live_call(
                operation="tool_selection",
                status="success",
                started=started,
                input_tokens=int(usage.get("promptTokenCount", 0) or 0),
                output_tokens=int(usage.get("candidatesTokenCount", 0) or 0),
            )
            return ToolSelection(
                tool_name=str(function_call["name"]),
                arguments=dict(function_call.get("args") or {}),
                rationale="Gemini returned a model-native functionCall part.",
                source="llm_function_call",
                provider=self.provider,
                model=self.model,
                used_live_llm=True,
            )
        except Exception:
            self._record_live_call(operation="tool_selection", status="error", started=started)
            raise

    def _generate_openai_compatible(self, *, system: str, user: str, temperature: float) -> str:
        endpoint = self.OPENAI_COMPATIBLE_ENDPOINTS[self.provider]
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "max_completion_tokens": 900,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        started = time.perf_counter()
        try:
            response = httpx.post(
                endpoint,
                headers=self._headers(),
                json=payload,
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            self._record_live_call(
                operation="generation",
                status="success",
                started=started,
                input_tokens=int(usage.get("prompt_tokens", 0) or 0),
                output_tokens=int(usage.get("completion_tokens", 0) or 0),
            )
            return str(data["choices"][0]["message"]["content"])
        except Exception:
            self._record_live_call(operation="generation", status="error", started=started)
            raise

    def _generate_gemini(self, *, system: str, user: str, temperature: float) -> str:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.settings.gemini_api_key}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 900},
        }
        started = time.perf_counter()
        try:
            response = httpx.post(endpoint, json=payload, timeout=self.settings.llm_timeout_seconds)
            response.raise_for_status()
            data = response.json()
            usage = data.get("usageMetadata", {})
            self._record_live_call(
                operation="generation",
                status="success",
                started=started,
                input_tokens=int(usage.get("promptTokenCount", 0) or 0),
                output_tokens=int(usage.get("candidatesTokenCount", 0) or 0),
            )
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(str(part.get("text", "")) for part in parts).strip()
        except Exception:
            self._record_live_call(operation="generation", status="error", started=started)
            raise

    def _record_live_call(
        self,
        *,
        operation: str,
        status: str,
        started: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        latency_seconds = max(time.perf_counter() - started, 0.0)
        self.observability.record_llm_call(
            provider=self.provider,
            model=self.model,
            operation=operation,
            status=status,
            latency_seconds=latency_seconds,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=0.0,
        )

    def _api_key(self) -> str | None:
        if self.provider == "groq":
            return self.settings.groq_api_key
        if self.provider == "openrouter":
            return self.settings.openrouter_api_key
        if self.provider == "gemini":
            return self.settings.gemini_api_key
        return None

    def _headers(self) -> dict[str, str]:
        key = self._api_key()
        if not key:
            raise ValueError(f"No API key configured for provider '{self.provider}'")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if self.provider == "openrouter":
            headers.update(
                {
                    "HTTP-Referer": self.settings.openrouter_site_url,
                    "X-Title": "ContractGuard AI Capstone",
                }
            )
        return headers

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    @classmethod
    def _clean_schema(cls, value: Any) -> Any:
        """Remove annotation-only JSON Schema fields rejected by some provider APIs."""
        if isinstance(value, list):
            return [cls._clean_schema(item) for item in value]
        if isinstance(value, dict):
            return {
                key: cls._clean_schema(item)
                for key, item in value.items()
                if key not in {"title", "$defs", "$schema", "default"}
            }
        return value


# Backwards-compatible import name used by earlier project versions.
GroqReasoner = AgentReasoner
