"""Document Analyst Agent: contract ingestion and clause extraction specialist."""
from __future__ import annotations

import re
from typing import Any

from .base import BaseAgent

class DocumentAnalystAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        output, observation = self.call_tool(
            state,
            tool_name="read_contract",
            arguments={
                "contract_path": state.get("contract_path"),
                "contract_text": state.get("contract_text_input"),
            },
            rationale="The document must be converted into trusted text before clause-level analysis.",
        )
        if observation["status"] != "success":
            raise RuntimeError(observation["summary"])
        state["contract_text"] = output["text"]
        state["sanitized_contract_text"] = output["text"]

        clauses, clause_observation = self.call_tool(
            state,
            tool_name="extract_contract_clauses",
            arguments={"contract_text": output["text"]},
            rationale="Structured clauses are required so specialist agents can search the right policy domains.",
        )
        if clause_observation["status"] != "success":
            raise RuntimeError(clause_observation["summary"])
        state["clauses"] = clauses
        state["contract_metadata"] = self._extract_metadata(output["text"])
        self.send(
            state,
            recipient="Policy Research Agent",
            message_type="handoff",
            content=f"Extracted {len(clauses)} clauses and contract metadata.",
            payload={"metadata": state["contract_metadata"], "topics": sorted({c["topic"] for c in clauses})},
        )

    @staticmethod
    def _extract_metadata(text: str) -> dict[str, Any]:
        vendor_match = re.search(r"(?:Vendor|Supplier|Provider)\s*:\s*([^\n]+)", text, re.I)
        value_match = re.search(
            r"(?:Contract\s+Value|Total\s+Value|Value)\s*:\s*(?:SAR\s*)?([\d,]+(?:\.\d+)?)",
            text,
            re.I,
        )
        vendor = vendor_match.group(1).strip() if vendor_match else "Unknown Vendor"
        value = float(value_match.group(1).replace(",", "")) if value_match else 0.0
        return {"vendor_name": vendor, "contract_value_sar": value}
