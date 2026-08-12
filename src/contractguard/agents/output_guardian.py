"""Output Guardian Agent: executable output/data-protection specialist."""
from __future__ import annotations

from typing import Any

from ..guardrails import OutputGuardrail
from .base import BaseAgent
from .rendering import render_report_markdown


class OutputGuardianAgent(BaseAgent):
    def __init__(self, *args, output_guardrail: OutputGuardrail | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.output_guardrail = output_guardrail or OutputGuardrail()

    def run(self, state: dict[str, Any]) -> None:
        result = self.output_guardrail.enforce(state.get("report") or {})
        state["output_valid"] = bool(result["valid"])
        state["output_feedback"] = result["feedback"]
        state["pii_redactions"] = int(result["redactions"])
        state["output_guardrail_enforced"] = True
        if result["valid"]:
            state["report"] = result["report"]
            state["final_markdown"] = render_report_markdown(result["report"])
            self.send(
                state,
                recipient="Artifact Storage Agent",
                message_type="result",
                content=f"OutputGuardrail.enforce passed; {result['redactions']} PII item(s) were masked.",
                payload={"categories": result["categories"]},
            )
        else:
            self.observability.record_guardrail(
                "output_validation", state["thread_id"], result["feedback"]
            )
            self.send(
                state,
                recipient="Report Writer Agent",
                message_type="critique",
                content=result["feedback"],
                payload={"revision": state.get("report_revision_count", 0)},
            )
