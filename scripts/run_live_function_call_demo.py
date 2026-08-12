#!/usr/bin/env python3
"""Run one genuine provider-native function-calling audit and save safe evidence.

Configure one provider in the environment before running:

- ``LLM_PROVIDER=groq`` and ``GROQ_API_KEY``
- ``LLM_PROVIDER=openrouter`` and ``OPENROUTER_API_KEY``
- ``LLM_PROVIDER=gemini`` and ``GEMINI_API_KEY``

The script fails rather than silently claiming success when the provider falls back to
the offline schema router. API keys are never written to the evidence file.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from contractguard.config import Settings  # noqa: E402
from contractguard.models import AuditStartRequest  # noqa: E402
from contractguard.service import ContractGuardService  # noqa: E402


def main() -> int:
    settings = Settings.from_env(PROJECT_ROOT)
    with tempfile.TemporaryDirectory(prefix="contractguard-live-") as temp_dir:
        temp = Path(temp_dir)
        settings.checkpoint_db = temp / "checkpoints.sqlite"
        settings.log_file = temp / "execution.jsonl"
        settings.metrics_file = temp / "metrics.prom"
        settings.artifact_dir = temp / "artifacts"
        settings.minio_endpoint = None
        settings.ensure_directories()

        service = ContractGuardService(settings)
        if not service.reasoner.enabled:
            service.close()
            raise SystemExit(
                "No live provider credential is configured. Set LLM_PROVIDER and the matching API key."
            )

        thread_id = f"live-tool-{uuid4().hex[:10]}"
        state = service.start(
            AuditStartRequest(
                thread_id=thread_id,
                request_text=(
                    "Audit this contract and let the Policy Research Agent choose its "
                    "registered search function through native function calling."
                ),
                contract_path=str(PROJECT_ROOT / "data" / "samples" / "vendor_contract_low_risk.txt"),
            )
        )
        service.close()

        live_calls = [call for call in state["tool_calls"] if call.get("used_live_llm")]
        if state.get("live_llm_tool_call_count", 0) < 1 or not live_calls:
            raise SystemExit(
                "The provider did not complete a native function call; no live evidence was written."
            )

        observations = {item["call_id"]: item for item in state["tool_observations"]}
        evidence = {
            "project": "ContractGuard AI",
            "thread_id": thread_id,
            "status": state["status"],
            "provider": service.reasoner.provider,
            "model": service.reasoner.model,
            "live_llm_tool_call_count": state["live_llm_tool_call_count"],
            "reasoner_modes": state["reasoner_modes"],
            "function_calls": [
                {
                    "call_id": call["call_id"],
                    "agent": call["agent"],
                    "tool_name": call["tool_name"],
                    "arguments": call["arguments"],
                    "decision_source": call["decision_source"],
                    "protocol": call["protocol"],
                    "model_provider": call["model_provider"],
                    "model_name": call["model_name"],
                    "observation": observations.get(call["call_id"], {}),
                }
                for call in live_calls
            ],
            "api_key_persisted": False,
        }
        output = PROJECT_ROOT / "evidence" / "06_live_llm_function_call.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        print(output)
        print(
            f"Captured {len(live_calls)} provider-native function call(s) "
            f"from {evidence['provider']}/{evidence['model']}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
