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
