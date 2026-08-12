"""Application service for starting, resuming, and inspecting audits."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from .agents import (
    ArtifactStorageAgent,
    ComplianceAnalystAgent,
    CoordinatorAgent,
    DocumentAnalystAgent,
    InputSecurityAgent,
    OutputGuardianAgent,
    PolicyResearchAgent,
    QualityReviewerAgent,
    ReportWriterAgent,
    SecurityReviewerAgent,
)
from .config import Settings
from .llm import GroqReasoner
from .models import AuditStartRequest, ResumeRequest, new_audit_state
from .observability import Observability
from .persistence import SQLiteCheckpointer
from .tools import build_tool_registry
from .workflow import ContractAuditWorkflow


class AuditNotFoundError(KeyError):
    pass


class AuditConflictError(RuntimeError):
    pass


class ContractGuardService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.settings.ensure_directories()
        self.observability = Observability(self.settings.log_file)
        self.checkpointer = SQLiteCheckpointer(self.settings.checkpoint_db)
        self.tools = build_tool_registry(self.settings, self.observability)
        self.reasoner = GroqReasoner(self.settings, self.observability)
        self.agents = self._build_agents()
        self._closed = False

    def _build_agents(self) -> dict[str, Any]:
        obs, tools = self.observability, self.tools
        return {
            "input_security": InputSecurityAgent(
                "Input Security Agent", "Prompt-injection gate", tools, obs
            ),
            "coordinator": CoordinatorAgent(
                "Coordinator Agent", "Centralized planner and execution coordinator", tools, obs
            ),
            "document_analyst": DocumentAnalystAgent(
                "Document Analyst Agent", "Contract ingestion and clause extraction", tools, obs
            ),
            "policy_research": PolicyResearchAgent(
                "Policy Research Agent", "Corporate policy retrieval specialist", tools, obs
            ),
            "compliance_analyst": ComplianceAnalystAgent(
                "Compliance Analyst Agent", "Clause-to-policy comparison specialist", tools, obs
            ),
            "quality_reviewer": QualityReviewerAgent(
                "Quality Reviewer Agent", "Reflexion and evidence-coverage critic", tools, obs
            ),
            "security_reviewer": SecurityReviewerAgent(
                "Security Reviewer Agent", "Risk scoring and approval router", tools, obs, self.settings
            ),
            "report_writer": ReportWriterAgent(
                "Report Writer Agent", "Structured report generator", tools, obs, self.reasoner
            ),
            "output_guardian": OutputGuardianAgent(
                "Output Guardian Agent", "Schema validation and PII data-protection gate", tools, obs
            ),
            "artifact_storage": ArtifactStorageAgent(
                "Artifact Storage Agent", "Durable filesystem or MinIO/S3 persistence", tools, obs
            ),
        }

    @contextmanager
    def _active_run(self) -> Iterator[None]:
        self.observability.active_workflows.inc()
        try:
            yield
        finally:
            self.observability.active_workflows.dec()

    def start(self, request: AuditStartRequest) -> dict[str, Any]:
        self._assert_open()
        if not (request.contract_text and request.contract_text.strip()) and not request.contract_path:
            raise ValueError("Either contract_text or contract_path must be provided")
        thread_id = request.thread_id or f"audit-{uuid4().hex[:12]}"
        if self.checkpointer.load(thread_id) is not None:
            raise AuditConflictError(f"Thread already exists: {thread_id}")
        state = new_audit_state(
            thread_id=thread_id,
            request_text=request.request_text,
            contract_path=request.contract_path,
            contract_text=request.contract_text,
            flags=request.flags,
        )
        state.update(
            {
                "max_policy_retries": self.settings.max_policy_retries,
                "max_quality_retries": self.settings.max_quality_retries,
                "max_report_revisions": self.settings.max_report_revisions,
            }
        )
        self.checkpointer.save(thread_id, "received", state)
        self.observability.log(
            "workflow_started",
            thread_id=thread_id,
            source="file" if request.contract_path else "inline_text",
            llm_provider=self.settings.llm_provider,
            tool_count=len(self.tools.describe()),
        )
        workflow = self._workflow(state=state, node="received")
        with self._active_run():
            result = workflow.run_until_pause_or_terminal()
        self.observability.export_metrics(self.settings.metrics_file)
        return result

    def resume(self, thread_id: str, request: ResumeRequest) -> dict[str, Any]:
        self._assert_open()
        checkpoint = self.checkpointer.load(thread_id)
        if checkpoint is None:
            raise AuditNotFoundError(thread_id)
        if checkpoint["node"] != "awaiting_approval":
            raise AuditConflictError(
                f"Thread '{thread_id}' is at node '{checkpoint['node']}' and cannot be resumed as an approval"
            )
        workflow = self._workflow(state=checkpoint["state"], node=checkpoint["node"])
        with self._active_run():
            result = workflow.resume(request)
        self.observability.export_metrics(self.settings.metrics_file)
        return result

    def get(self, thread_id: str) -> dict[str, Any]:
        self._assert_open()
        checkpoint = self.checkpointer.load(thread_id)
        if checkpoint is None:
            raise AuditNotFoundError(thread_id)
        return checkpoint

    def history(self, thread_id: str) -> list[dict[str, Any]]:
        self._assert_open()
        if self.checkpointer.load(thread_id) is None:
            raise AuditNotFoundError(thread_id)
        return self.checkpointer.history(thread_id)

    def graph_spec(self) -> dict[str, Any]:
        return ContractAuditWorkflow.graph_spec()

    def _workflow(self, *, state: dict[str, Any], node: str) -> ContractAuditWorkflow:
        return ContractAuditWorkflow(
            state=state,
            initial_node=node,
            agents=self.agents,
            settings=self.settings,
            checkpointer=self.checkpointer,
            observability=self.observability,
        )

    def close(self) -> None:
        if self._closed:
            return
        try:
            self.observability.export_metrics(self.settings.metrics_file)
        finally:
            self.checkpointer.close()
            self.observability.close()
            self._closed = True

    def _assert_open(self) -> None:
        if self._closed:
            raise RuntimeError("Service is closed")

    def __enter__(self) -> "ContractGuardService":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
