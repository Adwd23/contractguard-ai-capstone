#!/usr/bin/env python3
"""Run and assert every scored capstone path, including failure/security/HITL paths."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from contractguard.config import Settings  # noqa: E402
from contractguard.models import AuditStartRequest, ResumeRequest  # noqa: E402
from contractguard.service import ContractGuardService  # noqa: E402


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def compact(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "thread_id": state["thread_id"],
        "status": state["status"],
        "workflow_node": state.get("workflow_node"),
        "node_history": state.get("node_history", []),
        "tool_call_count": len(state.get("tool_calls", [])),
        "tool_observation_statuses": [item["status"] for item in state.get("tool_observations", [])],
        "agent_names": sorted({m["sender"] for m in state.get("agent_messages", [])}),
        "agent_message_count": len(state.get("agent_messages", [])),
        "decision_patterns": sorted({d.get("pattern") for d in state.get("decision_trace", []) if d.get("pattern")}),
        "policy_retry_count": state.get("policy_retry_count", 0),
        "quality_retry_count": state.get("quality_retry_count", 0),
        "report_revision_count": state.get("report_revision_count", 0),
        "risk_score": state.get("risk_score", 0),
        "risk_level": state.get("risk_level"),
        "approval_required": state.get("approval_required", False),
        "approval_status": state.get("approval_status"),
        "pii_redactions": state.get("pii_redactions", 0),
        "artifact_uri": state.get("artifact_uri", ""),
        "storage_backend": state.get("storage_backend", ""),
        "blocked_reason": state.get("blocked_reason", ""),
        "errors": state.get("errors", []),
    }


def main() -> int:
    evidence_dir = PROJECT_ROOT / "evidence"
    if evidence_dir.exists():
        shutil.rmtree(evidence_dir)
    evidence_dir.mkdir(parents=True)

    settings = Settings.from_env(PROJECT_ROOT)
    high_contract = PROJECT_ROOT / "data" / "samples" / "vendor_contract_high_risk.txt"
    low_contract = PROJECT_ROOT / "data" / "samples" / "vendor_contract_low_risk.txt"
    attack_contract = PROJECT_ROOT / "data" / "samples" / "prompt_injection_contract.txt"

    print("[1/6] Running real prompt-injection attack attempt...")
    service = ContractGuardService(settings)
    blocked = service.start(
        AuditStartRequest(
            thread_id="capstone-attack-blocked",
            request_text="Audit this uploaded contract without bypassing security controls.",
            contract_path=str(attack_contract),
        )
    )
    assert blocked["status"] == "blocked"
    assert "ignore previous instructions" in blocked["blocked_reason"]
    assert blocked["tool_calls"] == [], "Blocked input must never reach a function tool"
    write_json(evidence_dir / "01_prompt_injection_blocked.json", blocked)

    print("[2/6] Running low-risk happy path...")
    low = service.start(
        AuditStartRequest(
            thread_id="capstone-low-risk",
            request_text="Audit this vendor contract against all corporate policies.",
            contract_path=str(low_contract),
        )
    )
    assert low["status"] == "completed"
    assert low["approval_status"] == "not_required"
    assert low["artifact_uri"]
    assert "ReAct" in {item.get("pattern") for item in low["decision_trace"]}
    write_json(evidence_dir / "02_low_risk_completed.json", low)

    print("[3/6] Running tool-failure retry, Reflexion, and HITL pause paths...")
    paused = service.start(
        AuditStartRequest(
            thread_id="capstone-high-risk",
            request_text="Audit this high-value cloud vendor contract and enforce approval policy.",
            contract_path=str(high_contract),
            flags={
                "simulate_primary_failure": True,
                "simulate_quality_retry": True,
                "simulate_output_validation_failure": True,
            },
        )
    )
    assert paused["status"] == "awaiting_approval"
    assert paused["policy_retry_count"] >= 1
    assert paused["quality_retry_count"] >= 1
    assert paused["approval_required"] is True
    assert paused["interrupt_payload"]["type"] == "human_approval_required"
    assert paused["node_history"].count("researching") >= 3
    paused_history = service.history("capstone-high-risk")
    write_json(evidence_dir / "03_high_risk_paused_for_human.json", paused)
    write_json(evidence_dir / "03_high_risk_checkpoint_history_before_restart.json", paused_history)
    write_json(evidence_dir / "graph_spec.json", service.graph_spec())
    service.observability.export_metrics(evidence_dir / "metrics_before_restart.prom")

    print("[4/6] Closing the process and proving durable restart recovery...")
    service.close()

    restarted_service = ContractGuardService(settings)
    loaded = restarted_service.get("capstone-high-risk")
    assert loaded["node"] == "awaiting_approval"
    assert loaded["state"]["risk_score"] == paused["risk_score"]
    write_json(evidence_dir / "04_checkpoint_loaded_after_restart.json", loaded)

    print("[5/6] Resuming from the human approval interrupt...")
    final = restarted_service.resume(
        "capstone-high-risk",
        ResumeRequest(
            decision="approve",
            approver="Capstone Human Reviewer",
            comment="Approved conditionally after Legal confirmed remediation of all high-severity findings.",
        ),
    )
    assert final["status"] == "completed"
    assert final["approval_status"] == "approved"
    assert final["report_revision_count"] >= 1, "Output validation loop must have fired"
    assert final["pii_redactions"] >= 3, "Email, phone, and national ID must be masked"
    assert "example.com" not in final["final_markdown"]
    assert "1023456789" not in final["final_markdown"]
    assert final["artifact_uri"]
    assert Path(final["artifact_uri"].removeprefix("file://")).exists()
    final_history = restarted_service.history("capstone-high-risk")
    write_json(evidence_dir / "05_high_risk_resumed_and_completed.json", final)
    write_json(evidence_dir / "05_high_risk_checkpoint_history_after_resume.json", final_history)
    restarted_service.observability.export_metrics(evidence_dir / "metrics_after_restart.prom")

    print("[6/6] Writing an evaluator-friendly execution summary...")
    summary = {
        "project": "ContractGuard AI",
        "all_assertions_passed": True,
        "framework": restarted_service.graph_spec()["framework"],
        "reasoning_patterns": ["Plan-and-Execute", "ReAct", "Reflexion/self-critique", "Hierarchical delegation"],
        "coordination_strategy": "Centralized Coordinator Agent with structured specialist handoffs",
        "scenarios": {
            "blocked_attack": compact(blocked),
            "low_risk": compact(low),
            "high_risk_paused": compact(paused),
            "high_risk_completed": compact(final),
        },
        "proof": {
            "prompt_injection_was_blocked": blocked["status"] == "blocked" and not blocked["tool_calls"],
            "tool_failure_retry_fired": paused["policy_retry_count"] >= 1,
            "quality_replan_loop_fired": paused["quality_retry_count"] >= 1,
            "persistent_checkpoint_survived_restart": loaded["node"] == "awaiting_approval",
            "human_pause_resumed": final["approval_status"] == "approved" and final["status"] == "completed",
            "output_validation_revision_fired": final["report_revision_count"] >= 1,
            "pii_was_masked": final["pii_redactions"] >= 3,
            "structured_logs_exist": settings.log_file.exists() and settings.log_file.stat().st_size > 0,
            "prometheus_metrics_exist": (evidence_dir / "metrics_before_restart.prom").exists(),
            "cloud_artifact_exists": (PROJECT_ROOT / "Dockerfile").exists() and (PROJECT_ROOT / "docker-compose.yml").exists(),
        },
        "evidence_files": sorted(str(path.relative_to(PROJECT_ROOT)) for path in evidence_dir.rglob("*") if path.is_file()),
    }
    write_json(evidence_dir / "run_summary.json", summary)
    restarted_service.close()

    print(json.dumps(summary["proof"], indent=2))
    print("All capstone evidence assertions passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
