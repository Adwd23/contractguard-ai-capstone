from __future__ import annotations

from typing import Any

from contractguard.llm import AgentReasoner
from contractguard.observability import Observability
from contractguard.tools import build_tool_registry


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def test_openrouter_native_function_call_is_parsed_and_locked(monkeypatch, isolated_settings) -> None:
    isolated_settings.llm_provider = "openrouter"
    isolated_settings.openrouter_api_key = "test-openrouter-key"
    isolated_settings.openrouter_model = "test/tool-model"
    observability = Observability(isolated_settings.log_file)
    registry = build_tool_registry(isolated_settings, observability)
    captured: dict[str, Any] = {}

    def fake_post(url: str, *, headers: dict[str, str], json: dict[str, Any], timeout: float):
        captured.update({"url": url, "headers": headers, "request": json, "timeout": timeout})
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "call-live-1",
                                    "type": "function",
                                    "function": {
                                        "name": "search_policy_knowledge_base",
                                        "arguments": (
                                            '{"query":"Saudi breach notification data residency",'
                                            '"topic":"malicious_override","top_k":4,"attempt":99}'
                                        ),
                                    },
                                }
                            ]
                        }
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8},
            }
        )

    monkeypatch.setattr("contractguard.llm.httpx.post", fake_post)
    reasoner = AgentReasoner(isolated_settings, observability)
    candidate = {
        "query": "privacy policy evidence",
        "topic": "data_protection",
        "top_k": 2,
        "attempt": 1,
        "simulate_primary_failure": False,
    }
    selection = reasoner.select_tool(
        agent_name="Policy Research Agent",
        task="Retrieve policy evidence about data residency and breach notification.",
        context={"topic": "data_protection"},
        tools=registry.describe({"search_policy_knowledge_base"}),
        candidate_arguments={"search_policy_knowledge_base": candidate},
        locked_arguments={
            "search_policy_knowledge_base": {
                "topic",
                "attempt",
                "simulate_primary_failure",
            }
        },
    )

    assert selection.used_live_llm is True
    assert selection.source == "llm_function_call"
    assert selection.tool_name == "search_policy_knowledge_base"
    assert selection.arguments["query"] == "Saudi breach notification data residency"
    assert selection.arguments["top_k"] == 4
    assert selection.arguments["topic"] == "data_protection"
    assert selection.arguments["attempt"] == 1
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer test-openrouter-key"
    assert captured["request"]["tool_choice"] == "required"
    assert captured["request"]["tools"][0]["function"]["name"] == "search_policy_knowledge_base"
    assert "contractguard_llm_calls_total" in observability.metrics_bytes().decode()
    observability.close()


def test_invalid_live_tool_response_falls_back_to_offline_router(monkeypatch, isolated_settings) -> None:
    isolated_settings.llm_provider = "groq"
    isolated_settings.groq_api_key = "test-groq-key"
    observability = Observability(isolated_settings.log_file)
    registry = build_tool_registry(isolated_settings, observability)

    def fake_post(*args, **kwargs):
        return _FakeResponse({"choices": [{"message": {"content": "No function call"}}]})

    monkeypatch.setattr("contractguard.llm.httpx.post", fake_post)
    reasoner = AgentReasoner(isolated_settings, observability)
    candidate = {
        "query": "security controls",
        "topic": "security",
        "top_k": 2,
        "attempt": 0,
        "simulate_primary_failure": False,
    }
    selection = reasoner.select_tool(
        agent_name="Policy Research Agent",
        task="Search the policy knowledge base for security controls.",
        context={"topic": "security"},
        tools=registry.describe({"search_policy_knowledge_base"}),
        candidate_arguments={"search_policy_knowledge_base": candidate},
    )

    assert selection.used_live_llm is False
    assert selection.source == "offline_schema_router"
    assert selection.tool_name == "search_policy_knowledge_base"
    observability.close()
