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
    "AGENT_ROLE_MANIFEST",
]

# Evaluator-friendly role index. These entries mirror concrete classes instantiated in
# ContractGuardService._build_agents(); they are not virtual personas or prompt labels.
AGENT_ROLE_MANIFEST = (
    ("InputSecurityAgent", "Input Security Agent", "Enforce input prompt-injection boundary"),
    ("CoordinatorAgent", "Coordinator Agent", "Create and coordinate the Plan-and-Execute workflow"),
    ("DocumentAnalystAgent", "Document Analyst Agent", "Read contracts and extract structured clauses"),
    ("PolicyResearchAgent", "Policy Research Agent", "Retrieve corporate policy evidence with tools"),
    ("ComplianceAnalystAgent", "Compliance Analyst Agent", "Compare clauses to policy and produce findings"),
    ("QualityReviewerAgent", "Quality Reviewer Agent", "Perform Reflexion/self-critique and request re-search"),
    ("SecurityReviewerAgent", "Security Reviewer Agent", "Score risk and route human approval"),
    ("ReportWriterAgent", "Report Writer Agent", "Generate structured compliance reports"),
    ("OutputGuardianAgent", "Output Guardian Agent", "Enforce PII/schema output controls"),
    ("ArtifactStorageAgent", "Artifact Storage Agent", "Persist approved audit artifacts"),
)
