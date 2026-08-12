"""Distinct ContractGuard AI specialist agent classes.

Each role is implemented in its own module and instantiated as its own object. Agents
communicate through AgentMessage records and the shared LangGraph AuditState.
"""
from .artifact_storage import ArtifactStorageAgent
from .base import AgentToolPermissionError, BaseAgent
from .compliance_analyst import ComplianceAnalystAgent
from .coordinator import CoordinatorAgent
from .document_analyst import DocumentAnalystAgent
from .input_security import InputSecurityAgent
from .output_guardian import OutputGuardianAgent
from .policy_researcher import PolicyResearchAgent
from .quality_reviewer import QualityReviewerAgent
from .report_writer import ReportWriterAgent
from .security_reviewer import SecurityReviewerAgent

__all__ = [
    "AgentToolPermissionError",
    "BaseAgent",
    "InputSecurityAgent",
    "CoordinatorAgent",
    "DocumentAnalystAgent",
    "PolicyResearchAgent",
    "ComplianceAnalystAgent",
    "QualityReviewerAgent",
    "SecurityReviewerAgent",
    "ReportWriterAgent",
    "OutputGuardianAgent",
    "ArtifactStorageAgent",
]
