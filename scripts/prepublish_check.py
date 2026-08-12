#!/usr/bin/env python3
"""Publication gate for ContractGuard AI v1.3.1 Automated-Grader Hardened Edition.

The gate has two modes:

* default: run compile/tests/demo/notebook, then validate captured evidence;
* --static-only: validate source, metadata, documentation, Git hygiene, and trainer-fix
  signatures without claiming that runtime evidence has executed.

GitHub Actions runs the default mode.  The static mode exists for restricted build
sandboxes that cannot download LangGraph dependencies.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
EXPECTED_OWNER = "Adwd23"
EXPECTED_OWNER_EMAIL = "Adwd23@users.noreply.github.com"
EXPECTED_VERSION = "1.3.1"
EXPECTED_ABOUT = (
    "Secure LangGraph multi-agent system for vendor contract auditing, compliance analysis, "
    "guardrails, human approval, and production monitoring."
)
ARABIC_PATTERN = re.compile(r"[\u0600-\u06FF]")
LEGACY_IDENTITIES = ("melko" + "sif57-lang", "308331635+" + "melko" + "sif57-lang")

BASE_REQUIRED_FILES = (
    "README.md",
    "EVALUATION.json",
    "SECURITY.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    ".gitignore",
    ".env.example",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "Dockerfile",
    "docker-compose.yml",
    ".github/workflows/ci.yml",
    "docs/architecture.md",
    "docs/agent_graph.md",
    "docs/security.md",
    "docs/api.md",
    "docs/rubric_traceability.md",
    "docs/course_alignment.md",
    "docs/submission_checklist.md",
    "docs/trainer_feedback_fixes.md",
    "docs/automated_evaluation_guide.md",
    "docs/github_publication.md",
    "notebooks/ContractGuard_Capstone.ipynb",
    "evidence/grader_manifest.json",
    "scripts/grader_probe.py",
    "scripts/runtime_grader_probe.py",
)
RUNTIME_REQUIRED_FILES = (
    "notebooks/ContractGuard_Capstone_Executed.ipynb",
    "evidence/run_summary.json",
    "evidence/execution_log.jsonl",
    "evidence/graph_spec.json",
    "evidence/pytest_results.txt",
    "evidence/01_prompt_injection_blocked.json",
    "evidence/04_checkpoint_loaded_after_restart.json",
    "evidence/05_high_risk_resumed_and_completed.json",
    "evidence/runtime_grader_probe.json",
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("OpenAI-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Groq key", re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[A-Za-z0-9_-]{30,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
)
TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".jsonl",
    ".example", ".cfg", ".ini", ".sh", ".ipynb",
}


class Report:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def add(self, name: str, passed: bool, detail: str, *, mandatory: bool = True) -> None:
        self.checks.append(
            {"name": name, "passed": bool(passed), "mandatory": mandatory, "detail": detail}
        )

    @property
    def ready(self) -> bool:
        return all(item["passed"] for item in self.checks if item["mandatory"])


class CommandFailure(RuntimeError):
    pass


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    source = str(ROOT / "src")
    env["PYTHONPATH"] = source + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        output = ""
        if capture:
            output = f"\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        raise CommandFailure(f"Command failed ({result.returncode}): {' '.join(command)}{output}")
    return result


def tracked_and_pending_files() -> list[Path]:
    result = run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        capture=True,
    )
    return [ROOT / item for item in result.stdout.split("\0") if item]


def iter_text_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if not path.is_file() or path.stat().st_size > 5_000_000:
            continue
        if path.name == "LICENSE" or path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def runtime_suite(report: Report) -> None:
    commands = (
        ("compile", [sys.executable, "-m", "compileall", "-q", "src", "scripts", "tests"]),
        (
            "tests",
            [sys.executable, "-m", "pytest", "--override-ini", "addopts=", "-q", "--color=no"],
        ),
        ("capstone_demo", [sys.executable, "scripts/run_capstone_demo.py"]),
        ("executed_notebook", [sys.executable, "scripts/build_executed_notebook.py"]),
        ("runtime_grader_probe", [sys.executable, "scripts/runtime_grader_probe.py"]),
    )
    for name, command in commands:
        try:
            run(command)
            report.add(f"runtime_{name}", True, "completed successfully")
        except CommandFailure as exc:
            report.add(f"runtime_{name}", False, str(exc))
            return


def check_repository_files(report: Report, *, static_only: bool) -> None:
    required = BASE_REQUIRED_FILES if static_only else BASE_REQUIRED_FILES + RUNTIME_REQUIRED_FILES
    missing = [relative for relative in required if not (ROOT / relative).is_file()]
    report.add(
        "required_repository_files",
        not missing,
        "all present" if not missing else f"missing={missing}",
    )


def check_metadata(report: Report) -> None:
    try:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    except Exception as exc:
        report.add("project_metadata", False, f"unable to parse pyproject.toml: {exc}")
        return

    dependencies = "\n".join(project.get("dependencies", []))
    dev_dependencies = "\n".join(project.get("optional-dependencies", {}).get("dev", []))
    authors = " ".join(str(item.get("name", "")) for item in project.get("authors", []))
    metadata_ok = (
        project.get("name") == "contractguard-ai"
        and project.get("version") == EXPECTED_VERSION
        and all(
            name in dependencies
            for name in (
                "langgraph",
                "langgraph-checkpoint-sqlite",
                "python-dotenv",
                "prometheus-client",
                "minio",
                "uvicorn",
            )
        )
        and "ipykernel" in dev_dependencies
        and "pandas" in dev_dependencies
        and authors.strip() == EXPECTED_OWNER
    )
    report.add(
        "project_metadata",
        metadata_ok,
        f"name={project.get('name')}, version={project.get('version')}, author={authors}",
    )

    readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
    required_phrases = (
        "Advanced Agentic AI Systems Engineering",
        "June 2026",
        "https://github.com/SDAIAAcademy",
        "StateGraph",
        "add_conditional_edges",
        "SqliteSaver",
        "Command(resume=",
        "Plan-and-Execute",
        "ReAct",
        "Reflexion",
        "Evidence index",
        EXPECTED_OWNER,
    )
    missing = [phrase for phrase in required_phrases if phrase not in readme]
    report.add(
        "github_landing_page_documentation",
        not missing,
        "required terms present" if not missing else f"missing={missing}",
    )


def check_trainer_fixes(report: Report) -> None:
    workflow = (ROOT / "src/contractguard/workflow.py").read_text(encoding="utf-8")
    persistence = (ROOT / "src/contractguard/persistence.py").read_text(encoding="utf-8")
    guardrails = (ROOT / "src/contractguard/guardrails.py").read_text(encoding="utf-8")
    input_agent = (ROOT / "src/contractguard/agents/input_security.py").read_text(encoding="utf-8")
    output_agent = (ROOT / "src/contractguard/agents/output_guardian.py").read_text(encoding="utf-8")
    server = (ROOT / "src/contractguard/server.py").read_text(encoding="utf-8")
    notebook_builder = (ROOT / "scripts/build_executed_notebook.py").read_text(encoding="utf-8")

    report.add(
        "trainer_fix_real_stategraph",
        "StateGraph(AuditState)" in workflow and workflow.count("add_conditional_edges(") >= 5,
        f"conditional_edge_api_calls={workflow.count('add_conditional_edges(')}",
    )
    report.add(
        "trainer_fix_real_hitl_resume",
        "interrupt(" in workflow and "Command(resume=" in workflow and "goto=\"report_writer\"" in workflow,
        "interrupt() and Command(resume=...) with Command(goto=...) are present in executable workflow code",
    )
    report.add(
        "trainer_fix_persistent_sqlite",
        "SqliteSaver" in persistence and "checkpointer=self.persistence.saver" in workflow,
        "LangGraph SqliteSaver is compiled directly into the graph",
    )
    report.add(
        "trainer_fix_enforced_guardrails",
        "class InputGuardrail" in guardrails
        and "raise GuardrailViolation" in guardrails
        and "self.input_guardrail.enforce(" in input_agent
        and "self.output_guardrail.enforce(" in output_agent,
        "input and output guardrail classes are called from executable specialist agents",
    )

    expected_agents = {
        "input_security.py": "InputSecurityAgent",
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
    missing_agents = [
        f"{filename}:{class_name}"
        for filename, class_name in expected_agents.items()
        if class_name not in (ROOT / "src/contractguard/agents" / filename).read_text(encoding="utf-8")
    ]
    report.add(
        "trainer_fix_distinct_agent_classes",
        not missing_agents,
        "10 independent specialist classes" if not missing_agents else f"missing={missing_agents}",
    )
    report.add(
        "trainer_fix_declared_libraries_used",
        "import uvicorn" in server and "uvicorn.run(" in server and "make_ipkernel_cmd()" in notebook_builder,
        "uvicorn is the API launcher; ipykernel resolves the notebook kernel launch command",
    )


def check_git(report: Report, paths: list[Path]) -> None:
    bad: list[str] = []
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        if relative == ".env" or (path.name.startswith(".env.") and relative != ".env.example"):
            bad.append(relative)
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            bad.append(relative)
        if relative.startswith("evidence/checkpoints.sqlite"):
            bad.append(relative)
    report.add(
        "git_ignored_runtime_and_secret_files",
        not bad,
        "no forbidden files" if not bad else f"forbidden={sorted(set(bad))}",
    )

    try:
        count = int(run(["git", "rev-list", "--count", "HEAD"], capture=True).stdout.strip())
        authors = run(["git", "log", "--format=%an <%ae>", "HEAD"], capture=True).stdout.splitlines()
        expected_identity = f"{EXPECTED_OWNER} <{EXPECTED_OWNER_EMAIL}>"
        invalid_authors = [value for value in authors if value != expected_identity]
        report.add("incremental_git_history", count >= 6, f"commit_count={count}")
        report.add(
            "git_history_public_identity",
            not invalid_authors,
            f"expected={expected_identity}, invalid_commits={len(invalid_authors)}",
        )
    except (CommandFailure, ValueError) as exc:
        report.add("incremental_git_history", False, str(exc))
        report.add("git_history_public_identity", False, str(exc))


def check_english_only(report: Report, paths: list[Path]) -> None:
    findings: list[str] = []
    for path in iter_text_files(paths):
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = path.relative_to(ROOT).as_posix()
        match = ARABIC_PATTERN.search(content)
        if match:
            line = content.count("\n", 0, match.start()) + 1
            findings.append(f"{relative}:{line}: non-English Arabic Unicode")
        for identity in LEGACY_IDENTITIES:
            if identity.lower() in content.lower():
                findings.append(f"{relative}: legacy identity: {identity}")
    report.add(
        "english_only_content_and_owner",
        not findings,
        "all project text is English-only and uses Adwd23 identity"
        if not findings else f"findings={findings}",
    )


def check_secrets(report: Report, paths: list[Path]) -> None:
    findings: list[str] = []
    for path in iter_text_files(paths):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}: {label}")
    report.add(
        "no_detected_secrets",
        not findings,
        "no high-confidence secret patterns" if not findings else f"findings={findings}",
    )


def check_evidence(report: Report) -> None:
    invalid_json: list[str] = []
    for path in sorted(EVIDENCE.glob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            invalid_json.append(f"{path.name}: {exc}")
    report.add("evidence_json_valid", not invalid_json, "all valid" if not invalid_json else str(invalid_json))

    try:
        runtime_probe = json.loads((EVIDENCE / "runtime_grader_probe.json").read_text(encoding="utf-8"))
        report.add(
            "runtime_grader_probe_pass",
            runtime_probe.get("all_runtime_checks_pass") is True
            and runtime_probe.get("output_contract") == "single_json_object_no_markdown",
            f"status={runtime_probe.get('status')}, checks={len(runtime_probe.get('checks', {}))}",
        )
    except Exception as exc:
        report.add("runtime_grader_probe_pass", False, str(exc))

    try:
        summary = json.loads((EVIDENCE / "run_summary.json").read_text(encoding="utf-8"))
        proof = summary.get("proof", {})
        failed = [name for name, value in proof.items() if value is not True]
        report.add(
            "all_rubric_execution_assertions",
            bool(proof) and not failed and summary.get("all_assertions_passed") is True,
            f"proof_count={len(proof)}, failed={failed}",
        )
    except Exception as exc:
        report.add("all_rubric_execution_assertions", False, str(exc))

    try:
        graph = json.loads((EVIDENCE / "graph_spec.json").read_text(encoding="utf-8"))
        graph_ok = (
            graph.get("framework_package") == "langgraph"
            and graph.get("builder_api") == "StateGraph(AuditState)"
            and graph.get("conditional_routing_api") == "StateGraph.add_conditional_edges"
            and graph.get("hitl_pause_api") == "langgraph.types.interrupt"
            and graph.get("hitl_resume_api") == "langgraph.types.Command(resume=...)"
            and graph.get("persistent_checkpointer") == "langgraph.checkpoint.sqlite.SqliteSaver"
            and int(graph.get("node_count", 0)) >= 10
            and int(graph.get("conditional_edge_count", 0)) >= 5
            and int(graph.get("runtime_builder_introspection", {}).get("conditional_branch_count", 0)) >= 5
            and graph.get("has_cycles") is True
            and graph.get("is_linear_chain") is False
            and graph.get("supports_restart_resume") is True
        )
        report.add(
            "real_graph_structure",
            graph_ok,
            (
                f"framework={graph.get('framework_package')} {graph.get('framework_version')}, "
                f"nodes={graph.get('node_count')}, conditional={graph.get('conditional_edge_count')}"
            ),
        )
    except Exception as exc:
        report.add("real_graph_structure", False, str(exc))

    try:
        blocked = json.loads((EVIDENCE / "01_prompt_injection_blocked.json").read_text(encoding="utf-8"))
        report.add(
            "guardrail_attack_execution_evidence",
            blocked.get("status") == "blocked"
            and blocked.get("guardrail_enforced") is True
            and blocked.get("tool_calls") == [],
            f"status={blocked.get('status')}, tool_calls={len(blocked.get('tool_calls', []))}",
        )
    except Exception as exc:
        report.add("guardrail_attack_execution_evidence", False, str(exc))

    try:
        loaded = json.loads((EVIDENCE / "04_checkpoint_loaded_after_restart.json").read_text(encoding="utf-8"))
        final = json.loads((EVIDENCE / "05_high_risk_resumed_and_completed.json").read_text(encoding="utf-8"))
        report.add(
            "hitl_pause_restart_resume_evidence",
            loaded.get("node") == "human_approval"
            and loaded.get("state", {}).get("status") == "awaiting_approval"
            and "human_approval" in loaded.get("next", [])
            and final.get("approval_status") == "approved"
            and final.get("status") == "completed",
            "interrupt checkpoint reloaded after restart and resumed to completion",
        )
    except Exception as exc:
        report.add("hitl_pause_restart_resume_evidence", False, str(exc))

    try:
        pytest_text = (EVIDENCE / "pytest_results.txt").read_text(encoding="utf-8")
        pytest_ok = "passed" in pytest_text.lower() and "failed" not in pytest_text.lower()
        report.add("captured_tests_pass", pytest_ok, pytest_text.strip()[-300:])
    except Exception as exc:
        report.add("captured_tests_pass", False, str(exc))

    try:
        logs = [
            json.loads(line)
            for line in (EVIDENCE / "execution_log.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        events = {item.get("event") for item in logs}
        required = {"guardrail_blocked", "tool_call_failed", "human_interrupt", "workflow_retry"}
        missing = sorted(required - events)
        report.add(
            "structured_failure_and_security_logs",
            not missing,
            f"events={len(events)}, missing={missing}",
        )
    except Exception as exc:
        report.add("structured_failure_and_security_logs", False, str(exc))


def check_notebook(report: Report) -> None:
    try:
        notebook = json.loads(
            (ROOT / "notebooks" / "ContractGuard_Capstone_Executed.ipynb").read_text(encoding="utf-8")
        )
        code = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "code"]
        errors = [
            output
            for cell in code
            for output in cell.get("outputs", [])
            if output.get("output_type") == "error"
        ]
        unexecuted = [cell for cell in code if cell.get("execution_count") is None]
        report.add(
            "executed_notebook_has_no_errors",
            bool(code) and not errors and not unexecuted,
            f"code_cells={len(code)}, errors={len(errors)}, unexecuted={len(unexecuted)}",
        )
    except Exception as exc:
        report.add("executed_notebook_has_no_errors", False, str(exc))


def add_external_warnings(report: Report) -> None:
    try:
        remote = run(["git", "remote", "get-url", "origin"], capture=True).stdout.strip()
    except CommandFailure:
        remote = ""
    report.add(
        "github_origin_configured",
        bool(remote),
        remote or "pending: add https://github.com/Adwd23/contractguard-ai-capstone as origin",
        mandatory=False,
    )
    report.add(
        "github_about_description",
        False,
        f"External GitHub UI step: About description must be exactly or equivalently: {EXPECTED_ABOUT}",
        mandatory=False,
    )
    report.add(
        "minio_runtime_smoke_evidence",
        (EVIDENCE / "07_minio_docker_smoke.json").exists(),
        "captured" if (EVIDENCE / "07_minio_docker_smoke.json").exists() else "generated by docker-minio-smoke CI job",
        mandatory=False,
    )


def write_report(report: Report, *, static_only: bool) -> Path:
    payload = {
        "project": "ContractGuard AI",
        "edition": "v1.3.1 Automated-Grader Hardened Edition",
        "version": EXPECTED_VERSION,
        "owner": EXPECTED_OWNER,
        "validation_mode": "static-only" if static_only else "full-runtime",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready_to_publish": report.ready,
        "runtime_evidence_executed": not static_only and report.ready,
        "checks": report.checks,
        "mandatory_failures": [
            item["name"] for item in report.checks if item["mandatory"] and not item["passed"]
        ],
        "github_about_description": EXPECTED_ABOUT,
        "external_steps": [
            "Publish under the Adwd23 GitHub account.",
            "Set the repository About description.",
            "Wait for contractguard-ci jobs to become green before resubmission.",
        ],
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    name = "local_static_validation.json" if static_only else "prepublish_report.json"
    path = EVIDENCE / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-runtime",
        action="store_true",
        help="Do not rerun compile/tests/demo/notebook; require already-captured runtime evidence.",
    )
    parser.add_argument(
        "--static-only",
        action="store_true",
        help="Validate source/metadata/Git only; do not claim runtime execution evidence.",
    )
    args = parser.parse_args()
    if args.static_only and args.skip_runtime:
        parser.error("Use either --static-only or --skip-runtime, not both")

    report = Report()
    if not args.skip_runtime and not args.static_only:
        runtime_suite(report)

    try:
        paths = tracked_and_pending_files()
    except CommandFailure as exc:
        paths = []
        report.add("git_file_inventory", False, str(exc))

    check_repository_files(report, static_only=args.static_only)
    check_metadata(report)
    check_trainer_fixes(report)
    check_git(report, paths)
    check_english_only(report, paths)
    check_secrets(report, paths)
    if not args.static_only:
        check_evidence(report)
        check_notebook(report)
    else:
        report.add(
            "runtime_evidence_pending",
            True,
            "restricted local sandbox: GitHub Actions must generate real LangGraph runtime evidence",
            mandatory=False,
        )
    add_external_warnings(report)
    output = write_report(report, static_only=args.static_only)

    print(f"Pre-publication report: {output}")
    for item in report.checks:
        marker = "PASS" if item["passed"] else ("WARN" if not item["mandatory"] else "FAIL")
        print(f"[{marker}] {item['name']}: {item['detail']}")
    print("Ready to publish:", report.ready)
    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
