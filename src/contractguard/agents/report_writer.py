"""Report Writer Agent: independent structured report-generation specialist."""
from __future__ import annotations

import json
from typing import Any

from ..guardrails import mask_object
from ..llm import AgentReasoner
from ..observability import Observability
from ..tools import ToolRegistry
from .base import BaseAgent, now_utc

class ReportWriterAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        role: str,
        tools: ToolRegistry,
        observability: Observability,
        reasoner: AgentReasoner,
        allowed_tools: set[str] | None = None,
    ):
        super().__init__(name, role, tools, observability, allowed_tools=allowed_tools)
        self.reasoner = reasoner

    def run(self, state: dict[str, Any]) -> None:
        findings = state.get("findings", [])
        metadata = state.get("contract_metadata", {})
        fallback_summary = self._fallback_summary(state)
        # Never transmit raw contract excerpts or direct identifiers to an optional
        # external model. Only the minimum fields required for the summary are sent.
        safe_findings = [
            {
                key: item.get(key)
                for key in (
                    "finding_id",
                    "topic",
                    "title",
                    "severity",
                    "policy_reference",
                    "recommendation",
                    "confidence",
                )
            }
            for item in findings
        ]
        llm_context, context_redactions, context_categories = mask_object(
            {
                "vendor": metadata.get("vendor_name"),
                "value_sar": metadata.get("contract_value_sar"),
                "risk_score": state.get("risk_score"),
                "risk_level": state.get("risk_level"),
                "findings": safe_findings,
            }
        )
        if context_redactions:
            self.observability.log(
                "llm_context_redacted",
                thread_id=state["thread_id"],
                agent=self.name,
                redactions=context_redactions,
                categories=sorted(set(context_categories)),
            )
        llm_summary = self.reasoner.generate(
            system=(
                "You are a senior Saudi enterprise contract-compliance reviewer. "
                "Write one concise executive-summary paragraph. Do not invent facts."
            ),
            user=json.dumps(llm_context, ensure_ascii=False),
        )
        recommendations = [item["recommendation"] for item in findings]
        if not recommendations:
            recommendations = ["Proceed under the standard approved contract template and retain the audit record."]

        report: dict[str, Any] = {
            "report_id": f"CGA-{state['thread_id']}",
            "thread_id": state["thread_id"],
            "generated_at": now_utc(),
            "vendor_name": metadata.get("vendor_name", "Unknown Vendor"),
            "contract_value_sar": float(metadata.get("contract_value_sar", 0.0) or 0.0),
            "executive_summary": llm_summary or fallback_summary,
            "risk_score": int(state.get("risk_score", 0)),
            "risk_level": state.get("risk_level", "LOW"),
            "findings": findings,
            "recommendations": list(dict.fromkeys(recommendations)),
            "approval_status": state.get("approval_status", "not_required"),
            "approval_comment": state.get("approval_comment", ""),
            "evidence_count": len(state.get("policy_evidence", [])),
            "pii_redactions": 0,
            "agent_trace_summary": [
                f"{message['sender']} → {message['recipient']}: {message['content']}"
                for message in state.get("agent_messages", [])[-12:]
            ],
        }

        if (
            state.get("flags", {}).get("simulate_output_validation_failure")
            and int(state.get("report_revision_count", 0)) == 0
        ):
            report.pop("recommendations", None)

        state["report"] = report
        self.send(
            state,
            recipient="Output Guardian Agent",
            message_type="handoff",
            content=f"Report draft revision {state.get('report_revision_count', 0)} is ready for validation.",
            payload={"report_id": report["report_id"]},
        )

    @staticmethod
    def _fallback_summary(state: dict[str, Any]) -> str:
        count = len(state.get("findings", []))
        return (
            f"The multi-agent audit identified {count} compliance finding(s) and assigned a "
            f"{state.get('risk_level', 'LOW')} risk rating of {state.get('risk_score', 0)}/100. "
            "The result was produced from clause extraction, policy retrieval, specialist review, "
            "security routing, and output validation rather than a single prompt."
        )
