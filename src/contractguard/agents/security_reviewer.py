"""Security Reviewer Agent: risk scoring and approval-routing specialist."""
from __future__ import annotations

from typing import Any

from ..config import Settings
from ..observability import Observability
from ..tools import ToolRegistry
from .base import BaseAgent

class SecurityReviewerAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        role: str,
        tools: ToolRegistry,
        observability: Observability,
        settings: Settings,
        allowed_tools: set[str] | None = None,
    ):
        super().__init__(name, role, tools, observability, allowed_tools=allowed_tools)
        self.settings = settings

    def run(self, state: dict[str, Any]) -> None:
        output, observation = self.call_tool(
            state,
            tool_name="calculate_contract_risk",
            arguments={
                "findings": state.get("findings", []),
                "contract_value_sar": state.get("contract_metadata", {}).get("contract_value_sar", 0.0),
                "approval_risk_threshold": self.settings.approval_risk_threshold,
                "approval_value_threshold_sar": self.settings.approval_value_threshold_sar,
            },
            rationale="Risk and value thresholds determine whether autonomous execution must stop for human approval.",
        )
        if observation["status"] != "success":
            raise RuntimeError(observation["summary"])
        state.update(output)
        state["approval_status"] = "pending" if output["approval_required"] else "not_required"
        self.send(
            state,
            recipient="Coordinator Agent",
            message_type="security",
            content=(
                f"Risk classified as {output['risk_level']} ({output['risk_score']}/100). "
                + ("Human approval required." if output["approval_required"] else "No approval interrupt required.")
            ),
            payload=output,
        )
