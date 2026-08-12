"""Artifact Storage Agent: durable filesystem/MinIO persistence specialist."""
from __future__ import annotations

from typing import Any

from .base import BaseAgent

class ArtifactStorageAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        metadata = {
            "thread_id": state["thread_id"],
            "status": state.get("status"),
            "risk_score": state.get("risk_score"),
            "risk_level": state.get("risk_level"),
            "quality_score": state.get("quality_score"),
            "node_history": state.get("node_history"),
            "tool_calls": len(state.get("tool_calls", [])),
            "policy_retries": state.get("policy_retry_count", 0),
            "report_revisions": state.get("report_revision_count", 0),
            "pii_redactions": state.get("pii_redactions", 0),
        }
        output, observation = self.call_tool(
            state,
            tool_name="store_report_artifact",
            arguments={
                "thread_id": state["thread_id"],
                "markdown": state["final_markdown"],
                "metadata": metadata,
            },
            rationale="The validated result and audit metadata must be stored as a production artifact.",
        )
        if observation["status"] != "success":
            raise RuntimeError(observation["summary"])
        state["artifact_uri"] = output["uri"]
        state["storage_backend"] = output["backend"]
        self.send(
            state,
            recipient="Coordinator Agent",
            message_type="status",
            content=f"Report persisted using {output['backend']}.",
            payload=output,
        )
