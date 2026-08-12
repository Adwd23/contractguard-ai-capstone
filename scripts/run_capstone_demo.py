#!/usr/bin/env python3
"""Run and assert every scored capstone path, including security/failure/HITL paths."""
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
    tool_calls = state.get("tool_calls", [])
    model_routes = sorted(
        {
            f"{item.get('model_provider')}:{item.get('model_name')}"
            for item in tool_calls
            if item.get("model_provider") and item.get("model_name")
        }
    )
    return {
        "thread_id": state["thread_id"],
        "status": state["status"],
        "workflow_node": state.get("workflow_node"),
        "node_history": state.get("node_history", []),
        "tool_call_count": len(tool_calls),
        "tool_names": [item.get("tool_name") for item in tool_calls],
        "tool_decision_sources": sorted({item.get("decision_source") for item in tool_calls}),
        "tool_protocols": sorted({item.get("protocol") for item in tool_calls}),
        "model_routes": model_routes,
        "reasoner_mode": state.get("reasoner_mode"),
        "reasoner_modes": state.get("reasoner_modes", []),
        "live_llm_tool_call_count": state.get("live_llm_tool_call_count", 0),
        "tool_observation_statuses": [item["status"] for item in state.get("tool_observations", [])],
        "agent_names": sorted({m["sender"] for m in state.get("agent_messages", [])}),
        "agent_message_count": len(state.get("agent_messages", [])),
        "decision_patterns": sorted(
            {d.get("pattern") for d in state.get("decision_trace", []) if d.get("pattern")}
        ),
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
    preserved: dict[str, str] = {}
    for name in ("README.md", "06_live_llm_function_call.json", "07_minio_docker_smoke.json"):
        path = evidence_dir / name
        if path.exists():
            preserved[name] = path.read_text(encoding="utf-8")
    if evidence_dir.exists():
        shutil.rmtree(evidence_dir)
    evidence_dir.mkdir(parents=True)
    for name, text in preserved.items():
        (evidence_dir / name).write_text(text, encoding="utf-8")

    settings = Settings.from_env(PROJECT_ROOT)
    # Keep the scored evidence deterministic and privacy-safe even when a developer has
    # live provider or MinIO values in an untracked local .env. Dedicated scripts/CI jobs
    # cover provider-native function calling and real MinIO persistence separately.
    settings.llm_provider = "offline"
    settings.groq_api_key = None
    settings.openrouter_api_key = None
    settings.gemini_api_key = None
    settings.minio_endpoint = None
    settings.api_key = None
    settings.ensure_directories()
    high_contract = PROJECT_ROOT / "data" / "samples" / "vendor_contract_high_risk.txt"
    low_contract = PROJECT_ROOT / "data" / "samples" / "vendor_contract_low_risk.txt"
    attack_contract = PROJECT_ROOT / "data" / "samples" / "prompt_injection_contract.txt"

    print("[1/6] Running a real indirect prompt-injection attack attempt...")
    service = ContractGuardService(settings)
    agent_tool_permissions = {
        agent.name: sorted(agent.allowed_tools) for agent in service.agents.values()
    }
    graph_spec = service.graph_spec()

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

    print("[2/6] Running the low-risk autonomous path with real schema-described functions...")
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
    assert any(
        call.get("decision_source") == "offline_schema_router"
        and call.get("tool_name") == "search_policy_knowledge_base"
        and call.get("protocol") == "mcp_json_schema"
        for call in low["tool_calls"]
    )
    write_json(evidence_dir / "02_low_risk_completed.json", low)

    print("[3/6] Running tool failure/retry, Reflexion, and durable HITL pause paths...")
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
    assert paused["node_history"].count("policy_research") >= 3
    paused_history = service.history("capstone-high-risk")
    write_json(evidence_dir / "03_high_risk_paused_for_human.json", paused)
    write_json(evidence_dir / "03_high_risk_checkpoint_history_before_restart.json", paused_history)
    write_json(evidence_dir / "graph_spec.json", graph_spec)
    service.observability.export_metrics(evidence_dir / "metrics_before_restart.prom")

    print("[4/6] Closing the service and proving durable SQLite restart recovery...")
    service.close()

    restarted_service = ContractGuardService(settings)
    loaded = restarted_service.get("capstone-high-risk")
    assert loaded["node"] == "human_approval"
    assert loaded["state"]["status"] == "awaiting_approval"
    assert "human_approval" in loaded.get("next", [])
    assert loaded["state"]["risk_score"] == paused["risk_score"]
    write_json(evidence_dir / "04_checkpoint_loaded_after_restart.json", loaded)

    print("[5/6] Applying human approval and resuming from the exact interrupt...")
    final = restarted_service.resume(
        "capstone-high-risk",
        ResumeRequest(
            decision="approve",
            approver="Capstone Human Reviewer",
            comment=(
                "Approved conditionally after Legal confirmed remediation of all "
                "high-severity findings."
            ),
        ),
    )
    assert final["status"] == "completed"
    assert final["approval_status"] == "approved"
    assert final["report_revision_count"] >= 1, "Output validation loop must have fired"
    assert final["pii_redactions"] >= 3, "Email, phone, and national ID must be masked"
    assert "example.com" not in final["final_markdown"]
    assert "1023456789" not in final["final_markdown"]
    assert final["artifact_uri"]
    assert final["storage_backend"] == "filesystem-fallback"
    assert Path(final["artifact_uri"].removeprefix("file://")).exists()
    final_history = restarted_service.history("capstone-high-risk")
    write_json(evidence_dir / "05_high_risk_resumed_and_completed.json", final)
    write_json(evidence_dir / "05_high_risk_checkpoint_history_after_resume.json", final_history)
    restarted_service.observability.export_metrics(evidence_dir / "metrics_after_restart.prom")

    print("[6/6] Writing evaluator-friendly architecture and proof summaries...")
    schema_routed_calls = [
        call
        for call in low.get("tool_calls", [])
        if call.get("decision_source") == "offline_schema_router"
        and call.get("protocol") == "mcp_json_schema"
    ]
    successful_low_observations = [
        item for item in low.get("tool_observations", []) if item.get("status") == "success"
    ]
    graph_is_real = (
        graph_spec.get("framework_package") == "langgraph"
        and graph_spec.get("is_linear_chain") is False
        and graph_spec.get("has_cycles") is True
        and graph_spec.get("has_conditional_routing") is True
        and int(graph_spec.get("conditional_edge_count", 0)) >= 5
        and graph_spec.get("conditional_routing_api") == "StateGraph.add_conditional_edges"
        and graph_spec.get("hitl_pause_api") == "langgraph.types.interrupt"
        and graph_spec.get("hitl_resume_api") == "langgraph.types.Command(resume=...)"
    )
    specialized_agents = {message["sender"] for message in final.get("agent_messages", [])}
    least_privilege_ok = (
        agent_tool_permissions.get("Document Analyst Agent")
        == ["extract_contract_clauses", "read_contract"]
        and agent_tool_permissions.get("Policy Research Agent")
        == ["search_policy_knowledge_base"]
        and agent_tool_permissions.get("Security Reviewer Agent")
        == ["calculate_contract_risk"]
        and agent_tool_permissions.get("Artifact Storage Agent")
        == ["store_report_artifact"]
    )

    proof = {
        "real_schema_validated_tools_executed": (
            len(low.get("tool_calls", [])) >= 6
            and len(successful_low_observations) == len(low.get("tool_observations", []))
        ),
        "schema_driven_tool_router_used": bool(schema_routed_calls),
        "shared_state_carried_across_nodes": (
            len(low.get("node_history", [])) >= 10 and bool(low.get("policy_evidence"))
        ),
        "real_framework_graph_has_conditions_and_cycles": graph_is_real,
        "multiple_specialized_agents_communicated": len(specialized_agents) >= 8,
        "per_agent_tool_permissions_configured": least_privilege_ok,
        "langgraph_stategraph_is_real": (
            graph_spec.get("builder_api") == "StateGraph(AuditState)"
            and graph_spec.get("framework_package") == "langgraph"
        ),
        "explicit_conditional_edges_are_real": (
            graph_spec.get("conditional_routing_api") == "StateGraph.add_conditional_edges"
            and int(graph_spec.get("conditional_edge_count", 0)) >= 5
        ),
        "input_guardrail_enforced_before_tools": (
            blocked.get("guardrail_enforced") is True and blocked.get("tool_calls") == []
        ),
        "output_guardrail_enforced": final.get("output_guardrail_enforced") is True,
        "langgraph_interrupt_and_command_resume": (
            paused["status"] == "awaiting_approval"
            and final["approval_status"] == "approved"
        ),
        "prompt_injection_was_blocked": (
            blocked["status"] == "blocked" and not blocked["tool_calls"]
        ),
        "tool_failure_retry_fired": paused["policy_retry_count"] >= 1,
        "quality_replan_loop_fired": paused["quality_retry_count"] >= 1,
        "persistent_checkpoint_survived_restart": (
            loaded["node"] == "human_approval"
            and loaded["state"]["status"] == "awaiting_approval"
            and "human_approval" in loaded.get("next", [])
        ),
        "human_pause_resumed": (
            final["approval_status"] == "approved" and final["status"] == "completed"
        ),
        "output_validation_revision_fired": final["report_revision_count"] >= 1,
        "pii_was_masked": final["pii_redactions"] >= 3,
        "structured_logs_exist": (
            settings.log_file.exists() and settings.log_file.stat().st_size > 0
        ),
        "prometheus_metrics_exist": (evidence_dir / "metrics_before_restart.prom").exists(),
        "cloud_deployment_artifacts_exist": (
            (PROJECT_ROOT / "Dockerfile").exists()
            and (PROJECT_ROOT / "docker-compose.yml").exists()
            and (PROJECT_ROOT / "deploy" / "prometheus.yml").exists()
        ),
    }
    assert all(proof.values()), {name: value for name, value in proof.items() if not value}

    summary = {
        "project": "ContractGuard AI",
        "version": "1.3.0",
        "all_assertions_passed": all(proof.values()),
        "framework": graph_spec["framework"],
        "framework_package": graph_spec["framework_package"],
        "framework_version": graph_spec["framework_version"],
        "reasoning_patterns": [
            "Plan-and-Execute",
            "ReAct",
            "Reflexion/self-critique",
            "Hierarchical delegation",
        ],
        "coordination_strategy": (
            "Centralized Coordinator Agent with typed shared-state specialist handoffs"
        ),
        "tool_interface": {
            "mode": "MCP-style JSON-schema function registry",
            "registered_tool_count": len(restarted_service.tools.describe()),
            "registered_tools": [item["name"] for item in restarted_service.tools.describe()],
            "default_reasoner": "offline_schema_router",
            "optional_native_providers": ["Gemini", "OpenRouter", "Groq"],
            "agent_tool_permissions": agent_tool_permissions,
        },
        "graph": {
            "node_count": graph_spec["node_count"],
            "edge_count": graph_spec["edge_count"],
            "conditional_edge_count": graph_spec["conditional_edge_count"],
            "branching_nodes": graph_spec["branching_nodes"],
            "loops": graph_spec["loops"],
        },
        "scenarios": {
            "blocked_attack": compact(blocked),
            "low_risk": compact(low),
            "high_risk_paused": compact(paused),
            "high_risk_completed": compact(final),
        },
        "proof": proof,
    }
    write_json(evidence_dir / "run_summary.json", summary)
    summary["evidence_files"] = sorted(
        str(path.relative_to(PROJECT_ROOT))
        for path in evidence_dir.rglob("*")
        if path.is_file()
    )
    write_json(evidence_dir / "run_summary.json", summary)
    restarted_service.close()

    print(json.dumps(summary["proof"], indent=2))
    print("All capstone evidence assertions passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
