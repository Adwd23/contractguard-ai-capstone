"""Input Security Agent: an independently instantiated security specialist."""
from __future__ import annotations

from typing import Any

from ..guardrails import GuardrailViolation, InputGuardrail
from .base import BaseAgent


class InputSecurityAgent(BaseAgent):
    """Runs the enforced prompt-injection boundary before any tool-capable node."""

    def __init__(self, *args, input_guardrail: InputGuardrail | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.input_guardrail = input_guardrail or InputGuardrail()

    def run(self, state: dict[str, Any]) -> None:
        try:
            result = self.input_guardrail.enforce(
                user_input=state.get("request_text", ""),
                document_text=state.get("contract_text_input", "") or "",
                contract_path=state.get("contract_path"),
            )
        except GuardrailViolation as exc:
            state["input_blocked"] = True
            state["blocked_reason"] = exc.reason
            state["guardrail_enforced"] = True
            state["guardrail_matches"] = exc.matches
            self.observability.record_guardrail(
                "input_prompt_injection", state["thread_id"], exc.reason
            )
            self.send(
                state,
                recipient="Coordinator Agent",
                message_type="security",
                content="InputGuardrail.enforce blocked the request before any function tool executed.",
                payload={"blocked": True, "reason": exc.reason, "matches": exc.matches},
            )
            return

        state["input_blocked"] = False
        state["blocked_reason"] = ""
        state["guardrail_enforced"] = True
        state["guardrail_matches"] = result["matches"]
        self.send(
            state,
            recipient="Coordinator Agent",
            message_type="security",
            content="InputGuardrail.enforce passed; execution may proceed to tool-capable agents.",
            payload={"blocked": False, "matches": result["matches"]},
        )
