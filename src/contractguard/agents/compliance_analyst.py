"""Compliance Analyst Agent: clause-to-policy comparison specialist."""
from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Iterable

from ..models import Finding
from .base import BaseAgent, truncate_text


def _count_by(items: Iterable[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in items:
        counts[str(item.get(key, "unknown"))] += 1
    return counts

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
                contract_excerpt=truncate_text(excerpt),
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
