from __future__ import annotations

from pathlib import Path
import json

from contractguard.models import AuditStartRequest, ResumeRequest
from contractguard.service import ContractGuardService


def test_indirect_prompt_injection_is_blocked_before_tools(isolated_settings) -> None:
    path = isolated_settings.project_root / "data" / "samples" / "prompt_injection_contract.txt"
    with ContractGuardService(isolated_settings) as service:
        state = service.start(
            AuditStartRequest(
                thread_id="attack-test",
                request_text="Audit the uploaded contract.",
                contract_path=str(path),
            )
        )
    assert state["status"] == "blocked"
    assert state["node_history"] == ["received", "guardrailed", "blocked"]
    assert state["tool_calls"] == []


def test_low_risk_contract_completes_without_human(isolated_settings) -> None:
    path = isolated_settings.project_root / "data" / "samples" / "vendor_contract_low_risk.txt"
    with ContractGuardService(isolated_settings) as service:
        state = service.start(
            AuditStartRequest(
                thread_id="low-risk-test",
                request_text="Audit the contract against policy.",
                contract_path=str(path),
            )
        )
    assert state["status"] == "completed"
    assert state["risk_score"] == 0
    assert state["approval_status"] == "not_required"
    assert state["artifact_uri"].startswith("file://")
    assert "awaiting_approval" not in state["node_history"]


def test_retry_pause_restart_resume_and_output_revision(isolated_settings) -> None:
    path = isolated_settings.project_root / "data" / "samples" / "vendor_contract_high_risk.txt"
    service = ContractGuardService(isolated_settings)
    paused = service.start(
        AuditStartRequest(
            thread_id="high-risk-test",
            request_text="Audit and enforce human approval policy.",
            contract_path=str(path),
            flags={
                "simulate_primary_failure": True,
                "simulate_quality_retry": True,
                "simulate_output_validation_failure": True,
            },
        )
    )
    assert paused["status"] == "awaiting_approval"
    assert paused["policy_retry_count"] == 1
    assert paused["quality_retry_count"] == 1
    assert paused["node_history"].count("researching") >= 3
    service.close()

    # A completely new service object reads the same SQLite checkpoint.
    restarted = ContractGuardService(isolated_settings)
    loaded = restarted.get("high-risk-test")
    assert loaded["node"] == "awaiting_approval"
    final = restarted.resume(
        "high-risk-test",
        ResumeRequest(
            decision="approve",
            approver="test-reviewer",
            comment="Approved after redline review.",
        ),
    )
    restarted.close()

    assert final["status"] == "completed"
    assert final["approval_status"] == "approved"
    assert final["report_revision_count"] == 1
    assert final["pii_redactions"] >= 3
    assert "example.com" not in final["final_markdown"]
    assert "1023456789" not in final["final_markdown"]
    assert Path(final["artifact_uri"].removeprefix("file://")).exists()


def test_offline_schema_router_executes_mcp_style_tool_selection(isolated_settings) -> None:
    path = isolated_settings.project_root / "data" / "samples" / "vendor_contract_low_risk.txt"
    with ContractGuardService(isolated_settings) as service:
        state = service.start(
            AuditStartRequest(
                thread_id="schema-router-test",
                request_text="Audit the contract and retrieve policy evidence.",
                contract_path=str(path),
            )
        )

    routed_calls = [
        call for call in state["tool_calls"]
        if call["tool_name"] == "search_policy_knowledge_base"
    ]
    assert routed_calls
    assert all(call["decision_source"] == "offline_schema_router" for call in routed_calls)
    assert all(call["protocol"] == "mcp_json_schema" for call in routed_calls)
    assert state["reasoner_mode"] == "offline_schema_router"
    assert "offline_schema_router" in state["reasoner_modes"]


def test_optional_llm_summary_receives_minimized_redacted_context(
    monkeypatch, isolated_settings
) -> None:
    source = (
        isolated_settings.project_root / "data" / "samples" / "vendor_contract_low_risk.txt"
    ).read_text(encoding="utf-8")
    source = source.replace("Vendor: Riyadh Analytics Company", "Vendor: nora@example.com")
    captured: dict[str, str] = {}

    with ContractGuardService(isolated_settings) as service:
        def fake_generate(*, system: str, user: str, temperature: float = 0.0) -> str:
            captured["system"] = system
            captured["user"] = user
            return "The audit completed with a low risk rating and no detected policy deviations."

        monkeypatch.setattr(service.reasoner, "generate", fake_generate)
        state = service.start(
            AuditStartRequest(
                thread_id="redacted-llm-context",
                request_text="Audit this contract and produce an executive summary.",
                contract_text=source,
            )
        )

    assert state["status"] == "completed"
    assert "nora@example.com" not in captured["user"]
    assert "[REDACTED_EMAIL]" in captured["user"]
    parsed = json.loads(captured["user"])
    assert all("contract_excerpt" not in finding for finding in parsed["findings"])
