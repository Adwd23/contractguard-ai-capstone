from __future__ import annotations

from contractguard.models import ToolCall
from contractguard.observability import Observability
from contractguard.tools import build_tool_registry


def test_tool_registry_exposes_json_schemas_and_real_policy_search(isolated_settings) -> None:
    observability = Observability(isolated_settings.log_file)
    registry = build_tool_registry(isolated_settings, observability)
    descriptions = registry.describe()
    assert len(descriptions) == 6
    assert all(item["input_schema"]["type"] == "object" for item in descriptions)

    call = ToolCall(
        agent="Test Agent",
        tool_name="search_policy_knowledge_base",
        arguments={
            "query": "Saudi data residency and 24 hour breach notification",
            "topic": "data_protection",
            "top_k": 2,
            "attempt": 0,
        },
        rationale="Retrieve real policy evidence.",
    )
    output, observation = registry.call(call, thread_id="tool-test")
    observability.close()
    assert observation.status == "success"
    assert len(output) >= 1
    assert any("Data Protection" in item["policy_name"] for item in output)


def test_tool_permissions_and_contract_path_allowlist(isolated_settings) -> None:
    from contractguard.agents import AgentToolPermissionError, BaseAgent

    observability = Observability(isolated_settings.log_file)
    registry = build_tool_registry(isolated_settings, observability)
    agent = BaseAgent("No-Tool Agent", "Must not execute functions", registry, observability, set())

    try:
        agent.call_tool(
            {"thread_id": "permission-test", "tool_calls": [], "decision_trace": []},
            tool_name="calculate_contract_risk",
            arguments={"findings": [], "contract_value_sar": 0},
            rationale="This call should be denied by the per-agent allow-list.",
        )
    except AgentToolPermissionError:
        pass
    else:
        raise AssertionError("An unauthorized agent was allowed to execute a function tool")

    call = ToolCall(
        agent="Test Agent",
        tool_name="read_contract",
        arguments={"contract_path": "/etc/hosts"},
        rationale="Attempt to escape the configured contract root.",
    )
    _, observation = registry.call(call, thread_id="path-test")
    observability.close()
    assert observation.status == "error"
    assert "outside allowed roots" in observation.summary


def test_tool_schemas_reject_undeclared_model_arguments(isolated_settings) -> None:
    observability = Observability(isolated_settings.log_file)
    registry = build_tool_registry(isolated_settings, observability)
    call = ToolCall(
        agent="Test Agent",
        tool_name="search_policy_knowledge_base",
        arguments={
            "query": "security policy",
            "topic": "security",
            "top_k": 2,
            "attempt": 0,
            "unexpected_model_field": "must be rejected",
        },
        rationale="Verify strict function-argument schemas.",
    )
    _, observation = registry.call(call, thread_id="strict-schema-test")
    observability.close()
    assert observation.status == "error"
    assert "extra_forbidden" in observation.summary
