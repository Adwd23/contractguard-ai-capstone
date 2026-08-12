"""Coordinator Agent: explicit centralized Plan-and-Execute manager."""
from __future__ import annotations

from typing import Any

from ..models import PlanStep
from .base import BaseAgent

class CoordinatorAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        source = "PDF/file" if state.get("contract_path") else "inline text"
        steps = [
            PlanStep(step_id="P1", owner="Document Analyst Agent", objective=f"Ingest and parse the {source} contract"),
            PlanStep(step_id="P2", owner="Policy Research Agent", objective="Retrieve evidence from corporate policy tools"),
            PlanStep(step_id="P3", owner="Compliance Analyst Agent", objective="Compare clauses with policy evidence and produce findings"),
            PlanStep(step_id="P4", owner="Quality Reviewer Agent", objective="Critique evidence coverage and re-plan if insufficient"),
            PlanStep(step_id="P5", owner="Security Reviewer Agent", objective="Calculate risk and route high-risk actions to a human"),
            PlanStep(step_id="P6", owner="Report Writer Agent", objective="Generate and validate the compliance report"),
            PlanStep(step_id="P7", owner="Artifact Storage Agent", objective="Persist report and audit artifacts"),
        ]
        state["plan"] = [step.model_dump(mode="json") for step in steps]
        self.send(
            state,
            recipient="Document Analyst Agent",
            message_type="plan",
            content="Plan-and-Execute plan created with seven bounded steps.",
            payload={"steps": state["plan"]},
        )
