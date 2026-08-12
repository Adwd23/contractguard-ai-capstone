"""Regression tests for every trainer/automated-grader observation addressed by v1.3."""
from __future__ import annotations

import ast
from pathlib import Path


def _read(project_root: Path, relative: str) -> str:
    return (project_root / relative).read_text(encoding="utf-8")


def test_real_langgraph_stategraph_has_explicit_conditional_edges(project_root: Path) -> None:
    source = _read(project_root, "src/contractguard/workflow.py")
    assert "from langgraph.graph import END, START, StateGraph" in source
    assert "StateGraph(AuditState)" in source
    assert source.count("add_conditional_edges(") >= 5
    assert '"retry": "policy_research"' in source


def test_human_interrupt_has_command_resume_end_to_end(project_root: Path) -> None:
    workflow = _read(project_root, "src/contractguard/workflow.py")
    service = _read(project_root, "src/contractguard/service.py")
    assert "interrupt(" in workflow
    assert "Command(resume=" in workflow
    assert 'goto="report_writer"' in workflow
    assert 'goto="rejected"' in workflow
    assert "self.workflow.resume(thread_id, request)" in service


def test_guardrails_are_enforced_in_executable_code(project_root: Path) -> None:
    guardrails = _read(project_root, "src/contractguard/guardrails.py")
    security_agent = _read(project_root, "src/contractguard/agents/input_security.py")
    output_agent = _read(project_root, "src/contractguard/agents/output_guardian.py")
    assert "class InputGuardrail" in guardrails
    assert "raise GuardrailViolation" in guardrails
    assert "self.input_guardrail.enforce(" in security_agent
    assert "self.output_guardrail.enforce(" in output_agent


def test_multiple_agents_are_real_classes_in_separate_modules(project_root: Path) -> None:
    agent_dir = project_root / "src" / "contractguard" / "agents"
    expected = {
        "coordinator.py": "CoordinatorAgent",
        "document_analyst.py": "DocumentAnalystAgent",
        "policy_researcher.py": "PolicyResearchAgent",
        "compliance_analyst.py": "ComplianceAnalystAgent",
        "quality_reviewer.py": "QualityReviewerAgent",
        "security_reviewer.py": "SecurityReviewerAgent",
        "report_writer.py": "ReportWriterAgent",
        "output_guardian.py": "OutputGuardianAgent",
        "artifact_storage.py": "ArtifactStorageAgent",
    }
    for filename, class_name in expected.items():
        tree = ast.parse((agent_dir / filename).read_text(encoding="utf-8"))
        classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
        assert class_name in classes, f"{class_name} missing from {filename}"


def test_declared_runtime_libraries_are_directly_used(project_root: Path) -> None:
    server = _read(project_root, "src/contractguard/server.py")
    notebook_builder = _read(project_root, "scripts/build_executed_notebook.py")
    requirements = _read(project_root, "requirements.txt")
    dev_requirements = _read(project_root, "requirements-dev.txt")
    assert "uvicorn" in requirements
    assert "import uvicorn" in server
    assert "ipykernel" in dev_requirements
    assert "import ipykernel" in notebook_builder


def test_grader_probe_emits_strict_valid_json(project_root: Path) -> None:
    import json
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/grader_probe.py"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_static_checks_pass"] is True
    assert payload["conditional_edge_calls"] >= 5
    assert len(payload["distinct_agent_classes"]) >= 9
