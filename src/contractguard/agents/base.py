"""Shared mechanics for independently instantiated specialist agents."""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from ..models import AgentMessage, ToolCall
from ..observability import Observability
from ..tools import ToolRegistry


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_state(state: dict[str, Any], key: str, value: Any) -> None:
    state.setdefault(key, []).append(value)


def truncate_text(text: str, limit: int = 280) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 1] + "..."


class AgentToolPermissionError(PermissionError):
    """Raised when a specialist agent attempts a function outside its allow-list."""


class BaseAgent:
    """Base for a real specialist object with its own role and tool permissions."""

    def __init__(
        self,
        name: str,
        role: str,
        tools: ToolRegistry,
        observability: Observability,
        allowed_tools: set[str] | None = None,
    ):
        self.name = name
        self.role = role
        self.tools = tools
        self.observability = observability
        self.allowed_tools = frozenset(allowed_tools or set())

    def send(
        self,
        state: dict[str, Any],
        *,
        recipient: str,
        message_type: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,  # type: ignore[arg-type]
            content=content,
            payload=payload or {},
        )
        append_state(state, "agent_messages", message.model_dump(mode="json"))
        self.observability.log(
            "agent_message",
            thread_id=state["thread_id"],
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            content=content,
        )

    def call_tool(
        self,
        state: dict[str, Any],
        *,
        tool_name: str,
        arguments: dict[str, Any],
        rationale: str,
        decision_source: str = "workflow",
        protocol: str = "mcp_json_schema",
        model_provider: str | None = None,
        model_name: str | None = None,
        used_live_llm: bool = False,
    ) -> tuple[Any, dict[str, Any]]:
        if tool_name not in self.allowed_tools:
            self.observability.log(
                "tool_permission_denied",
                level="warning",
                thread_id=state.get("thread_id"),
                agent=self.name,
                tool=tool_name,
                allowed_tools=sorted(self.allowed_tools),
            )
            raise AgentToolPermissionError(
                f"Agent '{self.name}' is not authorized to call tool '{tool_name}'"
            )

        call = ToolCall(
            agent=self.name,
            tool_name=tool_name,
            arguments=arguments,
            rationale=rationale,
            decision_source=decision_source,  # type: ignore[arg-type]
            protocol=protocol,  # type: ignore[arg-type]
            model_provider=model_provider,
            model_name=model_name,
            used_live_llm=used_live_llm,
        )
        call_dict = call.model_dump(mode="json")
        append_state(state, "tool_calls", call_dict)
        if used_live_llm:
            state["live_llm_tool_call_count"] = int(state.get("live_llm_tool_call_count", 0)) + 1
        modes = state.setdefault("reasoner_modes", [])
        if decision_source not in modes:
            modes.append(decision_source)
        if decision_source != "workflow":
            state["reasoner_mode"] = decision_source
        append_state(
            state,
            "decision_trace",
            {
                "pattern": "ReAct",
                "decision_summary": rationale,
                "decision_source": decision_source,
                "protocol": protocol,
                "model_provider": model_provider,
                "model_name": model_name,
                "used_live_llm": used_live_llm,
                "action": {"tool": tool_name, "arguments": arguments, "call_id": call.call_id},
                "timestamp": call.timestamp,
            },
        )
        output, observation = self.tools.call(call, thread_id=state["thread_id"])
        observation_dict = observation.model_dump(mode="json")
        append_state(state, "tool_observations", observation_dict)
        append_state(
            state,
            "decision_trace",
            {
                "pattern": "ReAct",
                "observation": observation.summary,
                "status": observation.status,
                "call_id": call.call_id,
                "timestamp": observation.timestamp,
            },
        )
        return output, observation_dict
