"""Role-specialized agents that communicate through structured shared state."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from pypdf import PdfReader

from .config import Settings
from .guardrails import mask_object, output_guardrail, scan_prompt_injection
from .llm import AgentReasoner
from .models import AgentMessage, Finding, PlanStep, ToolCall
from .observability import Observability
from .tools import ToolRegistry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(state: dict[str, Any], key: str, value: Any) -> None:
    state.setdefault(key, []).append(value)


def _truncate(text: str, limit: int = 280) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


class AgentToolPermissionError(PermissionError):
    """Raised when a specialist agent attempts a function outside its allow-list."""


class BaseAgent:
    def __init__(
        self,
        name: str,
        role: str,
        tools: ToolRegistry,
        observability: Observability,
        allowed_tools: set[str] | None = None,
    ):
        self.name = name
        self.role = role
        self.tools = tools
        self.observability = observability
        self.allowed_tools = frozenset(allowed_tools or set())

    def send(
        self,
        state: dict[str, Any],
        *,
        recipient: str,
        message_type: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,  # type: ignore[arg-type]
            content=content,
            payload=payload or {},
        )
        _append(state, "agent_messages", message.model_dump(mode="json"))
        self.observability.log(
            "agent_message",
            thread_id=state["thread_id"],
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            content=content,
        )

    def call_tool(
        self,
        state: dict[str, Any],
        *,
        tool_name: str,
        arguments: dict[str, Any],
        rationale: str,
        decision_source: str = "workflow",
        protocol: str = "mcp_json_schema",
        model_provider: str | None = None,
        model_name: str | None = None,
        used_live_llm: bool = False,
    ) -> tuple[Any, dict[str, Any]]:
        if tool_name not in self.allowed_tools:
            self.observability.log(
                "tool_permission_denied",
                level="warning",
                thread_id=state.get("thread_id"),
                agent=self.name,
                tool=tool_name,
                allowed_tools=sorted(self.allowed_tools),
            )
            raise AgentToolPermissionError(
                f"Agent '{self.name}' is not authorized to call tool '{tool_name}'"
            )

        call = ToolCall(
            agent=self.name,
            tool_name=tool_name,
            arguments=arguments,
            rationale=rationale,
            decision_source=decision_source,  # type: ignore[arg-type]
            protocol=protocol,  # type: ignore[arg-type]
            model_provider=model_provider,
            model_name=model_name,
            used_live_llm=used_live_llm,
        )
        call_dict = call.model_dump(mode="json")
        _append(state, "tool_calls", call_dict)
        if used_live_llm:
            state["live_llm_tool_call_count"] = int(state.get("live_llm_tool_call_count", 0)) + 1
        modes = state.setdefault("reasoner_modes", [])
        if decision_source not in modes:
            modes.append(decision_source)
        if decision_source != "workflow":
            state["reasoner_mode"] = decision_source
        _append(
            state,
            "decision_trace",
            {
                "pattern": "ReAct",
                # This is a concise, user-auditable rationale—not hidden chain-of-thought.
                "thought": rationale,
                "decision_summary": rationale,
                "decision_source": decision_source,
                "protocol": protocol,
                "model_provider": model_provider,
                "model_name": model_name,
                "used_live_llm": used_live_llm,
                "action": {"tool": tool_name, "arguments": arguments, "call_id": call.call_id},
                "timestamp": call.timestamp,
            },
        )
        output, observation = self.tools.call(call, thread_id=state["thread_id"])
        observation_dict = observation.model_dump(mode="json")
        _append(state, "tool_observations", observation_dict)
        _append(
            state,
            "decision_trace",
            {
                "pattern": "ReAct",
                "observation": observation.summary,
                "status": observation.status,
                "call_id": call.call_id,
                "timestamp": observation.timestamp,
            },
        )
        return output, observation_dict


class InputSecurityAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        # Inspect both the direct user request and the uploaded document before any
        # registered function tool is allowed to run. This catches direct and indirect
        # prompt injection while preserving the evidence that zero tools were called.
        raw_document = state.get("contract_text_input", "") or ""
        contract_path = state.get("contract_path")
        if contract_path and not raw_document:
            raw_document = self._read_untrusted_preview(contract_path)
        result = scan_prompt_injection(
            state.get("request_text", ""),
            raw_document,
        )
        state["input_blocked"] = bool(result["blocked"])
        state["blocked_reason"] = str(result["reason"])
        if result["blocked"]:
            self.observability.record_guardrail("input_prompt_injection", state["thread_id"], result["reason"])
            self.send(
                state,
                recipient="Coordinator Agent",
                message_type="security",
                content="Input blocked before any document or policy tool was allowed to run.",
                payload=result,
            )
        else:
            self.send(
                state,
                recipient="Coordinator Agent",
                message_type="security",
                content="Input guardrail passed; execution may proceed.",
                payload={"matches": result["matches"]},
            )

    @staticmethod
    def _read_untrusted_preview(contract_path: str) -> str:
        path = Path(contract_path).expanduser().resolve()
        if not path.exists() or not path.is_file() or path.stat().st_size > 10_000_000:
            return ""
        try:
            if path.suffix.lower() == ".pdf":
                reader = PdfReader(str(path))
                return "\n".join((page.extract_text() or "") for page in reader.pages)[:250_000]
            if path.suffix.lower() in {".txt", ".md"}:
                return path.read_text(encoding="utf-8")[:250_000]
        except Exception:
            return ""
        return ""


class CoordinatorAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        source = "PDF/file" if state.get("contract_path") else "inline text"
        steps = [
            PlanStep(step_id="P1", owner="Document Analyst Agent", objective=f"Ingest and parse the {source} contract"),
            PlanStep(step_id="P2", owner="Policy Research Agent", objective="Retrieve evidence from corporate policy tools"),
            PlanStep(step_id="P3", owner="Compliance Analyst Agent", objective="Compare clauses with policy evidence and produce findings"),
            PlanStep(step_id="P4", owner="Quality Reviewer Agent", objective="Critique evidence coverage and re-plan if insufficient"),
            PlanStep(step_id="P5", owner="Security Reviewer Agent", objective="Calculate risk and route high-risk actions to a human"),
            PlanStep(step_id="P6", owner="Report Writer Agent", objective="Generate and validate the compliance report"),
            PlanStep(step_id="P7", owner="Artifact Storage Agent", objective="Persist report and audit artifacts"),
        ]
        state["plan"] = [step.model_dump(mode="json") for step in steps]
        self.send(
            state,
            recipient="Document Analyst Agent",
            message_type="plan",
            content="Plan-and-Execute plan created with seven bounded steps.",
            payload={"steps": state["plan"]},
        )


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


class PolicyResearchAgent(BaseAgent):
    TOPIC_QUERIES = {
        "data_protection": "data residency Saudi Arabia subprocessors consent breach notification privacy",
        "security": "ISO 27001 encryption access control audit penetration testing security",
        "payment": "invoice payment terms net 30 procurement approval threshold SAR",
        "liability": "liability cap indemnity damages twelve months fees",
        "termination": "termination for convenience notice automatic renewal",
        "governing_law": "governing law Kingdom of Saudi Arabia jurisdiction",
        "service_levels": "service levels uptime SLA availability credits",
        "general": "vendor contract compliance mandatory clauses",
    }

    def __init__(
        self,
        name: str,
        role: str,
        tools: ToolRegistry,
        observability: Observability,
        reasoner: AgentReasoner,
        allowed_tools: set[str] | None = None,
    ) -> None:
        super().__init__(name, role, tools, observability, allowed_tools=allowed_tools)
        self.reasoner = reasoner

    def run(self, state: dict[str, Any]) -> None:
        topics = sorted({clause.get("topic", "general") for clause in state.get("clauses", [])})
        queries = [
            {"topic": topic, "query": self.TOPIC_QUERIES.get(topic, self.TOPIC_QUERIES["general"])}
            for topic in topics
        ]
        queries.extend(state.get("additional_policy_queries", []))
        state["policy_queries"] = queries
        attempt = int(state.get("policy_retry_count", 0))
        evidence: list[dict[str, Any]] = []
        state["policy_search_error"] = ""

        tool_name = "search_policy_knowledge_base"
        for index, item in enumerate(queries):
            candidate_arguments = {
                "query": item["query"],
                "topic": item["topic"],
                "top_k": 2,
                "attempt": attempt,
                "simulate_primary_failure": bool(state.get("flags", {}).get("simulate_primary_failure"))
                and index == 0,
            }
            selection = self.reasoner.select_tool(
                agent_name=self.name,
                task=(
                    "Retrieve authoritative corporate policy evidence for the contract "
                    f"topic '{item['topic']}' using the registered function tools."
                ),
                context={
                    "topic": item["topic"],
                    "recommended_query": item["query"],
                    "required_result": "ranked policy excerpts with policy names and sections",
                    "retry_attempt": attempt,
                },
                tools=self.tools.describe({"search_policy_knowledge_base"}),
                candidate_arguments={"search_policy_knowledge_base": candidate_arguments},
                locked_arguments={
                    "search_policy_knowledge_base": {
                        "topic",
                        "attempt",
                        "simulate_primary_failure",
                    }
                },
            )
            decision_source = (
                "llm_function_call" if selection.used_live_llm else "offline_schema_router"
            )
            output, observation = self.call_tool(
                state,
                tool_name=selection.tool_name,
                arguments=selection.arguments,
                rationale=selection.rationale,
                decision_source=decision_source,
                protocol=(
                    "provider_native_function_call"
                    if selection.used_live_llm
                    else "mcp_json_schema"
                ),
                model_provider=selection.provider,
                model_name=selection.model,
                used_live_llm=selection.used_live_llm,
            )
            if observation["status"] != "success":
                state["policy_search_error"] = observation["summary"]
                state["policy_retry_count"] = attempt + 1
                self.send(
                    state,
                    recipient="Coordinator Agent",
                    message_type="status",
                    content="Policy tool failed; requesting graph retry.",
                    payload={"attempt": attempt + 1, "error": observation["summary"]},
                )
                return
            evidence.extend(output)

        deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
        for item in evidence:
            key = (item["policy_name"], item["section"], item["topic"])
            previous = deduped.get(key)
            if previous is None or item["score"] > previous["score"]:
                deduped[key] = item
        state["policy_evidence"] = list(deduped.values())
        state["policy_search_error"] = ""
        self.send(
            state,
            recipient="Compliance Analyst Agent",
            message_type="result",
            content=f"Retrieved {len(state['policy_evidence'])} policy evidence records.",
            payload={"topics": sorted({item["topic"] for item in state["policy_evidence"]})},
        )


class ComplianceAnalystAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        clauses = state.get("clauses", [])
        metadata = state.get("contract_metadata", {})
        findings: list[dict[str, Any]] = []
        by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for clause in clauses:
            by_topic[clause.get("topic", "general")].append(clause)

        def evidence_ref(topic: str) -> str:
            candidates = [item for item in state.get("policy_evidence", []) if item.get("topic") == topic]
            if not candidates:
                candidates = state.get("policy_evidence", [])[:1]
            if not candidates:
                return "No policy evidence retrieved"
            item = max(candidates, key=lambda value: value.get("score", 0))
            return f"{item['policy_name']} — {item['section']}"

        def add(
            topic: str,
            title: str,
            severity: str,
            excerpt: str,
            recommendation: str,
            confidence: float = 0.92,
        ) -> None:
            finding = Finding(
                finding_id=f"F-{len(findings) + 1:02d}",
                topic=topic,
                title=title,
                severity=severity,  # type: ignore[arg-type]
                contract_excerpt=_truncate(excerpt),
                policy_reference=evidence_ref(topic),
                recommendation=recommendation,
                confidence=confidence,
            )
            findings.append(finding.model_dump(mode="json"))

        data_text = " ".join(item["text"] for item in by_topic.get("data_protection", [])).lower()
        if any(term in data_text for term in ("outside the kingdom", "any jurisdiction", "global locations", "outside saudi")):
            add(
                "data_protection",
                "Unrestricted cross-border data transfer",
                "high",
                data_text,
                "Require Saudi data residency or a documented transfer mechanism and prior written approval.",
            )
        if "subprocessor" in data_text and any(term in data_text for term in ("without consent", "without notice", "at its discretion")):
            add(
                "data_protection",
                "Subprocessor changes lack customer consent",
                "high",
                data_text,
                "Add prior notification, objection rights, and flow-down security obligations for subprocessors.",
            )
        if "breach" not in data_text or any(term in data_text for term in ("72 hours", "seventy-two", "commercially reasonable")):
            add(
                "data_protection",
                "Breach notification is missing or slower than policy",
                "high" if "72" in data_text else "medium",
                data_text or "No breach-notification clause detected.",
                "Require notification within 24 hours of suspected or confirmed breach discovery.",
                0.88,
            )

        security_text = " ".join(item["text"] for item in by_topic.get("security", [])).lower()
        security_negation = any(
            term in security_text
            for term in (
                "no iso 27001",
                "no encryption",
                "encryption commitment",
                "not guaranteed",
                "no customer audit",
            )
        )
        security_positive = (
            "iso 27001" in security_text
            and "encrypt" in security_text
            and any(term in security_text for term in ("audit right", "penetration testing", "penetration-test"))
        )
        if not security_positive or security_negation:
            add(
                "security",
                "Security baseline is incomplete",
                "high" if security_negation else "medium",
                security_text or "No dedicated security clause detected.",
                "Require ISO 27001-equivalent controls, encryption in transit/at rest, audit rights, and annual testing.",
                0.9 if security_negation else 0.86,
            )

        payment_text = " ".join(item["text"] for item in by_topic.get("payment", [])).lower()
        payment_days = [int(value) for value in re.findall(r"(\d{1,3})\s+days", payment_text)]
        if payment_days and min(payment_days) < 30:
            add(
                "payment",
                "Accelerated payment terms",
                "medium",
                payment_text,
                "Change payment terms to Net 30 or longer and condition payment on accepted deliverables.",
            )

        liability_text = " ".join(item["text"] for item in by_topic.get("liability", [])).lower()
        if any(term in liability_text for term in ("one month", "1 month", "fees paid in the preceding month")):
            add(
                "liability",
                "Liability cap is below corporate minimum",
                "high",
                liability_text,
                "Increase the vendor liability cap to at least twelve months of fees, with carve-outs for privacy and security.",
            )
        elif not liability_text:
            add(
                "liability",
                "Liability allocation is absent",
                "medium",
                "No liability clause detected.",
                "Add a balanced liability cap and indemnities for confidentiality, IP, privacy, and security breaches.",
                0.82,
            )

        termination_text = " ".join(item["text"] for item in by_topic.get("termination", [])).lower()
        if any(term in termination_text for term in ("90 days", "ninety days", "three years", "3 years")) or "for convenience" not in termination_text:
            add(
                "termination",
                "Termination and renewal terms are restrictive",
                "medium",
                termination_text or "No termination-for-convenience clause detected.",
                "Add termination for convenience on 30 days' notice and limit automatic renewal to one-year periods.",
                0.9,
            )

        law_text = " ".join(item["text"] for item in by_topic.get("governing_law", [])).lower()
        ksa_law_positive = any(
            term in law_text
            for term in (
                "governed by the laws of the kingdom of saudi arabia",
                "laws of the kingdom of saudi arabia",
                "saudi courts have jurisdiction",
            )
        )
        foreign_law_signal = any(
            term in law_text
            for term in ("delaware", "england and wales", "new york", "outside saudi arabia", "foreign courts")
        )
        if law_text and (foreign_law_signal or not ksa_law_positive):
            add(
                "governing_law",
                "Non-KSA governing law",
                "high",
                law_text,
                "Use the laws and courts of the Kingdom of Saudi Arabia unless Legal approves an exception.",
            )

        service_text = " ".join(item["text"] for item in by_topic.get("service_levels", [])).lower()
        if service_text and (
            any(term in service_text for term in ("98.0 percent", "98 percent", "98%"))
            or "no service credits" in service_text
        ):
            add(
                "service_levels",
                "Service levels are below the enterprise standard",
                "medium",
                service_text,
                "Require at least 99.9% monthly availability, service credits, and chronic-failure termination rights.",
                0.93,
            )

        value = float(metadata.get("contract_value_sar", 0.0) or 0.0)
        if value >= 500_000:
            add(
                "payment",
                "High-value procurement requires human approval",
                "high",
                f"Contract Value: SAR {value:,.2f}",
                "Route the contract to Procurement and Legal for explicit approval before signature.",
                1.0,
            )

        state["findings"] = findings
        self.send(
            state,
            recipient="Quality Reviewer Agent",
            message_type="result",
            content=f"Generated {len(findings)} compliance findings from contract clauses and policy evidence.",
            payload={"severities": dict(_count_by(findings, "severity"))},
        )


class QualityReviewerAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        required_topics = {
            clause.get("topic", "general")
            for clause in state.get("clauses", [])
            if clause.get("topic", "general") != "general"
        }
        evidence_topics = {item.get("topic") for item in state.get("policy_evidence", [])}
        covered = required_topics.intersection(evidence_topics)
        score = len(covered) / max(len(required_topics), 1)

        if state.get("flags", {}).get("simulate_quality_retry") and int(state.get("quality_retry_count", 0)) == 0:
            score = min(score, 0.5)

        state["quality_score"] = round(score, 3)
        missing = sorted(required_topics - evidence_topics)
        can_retry = int(state.get("quality_retry_count", 0)) < int(state.get("max_quality_retries", 1))
        state["needs_more_research"] = score < 0.75 and can_retry
        state["additional_policy_queries"] = [
            {
                "topic": topic,
                "query": f"mandatory corporate contract policy requirements for {topic.replace('_', ' ')}",
            }
            for topic in missing
        ]
        if state["needs_more_research"] and not state["additional_policy_queries"]:
            state["additional_policy_queries"] = [
                {"topic": "general", "query": "mandatory vendor contract compliance clauses and exceptions"}
            ]

        self.send(
            state,
            recipient="Coordinator Agent",
            message_type="critique",
            content=(
                f"Evidence coverage score is {score:.0%}; "
                + ("re-planning targeted research." if state["needs_more_research"] else "quality gate passed.")
            ),
            payload={"missing_topics": missing, "quality_score": state["quality_score"]},
        )


class SecurityReviewerAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        role: str,
        tools: ToolRegistry,
        observability: Observability,
        settings: Settings,
        allowed_tools: set[str] | None = None,
    ):
        super().__init__(name, role, tools, observability, allowed_tools=allowed_tools)
        self.settings = settings

    def run(self, state: dict[str, Any]) -> None:
        output, observation = self.call_tool(
            state,
            tool_name="calculate_contract_risk",
            arguments={
                "findings": state.get("findings", []),
                "contract_value_sar": state.get("contract_metadata", {}).get("contract_value_sar", 0.0),
                "approval_risk_threshold": self.settings.approval_risk_threshold,
                "approval_value_threshold_sar": self.settings.approval_value_threshold_sar,
            },
            rationale="Risk and value thresholds determine whether autonomous execution must stop for human approval.",
        )
        if observation["status"] != "success":
            raise RuntimeError(observation["summary"])
        state.update(output)
        state["approval_status"] = "pending" if output["approval_required"] else "not_required"
        self.send(
            state,
            recipient="Coordinator Agent",
            message_type="security",
            content=(
                f"Risk classified as {output['risk_level']} ({output['risk_score']}/100). "
                + ("Human approval required." if output["approval_required"] else "No approval interrupt required.")
            ),
            payload=output,
        )


class ReportWriterAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        role: str,
        tools: ToolRegistry,
        observability: Observability,
        reasoner: AgentReasoner,
        allowed_tools: set[str] | None = None,
    ):
        super().__init__(name, role, tools, observability, allowed_tools=allowed_tools)
        self.reasoner = reasoner

    def run(self, state: dict[str, Any]) -> None:
        findings = state.get("findings", [])
        metadata = state.get("contract_metadata", {})
        fallback_summary = self._fallback_summary(state)
        # Never transmit raw contract excerpts or direct identifiers to an optional
        # external model. Only the minimum fields required for the summary are sent.
        safe_findings = [
            {
                key: item.get(key)
                for key in (
                    "finding_id",
                    "topic",
                    "title",
                    "severity",
                    "policy_reference",
                    "recommendation",
                    "confidence",
                )
            }
            for item in findings
        ]
        llm_context, context_redactions, context_categories = mask_object(
            {
                "vendor": metadata.get("vendor_name"),
                "value_sar": metadata.get("contract_value_sar"),
                "risk_score": state.get("risk_score"),
                "risk_level": state.get("risk_level"),
                "findings": safe_findings,
            }
        )
        if context_redactions:
            self.observability.log(
                "llm_context_redacted",
                thread_id=state["thread_id"],
                agent=self.name,
                redactions=context_redactions,
                categories=sorted(set(context_categories)),
            )
        llm_summary = self.reasoner.generate(
            system=(
                "You are a senior Saudi enterprise contract-compliance reviewer. "
                "Write one concise executive-summary paragraph. Do not invent facts."
            ),
            user=json.dumps(llm_context, ensure_ascii=False),
        )
        recommendations = [item["recommendation"] for item in findings]
        if not recommendations:
            recommendations = ["Proceed under the standard approved contract template and retain the audit record."]

        report: dict[str, Any] = {
            "report_id": f"CGA-{state['thread_id']}",
            "thread_id": state["thread_id"],
            "generated_at": _now(),
            "vendor_name": metadata.get("vendor_name", "Unknown Vendor"),
            "contract_value_sar": float(metadata.get("contract_value_sar", 0.0) or 0.0),
            "executive_summary": llm_summary or fallback_summary,
            "risk_score": int(state.get("risk_score", 0)),
            "risk_level": state.get("risk_level", "LOW"),
            "findings": findings,
            "recommendations": list(dict.fromkeys(recommendations)),
            "approval_status": state.get("approval_status", "not_required"),
            "approval_comment": state.get("approval_comment", ""),
            "evidence_count": len(state.get("policy_evidence", [])),
            "pii_redactions": 0,
            "agent_trace_summary": [
                f"{message['sender']} → {message['recipient']}: {message['content']}"
                for message in state.get("agent_messages", [])[-12:]
            ],
        }

        if (
            state.get("flags", {}).get("simulate_output_validation_failure")
            and int(state.get("report_revision_count", 0)) == 0
        ):
            report.pop("recommendations", None)

        state["report"] = report
        self.send(
            state,
            recipient="Output Guardian Agent",
            message_type="handoff",
            content=f"Report draft revision {state.get('report_revision_count', 0)} is ready for validation.",
            payload={"report_id": report["report_id"]},
        )

    @staticmethod
    def _fallback_summary(state: dict[str, Any]) -> str:
        count = len(state.get("findings", []))
        return (
            f"The multi-agent audit identified {count} compliance finding(s) and assigned a "
            f"{state.get('risk_level', 'LOW')} risk rating of {state.get('risk_score', 0)}/100. "
            "The result was produced from clause extraction, policy retrieval, specialist review, "
            "security routing, and output validation rather than a single prompt."
        )


class OutputGuardianAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        result = output_guardrail(state.get("report") or {})
        state["output_valid"] = bool(result["valid"])
        state["output_feedback"] = result["feedback"]
        state["pii_redactions"] = int(result["redactions"])
        if result["valid"]:
            state["report"] = result["report"]
            state["final_markdown"] = render_report_markdown(result["report"])
            self.send(
                state,
                recipient="Artifact Storage Agent",
                message_type="result",
                content=f"Output schema passed and {result['redactions']} PII item(s) were masked.",
                payload={"categories": result["categories"]},
            )
        else:
            self.observability.record_guardrail("output_validation", state["thread_id"], result["feedback"])
            self.send(
                state,
                recipient="Report Writer Agent",
                message_type="critique",
                content=result["feedback"],
                payload={"revision": state.get("report_revision_count", 0)},
            )


class ArtifactStorageAgent(BaseAgent):
    def run(self, state: dict[str, Any]) -> None:
        metadata = {
            "thread_id": state["thread_id"],
            "status": state.get("status"),
            "risk_score": state.get("risk_score"),
            "risk_level": state.get("risk_level"),
            "quality_score": state.get("quality_score"),
            "node_history": state.get("node_history"),
            "tool_calls": len(state.get("tool_calls", [])),
            "policy_retries": state.get("policy_retry_count", 0),
            "report_revisions": state.get("report_revision_count", 0),
            "pii_redactions": state.get("pii_redactions", 0),
        }
        output, observation = self.call_tool(
            state,
            tool_name="store_report_artifact",
            arguments={
                "thread_id": state["thread_id"],
                "markdown": state["final_markdown"],
                "metadata": metadata,
            },
            rationale="The validated result and audit metadata must be stored as a production artifact.",
        )
        if observation["status"] != "success":
            raise RuntimeError(observation["summary"])
        state["artifact_uri"] = output["uri"]
        state["storage_backend"] = output["backend"]
        self.send(
            state,
            recipient="Coordinator Agent",
            message_type="status",
            content=f"Report persisted using {output['backend']}.",
            payload=output,
        )


def render_report_markdown(report: dict[str, Any]) -> str:
    findings = report.get("findings", [])
    rows = [
        "| ID | Severity | Topic | Finding | Policy reference |",
        "|---|---|---|---|---|",
    ]
    for finding in findings:
        rows.append(
            "| {id} | {severity} | {topic} | {title} | {policy} |".format(
                id=finding["finding_id"],
                severity=finding["severity"].upper(),
                topic=finding["topic"].replace("_", " "),
                title=finding["title"].replace("|", "/"),
                policy=finding["policy_reference"].replace("|", "/"),
            )
        )
    recommendations = "\n".join(f"{index}. {item}" for index, item in enumerate(report["recommendations"], 1))
    trace = "\n".join(f"- {item}" for item in report.get("agent_trace_summary", []))
    findings_table = "\n".join(rows) if findings else "No policy deviations were detected."
    finding_details = "\n\n".join(
        (
            f"### {item['finding_id']} — {item['title']}\n\n"
            f"- **Severity:** {item['severity'].upper()}\n"
            f"- **Topic:** {item['topic'].replace('_', ' ')}\n"
            f"- **Masked contract excerpt:** {item['contract_excerpt']}\n"
            f"- **Policy reference:** {item['policy_reference']}\n"
            f"- **Recommendation:** {item['recommendation']}"
        )
        for item in findings
    )
    return f"""# ContractGuard AI Compliance Report

**Report ID:** {report['report_id']}  
**Thread ID:** {report['thread_id']}  
**Generated:** {report['generated_at']}  
**Vendor:** {report['vendor_name']}  
**Contract value:** SAR {report['contract_value_sar']:,.2f}  
**Risk:** {report['risk_level']} ({report['risk_score']}/100)  
**Approval:** {report['approval_status']}  

## Executive Summary

{report['executive_summary']}

## Compliance Findings

{findings_table}

## Detailed Findings and Masked Evidence

{finding_details or 'No detailed findings.'}

## Recommendations

{recommendations}

## Human Approval Record

{report.get('approval_comment') or 'No human comment was supplied.'}

## Evidence and Data Protection

- Policy evidence records: {report['evidence_count']}
- PII items masked: {report['pii_redactions']}

## Agent Handoff Trace

{trace or '- No messages recorded.'}
"""


def _count_by(items: Iterable[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[str(item.get(key, "unknown"))] += 1
    return counts
