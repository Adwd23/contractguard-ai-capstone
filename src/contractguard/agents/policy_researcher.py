"""Policy Research Agent: tool-using retrieval specialist."""
from __future__ import annotations

from typing import Any

from ..llm import AgentReasoner
from ..observability import Observability
from ..tools import ToolRegistry
from .base import BaseAgent

class PolicyResearchAgent(BaseAgent):
    TOPIC_QUERIES = {
        "data_protection": "data residency Saudi Arabia subprocessors consent breach notification privacy",
        "security": "ISO 27001 encryption access control audit penetration testing security",
        "payment": "invoice payment terms net 30 procurement approval threshold SAR",
        "liability": "liability cap indemnity damages twelve months fees",
        "termination": "termination for convenience notice automatic renewal",
        "governing_law": "governing law Kingdom of Saudi Arabia jurisdiction",
        "service_levels": "service levels uptime SLA availability credits",
        "general": "vendor contract compliance mandatory clauses",
    }

    def __init__(
        self,
        name: str,
        role: str,
        tools: ToolRegistry,
        observability: Observability,
        reasoner: AgentReasoner,
        allowed_tools: set[str] | None = None,
    ) -> None:
        super().__init__(name, role, tools, observability, allowed_tools=allowed_tools)
        self.reasoner = reasoner

    def run(self, state: dict[str, Any]) -> None:
        topics = sorted({clause.get("topic", "general") for clause in state.get("clauses", [])})
        queries = [
            {"topic": topic, "query": self.TOPIC_QUERIES.get(topic, self.TOPIC_QUERIES["general"])}
            for topic in topics
        ]
        queries.extend(state.get("additional_policy_queries", []))
        state["policy_queries"] = queries
        attempt = int(state.get("policy_retry_count", 0))
        evidence: list[dict[str, Any]] = []
        state["policy_search_error"] = ""

        tool_name = "search_policy_knowledge_base"
        for index, item in enumerate(queries):
            candidate_arguments = {
                "query": item["query"],
                "topic": item["topic"],
                "top_k": 2,
                "attempt": attempt,
                "simulate_primary_failure": bool(state.get("flags", {}).get("simulate_primary_failure"))
                and index == 0,
            }
            selection = self.reasoner.select_tool(
                agent_name=self.name,
                task=(
                    "Retrieve authoritative corporate policy evidence for the contract "
                    f"topic '{item['topic']}' using the registered function tools."
                ),
                context={
                    "topic": item["topic"],
                    "recommended_query": item["query"],
                    "required_result": "ranked policy excerpts with policy names and sections",
                    "retry_attempt": attempt,
                },
                tools=self.tools.describe({"search_policy_knowledge_base"}),
                candidate_arguments={"search_policy_knowledge_base": candidate_arguments},
                locked_arguments={
                    "search_policy_knowledge_base": {
                        "topic",
                        "attempt",
                        "simulate_primary_failure",
                    }
                },
            )
            decision_source = (
                "llm_function_call" if selection.used_live_llm else "offline_schema_router"
            )
            output, observation = self.call_tool(
                state,
                tool_name=selection.tool_name,
                arguments=selection.arguments,
                rationale=selection.rationale,
                decision_source=decision_source,
                protocol=(
                    "provider_native_function_call"
                    if selection.used_live_llm
                    else "mcp_json_schema"
                ),
                model_provider=selection.provider,
                model_name=selection.model,
                used_live_llm=selection.used_live_llm,
            )
            if observation["status"] != "success":
                state["policy_search_error"] = observation["summary"]
                state["policy_retry_count"] = attempt + 1
                self.send(
                    state,
                    recipient="Coordinator Agent",
                    message_type="status",
                    content="Policy tool failed; requesting graph retry.",
                    payload={"attempt": attempt + 1, "error": observation["summary"]},
                )
                return
            evidence.extend(output)

        deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
        for item in evidence:
            key = (item["policy_name"], item["section"], item["topic"])
            previous = deduped.get(key)
            if previous is None or item["score"] > previous["score"]:
                deduped[key] = item
        state["policy_evidence"] = list(deduped.values())
        state["policy_search_error"] = ""
        self.send(
            state,
            recipient="Compliance Analyst Agent",
            message_type="result",
            content=f"Retrieved {len(state['policy_evidence'])} policy evidence records.",
            payload={"topics": sorted({item["topic"] for item in state["policy_evidence"]})},
        )
