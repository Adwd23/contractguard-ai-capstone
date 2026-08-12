"""Application service for starting, resuming, and inspecting LangGraph audits."""
from __future__ import annotations

from contextlib import contextmanager
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
from .guardrails import InputGuardrail, OutputGuardrail
from .llm import AgentReasoner
from .models import AuditStartRequest, ResumeRequest, new_audit_state
from .observability import Observability
from .persistence import LangGraphSQLitePersistence
from .tools import build_tool_registry
from .workflow import ContractAuditWorkflow


class AuditNotFoundError(KeyError):
    pass


class AuditConflictError(RuntimeError):
    pass


class ContractGuardService:
    """Owns distinct agent objects plus one persistent compiled LangGraph."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings.from_env()
        self.settings.ensure_directories()
        self.observability = Observability(self.settings.log_file)
        self.persistence = LangGraphSQLitePersistence(self.settings.checkpoint_db)
        self.tools = build_tool_registry(self.settings, self.observability)
        self.reasoner = AgentReasoner(self.settings, self.observability)
        self.agents = self._build_agents()
        self.workflow = ContractAuditWorkflow(
            agents=self.agents,
            settings=self.settings,
            persistence=self.persistence,
            observability=self.observability,
        )
        self._closed = False

    def _build_agents(self) -> dict[str, Any]:
        """Instantiate each role as an independent specialist object."""
        obs, tools = self.observability, self.tools
        return {
            "input_security": InputSecurityAgent(
                "Input Security Agent",
                "Prompt-injection enforcement specialist",
                tools,
                obs,
                set(),
                input_guardrail=InputGuardrail(),
            ),
            "coordinator": CoordinatorAgent(
                "Coordinator Agent",
                "Centralized Plan-and-Execute coordinator",
                tools,
                obs,
                set(),
            ),
            "document_analyst": DocumentAnalystAgent(
                "Document Analyst Agent",
                "Contract ingestion and clause-extraction specialist",
                tools,
                obs,
                {"read_contract", "extract_contract_clauses"},
            ),
            "policy_research": PolicyResearchAgent(
                "Policy Research Agent",
                "Corporate-policy retrieval specialist",
                tools,
                obs,
                self.reasoner,
                {"search_policy_knowledge_base"},
            ),
            "compliance_analyst": ComplianceAnalystAgent(
                "Compliance Analyst Agent",
                "Clause-to-policy comparison specialist",
                tools,
                obs,
                set(),
            ),
            "quality_reviewer": QualityReviewerAgent(
                "Quality Reviewer Agent",
                "Reflexion and evidence-coverage critic",
                tools,
                obs,
                set(),
            ),
            "security_reviewer": SecurityReviewerAgent(
                "Security Reviewer Agent",
                "Risk scoring and human-approval routing specialist",
                tools,
                obs,
                self.settings,
                {"calculate_contract_risk"},
            ),
            "report_writer": ReportWriterAgent(
                "Report Writer Agent",
                "Structured report-generation specialist",
                tools,
                obs,
                self.reasoner,
                set(),
            ),
            "output_guardian": OutputGuardianAgent(
                "Output Guardian Agent",
                "Schema validation and PII data-protection specialist",
                tools,
                obs,
                set(),
                output_guardrail=OutputGuardrail(),
            ),
            "artifact_storage": ArtifactStorageAgent(
                "Artifact Storage Agent",
                "Durable filesystem or MinIO/S3 persistence specialist",
                tools,
                obs,
                {"store_report_artifact"},
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
        if request.contract_path and not self.settings.is_contract_path_allowed(request.contract_path):
            allowed = ", ".join(str(path) for path in self.settings.allowed_contract_roots)
            raise ValueError(
                f"Contract path is outside the configured allow-list. Allowed roots: {allowed}"
            )

        thread_id = request.thread_id or f"audit-{uuid4().hex[:12]}"
        if self.persistence.thread_exists(thread_id):
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
        self.observability.log(
            "workflow_started",
            thread_id=thread_id,
            framework="LangGraph StateGraph",
            source="file" if request.contract_path else "inline_text",
            llm_provider=self.settings.llm_provider,
            tool_count=len(self.tools.describe()),
            agent_count=len(self.agents),
        )
        with self._active_run():
            result = self.workflow.start(state)
        self.observability.export_metrics(self.settings.metrics_file)
        return result

    def resume(self, thread_id: str, request: ResumeRequest) -> dict[str, Any]:
        """Resume a real LangGraph interrupt by delegating to Command(resume=...)."""
        self._assert_open()
        checkpoint = self.workflow.get(thread_id)
        if checkpoint is None:
            raise AuditNotFoundError(thread_id)
        if checkpoint["state"].get("status") != "awaiting_approval":
            raise AuditConflictError(
                f"Thread '{thread_id}' is at status '{checkpoint['state'].get('status')}' and is not awaiting approval"
            )
        with self._active_run():
            result = self.workflow.resume(thread_id, request)
        self.observability.export_metrics(self.settings.metrics_file)
        return result

    def get(self, thread_id: str) -> dict[str, Any]:
        self._assert_open()
        checkpoint = self.workflow.get(thread_id)
        if checkpoint is None:
            raise AuditNotFoundError(thread_id)
        return checkpoint

    def history(self, thread_id: str) -> list[dict[str, Any]]:
        self._assert_open()
        history = self.workflow.history(thread_id)
        if not history:
            raise AuditNotFoundError(thread_id)
        return history

    def graph_spec(self) -> dict[str, Any]:
        return self.workflow.graph_spec()

    def close(self) -> None:
        if self._closed:
            return
        try:
            self.observability.export_metrics(self.settings.metrics_file)
        finally:
            self.persistence.close()
            self.observability.close()
            self._closed = True

    def _assert_open(self) -> None:
        if self._closed:
            raise RuntimeError("Service is closed")

    def __enter__(self) -> "ContractGuardService":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
