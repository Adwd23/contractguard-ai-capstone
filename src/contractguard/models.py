"""Typed contracts shared by agents, tools, API, and guardrails."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AgentMessage(BaseModel):
    sender: str
    recipient: str
    message_type: Literal["plan", "handoff", "result", "critique", "security", "approval", "status"]
    content: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=utc_now)


class PlanStep(BaseModel):
    step_id: str
    owner: str
    objective: str
    status: Literal["pending", "running", "completed", "failed", "skipped"] = "pending"


class ToolCall(BaseModel):
    call_id: str = Field(default_factory=lambda: str(uuid4()))
    agent: str
    tool_name: str
    arguments: dict[str, Any]
    rationale: str
    timestamp: str = Field(default_factory=utc_now)


class ToolObservation(BaseModel):
    call_id: str
    tool_name: str
    status: Literal["success", "error"]
    summary: str
    output: Any = None
    latency_ms: float = 0.0
    timestamp: str = Field(default_factory=utc_now)


class ContractClause(BaseModel):
    clause_id: str
    heading: str
    text: str
    topic: str


class PolicyEvidence(BaseModel):
    policy_name: str
    policy_path: str
    section: str
    excerpt: str
    score: float
    topic: str


class Finding(BaseModel):
    finding_id: str
    topic: str
    title: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    contract_excerpt: str
    policy_reference: str
    recommendation: str
    confidence: float = Field(ge=0, le=1)


class AuditReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    thread_id: str
    generated_at: str
    vendor_name: str
    contract_value_sar: float
    executive_summary: str = Field(min_length=20)
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    findings: list[Finding]
    recommendations: list[str] = Field(min_length=1)
    approval_status: Literal["not_required", "pending", "approved", "rejected"]
    approval_comment: str = ""
    evidence_count: int = Field(ge=0)
    pii_redactions: int = Field(ge=0)
    agent_trace_summary: list[str] = Field(default_factory=list)

    @field_validator("recommendations")
    @classmethod
    def recommendations_not_blank(cls, values: list[str]) -> list[str]:
        if not any(v.strip() for v in values):
            raise ValueError("At least one non-empty recommendation is required")
        return values


class AuditStartRequest(BaseModel):
    thread_id: str | None = None
    request_text: str = Field(min_length=3)
    contract_path: str | None = None
    contract_text: str | None = None
    flags: dict[str, Any] = Field(default_factory=dict)

    @field_validator("contract_text")
    @classmethod
    def at_least_one_contract_source(cls, value: str | None, info):
        # Cross-field validation is completed by the service for a clearer API error.
        return value


class ResumeRequest(BaseModel):
    decision: Literal["approve", "reject"]
    comment: str = Field(default="", max_length=2000)
    approver: str = Field(default="human-reviewer", min_length=2, max_length=120)


def new_audit_state(
    *,
    thread_id: str,
    request_text: str,
    contract_path: str | None,
    contract_text: str | None,
    flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "thread_id": thread_id,
        "request_text": request_text,
        "contract_path": contract_path,
        "contract_text_input": contract_text,
        "contract_text": "",
        "sanitized_contract_text": "",
        "contract_metadata": {"vendor_name": "Unknown Vendor", "contract_value_sar": 0.0},
        "clauses": [],
        "plan": [],
        "policy_queries": [],
        "policy_evidence": [],
        "findings": [],
        "risk_score": 0,
        "risk_level": "LOW",
        "quality_score": 0.0,
        "policy_retry_count": 0,
        "quality_retry_count": 0,
        "report_revision_count": 0,
        "policy_search_error": "",
        "needs_more_research": False,
        "input_blocked": False,
        "blocked_reason": "",
        "approval_required": False,
        "approval_status": "not_required",
        "approval_comment": "",
        "approver": "",
        "interrupt_payload": None,
        "report": None,
        "final_markdown": "",
        "output_valid": False,
        "output_feedback": "",
        "pii_redactions": 0,
        "artifact_uri": "",
        "storage_backend": "",
        "status": "received",
        "errors": [],
        "agent_messages": [],
        "tool_calls": [],
        "tool_observations": [],
        "decision_trace": [],
        "node_history": ["received"],
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "flags": flags or {},
    }
