"""Typed shared state carried between all LangGraph nodes and specialist agents."""
from __future__ import annotations

from typing import Any, TypedDict


class AuditState(TypedDict, total=False):
    thread_id: str
    request_text: str
    contract_path: str | None
    contract_text_input: str | None
    contract_text: str
    sanitized_contract_text: str
    contract_metadata: dict[str, Any]
    clauses: list[dict[str, Any]]
    plan: list[dict[str, Any]]
    policy_queries: list[dict[str, Any]]
    policy_evidence: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    risk_score: int
    risk_level: str
    quality_score: float
    policy_retry_count: int
    quality_retry_count: int
    report_revision_count: int
    max_policy_retries: int
    max_quality_retries: int
    max_report_revisions: int
    policy_search_error: str
    needs_more_research: bool
    additional_policy_queries: list[dict[str, Any]]
    input_blocked: bool
    blocked_reason: str
    guardrail_enforced: bool
    guardrail_matches: list[str]
    output_guardrail_enforced: bool
    approval_required: bool
    approval_status: str
    approval_comment: str
    approver: str
    interrupt_payload: dict[str, Any] | None
    report: dict[str, Any] | None
    final_markdown: str
    output_valid: bool
    output_feedback: str
    output_retry_requested: bool
    pii_redactions: int
    artifact_uri: str
    storage_backend: str
    status: str
    workflow_node: str
    errors: list[str]
    agent_messages: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    tool_observations: list[dict[str, Any]]
    decision_trace: list[dict[str, Any]]
    reasoner_mode: str
    reasoner_modes: list[str]
    live_llm_tool_call_count: int
    node_history: list[str]
    created_at: str
    updated_at: str
    flags: dict[str, Any]
