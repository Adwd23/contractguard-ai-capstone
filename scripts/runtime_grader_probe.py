#!/usr/bin/env python3
"""Emit one strict JSON object with end-to-end runtime evidence.

The probe is designed for automated repository graders. It never mixes human-readable
progress messages with JSON. With ``--refresh`` it runs the complete capstone demo while
capturing that runner's stdout/stderr, then validates the generated evidence files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"


def load_json(name: str) -> dict[str, Any]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def error_payload(message: str, *, detail: str = "") -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "output_contract": "single_json_object_no_markdown",
        "project": "ContractGuard AI",
        "edition": "v1.3.1 Automated-Grader Hardened Edition",
        "version": "1.3.1",
        "owner": "Adwd23",
        "status": "error",
        "all_runtime_checks_pass": False,
        "error": message,
        "detail": detail[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Run scripts/run_capstone_demo.py first and capture its output silently.",
    )
    args = parser.parse_args()

    captured_stdout = ""
    captured_stderr = ""
    try:
        if args.refresh or not (EVIDENCE / "run_summary.json").exists():
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "run_capstone_demo.py")],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            captured_stdout = result.stdout
            captured_stderr = result.stderr
            if result.returncode != 0:
                payload = error_payload(
                    "Capstone demo failed before runtime evidence could be validated.",
                    detail=(result.stdout + "\n" + result.stderr),
                )
                json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
                sys.stdout.write("\n")
                return 1

        summary = load_json("run_summary.json")
        blocked = load_json("01_prompt_injection_blocked.json")
        low = load_json("02_low_risk_completed.json")
        paused = load_json("03_high_risk_paused_for_human.json")
        restarted = load_json("04_checkpoint_loaded_after_restart.json")
        final = load_json("05_high_risk_resumed_and_completed.json")
        graph = load_json("graph_spec.json")

        senders = sorted({m.get("sender") for m in final.get("agent_messages", []) if m.get("sender")})
        recipients = sorted({m.get("recipient") for m in final.get("agent_messages", []) if m.get("recipient")})
        successful_tools = [o for o in low.get("tool_observations", []) if o.get("status") == "success"]
        failed_tools = [o for o in paused.get("tool_observations", []) if o.get("status") == "error"]
        final_artifact = str(final.get("artifact_uri", ""))
        artifact_exists = final_artifact.startswith("file://") and Path(final_artifact.removeprefix("file://")).exists()

        checks = {
            "input_attack_blocked": blocked.get("status") == "blocked",
            "guardrail_enforced": blocked.get("guardrail_enforced") is True,
            "zero_tools_after_block": blocked.get("tool_calls") == [],
            "real_tools_executed": len(low.get("tool_calls", [])) >= 6 and len(successful_tools) >= 6,
            "react_trace_present": "ReAct" in {d.get("pattern") for d in low.get("decision_trace", [])},
            "stategraph_non_linear": graph.get("framework_package") == "langgraph" and graph.get("is_linear_chain") is False,
            "conditional_edges_present": int(graph.get("conditional_edge_count", 0)) >= 5,
            "runtime_stategraph_branches_registered": int(graph.get("runtime_builder_introspection", {}).get("conditional_branch_count", 0)) >= 5,
            "bounded_graph_cycle_executed": paused.get("node_history", []).count("policy_research") >= 3,
            "tool_failure_retry_executed": bool(failed_tools) and int(paused.get("policy_retry_count", 0)) >= 1,
            "reflexion_retry_executed": int(paused.get("quality_retry_count", 0)) >= 1,
            "multiple_agents_communicated": len(senders) >= 8 and len(recipients) >= 5,
            "human_interrupt_paused": paused.get("status") == "awaiting_approval",
            "checkpoint_survived_restart": restarted.get("node") == "human_approval" and restarted.get("state", {}).get("status") == "awaiting_approval",
            "command_resume_completed": final.get("status") == "completed" and final.get("approval_status") == "approved",
            "output_revision_executed": int(final.get("report_revision_count", 0)) >= 1,
            "pii_masking_executed": int(final.get("pii_redactions", 0)) >= 3,
            "output_guardrail_enforced": final.get("output_guardrail_enforced") is True,
            "artifact_persisted": bool(final_artifact) and artifact_exists,
            "structured_logs_exist": (EVIDENCE / "execution_log.jsonl").exists() and (EVIDENCE / "execution_log.jsonl").stat().st_size > 0,
            "prometheus_metrics_exist": (EVIDENCE / "metrics_before_restart.prom").exists(),
        }

        payload = {
            "schema_version": "1.0",
            "output_contract": "single_json_object_no_markdown",
            "project": "ContractGuard AI",
            "edition": "v1.3.1 Automated-Grader Hardened Edition",
            "version": "1.3.1",
            "owner": "Adwd23",
            "status": "pass" if all(checks.values()) else "fail",
            "all_runtime_checks_pass": all(checks.values()),
            "checks": checks,
            "evidence": {
                "blocked_attack": "evidence/01_prompt_injection_blocked.json",
                "low_risk_tools": "evidence/02_low_risk_completed.json",
                "high_risk_pause": "evidence/03_high_risk_paused_for_human.json",
                "restart_checkpoint": "evidence/04_checkpoint_loaded_after_restart.json",
                "resume_completion": "evidence/05_high_risk_resumed_and_completed.json",
                "graph": "evidence/graph_spec.json",
                "logs": "evidence/execution_log.jsonl",
                "metrics": "evidence/metrics_before_restart.prom",
            },
            "observed": {
                "conditional_edge_count": graph.get("conditional_edge_count"),
                "runtime_builder_introspection": graph.get("runtime_builder_introspection", {}),
                "branching_nodes": graph.get("branching_nodes", []),
                "loops": graph.get("loops", []),
                "agent_senders": senders,
                "agent_recipients": recipients,
                "tool_call_count": len(low.get("tool_calls", [])),
                "failed_tool_observations": len(failed_tools),
                "policy_retry_count": paused.get("policy_retry_count", 0),
                "quality_retry_count": paused.get("quality_retry_count", 0),
                "report_revision_count": final.get("report_revision_count", 0),
                "pii_redactions": final.get("pii_redactions", 0),
                "approval_status": final.get("approval_status"),
                "artifact_uri": final_artifact,
            },
            "runner_capture": {
                "stdout_was_captured": bool(captured_stdout),
                "stderr_was_captured": bool(captured_stderr),
            },
            "summary_proof": summary.get("proof", {}),
        }
    except Exception as exc:  # Always return parseable JSON, even on evaluator failures.
        payload = error_payload(type(exc).__name__, detail=str(exc))

    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if payload.get("all_runtime_checks_pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
